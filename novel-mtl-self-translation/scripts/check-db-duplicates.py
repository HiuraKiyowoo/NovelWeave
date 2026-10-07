#!/usr/bin/env python3
"""Read-only duplicate/slug preflight across SQLite databases."""
from __future__ import annotations
import argparse
import re
import sqlite3
from pathlib import Path

NAME_COLS = {"slug", "judul", "judul_asli", "title", "name", "original_title"}

def ident(x: str) -> str:
    return '"' + x.replace('"', '""') + '"'

def norm(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", x.casefold()).strip()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", nargs="+", type=Path)
    ap.add_argument("--slug")
    ap.add_argument("--title")
    args = ap.parse_args()
    terms = [x for x in (args.slug, args.title) if x]
    if not terms:
        ap.error("provide --slug and/or --title")
    hits = 0
    for db in args.db:
        db = db.expanduser().resolve()
        if not db.is_file():
            print(f"SKIP missing: {db}")
            continue
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                cols = [r[1] for r in con.execute(f"PRAGMA table_info({ident(table)})")]
                candidates = [c for c in cols if c.casefold() in NAME_COLS]
                if not candidates:
                    continue
                selected = ', '.join(ident(c) for c in cols[:12])
                where, params = [], []
                for col in candidates:
                    for term in terms:
                        where.append(f"lower({ident(col)}) = lower(?) OR lower({ident(col)}) LIKE lower(?)")
                        params.extend([term, f"%{term}%"])
                sql = f"SELECT rowid, {selected} FROM {ident(table)} WHERE " + " OR ".join(f"({w})" for w in where) + " LIMIT 50"
                for row in con.execute(sql, params):
                    hits += 1
                    print(f"HIT\t{db}\t{table}\t{row}")
    print(f"matches: {hits}")
    return 2 if hits else 0

if __name__ == "__main__":
    raise SystemExit(main())
