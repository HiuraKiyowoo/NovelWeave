# Human-translation / already-target-language flow

This branch is **not** an MTL run.

## Decision

Inspect EPUB `dc:language`, PDF metadata/body, and a representative chapter. If the text is already Indonesian or is a human translation by another group:

1. stop all model calls;
2. record provenance privately and quarantine the asset;
3. extract chapters without rewriting the translation;
4. verify title, edition, chapter count, completeness, empty chapters, CJK/source-language leakage, and quote balance;
5. run only non-destructive cleanup with a backup;
6. stage it in a temporary DB;
7. require permission/approval before production promotion.

A free download or visible translator credit is not publication permission. Do not place the source URL, group name, or translator credit in public chapter text or synopsis.

## EPUB handling

Prefer EPUB when both EPUB and PDF exist because chapters are separated into XHTML. Ignore `nav.xhtml`, package metadata, empty separators, and colophon/about pages as chapters, but harvest their metadata. Reconcile the real XHTML chapter set against `nav.xhtml` and, when available, PDF headings.

## Output shape

Reuse the existing staging/import shape rather than creating a second insert path. Set the record as externally translated, keep its private provenance manifest, and mark approval status explicitly. The MTL-specific “perfect output” shortcut never applies to a third-party translation.
