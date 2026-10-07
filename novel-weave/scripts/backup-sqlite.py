#!/usr/bin/env python3
"""Create a timestamped SQLite backup and verify both source and backup."""
from __future__ import annotations
import argparse
import datetime as dt
import shutil
import sqlite3
from pathlib import Path


def integrity(path: Path) -> str:
    with sqlite3.connect(path) as con:
        row = con.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "no result"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", type=Path)
    ap.add_argument("--reason", default="before-change")
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args()
    src = args.db.expanduser().resolve()
    if not src.is_file():
        ap.error(f"database not found: {src}")
    src_check = integrity(src)
    if src_check != "ok":
        raise SystemExit(f"STOP: source integrity_check={src_check!r}; no backup/import performed")
    out_dir = (args.out_dir or src.parent).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = out_dir / f"{src.stem}.bak-{args.reason}-{stamp}{src.suffix}"
    shutil.copy2(src, dst)
    dst_check = integrity(dst)
    if dst_check != "ok":
        raise SystemExit(f"STOP: backup integrity_check={dst_check!r}: {dst}")
    print(f"source: {src}")
    print(f"backup: {dst}")
    print("source_integrity: ok")
    print("backup_integrity: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
