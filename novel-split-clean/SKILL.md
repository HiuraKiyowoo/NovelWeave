---
name: novel-split-clean
description: Use when splitting a scraped novel into clean chapters.
---

# Split & clean a scraped novel into chapters

Trigger: a raw scraped novel `*-teks.json` (one page = one JSON entry, one line per paragraph, NO blank lines between paragraphs, NO chapter headings) that must become chapter-sized `.txt` files for an e-reader/bookshelf.

## Hard rules
- **Never invent or reword story text.** Only mechanical edits allowed: quote-flip, remove junk, add blank lines. If a fix changes prose, don't do it.
- **Read the source with your eyes** before writing rules; the defect patterns are specific to each scrape.

## Procedure
1. Inspect provenance first: `kokka-teks.json` style = list of pages `{file, head, teks, img}`. Check for overlap/duplication between consecutive entries (normalize whitespace, compare tail-vs-head sets) — scrapers sometimes repeat a paragraph.
2. Find the real structure:
   - Scene separators (here `♦`, elsewhere `❖`/`◇`/`***`). Count them, inspect context — they are the ONLY split points when there are no chapter headings.
   - Junk lines: leftover `">`, `Share this`, `Related`, comment blocks, bare page numbers, stray translator meta notes (e.g. "aku akan ulangi terjemahan paragraf terakhir"). Verify 'komentar' hits etc. are in-story before deleting.
   - Backmatter: afterword/`Kata Penutup` starts at a recognisable line ("Halo, saya <author>") — split it off as its own file.
3. Decide chapter boundaries by **paragraph counts between separators**, never by cutting inside a scene. Fixed explicit mapping (`GROUPS = [[0],[1,2],...]`) is more reliable than a greedy algorithm; read segment first-lines to sanity-check. Target ~140–250 paragraphs/chapter; a lone short segment can merge into its neighbour.
4. Per chapter, build the text: join paragraphs with `\n\n`, render each scene separator as an ornament line (`❖ ❖ ❖`).
5. Balance quotes per chapter with **per-paragraph** mechanical rules only:
   - leading `”` (closer) with no opener → `“`
   - doubled opener `“ “X` → `“X`
   - stray opener after a closer at end `...” “` → `...”`
   - paragraph starts AND ends with opener → flip last to closer
   - `“……… “` → `“………”`; stray space before closing `”` → drop it
   - `“…”<more text>` → `“…<more text>` (drop stray closer) — BUT only when text follows (`(?=\S)`); a whole-paragraph `“…”` is valid, don't touch it.
   Verify o==c per chapter. Expect only a handful of source typos to change (e.g. 16 of 2268 paragraphs), not hundreds.
6. Verify:
   - content preservation: every output paragraph must equal a source paragraph after normalisation (compare as sets). 0 lost, 0 invented.
   - blank lines: `\n\n` only, no `\n\n\n`, no `\r`.
   - chapter start = capital/opening-quote; chapter end = `. ! ? … ”` or the source's own trailing `─────` (authorial cut — check the next line to confirm it's a real scene break, not truncation).
   - quote count balanced per file.
7. Write `kokka-bersih/NN.txt` + a `DAFTAR-BAB.txt` manifest; delete stale files from earlier runs (renumbering leaves orphans).

## Pitfalls seen
- Removing a `”` that closes a legit `“…”` paragraph (breaking balance) — guard ellipsis fixes with lookahead for following text.
- Ordering: convert a leading `”`→`“` BEFORE collapsing a doubled opener, else dedup misses it.
- Regex replacement string with `\uXXXX` raises `bad escape \u` in `re.sub` — use real characters.
