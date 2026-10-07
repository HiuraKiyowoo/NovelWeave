# Handling failed chunks — never write source text, never silently mark done

Depth for the rule in SKILL.md: a chunk that failed after all models and retries must NOT be
persisted as the source-language text, and a chapter with any unresolved failed chunk must not be
marked finished.

## The failure mode

A transient network outage drops every in-flight request at once. A pipeline whose last-resort
branch is `hasil = teks_asli` (write the original text when translation fails) then writes
untranslated source text into the chapter, marks the chapter done, and the run's log looks like
normal progress. Nobody sees it until a reader hits a wall of Cyrillic/Chinese mid-book.

Verified: a network outage produced **30 consecutive chunks written as raw Russian** (chunks 25–54
of a single chapter), saved as if complete. The run reported success.

## The rules

1. **The failure branch must never emit source text.** On a chunk that fails after every model and
every retry, abort the CHAPTER: mark it `gagal_sebagian` (or equivalent) and do NOT persist it as
finished. Leave the previously-good version (or nothing) so the next run re-does only that chapter.

2. **Absorb short outages by waiting, not by failing over instantly.** A 60–90 s connectivity drop
   should be handled by a patient retry loop (backoff, re-check reachability), not converted into
dozens of corrupted chunks. Waiting costs minutes; writing raw text costs a silently broken book.

3. **Make the resume skip only genuinely-finished chapters.** Because a corrupted chapter is
   marked done, the resume will skip it — so the corruption is permanent unless you look for it.

4. **Verify by script-found residue, not by the run's own log.** Count source-script characters
   per chapter:
   ```python
   def sisa(t):
       return {"cyr": sum(1 for c in t if '\u0400' <= c <= '\u04ff'),
               "han": sum(1 for c in t if '\u4e00' <= c <= '\u9fff'),
               "kana": sum(1 for c in t if '\u3040' <= c <= '\u30ff')}
   ```
   Any chapter above ~0 (a handful of stray chars = names) is untranslated residue. This is the
   only reliable catch, since the chapter is marked complete.

5. **`finish_reason` of `abort` (or any non-`stop`) with 0 output is a model quirk, not content
   refusal.** Do not hunt for taboo content. Retry the same chunk with the fallback model, or split
   it smaller — verified: a 1356-char chunk succeeded on the fallback where the whole block aborted.

## Repair: patch the residual PARAGRAPHS, do not redo the chapter

Residue is usually **not** whole chapters — it is one or two untranslated paragraphs left inside
otherwise-good chapters (a chunk that came back source-language while its siblings succeeded).
Verified: 4 of 62 chapters flagged, each holding only 1–2 Vietnamese paragraphs amid clean
Indonesian.
**Do not discard or re-translate the whole chapter** — that re-spends quota and risks new variance
on text that was already correct. Repair in place:
1. Flag the offending paragraphs, not the chapter: a paragraph whose source-script ratio is high
   (e.g. the VN-only stopword set `của/người/không/được/những/với/một/cô/chị/rằng` ≥ a few hits).
2. Re-translate ONLY those paragraphs (one call each, or batched), then **substitute them back into
the same position** in the chapter text.
3. Re-run the residue sweep to confirm the count is now 0; assert the aksara total barely moved
   (fail loudly if it dropped — substitution must not swallow neighbouring paragraphs).
WHY: re-doing a whole chapter for two paragraphs is wasteful and can regress good text; the
in-place patch is strictly smaller and verifiable.

## Idempotency note

See SKILL.md's resume section for the three defects that make `--lanjut` destructive. The rule here
is a sibling: corruption from a bad failure branch is INVISIBLE to the resume (chapter marked
done), so a residue sweep must run after every long MTL session, not only when something looks wrong.


## Resumability is a data contract

A retryable chunk must retain its source text, index, source hash, endpoint/model, attempt history, and failure body. Save it atomically as it completes and keep a manifest of completed/failed chunks. A rate-limit or quota failure pauses the run; it does not clear the manifest. See `resumable-mtl-runs.md` for the resume checklist.
