#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pasang-cover.py — bulk-normalise drop-in covers and register them in the DB.

The user often cannot supply covers one-at-a-time; they paste a batch of URLs or
save files into cover-asli/. This is the batch end of the cover workflow: it turns
every cover-asli/<id>.jpg into the served cover/<id>.webp at the archive ratio and
updates the novel row, so the missing-cover filter stops hiding those novels.

Usage:
    python3 pasang-cover.py 1385 1426 1695        # explicit ids
    python3 pasang-cover.py --semua               # every id present in cover-asli/

Edit BASE / DB / TW,TH / KUAL to match the archive. TW,TH must match the ratio the
existing covers actually use — measure first, do not assume 2:3 (see
references/mtl-cover-and-assets.md section 2).
"""
import sys, os
from PIL import Image
import sqlite3

BASE = "/root/WORKS/naver-server"
DB = f"{BASE}/naver.db"
TW, TH = 600, 840          # 5:7 ≈ 1.400, the archive's dominant ratio
KUAL = 88


def pasang(nid):
    src = f"{BASE}/cover-asli/{nid}.jpg"
    if not os.path.exists(src):
        return f"❌ berkas tidak ada: cover-asli/{nid}.jpg"
    try:
        im = Image.open(src).convert("RGB")
        w, h = im.size
        # scale so the TARGET box is fully covered, then trim centred — never letterbox
        skala = max(TW / w, TH / h)
        nw, nh = int(w * skala + 0.5), int(h * skala + 0.5)
        im2 = im.resize((nw, nh), Image.LANCZOS)
        x, y = (nw - TW) // 2, (nh - TH) // 2
        im2 = im2.crop((x, y, x + TW, y + TH))
        os.makedirs(f"{BASE}/cover", exist_ok=True)
        dst = f"{BASE}/cover/{nid}.webp"
        im2.save(dst, "WEBP", quality=KUAL, method=5)
        return f"✅ {nid}: {w}x{h} → {TW}x{TH} ({os.path.getsize(dst)//1024}KB)"
    except Exception as e:
        return f"❌ {nid}: {str(e)[:70]}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    if sys.argv[1] == "--semua":
        ids = sorted(int(f.split(".")[0]) for f in os.listdir(f"{BASE}/cover-asli")
                     if f.endswith(".jpg") and f.split(".")[0].isdigit())
    else:
        ids = [int(x) for x in sys.argv[1:]]

    c = sqlite3.connect(DB)
    ok = []
    for nid in ids:
        h = pasang(nid)
        print("  " + h)
        if h.startswith("✅"):
            c.execute("UPDATE novel SET cover_webp=?, cover_jpg=? WHERE id=?",
                      (f"cover/{nid}.webp", f"cover-asli/{nid}.jpg", nid))
            ok.append(nid)
    c.commit()
    print()
    print(f"  db: {len(ok)} novel dicatat punya cover")
    n_tanpa = c.execute("SELECT COUNT(*) FROM novel WHERE cover_webp IS NULL OR cover_webp=''").fetchone()[0]
    n_total = c.execute("SELECT COUNT(*) FROM novel").fetchone()[0]
    print(f"  total novel: {n_total} · masih tanpa cover: {n_tanpa}")
    # Verify the served file actually answers 200 — the row alone proves nothing.
    print(f"  → probe: curl -s -o /dev/null -w '%{{http_code}} %{{content_type}}\\n' http://127.0.0.1:8100/cover/<id>.webp")
    c.close()


if __name__ == "__main__":
    main()
