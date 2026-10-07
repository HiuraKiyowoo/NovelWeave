# Cleaning a scraped chapter's text (layout wrap, site furniture, chapter titles)

Depth for the "rapikan isi novel" workstream: chapters already in the archive (from a scraper
or an EPUB) whose *story text* is intact but whose *layout* is broken. This is not
verification and not translation — it is a text-repair pass that runs before/around the MTL
stages, usually on one novel at a time at the user's insistence.

## The user's standing rules for this pass

- **One novel at a time, never bulk.** Verbatim: *"kita benerin satu" kalo di bulk bakalan ga
  sempurna… mending lama gpp asal bagus*. Fix a single novel, show the result, then move on.
  A 19-novel bulk pass produces worse output than 19 careful single passes.
- **Do not add or change finished features without asking.** Clean *content*; do not reshape
  the schema or UI in the same pass unless the user asked for it that turn.
- **Back up before writing.** Copy `naver.db` AND dump the target novel's rows to JSON
  (`undo/<id>-sebelum-*.json`: the `novel` row + all its `bab` rows) so the pass is reversible
  per-novel, then write.
- **Always add a safety net that fails loudly.** The cleaning script must count paragraphs
  before and after and print `paragraf BERUBAH: 0` as a hard assertion — a repair pass that
  silently changes paragraph count has destroyed structure. Verified: the count is what caught
  a whole class of bug that the eye never saw.

## The core fix: re-join layout-wrapped lines while KEEPING real paragraph breaks

A scraper or EPUB extractor emits the novel's *layout* line breaks, so one real paragraph
arrives split across many short lines:

```
Cahaya lembut musim semi menembus
 tirai.

Tentunya ini adalah hari Minggu
di bulan April.
```

Real paragraph boundaries are the **blank line** (`\n\n`). So the correct operation is a
single regex that collapses `\n` **inside** a paragraph to a space and leaves `\n\n` alone:

```python
import re
def gabung_paragraf(teks: str) -> str:
    # collapse single newlines (and their surrounding spaces) to one space;
    # a run of >=2 newlines is a real paragraph break and is preserved.
    t = re.sub(r"[ \t]*\n[ \t]*", " ", teks)         # every \n -> space
    t = re.sub(r"(?: \n){2,}", "\n\n", t)            # restore paragraph breaks
    return re.sub(r"[ \t]{2,}", " ", t).strip()
```

**Never build paragraphs from scratch** (split into sentences and re-flow). That is the
approach that destroys the author's paragraphing and merges the whole chapter into one block.
Verified twice: a `gabung_baris` + `bersih_spasi` pair that ran as two separate passes deleted
all structure and produced `baris kosong: 0 pasang`, one giant blob. One regex, one pass.

### The single-`\n` rule above is NOT universal — when a lone `\n` carries THREE meanings, use a data map, never a punctuation rule

The collapse-every-`\n` recipe works when a lone `\n` is ALWAYS layout wrap. Some sources
(notably blogspot human fan-translations) use a lone `\n` for **three distinct things**, and a
single-pass regex cannot tell them apart:

1. **Soft wrap** — the source's own line width broke a sentence mid-paragraph → JOIN (space).
2. **A speech pause inside one dialog** — `“Senang bertemu denganmu.` `\n` `Namaku Ayase Saki. ”`
   is ONE spoken paragraph → JOIN, do NOT split (the closing `”` is alone on the second line).
3. **A real paragraph boundary** the author wrote as a single `\n` → SPLIT (keep the break).

The device that distinguishes them is the surrounding DIALOG state and whether the line ends on
sentence-final punctuation — but **punctuation rules alone corrupt real dialog**. Verified: four
successive punctuation/glyph algorithms (`!?.”…` ends-with, quote-balance gates, title-lookahead)
each fixed one case and broke another, because a legit multi-paragraph dialog opens with `“` and
closes with `”` two or three paragraphs later — *any* rule that splits on `“`/`!`/`?` chops it in
two. Balance count went 3,826 odd → 3,820 odd across attempts (barely moved).

**The method that worked = classify EVERY lone-`\n` occurrence into an explicit type, then apply
per-type.** Build a data map first, print the counts, and reason over the classes:

- Class C — soft wrap, no dialog → JOIN.
- Class A — a complete sentence followed by a new uppercase sentence, no dialog → SPLIT.
- Class B — dialog line ending on `.`/`!` but with an unclosed `“` and a following non-`”` line →
  JOIN (it is one spoken sentence wrapped, not two paragraphs).
- Class D — soft wrap *inside* a dialog that is still open → JOIN.
- etc. Print each class's count before changing anything; 15 spot-checked Class-B samples were all
  soft-wrap, which is what licensed JOIN.

**Then a SECOND stage merges the dialogs the first stage could not see.** A dialog can be split
across a real `\n\n` boundary: a paragraph ending with an unclosed `“…` followed by a paragraph
whose only content is the closer (or the tail sentence ending `”`). Verified: after stage 1 the odd
balance sat at 196, and every one was a `\n\n`-split dialog (97 pairs); merging them dropped it to
2 — and those 2 were a LEGIT two-paragraph dialog that must be left alone.

**The balance count is the reliable progress meter; the eye is the final judge.** Track
`teks.count('“') - teks.count('”')` per chapter — a small nonzero residue after both stages is
usually legitimate multi-paragraph dialog, so read those chapters before "fixing" the remainder.
Never declare done on a green count alone: read the affected chapter's full body and confirm the
dialog is one continuous quote. The user's standing rule applies hardest here — *"lu jangan
ngandelin alat bro, lu harus ngecek sendiri juga"*.

### `“` in the MIDDLE of a sentence is a miswritten CLOSER — count them first, every one is a defect

<!-- verified: an MTL/human output carried exactly 8 `“` preceded by a letter/digit; all 8 were wrong
(a dialog opening that should have closed), 0 were legitimate, and the only near-miss `(“Ayo…` after a
`(` correctly stayed untouched -->
The model/translator sometimes types an OPENING `“` where a CLOSING `”` belongs, so a `“` lands
mid-sentence right after a letter or digit (`…siap.“ Tanpa disadari…`). Before writing any repair:
**enumerate them and count** — `re.findall(r'[A-Za-z0-9]“', teks)`. If the pattern is a *handful*
and every sampled one is a defective closer (never followed by a fresh sentence-start), convert just
those (`re.sub(r'(?<=[A-Za-z0-9])“', '”', teks)`), then re-check balance. This is the narrow,
safe repair — do NOT widen it to all `“`, and do NOT repair `“` that follows `(`/whitespace/start
(a legit opener). A repair that flips legitimate openers (a broad `“`→`”` pass) is a KNOWN failure
mode in this project — narrow the rule to the `(?<=[alnum])` position and nothing else.

## Read the source's line-length distribution before assuming lines are wrapped

Whether short lines are layout wrap or real paragraphs is **measurable**, and the answer
differs per source:

```python
import statistics
lens = [len(l) for l in teks.split("\n") if l.strip()]
print(statistics.median(lens), len([l for l in teks.split("\n\n")]) )   # median + para count
```

<!-- verified: Kaito rows had median ~32 chars (wrapped layout) while Sakura rows had median ~65 (real paragraphs) -->
A low median with many very short lines ("tirai." at 6 chars, "di bulan April." at 15) is
layout wrap → re-join. A median near a normal sentence length is the author's own linework →
leave it. Do not run the same cleaner over every source without checking this.

## Donor-site watermark blocks are a THIRD junk class (distinct from header/footer/nav)

A fan-translation donor (e.g. ruidrive) splices its own promo block **between narration paragraphs,
mid-chapter** — not at chapter top/bottom, so header/footer rules never see it. Signature: *"Kami
dengan sepenuh hati telah menyusun PDF light novel ini… Kunjungi blog sederhana kami di
https://<host>/ … donasi … trakteer.id/<host> … Terima kasih atas perhatian dan dukungannya!"*, and a
short sip form as a bare `Ruidrive -` line mid-dialog. Remove ONLY the matched block (a `re.sub(...)`
with `re.S` anchored on the block's first and last sentence); never blank an unbounded region, because
real narrative sits immediately before/after. Sweep for the donor name + `trakteer` + `https?://` +
`blog sederhana` + `donasi`; one hit means dozens of chapters hold it. Re-run until zero — a sip form
needs a second pattern. Strip `\u00a0` inside the block or the match misses.

**Audit SIBLING novels too.** The watermark, glued words and quote corruption come from the source,
so one novel's defect predicts the others from the same donor — grep the whole DB before reporting
done; a published novel carrying the same junk is the higher-priority fix.

## Blogger/scraper feed garbage appended to EVERY chapter

A blogspot-sourced dump can carry a block of JS + a trailing link list at the END of each chapter:
`function getFeedUrl`, `//Error: No Results Found`, `resources.blogblog.com`, and a list of links to
OTHER novels (sometimes `Saijou no Osewa Jilid 12…`). Measured: ~7.5 KB appended to **every** chapter
of one novel, leaving real story only ~72% of each. Detect by locating the first JS token
(`//Error`/`function getFeedUrl`) — the real story ends right before it. This is content loss (the
story tail is real), so fix it as a cleaning pass, not a truncation report.

## Site furniture: strip the header and the footer, keep the story

### `\nTags:\n<novel-title>` is a PERFECT chapter-boundary marker — but cut it only where it sits DEEP in the text

<!-- verified: a blogspot source appended a tag block after every chapter's real story; the marker
`\nTags:\n<Novel Name>` separated story from appended Comments/Donate/JS junk on all 258/258 chapters,
and one chapter's story would have been lost by a naive cut -->
When a source stamps `Tags:` + the novel's title after each chapter, that line is a **reliable,
unambiguous boundary** (the string is the novel's own title, not a common word) — far safer than a
furniture shape. But its POSITION varies and that is the trap:

- Cut from the FIRST `\nTags:\n<title>` that sits past **>15% of the chapter's length**. If the
  marker is near the top (head of the text), the "chapter" is an illustration/garbage page with no
  story to save — do NOT cut (there is nothing before it); blank the row instead.
- Verified failure it prevents: an aggressive "drop everything from the marker" cleaner emptied one
  chapter's real story to 338 chars because that chapter's marker legitimately sat at ~13% (the
  story was BELOW it, not above). The `>15%` gate is what keeps the story.
- This pairs with the general rule in this file: a boundary heuristic is only safe once you have
  checked WHERE the marker lands across the whole novel, not just on chapter 1.

> **Also see below:** the furniture cleaner can EXIST but never be called (a green `--uji` with dirty
data), furniture can sit in the MIDDLE of a chapter too, nav lines must be matched as whole lines (not
substrings — `'Sebelumnya'` appears in real dialogue), and the `Catatan dan Referensi` block right
under the footer is CORRECT CONTENT that must survive.

### A per-PAGE stamp defect is PER-VOLUME, not per-set — audit every volume separately

<!-- verified: one volume of a four-volume set carried 447 `PAGE N OF M | <site> | <site>` stamps, one
per PDF page (the raw was a 454-page PDF), while the other three volumes of the SAME novel were
completely clean -->
A source can stamp every *page* rather than every *chapter*: an aggregator PDF-print adds
`PAGE 33 OF 454 | KAITO NOVEL | CSNOVEL` at each page break, so a single volume accumulates hundreds
of them and they land mid-paragraph (the page break falls mid-sentence), unlike a once-per-chapter
header. Two rules fall out:

- **Do not infer "this source has no stamps" from a clean volume.** Verified: the set's V1-V3 were
  clean and V4 held 447. Sweep **every volume of the set** even when the first few are spotless —
  the defect lives in the *raw's* format for that volume (here a different, PDF-derived raw), not in
  the source as a whole. This is the same per-volume non-uniformity as the §"furniture sweep residue"
  pitfall in SKILL.md, made concrete.
- **Match the page stamp by its own shape, and match it mid-line too.** The pattern is a
  `PAGE\s+\d+\s+OF\s+\d+` run with the site names after it; it is NOT at a line start, so a
  line-anchored furniture rule misses it. Strip with a non-anchored regex over the whole text, then
  collapse the double blank lines the removal leaves (`re.sub(r'\n{3,}', '\n\n', t)`).
- **A near-miss on the count is normal — read the residue.** 447 found and stripped, 0 left. If a
  handful remain, `repr()` them before re-running; the survivors are usually a variant spelling the
  pattern lacked, not a rule that failed.

### A decorative BULLET can leak as a CJK character glued to the dialog — it is an artifact, not a translation defect

<!-- verified: 9 rows in one volume began a dialog line with the stray kanji `\u81ea\u7531`, e.g. `\u81ea\u7531\"Aku ratain lagi kok, aman.\"` -->
A source that uses a bullet glyph (or an icon font) before spoken lines can arrive as a **CJK
character pair directly before the opening quote** — it reads as a leftover-kanji translation defect
but it is a rendering artifact of the bullet. Distinguish it from real leaked kanji:

- **Signature: the stray characters sit IMMEDIATELY before a dialog quote** (`自由"…"`,
  `自由“…”`), with no whitespace, on a line that otherwise reads as clean Indonesian.
  Real untranslated kanji sits *inside* prose, not glued to a quote opener.
- **Fix it locationally, not by dumping the characters globally:**
  `re.sub(r'<artifact>(?=\s*[“"『])', '', t)` — strip only where it precedes a quote — because the
  same characters may be legitimate content elsewhere. Then a plain global `.replace()` as a
  backstop only if you have confirmed they are not prose anywhere in the book.
- **Do not treat the CJK sweep count as "all defects" without reading the survivors.** After stripping
the artifact, the remaining CJK in the book can be legitimate (translator notes, ruby/reading
explanations, foreign-language quotes) — classify before deleting. A CJK sweep that reports 39 hits
where 38 are `[TLN: …]` notes is a clean book, not 39 defects.

A scraped chapter carries a nav header and a nav footer around the story:

- **Header:** `… Bahasa Indonesia by <uploader> · <date> · Chapter …` at the very start.
- **Footer:** `Sebelumnya || Daftar isi || Selanjutnya · Tags: …` at the very end.

Strip both by matching the furniture's own shape (the `Sebelumnya`/`Selanjutnya`/`Tags` markers,
and a leading credit/date line) and **verify by re-reading the first and last paragraph** — the
story must start on prose and end on the story's last line, not on a nav bar.

**Furniture has THREE positions, not two — scan the whole text, not just head and tail.** Besides the
header and footer, a nav block can sit in the MIDDLE of the chapter (after the story ends, before a
`Catatan dan Referensi` section). Build the cleaner as a full pass over every line, never as
"clean the first N lines and the last M lines". Verified: across one source, the nav+tags sat at
line 594 of ~800 in one novel, at line 0 in another, and at the tail in a third.

**The recognised furniture set (match on the line's own shape, case-insensitive):**
`Tags: <novel>` · `Kategori: …` · `Penerjemah:` / `Translator:` / `Editor:` · `Sebelumnya | Daftar isi |
Selanjutnya` (pipe count varies: `|` or `||`, sometimes `Sebelumnya` absent) · `| Daftar isi |
Selanjutnya` · **`<<=Sebelumnya |`** (angle/equals lead-in) · **`|| Daftar isi || Selanjutnya`** ·
**`Sebelumnya | Sesudahnya`** (the right-hand word can be `Sesudahnya`, not only `Selanjutnya`) ·
`by <name>` (possibly with a `- <date>` tail) · `- <Month> <D>, <YYYY>` ·
`<Source> Novel` · `Home` · `Beranda` · `Project LN/WN` · `_Tamat` · `Donate` · `English Version`.

**Normalise the nav line to its CORE before matching.** A robust detector strips any leading/trailing
run of `< > = | ‖` and whitespace (`inti = re.sub(r'^[<<=>=|‖\s]+', '', low)` plus the same on the tail),
then tests the core against the known word-sequence. Matching on the raw line misses every new lead-in
characters the source invents (`'<<=Sebelumnya |'`), while a substring test over-matches real prose —
the normalise-then-anchor form handles both.

**Match nav lines as WHOLE LINES, not substrings.** A "is there furniture?" test written
`if 'Sebelumnya' in teks` fires on legitimate prose and dialogue — verified false positives:
`'“Sebelumnya seperti apa?”'` and `'Selanjutnya, aku akan membawa Eito…'`. Use an anchored pattern
(`^\s*sebelumnya\s*\|`) so the story line is never touched.

**Do not strip `Catatan dan Referensi` + its numbered list, or a translator-note block.** Those sit
right after the nav footer in the same position and are CORRECT CONTENT (glossary/reference notes the
source added). A cleaner that drops "everything from the nav marker onward" deletes them. Drop the
furniture LINES only; keep the section beneath them.

**A "truncated tail" report from a length heuristic is often this footer, not a lost scene.**
Verified: 190 chapters were flagged "ekor kepotong" by a char/length check and every one of
them was intact — the story was complete and the site footer sat after it. Before believing a
truncation flag, open one flagged chapter and look at its actual last lines. Clean the
furniture, then re-measure.

### The furniture cleaner existed but was never CALLED — a green run with dirty data

<!-- verified: --uji reported all nets green while 29 of 32 chapters of one novel still carried the
site footer, because rapikan_teks never called the furniture cleaner at all -->
The nets (`paragraf BERUBAH`, `isi BERKURANG`, `judul '0'`) measure "changed vs unchanged" — and
*unchanged input passes them*. So a cleaner function that exists but is never invoked produces a
perfectly green report while the furniture sits in the prose. When cleaned text still looks wrong
after a green run, `grep` the function's **call site in `rapikan_teks`** before touching any regex:
a missing call is a different bug from a wrong regex, and no regex fix will help.

**Therefore: read the text yourself before declaring done.** Standing rule from the user, verbatim:
**"lu jangan ngandelin alat bro, lu harus ngecek sendiri juga"**. Read the head AND tail of the
cleaned text of several scattered chapters (not just #1), as `repr()`, and look for the furniture
markers with your own eyes.

### The byline/date line sits BETWEEN the stray title and the real title

A newer source layout puts a credit line and a publish date *after* the nav/title header, so they
land inside the body:

```
[0] <Novel> Jilid 1 Selingan 7 Bahasa Indonesia   ← stray title (generic)
[1] ''
[2] ' by Kareha '                                  ← furniture
[3] ' - Maret 17, 2024 '                           ← furniture
[4] ''
[5] ' Selingan 7 —'                                ← the REAL title
[6] ' Bagian Nene 4 '
```

Treat `' by <name> '` and `' - <Month> <D>, <YYYY> '`, plus nav crumbs (`Kaito Novel`, `Home`,
`Beranda`), as **furniture to drop AND skip over** — not as text. Two consequences, both verified:
(a) if the furniture line is not recognised as skippable, the title-harvest loop stops on it and the
real title on line 5 is never seen; (b) the furniture ends up in the cleaned text, so the chapter
opens on `'by Kareha - Maret 17, 2024'` instead of prose. **Measured scale: 103 chapters across three
novels of one source carried this — the whole source, not a stray row.** A harvest loop must skip a
*mix* of stray-title + blank + furniture lines before it reaches the real title, and only then give up.

### A stray-title detector that keys on `startswith(<novel name>)` misses titles with a connector word

The novel name is often shortened when building the match key (short words dropped), but the stray
line keeps the connector: novel `'Hanayome Ryakudatsu'` vs line `'Hanayome wo Ryakudatsu Jilid 1 …'`.
`startswith()` fails on every one. Match by **all name words present + short line + a unit marker**
(`chapter|bab|jilid|selingan|volume|prolog|epilog`) instead of a prefix.

**After removing the novel's words, strip the leftover connector words before testing the unit
marker.** A name like `'Ojou-sama no Yousu ga Okashii'` leaves `'ga   volume 1 prolog …'` after its
words are cut; the residue `ga` fails a `^(chapter|bab|…)` test that would otherwise pass. Drop a
leading run of 1-3-letter words (`^(\s*[a-z]{1,3}\s+)+`) and a trailing `bahasa indonesia` before the
unit test.

**Order the strip rules so a greedy pattern cannot eat a meaningful word.** A cleanup that removes
`volume N` / `vol N` / `jilid N` MUST run **before** any `^[a-z0-9]*`-style "drop the leading junk
word" rule. Reversed, the greedy rule swallows the entire word `volume`, leaving `'1 prolog bahasa
indonesia'`, which fails the unit test — and the resulting bug looks like "the matcher is too strict"
when it is really rule ORDER. Terse rule: specific removals first, greedy catch-alls last.

**A byline and its date can arrive as ONE line after earlier line-joins**, e.g.
`'by Kareha - Februari 14, 2025'`. A furniture pattern written as `^by\s+\S+\s*$` misses it. Allow a
`- <Month> <D>, <YYYY>` tail (or any `\d{4}` tail) on the byline pattern.

## A title can span 2-3 PHYSICAL LINES — harvest the continuation block, don't stop on line 1

Some source layouts break one chapter title across several lines, mixed with furniture:

```
'Chapter'
'5 —'
'Kencan di Rumah'          ← the real title is the LAST line, not the first
```

A harvest loop that reads only the first line yields `'Chapter'` (or `'Chapter 5 —'`) and mangles the
row. Rules that make it robust:

- **`_buntu_nomor` — a line that ENDS on a numeral/dash is an INCOMPLETE title, not a title.** Treat a
  buntu-marker line as "keep looking": include `chapter|bab|jilid|volume|prolog|epilog|interlude|
  ekstra|extra|selingan` and any line ending in `-`/`—`/`–` or a bare number. A multi-line title is
  harvested by consuming up to **2 continuation lines** after the buntu marker, so `'Chapter'`+`'5 —'`+
  `'Kencan di Rumah'` reassembles whole.

- **A continuation line may START with `—` OR may be plain prose ending in a period.** Two gates:
  allow a continuation that begins `—`/`–` (the dash is the join, as in `'Prolog'` + `'— Cinta Pertama'`),
  AND when the buntu line itself ended on `—` (`'Ekstra —'`), allow the continuation to end in a period
  (`'…Lima Tahun Kemudian ….'`). Two conditions, both needed — a rule that requires the continuation to
  be dash-led rejects the legitimate `'Ekstra —'` + prose-period case.

- **Order the gates so the buntu-marker exemption does not leak.** Compute `_lanjut_khas` ("this is a
  known multi-line title prefix") AND `_buntu` ("the previous line was left hanging") and let a
  period-terminated continuation pass on EITHER; otherwise the general `not re.search('[.…"]$', line)`
  guard (which protects the body-prose direction of error) silently rejects the real title.

- **A `_S`/furniture pattern that requires `:` immediately after the label misses `'Penerjemah : X'`.**
  When the cleaner's skip-set matches `'penerjemah:'`, write it as `penerjemah\s*:.*` (and the same for
  `editor\s*:`); the space-before-colon form is common and a strict pattern leaves the line unskipped,
  which makes the harvest stop one line early and the row loses its title.

**Regression-test all 8+ cleaned novels after ANY widening here.** The buntu/dash gates that fix the
3-line novel are exactly the ones that can start eating body prose elsewhere; re-run over every novel
already cleaned and assert the diff is still empty before writing the new one.

## Sorting the raw into volumes: the `bagian` column can hold TEXT, and type-lines must not swallow prose

<!-- verified: a source's raw JSON carried `bagian` values `'Bab 5 Epilog'`, `'Prolog'`, `'Bab SS'`,
`'Bab 1 Bagian 3'` — the sort key `int(b['bagian'])` died with
`invalid literal for int() with base 10: 'Bab 5 Epilog'` -->
Before any per-volume grouping of a batch-scraped source, build the sort key from the **title**, not
from a numeric-column assumption:

- **A column whose name suggests a number can hold a label.** `bagian` here held free text. Never
  `int()` it — derive `(jilid, jenis, sub)` from the title, and treat the column as a *fallback*
  only after `re.search` proves it is numeric.
- **Rank the non-numbered types explicitly, epilog LAST:** `Prolog`→-10, `SS`/`Selingan`→5000,
  `Kata Penutup`→9980, `Epilog`→9990, `Bab N`→N. A naive `re.search(r'Bab\s*(\d+)')` on
  `'Bab 5 Epilog'` extracts `5` and files the epilog in the *middle* of the volume.
- **An item with no `Jilid N` marker belongs to the LOWEST volume present, not a sentinel.** Verified:
  a lone `'Bab 5 Epilog'` with no jilid was the Epilog of Jilid 3 (the lowest volume the source had),
  not `volume 99`. Sorting so it lands at the very end puts an epilog after the last volume's epilog.
- **The generated title and the text must be built in that same order, per chapter.** Real names are
  harvested from the chapter's own leading line (see the title-harvest sections above), so run the
  harvest on the sorted set, not before it — otherwise the `Bab N` fallback counter is assigned in
  the wrong order.

### A type-only line (Prolog/Epilog) is a title in full — do NOT join the story sentence onto it

<!-- verified: `'Prolog'` + next line `'Akademi Kekaisaran sekarang sedang memasuki…'` was joined into
`'Prolog Akademi Kekaisaran sekarang sedang memasuki…'` -->
The multi-line-title join rule (above) must fire **only for titles that carry a NAME**
(`Bab 4 —` + `Penyelidikan Teman Masa Kecil`). When the leading line is exactly a type word
(`Prolog`, `Epilog`, `Kata Penutup`, `Bab SS`), the title IS that word — the following line is prose.
Gate the join on the line matching `^(Bab\s*\d+|Bab\s*SS)\s*—\s*$` (a dash-terminated numbered head),
not on the type-word alone. Joining here also *deletes* the first line of the story from the body,
so the defect is text loss as well as a wrong title.

## Empty chapters from an illustration page

A chapter titled "Ilustrasi" with 0 text is **correct** — it is an image page, not a lost
chapter. Verified: 6 empty chapters across two novels, all `Ilustrasi`. Keep the title honest
(`Volume N Ilustrasi`) rather than deleting the row or inventing text.

## A title-detector that fires on BODY PROSE is the dangerous direction of error

<!-- verified: a chapter's closing paragraph ("Terima kasih telah membeli buku 『<novel> N: …』…menulis kata penutup…") was deleted as a stray title, losing ~350 chars of real text -->
The stray-title cleaner must err toward *keeping* text. Two over-broad matchers, both verified to
have eaten real content:

- **Never key the match on ordinary words.** Keywords taken from the chapter title (`'Volume 4 Kata
  Penutup'` → `{volume, kata, penutup}`) matched a body paragraph because prose legitimately contains
  "volume" and "kata penutup". Maintain an explicit `KATA_UMUM` stop-set (`kata, penutup, volume,
  chapter, bab, prolog, epilog, ilustrasi, interlude, side, story, bonus, bagian, part, jilid`) and
  build the keyword list only from words outside it. A keyword list that is empty after filtering is
  correct — fall back to positional rules, not to looser words.
- **Anchor on position and shape, not on a substring anywhere in the line.** A stray title is a
  *short* leading line; body prose is long. Gate every substring-based rule with `len(line) <= ~80`
  and only consider the first few lines of the text. Without a length gate, one paragraph that happens
  to mention the book's own title ("…telah membeli buku 『<novel> 4…』") is misread as the title.

**Regression-test every widening of a matcher against a saved good output.** After each change, re-run
over the novels already cleaned and assert their diff is still empty — a detector broadened to fix
novel N is the classic way to silently start eating novel N-2.

### When a "stray title" is the chapter's ONLY content, the removal must be reverted

<!-- verified: an illustration page whose whole body was `<Novel> Volume 1 Ilustrasi` became an EMPTY chapter -->
A rule that strips a leading title will empty the row when the title *is* the row's content
(illustration/cover pages). Guard the whole transform, not the rule: if the cleaned text is blank
while the input was not, restore the input. This is a cheap, universal safety net and it also
catches any future over-broad rule — pair it with the paragraph-count assertion already required.

**Detect illustration pages from the CLEANED text, not the raw.** Judging "is this an illustration?"
on the raw text misfires when the raw is *just* a stray title (`<Novel> Volume 1 Chapter 1 …`, 111
chars) — that reads as short enough to be an illustration and then wrongly excludes a real chapter
from the volume's numbering. Clean first, then test length.

## Chapter titles: strip the novel name, normalise the numbering, fold the volume out

Scraped chapter titles carry the novel's own name and a zero-padded number:

- `Omae wo Onii-chan ni Shiteyarouka! Volume 1 Chapter 03` → `Volume 1 Chapter 3`
- 316 of 483 chapters in one source repeated the novel title; a title that repeats the work's
  own name is noise in a chapter list.
- Normalise `Chapter 01` → `Chapter 1` so the list sorts and reads evenly.
- **The volume belongs in its own column, not inside the title string.** Extract `Volume N` from
  the title into a new `volume` column on the `bab` table (the user chose this shape: "tambah
  kolom baru `volume`"), then keep the label in the title too if the site's UI folds by column.

## Debugging these cleaners: test the FUNCTION on tiny probes, not the file on a big novel

<!-- verified: the cleaner took SEVEN fix attempts, every one of them because only the first 150 chars
of a chapter's output were inspected instead of the function's behaviour on a 2-line probe -->
The failure mode is not a hard error — it is a cleaner that looks plausible in the first few
lines and is wrong three paragraphs in. Rules:

1. **Before touching a big file, run the function on 4-6 tiny strings** that each contain one
target edge case, and print `repr()` of input and output. The date-dash bug below was found in
one step this way after seven failed file-level attempts.
2. **Probe each regex step in isolation, printing `repr()` after every `re.sub`.** A lookbehind
that "should" match may simply not, and the only way to see it is the intermediate string.
3. **Delete `__pycache__` before concluding a code change had no effect.** Verified: an edited
module kept importing a stale `.pyc` (`rm -rf <pkg>/__pycache__`), which made two real fixes
look ineffective. Also `sys.dont_write_bytecode = True` in the probe.
4. **Verify the result from the DB after writing, not from the script's own log.** The script
   printing `PERUBAHAN DISIMPAN` is a claim; a read-back `SELECT` of titles, volumes, paragraph
   count and dash examples is the proof.
5. **A helper that takes a context argument and is called WITHOUT it behaves as if its feature is
   absent — check the CALL SITE before concluding the feature is broken.** Verified: the
   stray-title stripper never ran for any novel because `rapikan_teks(teks)` was invoked with the
   title/novel arguments omitted (the signature defaulted them to `""`), so the cleaner reported
   `teks dirapikan: 0` while stray titles sat in the output for months. A signature with optional
   parameters hides this completely — `grep` the definition AND every call, and confirm the caller
   passes the context the function needs. The tell is a *capability* reporting zero hits on input
   you can see it should match.
6. **A script that CRASHED before its `json.dump` leaves the PREVIOUS run's output on disk — you then
   debug a bug that is already fixed.** Verified: a fix script died on a `re.error` partway through
   (`bad escape \u` in a `re.sub` REPLACEMENT string — use a literal character there, not `\uXXXX`),
   so its `json.dump` never ran; every later "the fix did not work" reading was the OLD file being
   re-read, and the giveaway was that the byte size and every count matched the previous run exactly.
   Two habits close this:
   - **`rm -f <out>.json` before running, and print a sentinel next to the write** (`print('WROTE_V2')`
     immediately before `json.dump`). Then confirm the file's `mtime` actually moved. A run whose
     sentinel never printed did not write, no matter what the summary line said.
   - **When a result contradicts a function you just proved correct in isolation, suspect the INPUT
     before re-examining the function.** The decisive probe is to call the function on the exact
     string lifted from the file: if it transforms correctly there, the function is fine and the file
     you are reading is not the one it wrote.
   This is the same family as the `__pycache__` rule in (3): the artefact lies, so verify its identity
   (mtime, byte size, sentinel) before building any conclusion on it.
7. **Do not accuse the script of lying when the DB read-back disagrees — first check whether a
   rule is simply MISSING for the case.** A run reported `judul dirapikan: 3 / 47` and "PERUBAHAN
   DISIMPAN", yet the read-back still showed `'0'` titles, which reads exactly like a failed
   commit. It was not: the commit was fine and 44 rows genuinely needed no change *as far as the
   code knew*, because no rule recognised `'0'` as broken. The distinguishing test is to run the
   transform **in-process** and print its output for one known-bad row (`rapikan_judul('0', …)` →
   `'0'`); if the function returns the input unchanged, the bug is a missing rule, not a failed
   write. Suspect the write path only after the function is proven to change the value.

### The two-rules-collide class of bug (the date-dash case)

<!-- the single bug that cost seven attempts -->
A cleaner often normalises several things and the rules fight each other. Here: a date separator
must stay `"7 April – Murasaki-san"` while a reduplicated word must become `"Gadis-gadis"`.

```python
# rule A (date separator) and rule B (word-reduplication) both match "April – Murasaki"
```

Two generalisable fixes, in order of preference:

- **Do not fix "which rule runs first" — protect the intermediate result.** Rewrite the rule
  that must win so its output can no longer be matched by the losing rule, or pipe the protected
  span through a sentinel. Rule ordering is fragile; making the output non-matching is stable.
- **Check the lookbehind's actual precondition.** The real root cause here was
  `(?<=[0-9])` — but the character before the dash was a **space**, not the digit (`"7 April – …"`),
  so rule A never fired at all. Pattern the whole line-shaped context (`(angka)…(dash)…` on one
  line) rather than anchoring a lookbehind to the wrong neighbour.

A working end state, verified on the probes: `"Senin, 8 April  -  Upacara"` → `"Senin, 8 April –
Upacara"`, `"Gadis – gadis"` → `"Gadis-gadis"`, `"menembus\ntirai."` → `"menembus tirai."`

## When the source has no real chapter names, give an HONEST generated title

<!-- verified: a novel's chapter titles were all the literal string '0' (42 of 47 rows); the content was
intact and only the name was lost in the source EPUB -->
A broken source gives no name back — the title column is `'0'`, `''`, or punctuation only. Do NOT
leave the placeholder and do NOT invent a plot name. Apply the user's standing rule (recorded in
`CATATAN/ATURAN-JUDUL-BAB.md`):

- **Real name found → use it.** Otherwise:
- **Story chapter → `Bab N`, counted PER VOLUME, restarting at `Bab 1` in each volume.**
- **Illustration page → `Volume N — Ilustrasi`.**
- Rewrite any chapter already carrying the novel's name in its title so the title holds only the
  chapter identity; the novel name lives in the `novel` row, not repeated per chapter.

The placeholder is *not* an empty value — test it explicitly. `judul_tak_bermakna()` must return True
for `'0'`, `'00'`, `''`, whitespace, and symbol-only strings (`'...'`, `'—'`), because a regex that
only checks `== ""` walks straight past `'0'`. Note this is a **missing-rule** bug, not a write bug
(see the debugging section): the cleaner reports `judul dirapikan: 43/46` and commits fine, yet 43
titles stay `'0'` because no rule recognised them.

**Exclude illustration pages from the `Bab N` counter** — they are not story chapters, so counting
them shifts every following chapter by one (a volume whose illustration is #1 must still start its
first story chapter at `Bab 1`). Maintain an explicit skip-set of illustration row ids and pass it to
both the counter and the titler.

### A source label that REPEATS (Part 1/Part 2) must be renumbered sequentially, not copied

<!-- verified: an EPUB's own chapter files were `Chapter 1 (Part 1)`, `Chapter 1 (Part 2)`, `Chapter 2
(Part 1)`, … so the shelf listed `Volume 1 — Chapter 1` twice in a row; the user flagged it as
"Double" Chapternya" -->
A print-derived raw splits a long chapter into parts, and the part labels are per-*chapter*, not
global. Taking the source label straight into the title column produces a reader-visible duplicate
(`Chapter 1`, `Chapter 1`, `Chapter 2`, `Chapter 2`, …) that reads as a bug on the chapter list even
though every part is a real, distinct chapter.

**Rule: the archive titles chapters by SEQUENTIAL per-volume position, and the source's own label is
evidence of grouping, not of the final number.** Collapse `Chapter N (Part K)` parts into one running
counter and drop the part suffix:

```
Chapter 1 (Part 1) ┐
Chapter 1 (Part 2) ┴─►  Volume 1 — Chapter 1 , Volume 1 — Chapter 2
Chapter 2 (Part 1) ┐
Chapter 2 (Part 2) ┴─►  Volume 1 — Chapter 3 , Volume 1 — Chapter 4
```

- **Check the existing shelf before choosing the shape.** Read the chapter list of the novels already
  on the rack (`SELECT judul FROM bab WHERE novel_id=<a settled novel> ORDER BY urutan`): if they run
  `Chapter 1, 2, 3, 4, 4.5, 5`, the convention is a sequential counter — match it, because the standing
  reason is consistency with the other novels on the shelf, not your own preference.
- **A `Part` suffix is a real distinction you are choosing to fold, so say so when you report it.**
  Offer the alternative explicitly (`Chapter 1`, `Chapter 1.5`, or keeping `Part 1/Part 2`) and let the
  user pick; do not silently decide. The user's honest-numbering rule wants the READER not to be
  confused, which sequential numbering satisfies.
- **This is a TITLE-ONLY fix once the rows exist.** Re-titling is a plain `UPDATE bab SET judul=? WHERE
  novel_id=? AND nomor=?` — it never needs a re-import, so a duplicate-label report is a two-minute
  correction, not a reload. Do not rebuild the novel to fix titles.
- **Renumber the whole volume in one pass, never row-by-row by hand** — a single off-by-one anywhere
  re-creates a duplicate or a gap, and the per-row edit hides it. Write the full `{nomor: judul}` map,
  apply it, then re-read the chapter list from the DB and eyeball the sequence.

## Post-processing MTL output: ONE pass per normalisation, then stop (and never diagnose a file you already rewrote)

<!-- verified: six successive quote scripts over the same volume (a `“ ↔ ”` swap, a per-line pairing, a
per-line normaliser, a model-assisted fix, and two more) left the SAME chapter reading `“”`-balanced on
the count report while individual lines were reversed, because each pass repaired the lines the previous
pass broke and broke others -->
Style normalisation on freshly-translated text (quote character, register, separator) has a failure mode
that is *not* a bad rule — it is running the pass again. Every rewrite is a lossy projection of the
previous one, so N passes leave a mixture of every rule that ran and no pass can tell what a given line
already received.

- **ONE normalisation pass, then STOP. Do not write a second script that "fixes the leftovers" of the
  first.** A pass that flips a reversed pair and a later pass that flips it back BOTH report success.
  The invariant you can check (balanced `“`/`”` counts) is not the invariant that matters (per-LINE
  shape), and the count stays green while the prose flips. If the first pass did not produce the right
  shape, delete its output and redo the logic — do not run a second pass on top.
- **After any mutation, the file can no longer be diagnosed — restore from the raw FIRST.** Every wrong
  conclusion in that session came from measuring a file an earlier script had already rewritten: a
  script-repaired `“…”` line made a `find("“") > find("”")` reversal test return 0, which read as "the
  data is clean" when the truth was "my own earlier pass removed the evidence". Before further diagnosis,
  **rebuild the chapter text from the untouched per-chunk translation output** (re-join the saved chunks
  with the separator) and measure THAT. If you cannot reconstruct the pristine text, you cannot reason
  about the damage — rebuild, do not patch the corrupted copy again.
- **A "0 problems" report from a rule-based checker is not evidence — read the lines you already saw
  with your own eyes.** Standing user rule: *"lu jangan ngandelin alat bro, lu harus ngecek sendiri
  juga"*. A detector that keys on a *count* (`“` == `”`) or on one ordering heuristic will pass text that
  is visibly wrong. When your own eyes caught a bad line minutes earlier and the tool now says 0, the
  tool or the file changed — find out which before believing the 0.

### Check whether the model even PRODUCED the defect before you try to repair it

<!-- verified: seven scripts over six passes chased "reversed curly quotes" that did not exist in the
model's output — the MTL had emitted straight `"` quotes, correctly paired, and every `“`/`”` in the
file had been introduced by the first style pass, which paired them wrongly -->
The `“ ↔ ”` corruption you are hunting is frequently *your own* style pass's output, not the model's.
Before writing any repair script, measure the **untouched raw chunk output**:

```python
print(teks.count('"'), teks.count('“'), teks.count('”'))   # on the RAW chunk text
```

If the raw carries only straight `"` (and a balanced count of them), then the model has **no** quote
defect — the style pass is the sole source of the problem, and "reversed pairs" are an artifact of
the conversion, not something to sweep for. Converting `"`→`“”` correctly is then the *only* step
needed, and doing it once is enough. This one probe is what would have ended the multi-pass detour:
chasing a defect on a file you already rewrote is chasing your own pass's output. It is also why the
restore path is *rebuild from the per-chunk `terjemah` files*, never another edit of the mutated file.

- **Convert straight→curly by pairing from the left, one pass, and assert balance — but expect a
  chapter whose count is ODD, and do not "fix" it by re-pairing.** A chapter's quote count can be odd
  because a chunk seam split a dialogue (open in one chunk, close in the next) or the model omitted a
  closer. Locate the odd line and correct THAT line; do not re-run the pairing (that reverses correct
  lines and is the exact corruption this section warns about).
- **Distinguish a genuine reversed pair (`”text“`) from two correctly-ordered adjacent dialogs.**
  `"X.” “Y` is CORRECT — `”` closing the first dialog, `“` opening the second. A detector that flags
  "a `”` appears before a `“` on this line" fires on this normal case and reports thousands of false
  positives. Test per *pair*, or read the line, before calling it reversed.

### The MTL model's real quote defects are its OWN class — not a style pass

Straight→curly conversion (the SKILL.md quote axis) is a *style* normalisation and is safe as ONE pass
with balanced counts. But the model also produces defects no style pass fixes, and they must be swept on
the **raw chunk output**, before any normalisation:

- **Reversed dialogue (`”text“`).** The model occasionally wraps a spoken line with the closing quote
  first. Test per line: `p = line.find("“"); q = line.find("”"); reversed if q >= 0 and p >= 0 and q < p`.
  Fix the line by hand with it in front of you. Do **not** flip every such line in a bulk swap — the bulk
  swap also flips the correctly-ordered lines, which is how a "fix" makes the file worse.
- **A quote pair straddling a chunk boundary.** Because chunks are translated independently, a dialogue
  that opens in one chunk and closes in the next arrives with an unmatched quote at the seam. Treat the
  joined chapter (all chunks re-joined) as the unit for balance checks, never the individual chunk — and
  when a chapter's balance is off by one, look at the paragraph that *spans* two chunk files.
- **A chunk left UNTRANSLATED (source language, verbatim) or answered by the model instead of
translated.** The tell is a chunk whose joined length is far below the language-pair band — a chunk at
  ~66% of its source length is the signal. `repr()` it, do not trust the ratio alone. Verified: one chunk
  came back as the model TALKING TO YOU (`"…berikan teks bahasa Inggris lengkapnya, aku akan
  menerjemahkan seluruhnya…"`) and that reply was spliced into the novel as prose. Two fixes: re-request
  that single chunk, and **scan the joined text for the model addressing you** — grep for phrases like
  `teks bahasa Inggris lengkapnya`, `berikan`, `akan menerjemahkan`, `sesuai aturan`, and reject any chunk
  whose length is outside the band. A model-assisted "fix" pass is the wrong tool here: it can 
  silently drop a third of the text (a 39,536-char chapter returned as 28,368 chars) — gate every
  model-assisted text pass on a character-count check against its input and refuse a shrunken result.

## Volume is inherited FORWARD, and an existing column value is NEVER overwritten by a guess

<!-- verified: a novel's Volume 4 had no 'Volume 4' marker anywhere in its titles; a forward-inherit
guess silently rewrote its correctly-stored volume 4 down to 3 -->
Two rules that must both hold, in this order:

1. **Trust the stored `volume` column first.** If a row already has a non-NULL `volume`, keep it;
   only derive from the title when the column is NULL. Guessing over a known-good value is the one
   way this pass destroys data that a previous pass got right.
2. **Inherit a volume marker forward.** A volume number stated in one chapter title applies to every
   following chapter until a higher number appears — the chapters between markers have no way to know
   their volume otherwise. This is *why* iteration order matters: compute the per-row volume in a
   first pass over the rows sorted by `urutan`, then apply it.

Verify by grouping: `SELECT volume, COUNT(*), MIN(urutan), MAX(urutan) … GROUP BY volume` must match the
known breakdown before writing. A volume asserted from a guess that the stored column disagrees with is
a red flag to stop, not to write.

## Writing the result back, one novel at a time

1. Back up `naver.db` (full copy) and dump the novel's rows to `undo/<id>-sebelum-*.json`.
2. Run the cleaner with `--uji` first: it must print `paragraf BERUBAH: 0` and show before/after
   for titles, volume and text.
3. Run with `--tulis` (add the `volume` column if missing — `ALTER TABLE bab ADD COLUMN volume`).
4. **Verify from the DB, not the log:** the `volume` column exists, the volume breakdown sums to
   the chapter count, `0` chapters still carry the novel name in the title, `0` paragraphs still
   contain an inner `\n`, and one date-dash example reads correctly.
5. Report which novel id was done and which are still pending; do not proceed to the next novel
   without the user's go-ahead.

## The safety net must treat a line-JOIN `replace` as legitimate, not as damage

The `paragraf BERUBAH: 0` / `isi BERKURANG: 0` nets exist to catch deletion of real text. But the
cleaner's **primary job** is joining the source's layout-wrapped lines, which difflib reports as a
`replace` opcode (`'Selingan 7 —\nBagian Nene 4'` → `'Selingan 7 – Bagian Nene 4'` — same content,
newline folded to a space). A net that flags *any* `replace` fires on correct output and, worse,
teaches you to ignore the net. Restrict the danger test to **`delete` and `replace` that reduce the
character count outside the leading title region**; a same-or-longer `replace` at the start of the
text is the normal re-join. Verified against a 37-chapter novel after the fix: all nets green,
zero real changes.

### A UNIFORM `isi BERKURANG` across EVERY chapter is the header/footer strip doing its job

<!-- verified: `--uji` reported `isi BERKURANG: 39` and `paragraf BERUBAH: 101` on a 102-chapter novel —
every chapter down ~158 chars, and every span was the blog header/footer furniture -->
When the source is a blog (Kaito-style) and its header/footer furniture is still IN the stored text,
the cleaning run will report a uniform loss per chapter. That is the furniture leaving, not damage:
the per-chapter budget is deterministic (`judul tembel [LN] <novel> … Bahasa Indonesia` + ` by <name>`
+ `- <Bulan> <tgl>, <tahun>` + nav line + `Tags: …` ≈ 150-160 chars here). Two rules:

- **Strip the header/footer in the STAGING step, before the rows reach the warehouse**, so the
  `--uji` net does not fire on furniture and the run goes green legitimately. A net that always fires
  on correct input is a net you are being trained to ignore.
- **Judge by the distribution, not the total.** A *uniform* per-chapter drop is furniture. A drop
  concentrated in ONE chapter (that chapter far below its siblings) is real content loss — open it and
  read head+tail before suspecting the rule. Never widen or disable the net to silence a uniform number.

### `isi BERKURANG` is often SPACES AND GARBAGE, not lost story — prove it per-span with difflib

<!-- verified: seven chapters reported "kurang ~130-580 aksara"; every deleted span was whitespace or
furniture, zero story sentences -->
A shrinking character count is the net doing its job, not proof of damage. Prove it per-span:

```python
sm = difflib.SequenceMatcher(None, lama, baru, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag in ("delete", "replace"):
        print(tag, repr(lama[i1:i2][:200]))     # read EVERY span, do not scan
```

Safe spans are `' '` and `'\n'` — the cleaner's own line-join collapsing double spaces, plus the
dropped furniture. Danger spans contain story sentences. Expected shrink budget on a wrapped-layout
source: roughly `(joined line-pairs) × 1 space` per chapter plus the furniture length — hundreds of
characters per chapter is NORMAL once the spans are proven to be whitespace. **Do not roll back a
backup or re-run the pass over an unverified `isi BERKURANG` number**, and **do not report "0 loss"**
when the raw number is not 0 — say the count went down and name what went down (spaces, furniture).

## `--uji`'s "judul dirapikan N/M" is a CHANGE COUNT, not a damage report

A novel reading `judul dirapikan 51/52` on the dry run looks like 51 rows about to be mangled — it
was 51 genuine *improvements* (`'Volume 1 Prolog'` → `'Prolog'`). Before treating a high change
count as a red flag, print the stored title beside the proposed title for all N rows and read the
diff. Only the *diff* is evidence; the count alone is not.

## If the harvested titles are still misshapen, STOP — do not write

<!-- verified: two novels in a row produced `'Bab 1'` where that was really the first line of prose,
and `'Chapter'` truncated, because the title-harvest was imperfect -->
Once `--tulis` runs, the source's leading title lines are gone from the text, so a *second* harvest
has nothing to find — a bad title set written now cannot be re-harvested later. So: the text nets
going green licenses the *text* fix, not the *title* fix. If titles like `'Bab 1'` (actually prose)
or a truncated `'Chapter'` remain, report the novel as unfinished and leave the warehouse row
untouched. A wrong title is repairable from a backup; a cleaned-away title line is not.
