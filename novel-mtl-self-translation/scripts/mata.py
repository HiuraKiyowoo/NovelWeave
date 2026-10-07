#!/usr/bin/env python3
"""Print ONE chapter in full for an eyes-on read (the eyes are the judge).

Per-chapter manual read-through is a standing order; this prints the whole
chapter plus cheap FINDER counts (quotes balanced? junk? glued words?) — the
counts only point, your eyes decide. Read the head AND the tail; a nav/watermark
block can sit in the MIDDLE, so also scan the body.

Usage:
    python3 mata.py <novel_id> <bab_nomor> [db_path]
"""
import sqlite3, re, sys

DB = sys.argv[3] if len(sys.argv) > 3 else "/root/WORKS/naver-server/naver.db"
NID, NOMOR = int(sys.argv[1]), int(sys.argv[2])
QB, QT = "\u201c", "\u201d"

c = sqlite3.connect(DB)
row = c.execute(
    "SELECT judul, teks FROM bab WHERE novel_id=? AND nomor=?", (NID, NOMOR)
).fetchone()
c.close()
if not row:
    sys.exit(f"BAB {NOMOR} novel {NID}: TIDAK ADA")
judul, t = row

print(f"### NOVEL {NID} · BAB {NOMOR}: {judul} · {len(t):,} aksara ###")
print(f"kutip tipografi: {t.count(QB)} buka / {t.count(QT)} tutup")
print(f"kutip lurus: {t.count(chr(34))}  |  spasi-sebelum-tanda: {len(re.findall(r' [.,?!]', t))}")
print(f"kutip berlipat (chain): {len(re.findall(r'[\u201c\u201d]{2,}', t))}")
junk = re.findall(r"ruidrive|trakteer|https?://|blog sederhana|function |//Error|@media|<div", t, re.I)
print(f"kotoran (watermark/URL/JS): {len(junk)} {sorted(set(junk))}")
print(f"kata nempel kkBB: {re.findall(r'[a-z]{2,}[A-Z][a-z]{2,}', t)[:8]}")
par = t.split("\n\n")
g = [(i, p) for i, p in enumerate(par) if p.count(QB) != p.count(QT)]
print(f"paragraf kutip ganjil: {len(g)}")
for i, p in g:
    # Print head AND tail of each odd paragraph — classify before repairing.
    # b=1 t=0 + next is narration -> closing quote lost; b=0 t=1 -> opening lost;
    # a matching pair of odd paragraphs = legit multi-paragraph dialog, leave it.
    print(f"  [{i}] b={p.count(QB)} t={p.count(QT)} | {p[:70]!r} ... {p[-22:]!r}")
print("=" * 64)
print(t)
