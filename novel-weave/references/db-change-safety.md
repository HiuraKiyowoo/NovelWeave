# Database change safety

Treat every DB write as a migration, even when it is one novel.

## 1. Search before insert

Search every relevant DB and staging output for the full title, original title, normalized title, and slug. Exact full-title/slug hits are stop conditions; partial keyword hits require manual confirmation.

Example read-only probe:

```sql
SELECT id, judul, judul_asli, slug
FROM novel
WHERE slug = :slug
   OR judul = :display_title
   OR judul_asli = :original_title;
```

Also inspect imported/quarantine DBs and `mtl/*.json`. Do not silently solve a collision by adding `(2)` to the slug.

## 2. Backup before any write

```bash
python scripts/backup-sqlite.py /path/to/naver.db --reason before-novel-import
```

The backup must be on the same device, have a timestamped name, and be reported before the write begins. Check it:

```bash
sqlite3 /path/to/naver.db 'PRAGMA integrity_check;'
```

If the check is not `ok`, stop. Do not repair a damaged DB as part of an import.

## 3. Stage and promote

1. import to a temporary/staging DB or staging table;
2. run duplicate, count, slug, text-integrity, and cover checks;
3. review the exact rows to be promoted;
4. back up production immediately before promotion;
5. promote one novel in one transaction;
6. run `PRAGMA integrity_check` and re-query the promoted slug.

Never write directly to production because a translation file says `selesai: true`.

## 4. Rollback record

Record: DB path, backup path, transaction time, slug, inserted IDs, row count, and validation output. If any validation fails, restore the backup or delete only the transaction's recorded IDs; never guess which rows belong to the run.
