# QA checklist

Run this checklist independently of the translation loop. Save the report with the staging manifest.

## Source and structure

```text
[ ] title/edition/source language verified
[ ] source rights basis recorded privately
[ ] source hash recorded
[ ] chapter/episode/volume coverage reconciled
[ ] TOC/nav/colophon not counted as prose chapters
[ ] scene separators preserved
[ ] no teaser, empty shell, or wrong work
```

## Translation output

```text
[ ] every planned chunk exists exactly once
[ ] no chunk is empty, truncated, or misaligned
[ ] source text is retained for every failed/retryable chunk
[ ] no source-script/CJK/kana leakage
[ ] no model menu, continuation, refusal, or policy text
[ ] length ratio is plausible for this language pair
[ ] glossary names/terms are consistent
[ ] NAMA_SALAH variants are absent
[ ] register, tense, voice, and honorifics match the shelf
[ ] quote pairs are balanced and style is consistent
[ ] first and last paragraphs are real story content
[ ] each RAW paragraph maps to one output paragraph unless a hard-wrap repair is documented
[ ] narration and clearly marked dialogue turns are separate; no invented line breaks
[ ] heading/chapter-marker/scene-break token order matches RAW
[ ] whitespace cleanup did not alter paragraph boundaries or story order
```

## Staging DB

```text
[ ] exact/full-title/slug duplicate search is clean
[ ] staging DB backup exists
[ ] PRAGMA integrity_check = ok
[ ] chapter count and global urutan are correct
[ ] no empty chapter/body rows
[ ] volume labels and fallback Bab N policy are correct
[ ] cover paths and FTS/index behavior are valid
[ ] synopsis status is official/platform/catalog/draft-review/unavailable
[ ] public fields contain no private provenance
[ ] undo-log and inserted IDs are recorded
```

## Severity

- **Blocker:** rights, wrong title, duplicate slug, missing chunk, source leakage, broken DB, unknown quota, or private provenance in public output.
- **Review:** style drift, uncertain synopsis, estimated volume boundary, or minor parser anomaly.
- **Pass:** all blocker checks clear and review items explicitly recorded.
