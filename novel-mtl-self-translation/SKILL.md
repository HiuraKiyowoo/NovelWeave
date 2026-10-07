---
name: novel-mtl-self-translation
description: "Safe, resumable machine-translation workflow for rights-cleared novels: rights check, DB preflight, metadata/source verification, adaptive parsing, quota-aware translation, QA, staging, and controlled promotion."
license: MIT
metadata:
  hermes:
    tags: [mtl, novel, translation, light-novel, pdf, epub, sqlite, staging, qa]
---

# Novel MTL — dispatcher workflow

Use this skill for translating a rights-cleared novel into Indonesian and loading it safely into a novel archive. Execute the phases in order. **A failed gate is a stop condition, not an invitation to improvise.** Keep source URLs, translator/group names, private provenance, and raw manuscripts out of public output.

## Decision tree

1. **Is the input already Indonesian or already a human translation?**
   - Yes → do **not** MTL. Follow `references/human-translation-flow.md`.
   - No → continue.
2. **Is the work a free official web novel or a print light novel/authorized file?**
   - Web novel → read `references/web-novel-raw-sources.md` and `references/web-vs-print.md`.
   - Print LN/EPUB/PDF → read `references/pdf-raw-extraction.md`, `references/epub-import.md`, and `references/web-vs-print.md` as applicable.
3. **Are the rights to transform and publish clear?**
   - No/unknown → STOP. Follow `references/safety-and-rights.md` and report the blocker.
4. **Does the work already exist in any DB or staging output?**
   - Exact/full-title or slug hit → STOP and review the existing record. A partial keyword hit is not a match until confirmed.

## The 14-phase flow

### 1. Intake and rights check

Identify the supplied file/URL, source language, work edition, and rights basis: owned, licensed, public-domain, explicitly authorized, or official author upload whose terms allow the intended use. Do not bypass DRM, paywalls, access controls, anti-bot systems, or rate limits. A reachable URL is not proof of publication permission. If the input is a third-party human translation, quarantine it; do not publish it without permission.

Read: `references/safety-and-rights.md`, and for an already translated input `references/human-translation-flow.md`.

### 2. Archive and DB preflight

Before searching for a raw or creating files, search **every** relevant main, imported, quarantine, staging DB and `mtl/*.json` for:

- exact and normalized `slug`;
- full display title;
- original title;
- verified aliases.

Use `scripts/check-db-duplicates.py` when the DB is SQLite. Distinguish a full-title match from a common-word match. An exact slug collision stops the run; never silently append `-new`, `(2)`, or another guessed slug.

Read: `references/db-change-safety.md`.

### 3. Identify the exact work and metadata

Confirm original/native title, verified English title or romanji, author, language, edition, work type, and web/print axis. A shared series word is not an identity match; rule out manga adaptations and similarly named works. Public `judul` must use a verified English title or romanji when the local Indonesian title is not official. Never invent an ATL.

Build synopsis metadata in this order: official publisher/author → official platform → licensed catalog → reviewed factual draft. If none exists, leave synopsis empty and report `sinopsis: tidak tersedia`; never infer a synopsis from a few chapter lines or copy a third-party translator's blurb.

Read: `references/verifying-a-novels-title.md`, `references/title-metadata-policy.md`.

### 4. Select and verify the raw source

Fetch the candidate and prove all of these before extraction:

```text
same work and edition
correct source language
complete text, not teaser/preview/empty JS shell
source coverage and chapter/volume scope known
rights basis recorded privately
```

Check page `<title>`, metadata, and 2–3 real body lines. HTTP 200 alone is not evidence. If no lawful usable raw exists, stop and ask for an owned/licensed file or choose an official author upload.

Read: `references/source-selection.md`, `references/raw-source-map.md`, `references/web-novel-raw-sources.md`, `references/third-language-raw-sources.md`.

### 5. Extract and inspect the raw

Choose tooling from the actual container: `pdftotext` for text PDFs, stdlib ZIP/XHTML for EPUB, verified HTML/API extraction for web novels. Record source hash, page/episode count, language, and metadata. Do not trust a TOC, filename, slug, or container language without inspecting the content.

Read as needed: `references/pdf-raw-extraction.md`, `references/epub-import.md`, `references/epub-illustration-extraction.md`.

### 6. Parse chapters, volumes, and scene boundaries

Probe the raw before choosing a splitter. Test single newline versus blank line, HTML headings, EPUB `h1`, form-feed `\f`, and source-specific chapter markers. Treat `＊＊＊`, `***`, and horizontal rules as scene separators, not chapters. Separate TOC/nav/colophon from real prose using following-content length and sample reconstruction. If a real chapter title is unavailable, use `Bab N` with the counter restarting **per volume**; keep global ordering separately.

Never apply a global “merge short lines” rule without checking dialogue/quote state. It can destroy dialogue and epigraphs. Preserve RAW paragraph boundaries, separate only clearly marked dialogue turns, and never add decorative line breaks.

Read: `references/parser-adaptation.md` and `references/text-structure-and-formatting.md`, `references/source-shipped-as-volume.md`, `references/warehouse-volume-assembly.md`, `references/pdf-raw-to-chapters.md`.

### 7. Plan chunks and glossary

Split on paragraph boundaries, then sentence boundaries; never split mid-word or mid-sentence. Create a manifest with source hash, chunker version, chunk size, endpoint/model placeholders, and progress arrays. Rebuild `GLOSARIUM` and `NAMA_SALAH` from this novel only. Include names, surname/given-name parts, honorifics, ranks, locations, and terminology policy.

Read: `references/glossary-and-consistency.md`, `references/jp-to-id-translation.md`, `references/resumable-mtl-runs.md`.

### 8. Endpoint, model, and quota preflight

Do not treat `http://localhost:20128/v1` as an MTL route merely because it responds or lists models. Probe the actual OpenAI-compatible endpoint and model with one real-sized prose block. Accept only a genuine Indonesian translation—reject continuation, menu, refusal, or source-script output. Inspect quota/rate-limit headers or provider allowance status before launching a batch. Unknown quota means no large batch.

Read: `references/mtl-endpoint-and-model-selection.md`. Keep endpoint, model, and quota result in the private manifest.

### 9. Translate with resumability

Send chunks independently with the same glossary and translation policy. Save each chunk atomically with source text, source hash, response, index, endpoint/model, attempts, and validation status. On a failed chunk, save the failure and continue; never `break` and never discard the source text. On 429/402/503, allowance exhaustion, OOM, or endpoint instability: pause, preserve completed chunks, and resume only after a fresh preflight.

Do not patch a file while its worker is writing. Do not rebuild a list containing good translations just to fill blanks.

Read: `references/resumable-mtl-runs.md`, `references/chunk-failure-handling.md`.

### 10. Text QA and repair

Run independent QA over the joined output, not only the pipeline's `selesai` flag:

- no missing/truncated/misaligned chunks;
- no CJK/kana/source-script leakage;
- no refusal/menu/continuation text;
- plausible source/target length ratio;
- glossary names/terms consistent and `NAMA_SALAH` absent;
- register, tense, voice, and honorifics match the archive;
- quote pairing/style matches the archive;
- scene separators preserved exactly once;
- first and last paragraphs are real story content;
- chapter and volume counts reconcile with the source;
- RAW paragraph/dialogue/heading/scene-break token order is unchanged;
- no arbitrary line breaks or global whitespace collapse changed the structure.

Inspect raw output before any destructive normalizer. Apply register/quote/separator normalization at most once, back up first, then re-run QA. Read: `references/glossary-and-consistency.md`, `references/qa-checklist.md`, `references/verifying-and-repairing-novel-text.md`, `references/cleaning-scraped-chapter-text.md`.

### 11. Stage the result

Load one novel into a temporary/staging DB or staging table, never directly into production. Keep third-party translated input in quarantine and require explicit approval before any promotion. Attach the private manifest and undo-log to the staging record.

### 12. Staging QA

Verify duplicate slug/title, chapter count, global ordering, volume labels, empty chapters, text integrity, cover paths, FTS/index behavior, metadata completeness, synopsis provenance, and public-output cleanliness. Run `PRAGMA integrity_check`. A row count alone is not verification.

Read: `references/qa-checklist.md`, `references/db-change-safety.md`, `references/mtl-cover-and-assets.md`.

### 13. Backup and promote one novel

Immediately before production promotion:

```bash
python scripts/backup-sqlite.py /path/to/naver.db --reason before-novel-import
```

Require a valid backup and `integrity_check: ok`. Promote one novel in one transaction, record inserted novel/chapter IDs and undo-log path, then run integrity check and re-query the slug/title. If any check fails, roll back; do not guess or “fix forward” in production.

### 14. Public-output audit

Before the site/API serves the result, scan public fields and rendered chapter text for source URLs, mirror/download links, private translator/group names, scrape notes, rights claims not supported by the manifest, accidental raw-language text, and internal file paths. Remove or quarantine anything that should remain private. Do not publish a full translation without a clear rights basis.

Read: `references/public-output-audit.md`, `references/safety-and-rights.md`.

## Stop conditions

Stop and report the exact phase and blocker if any of these occurs:

- rights or publication permission is unclear;
- input is already Indonesian/human-translated but the user asks for MTL;
- title/edition/source cannot be verified;
- no lawful complete raw is available;
- exact slug/full-title collision exists;
- source hash or chunk alignment changes during resume;
- endpoint returns continuations/refusals/source text;
- quota/rate limit is unknown or exhausted;
- QA finds missing chunks, leakage, inconsistent glossary, or broken quotes;
- DB backup/integrity check fails;
- public-output audit finds private provenance or unsupported rights claims.

Never hide a blocker by inventing metadata, changing a slug, deleting a scene, silently skipping a chunk, or importing directly into production.

## Quick command reference

```bash
# list the package
npx skills add https://github.com/HiuraKiyowoo/novel-mtl-skill --list

# install/update this skill in Hermes
npx skills add https://github.com/HiuraKiyowoo/novel-mtl-skill \
  --skill novel-mtl-self-translation --agent hermes-agent --global --copy --yes
npx skills update novel-mtl-self-translation

# DB preflight and backup
python scripts/check-db-duplicates.py /path/to/naver.db --slug <slug> --title <title>
python scripts/backup-sqlite.py /path/to/naver.db --reason before-novel-import
```

## Reference map

- **Rights and public safety:** `safety-and-rights.md`, `public-output-audit.md`
- **Decision branches:** `human-translation-flow.md`, `web-vs-print.md`
- **Metadata/source:** `title-metadata-policy.md`, `verifying-a-novels-title.md`, `source-selection.md`
- **Extraction/parsing:** `pdf-raw-extraction.md`, `epub-import.md`, `parser-adaptation.md`, `text-structure-and-formatting.md`, `pdf-raw-to-chapters.md`
- **Translation runtime:** `mtl-endpoint-and-model-selection.md`, `resumable-mtl-runs.md`, `chunk-failure-handling.md`, `glossary-and-consistency.md`, `jp-to-id-translation.md`
- **QA/import:** `qa-checklist.md`, `text-structure-and-formatting.md`, `verifying-and-repairing-novel-text.md`, `db-change-safety.md`, `mtl-cover-and-assets.md`
- **Deep edge cases:** `raw-source-map.md`, `web-novel-raw-sources.md`, `third-language-raw-sources.md`, `warehouse-volume-assembly.md`, `legacy-detailed-rules.md` (read only when a case is not covered above).
