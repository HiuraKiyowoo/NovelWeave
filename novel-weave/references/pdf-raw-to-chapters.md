# Cleaning a PDF-sourced raw into archive chapters

Depth for the case where the raw is a **PDF** (a scan-less, text-layer PDF made in Word by a
fan-translation group) rather than a scraper dump or an EPUB. The text is a finished human
translation already in the target language, so there is no MTL step — the whole job is
structure extraction plus a cleaning pass, and the cleaning pass has its own defect set
distinct from the scraped-HTML one in `cleaning-scraped-chapter-text.md`.

## 0. Decide the raw is already in the target language, and that it is worth using

Read `pdfinfo` first (`Title`, `Author`, `Creator`, page count, encryption) and then the
extracted text. A PDF produced by `Microsoft® Word 2016` whose Title field is the work's
name and whose body reads as fluent target-language prose is a **finished translation** —
skip MTL entirely and say so. Two useful signals:

- **`Creator: Microsoft® Word …`** means a text PDF rendered from a document, not a scan —
  so `pdftotext` will be clean and OCR is unnecessary.
- The PDF's own `Keywords`/`Title` carry the translation group and source site. Record both
  for provenance, and treat the group as a **third party** (see `epub-import.md` §7: the
  "provably-perfect MTL loads straight to the main DB" carve-out does NOT apply — stage it
  and let the user approve).

A PDF whose pages are ~170 for a single volume and whose char count lands near 280k is a
normal full volume, not an excerpt. **Prove "this is the whole work" from outside the file**
— RanobeDB and the retailer's series page — never from the filename (see SKILL.md, "Proving
a work's TOTAL volume count").

### 0b. Read a MID-BOOK passage to prove language & quality — not the front matter, not the first heading hit
<!-- verified: a ruidrive ID set was confirmed "human Indonesian, fluent" by reading the SECOND
     `Prologue` hit in each file — the first hit is the ToC entry (`Prologue` at char ~357), the
     real chapter opening is the one after it (~2856), which is where real prose lives -->
When the goal is "is this a human translation in the target language, or English / MTL / a stub?",
the front matter lies: covers, credits and the table of contents still read as the title language
and say nothing about the body. Read a **real story passage from inside the book**:

- The first occurrence of a heading (`Prologue`, `Prolog`) is usually the **ToC entry**; the
  second occurrence is the chapter's own opening. Read from the *second* hit (see §2's ToC trap —
  the same heading appears in both places).
- Judge from the prose itself: does it read as fluent, natural target-language narrative
  (idiomatic dialogue, correct honorifics) rather than word-for-word machine output or English?
- Do this for a couple of volumes across the set (here: v01, v06, v11) — a single volume can be an
  outlier, and the point is to certify the SOURCE, not one file.
- Report the verdict with a quoted sample sentence as evidence, per the user's standing rule
  (`lu jangan ngandelin alat bro, lu harus ngecek sendiri juga`).

One clause of provenance this fixes: a set can be the **same** language as the front matter but
still MTL — the mid-book read is what separates a human translation from a machine pass over the
same PDF.

## 1. `pdftotext -layout` keeps the line structure you need to repair

```bash
pdfinfo <file>                  # page count, encryption, fonts, Title/Author
pdftotext -layout <file> out.txt
```

`-layout` preserves the rendered line breaks, which is what makes the wrapped-line repair in
step 3 possible. Do **not** use `-raw`; it reorders text by content stream and destroys the
line structure.

### 1a. PLAIN `pdftotext` (no `-layout`) SILENTLY TRUNCATES text at the column edge — always measure both
<!-- verified: a Shinra/Matcha PDF read 265,913 chars plain vs 296,335 with `-layout` — a 30,422-char
     loss. The truncated text was real prose, not whitespace: line 1 ended `… pilihan sederhana : Ya atau `
     with "Tidak." simply GONE, and interior lines lost whole words (`…terlihat begitu menawan hin`, `…terlihat keme`). -->
The failure is worse than the two-column loss in §1b because the output LOOKS complete — the char
count is plausible, prose flows, and the delivered text reads as if the author wrote chopped
sentences (`…terlihat keme`). Nothing errors; the only tell is a comparison against `-layout`.

**Always extract BOTH and compare before cleaning**:

```bash
pdftotext           novel.pdf plain.txt      # can truncate at the column edge
pdftotext -layout   novel.pdf layout.txt     # preserves rendered lines
wc -c plain.txt layout.txt                   # layout.txt should be >= plain.txt
```

If `-layout` is meaningfully larger, the plain output lost text — **use `-layout`, never plain**,
for any source where the two differ. A cheap spot-check on the truncation shape is to look for a
line ending mid-word or on a bare space: `re.search(r'\s$', baris)` at a line end is the tell.

**Corollary:** when the PDF was produced by a word processor (a `Microsoft® Word` `Creator`), the
renderer wrapped lines to the page width, so plain extraction truncates. Reserve plain extraction
for PDFs whose lines are already one-per-paragraph (see §2b) AND whose char count matches `-layout`.

### 1b. `pdftotext` can SILENTLY UNDER-EXTRACT a 2-column PDF — fall back to `pypdf`, and sanity-check the char count
<!-- verified twice on ruidrive 2-column PDFs: `pdftotext` returned 9,387 chars for a whole volume
     where `pypdf` returned 389,369 — a ~40× loss, with no error and no warning -->
On a **two-column** PDF, `pdftotext` often emits only the front matter (cover, credits, ToC) and a
few pages, then stops or drops most of the body — the output is a tiny fraction of the real text
and looks exactly like "this volume is nearly empty / the source is broken", NOT like a layout
problem. Never conclude a PDF is short or empty from `pdftotext` alone. **Always compare the char
count against an independent extractor** before trusting it:

```python
import pypdf                       # or `import fitz` (PyMuPDF) if installed
r = pypdf.PdfReader("v01.pdf")
print(len(r.pages), sum(len((p.extract_text() or "")) for p in r.pages))
```

Heuristic: a full LN volume is **roughly 300k+ chars** (a 300-500 page translated volume). If
`pdftotext` reports tens of thousands for something that long, **switch to `pypdf`/`fitz`** for
the extraction and keep the `-layout`-based join rules only for whichever tool preserved the line
structure you need. `pdftotext` and `pypdf` disagree wildly on which is "broken" — measure both,
use the one that yields the sane count, and record which tool you used.

## 2. Find the chapter boundaries, then CUT on them

The translation's own headings are the boundary markers: `Prolog`, `Chapter N`, `Epilog`,
`Kata Penutup`. They appear on their own short line, so an anchored regex over the extracted
text finds them all in one pass:

```python
import re
BATAS = re.compile(r'^\s*[^\S\n]*(PROLOG|Chapter\s+(\d+)|EPILOG|KATA\s+PENUTUP)\s*$', re.M | re.I)
bb = [(m.start(), m.group(0).strip()) for m in BATAS.finditer(teks)]
```

Then slice between consecutive hits (`teks[bb[i][0]:bb[i+1][0]]`, last one to end of file).

**Two traps, both verified:**
- **The same headings also appear in the table of contents**, so the first match is a ToC entry
  followed by dot-leaders (`CHAPTER 1 .......... 10`), not a chapter start. The anchored
  `^…$` form above rejects the dot-leader lines because they do not end at the heading; if your
  regex is looser, filter by "is the following content real prose of reasonable length".
- **Print the found boundary offsets before cutting.** 22 offsets with clean names is the proof
the split is right; a count that disagrees with the ToC means the regex caught something else.

**The ToC is not only a trap — it is the best source of the chapter NAMES.** Read it deliberately
(usually the first 2-3 pages): each entry is `<name> <separator> <page>`, and splitting on the
separator yields the exact name set to (a) match body headings against and (b) use as the DB title.
A PDF whose ToC names the chapters lets you skip any title-invention step entirely — reserve the
`Bab N` fallback for a source whose ToC is missing or page-number-only.

**Cut by page, then join — not by a flat text slice, when the boundary is page-aligned.** Page-splitting
the extract on `\f` and taking `[start_page:next_start_page]` keeps every chapter's content in its
own pages and survives a heading that appears mid-page. Confirm the page index of the first and last
chapter before slicing, and treat the last chapter's end as `len(pages)` rather than a heading offset.

## 2a. Harvesting the PDF itself: a download-aggregator page often offers GDrive/MEGA/MediaFire

<!-- verified: ruenovel.site offered three mirrors per volume; the GDrive link downloaded a clean
     text PDF with a single curl, no Cloudflare, no safelink redirect -->
Some aggregators (ruenovel.site and similar) publish **one post = one novel, one mirror set per
volume** and put the story in a PDF on the mirror. The GDrive mirror is the cheapest to harvest —
the `view` URL's file id converts to a direct download with no challenge:

```bash
grep -oE 'href="(https://(drive\.google\.com/file/d/|www\.mediafire\.com/file/|mega\.nz/file/)[^"]+)"' vol.html
# extract the id from /file/d/<ID>/ and pull the bytes:
curl -sL -o v1.pdf "https://drive.google.com/uc?export=download&id=<ID>"
file v1.pdf          # MUST say 'PDF document' — a 200 with an HTML body is the virus-scan interstitial
```

- For a large file GDrive can return the **"can't scan for viruses" HTML page** instead of the PDF;
  the tell is `file` reporting HTML, not PDF. Adding `&confirm=t` to the URL clears it.
- Confirm the page count with `pdfinfo` before trusting the file, and read the front matter to get
  the metadata the post card also lists (`Penulis`, `Ilustrator`, `Genre`, `Status`, `Tahun`,
  `Penerjemah`).
- The same rule as any third-party source applies: a human translation from an aggregator is
  someone else's work — quarantine, report, wait for approval (SKILL.md, third-party carve-out).

## 2b. `-layout` is the DEFAULT; plain is only safe when the lines are already one-per-paragraph AND the counts match

`-layout` (step 1) is the right default, because the wrapped-line repair in step 3c depends on it.
A source rendered so that each paragraph already sits on its own logical line needs no join, and
`-layout` then only adds indentation to strip — so plain `pdftotext` MAY be chosen, but **only after
proving it loses nothing** (§1a: compare `wc -c` plain vs `-layout`; if plain is smaller, it
TRUNCATED and you must not use it). Run plain, **measure before choosing**: a low median line
length with many short lines = wrapped (use `-layout` + join); a median near a normal sentence
length = already one-line-per-paragraph (plain is enough) — provided the char count agrees.

Verified on a 4-volume set rendered plain: the text arrived one paragraph per line, so no
line-join ran at all — and the residual defect was a *different* one (heading glued to the
first body line, step 3e). Do not port the `-layout` line-join onto a source that does not need
it; a join rule with nothing to join is a rule that can only misfire.

## 2c. A SET of volumes: verify each volume's identity before splitting, and number across the set

<!-- verified: a 4-volume set from one aggregator; the file named "Volume 04" contained Volume 01,
and one volume's ToC skipped a chapter number entirely -->
When the raw is several per-volume PDFs of ONE work, two traps appear that do not exist for a
single file. Both are cheap to close and expensive to miss.

**a) A mislabeled volume is undetectable by re-downloading.** Never trust the filename, and never
treat "I fetched it from another mirror too" as corroboration — every mirror of the same upload
serves the **same** bad file (`md5` identical across Mega/MediaFire/Terabox here). The only test
that works is comparing the file's OWN label against its name:

```bash
pdftotext "<pdf>" - | head -c 8000 | grep -o 'Volume[[:space:]]*0\?[0-9]' | sort -u
# and read the 'Daftar isi' page — the chapter NAMES identify the volume unambiguously
```

**The same md5 equality has a second, different verdict: the volume may simply NOT EXIST.**
<!-- verified: a two-volume post's "Volume 2" mirror (MediaFire) returned a file md5-identical to
     Volume 1 — twice, from a differently-encoded URL of the same link. The novel genuinely had one
     volume; the aggregator's second link was stale. -->
Before spending more effort hunting a "broken" mirror, compare the two files:

```bash
md5sum v1.pdf v2.pdf        # identical  -> the 'second volume' link serves volume 1
pdfinfo v1.pdf v2.pdf | grep -iE 'pages|title'
```

If the md5s and page counts match, the source has **one** volume and the extra link is a duplicate —
report that plainly and load the volumes you actually have. Do not keep re-trying mirrors, and do not
pad the shelf with a second copy under a "Volume 2" label (that silently duplicates the whole story).
The wrong-vs-absent distinction matters: a mislabel means *find the right file*, a duplicate means
*there is nothing to find*.

Run it for **every** volume in the set, not just the suspicious one. Two extra tells of a swapped
file: its watermark pattern differs from its siblings (`Ruidrive - NN_ruidrive.jpg` vs
`QWER - NN_ruidrive.jpeg`), and its ToC chapter names match another volume's. On a mismatch:
**stop — do not load it**, record it in `CATATAN/`, and ask the user for a correct link. Loading a
swapped volume silently overwrites a good volume's chapter list.

**The file's own internal label is NOT a reliable identity either — verify against the SOURCE raw.**
<!-- verified: a 4-volume set where THREE of the four PDFs were mislabeled; the file named
"Volume 04" internally said "Volume 01", and the files named "Volume 02" and "Volume 03" BOTH
contained the same later material — only "Volume 01" was correct. Re-downloading every mirror gave
the same md5, and the internal `Volume 01` label agreed between them, so nothing local exposed it. -->
A mislabel can be *self-consistent*: the wrong upload says "Volume 01" on its own first page and in
its footer, so the label-check in (a) passes while the content is a different volume than the
filename. When the work exists as a **free official web raw** (Kakuyomu/Syosetu — see
`references/web-novel-raw-sources.md`), pull that raw and use it as the authority the PDFs must
match. This is the only test that resolves a self-consistent mislabel, and it doubles as your
source for any volume the bad uploads lost.

**The tool is a NUMERIC FINGERPRINT: a distinctive fact in the prose maps a PDF chapter to its raw
chapter.** A streaming novel accumulates hard numbers that are unique per story-beat — subscriber
counts, viewer counts, ranks. Pull the raw chapters' titles and scan their text for the same kind of
fact, and you can name the exact range a mislabeled PDF came from:

```python
# the finished ID text says Rina has 700,000 subscribers; find which JP raw chapter says so
for b in raw_bab:
    t = open(b['berkas'], encoding='utf-8').read()
    if '70万' in t and 'アクシス' in t:      # 70万 = 700,000
        print(b['no'], b['judul'])
```

Any fact that changes monotonically across the story (a follower count, a rank, a competition
placement) works; the point is that it is *asserted in the prose*, so it identifies the beat without
needing to translate the raw. Verified use: `700,000` subscribers in the ID text matched the raw
chapter that states `70万` (chapter 45), proving the PDF labeled "Volume 02" was actually the raw's
later material — while the raw chapter with `60万` (chapter 31) shared its opening line with the same
PDF, exposing the mislabel. Cross-check two or three such facts before concluding; one match can be
a coincidence.

**Recovery order once a set is proven bad: look for a correct human translation FIRST, then translate the raw yourself.**
<!-- verified: a 4-volume set had V2/V3/V4 all wrong; a search across translation blogs and
aggregators found the work's volume split but NO correct Indonesian text for the missing volumes;
the run then fell back to MTL-ing the official raw range itself -->
Exhaust the cheap source search before committing to translation, and do it in this order:

1. **Search for a correct human translation of the missing volumes** (translation blogs,
   aggregators, the sites that surfaced in the original hunt). Read their ToC to confirm the
   volume split matches the raw — that alone is useful information even when their text is not
   usable.
2. **If a site holds the correct text, apply the third-party-content rule, do not take it
   silently.** A human translation is someone else's work → quarantine + report + wait for
   approval; the "provably-perfect MTL loads straight to the main DB" carve-out does NOT apply.
   Say this plainly when the user asks you to pull from such a site (see
   `references/web-novel-raw-sources.md` §2d).
3. **If no correct translation exists anywhere, translate the raw range yourself** with the JP→ID
   pipeline (`references/jp-to-id-translation.md`) — the raw is free and official, so this is the
   clean-provenance path, and it also becomes the authority for correcting the mislabeled volumes.
   Scope the job to the exact chapter range the mislabel lost (map it with the numeric fingerprint
   above), not the whole work.
4. **Do not leave the bad volumes loaded while you search.** The wrong chapters read out of order
   to the reader; either fix the `volume` mapping immediately or report the damage and hold.

**A mislabeled volume that was ALREADY LOADED is an audit, not just a re-import.** Do not assume the
bad file only threatens the load you were about to do. Re-derive which raw range every already-
inserted chapter actually came from (same fingerprint technique, run over the rows in the DB), list
which chapters are in the wrong volume, and report the whole picture before changing anything.

**Re-mapping the `volume` column is NOT enough when the loaded text is a DUPLICATE of another
volume.** <!-- verified: V2 and V3 both carried the same later-range text as V4, so no re-labeling
could make them correct — the rows had to be deleted and replaced by the real MTL set --> Decide
which of two damages you have before touching a row:

- **Wrong LABEL, right text** (the chapter belongs to this novel but the `volume`/`nomor` is off):
  fix the columns only.
- **Wrong TEXT** (the loaded chapters are a duplicate of another volume's range, i.e. the same
  scene appears twice on the shelf): re-labeling leaves the duplicate in place and the real volume
  missing. **Delete the bad volume's rows and insert the correct set under the SAME novel id.**

Procedure for the duplicate case, in this order:
1. **Back the DB up first** (`cp naver.db naver.db.bak-sebelum-perbaiki-<slug>`), then do the swap —
   a delete-and-reinsert of a whole volume is not reversible otherwise.
2. **Delete only the affected volume**, never the whole novel: `DELETE FROM bab WHERE novel_id=? AND
   volume IN (…)` plus their `bab_gambar` rows. The correct volume(s) of the same novel must stay
   untouched — confirm the survivor count before inserting anything.
3. **Insert the replacement set under the same `novel_id`** and keep the GLOBAL `nomor`/`urutan`
   continuous across the surviving volumes (see (c) above) — a volume swap must not renumber the
   book or the reader's order changes.
4. **The correct text usually comes from your own MTL** of the official raw range — that is the
   clean-provenance replacement, and it also means the title column needs the full JP→ID title pass
   (marker strip + style match; see `references/jp-to-id-translation.md` § Titles).
5. **Re-verify from the WEB, not just the DB, and not from a cached page.** The detail page can keep
   serving the old chapter list after a DB write; confirm with a DB read AND a fresh fetch of the
   novel page, and if the page still shows the old list, restart the web tier before concluding the
   write failed.

**b) A gap in the source's own ToC is a SOURCE defect, not your splitter.** One volume's ToC ran
`Chapter 2 → Chapter 4` with no Chapter 3. Prove it before reporting either way: `grep` the missing
heading across the **whole** PDF (`pdftotext f - | grep -c 'Chapter 3'`). Zero hits = the
translator dropped it; report as a source defect. Non-zero = your boundary regex missed it; fix the
splitter. Do not paper over the gap with a chapter from a neighbouring volume.

**b1b) A whole ToC's worth of headings can be ABSENT from the body — the PDF was built without the
chapter-title pages.** <!-- verified: a ruidrive volume whose ToC listed `13, 14, 15, 16, 16.5, 17,
17.5, 18, 19` (and a sibling whose ToC listed `Prolog, 1, 2, 3, 4, Epilog`) produced ZERO heading
boundaries from the body — the uploader simply omitted the title pages. -->
A bare `^\d{1,3}$` regex will then match the per-page NUMBER instead, minting dozens of 1-3k-char
"chapters" — and worse, swallowing the real chapters. Prove the headings are absent (not that your
regex is wrong) by reading the PDF page-by-page before concluding:

```python
r = pypdf.PdfReader("v10.pdf")
for i, pg in enumerate(r.pages):
    t = (pg.extract_text() or "").strip()
    if t and len(t) < 400:                    # a chapter-title page is always short
        print(i + 1, repr(t[:150]))
```

No short page carries a chapter name → **source defect**. Report it honestly; never invent titles and
call them the original. Handle it by: (1) rebuilding paragraphs from the hard-wrapped lines first
(§3c/§3c2 — the PDF has almost no `\n\n`), (2) splitting the rebuilt PARAGRAPH list into the number of
chapters the ToC names, cutting only on paragraph boundaries — an equal split over a raw string cuts
mid-sentence and gives chapters opening on fragments like `akan membunuhmu! Dan kau, Amatsu…`, (3)
titling them `Chapter <ToC number>`, and (4) recording the split in `CATATAN/`. See the sibling
`naver-panen-sumber-blogger` → `references/blogspot-feed-dan-rapikan.md` §6c for the aggregator-side
detail.

**b2) A DUPLICATE chapter label is the sibling defect — renumber by POSITION, and take the names
from the ToC anyway.**
<!-- verified: one volume's ToC listed `Chapter 1` twice and no `Chapter 2` at all, and the body
     agreed (two `Chapter 1` headings). The second one's opening content — a chapter's own setting
     and cast — is plainly chapter 2. -->
A Word-rendered translation can repeat a heading, so counting distinct heading TEXTS under-counts the
chapter list and leaves a duplicate number in the title column. Two rules:

1. **Number the story chapters by their ORDER of appearance, not by the number printed in the
   heading.** Walk the boundary list, increment your own counter for each `Chapter …` hit, and store
   that — so two `Chapter 1` headings become `Chapter 1` and `Chapter 2`. Cross-check the final count
   against the ToC's chapter-entry count; a mismatch means you caught a heading twice, not that the
   book has an extra chapter.
2. **Still harvest the NAMES from the ToC, because the ToC is where they are authoritative.** A ToC
   can carry the full name (`Chapter 1: Festival Olahraga dan Melankolis Narika`) while the body
   heading is truncated to two lines and the pattern differs per volume (`Chapter 1 : <name>` vs
   `Chapter 1 — <name>` vs bare `Chapter 1`). Build the name set from the ToC once, then match
   body headings against it — and when the body heading is genuinely truncated mid-phrase
   (`Chapter Bonus 3 — Hinako dan`), the ToC gives the completion (`… dan Bantal Guling`).
3. **Do not let a heading's own `Part N` sub-label leak into the body.** These translations mark
   sub-parts (`Part 1`, `Part 5`) under a chapter; strip the bare `Part N` line wherever it sits
   (including mid-chapter), since it is structural, not prose.

**c) Number across the SET, not per volume.** When inserting several volumes of one novel, `nomor`
and `urutan` must run **globally ascending** across the whole novel (the site lists the chapters in
reading order off these), while `volume` carries the per-volume number and the title's `Bab N`
restarts at 1 inside each volume. Read the last row's `MAX(nomor)`/`MAX(urutan)` for that novel
first and continue from it; do not restart the global counter at 1 for the second volume, or the
chapters interleave.

**d) Write the splitter as ONE parameterised tool, not a per-volume script.** A signature like
`pisah-<work>.py <pdf> <volume> <out.json>` run once per volume keeps the cleaning rules identical
across the set and makes the mislabel check in (a) a per-file assertion rather than a chore. A
per-volume copy of the script is how the rules drift between volumes.

## 2d. A char-count "loss" after cleaning is usually SPACING, not missing text — prove it by NON-WHITESPACE count

<!-- verified: a 490-page volume read 377,706 chars raw and 293,611 after cleaning — an apparent
     84k "loss". It was entirely indentation, blank lines and headers: the same chapter measured
     79,471 raw vs 78,209 cleaned, and the story ran intact to the last line. -->
When a source is already close to one-paragraph-per-line, the raw total minus the cleaned total is
mostly whitespace you deliberately dropped. Do **not** read a large negative delta as lost prose:
compare a single chapter's raw slice against its cleaned text (delta should be small and all
whitespace), and confirm the LAST chapter ends on the source's own closing line. A genuine loss
shows up as a chapter whose cleaned length is a fraction of its raw slice, not as a uniform few-percent
shrink across every chapter.

**The cheapest proof is the NON-WHITESPACE character count of the WHOLE text — do this first, before
digging per chapter.** <!-- verified: a 447-page PDF read 383,898 raw vs 338,543 cleaned = an apparent
     45k "loss" that looked alarming. Stripping whitespace from both gave 383,898→ still 383,898 raw and
     the cleaned text's non-space count was within 195 chars (0.07%) of it — the entire "loss" was
     spaces, blank lines, running headers and page furniture. Only then was per-chapter work worth doing. -->

```python
import re
nsp = lambda t: len(re.sub(r'\s+', '', t))
print(nsp(raw), nsp(cleaned))     # a delta of ~0.1% or less = whitespace only, NOT lost prose
```

Run this on the raw extract and the cleaned output BEFORE worrying about "missing text". A
non-whitespace delta under ~1% is proof the story is intact, whatever the total char count says.

**Corollary: moving chapter titles into metadata makes the PARAGRAPH count drop by ≈ the chapter
count — that is not lost text either.** When the clean pass harvests each chapter's heading out of
the body and stores it in `bab.judul` (per §3e), the paragraph count falls by exactly the number of
chapters whose title line was a paragraph. Verified: 4,403 raw paragraphs → 4,394 cleaned = a delta
of 9, which matched the 9 chapter titles relocated. So when paragraph count drops, first check
"does the drop equal the chapter count?" and account for the title lines before suspecting a
swallowed paragraph — and confirm the non-space char delta is still ~0.

## 2e. NEVER let a whitespace normaliser touch `\n` — a `re.sub` that inserts a space after `.`
can EAT the paragraph break and merge chapters' paragraphs

<!-- verified: a 'insert a space after a period before a capital' pass written as
     re.sub(r'([a-z]) \. ([A-Z][a-z])', r'\1. \2', t) ran over the WHOLE text (newlines included),
     collapsing ~352 paragraph breaks in one volume (4088 -> 3736 paragraphs) and 326 in another. -->
A sentence-glue fix (`.Next` -> `. Next`) must be applied **per paragraph, on strings that contain
no newlines** — split on `\n\n` first, fix each paragraph, rejoin. Run it on the whole text with a
`.` -> `. ` substitution and the pattern can match across the blank line, silently welding two
paragraphs into one. The damage is invisible in total char count (it goes DOWN, looking like
cleaning) and only shows in the **paragraph count** — so always print paragraph count before/after
every normalisation pass and treat a DROP as a bug, not progress. Same rule for any rule keyed on
punctuation: scope it to a single paragraph.

## 3. The defects a PDF text layer adds — all seven, all verified

**a) A per-page running header repeating the novel name.** `pdfinfo` and the page text carry
`PAGE <N> OF <TOTAL> | <Novel Title>` once per page (170× for a 170-page file). Strip both
halves with two patterns (`PAGE\s+\d+\s+OF\s+\d+` and the title), and count the hits before
and after — the expected end state is 0.

**The header's exact shape varies by group, so match the LETTERS, not one literal format.**
<!-- verified: a different group's PDF stamped `<N> - KAITO NOVEL` (number, hyphen, group name)
AND a full `<Novel Title> … Volume <N>` footer line per page, 751× across a 375-page volume -->
Both halves can change form (`N - GROUP NAME` instead of `PAGE N OF M | Title`; the full title instead
of a short one). Write one case-insensitive rule per repeating string — a bare `<domain/group>` token
on a line, a `<N> - <GROUP>` shape, the work's full title line, and a `Volume <N>` footer — each as
`re.fullmatch` on a stripped line where the string is short, and count before/after. Do not assume the
first group's header format; read one page's `repr()` first.

**A group header can carry its page number mid-line in brackets — match the whole line shape, not
just the number.** <!-- verified: a Matcha PDF stamped `Shinra - [ 12 ] - Novel` once per page
(303× on a 313-page file), the number bracketed between the group name and the literal word
"Novel". --> This is a fourth shape: `GROUP - [ N ] - Novel`. Strip it with a regex that anchors on
the group name and the trailing `Novel` word (`re.fullmatch(r'\s*<GROUP>\s*-\s*\[\s*\d+\s*\]\s*-\s*Novel\s*', s, re.I)`)
rather than a bare `\[\d+\]`, or you eat a bracketed numeral the author wrote in prose. Confirm
0 hits after the sweep, and re-check the same shape's residue on a partial-count source.

**b) A credit page.** The translator/uploader block (`<Group>`, site name) appears once, not
per page. Strip it too, but only after harvesting the group name for provenance.

**b2) A per-page SITE-DOMAIN watermark plus a volume footer — the aggregator's own mark.**
<!-- verified: a ruidrive.com-sourced 4-volume set carried the bare line `ruidrive.com` 432×/408×/
447× in three volumes and 45× in the fourth, next to a `Volume 01` footer -->
A download-aggregator's PDF stamps its own domain as a **whole line by itself** on most pages,
with a `Volume N` footer under it. Unlike the `PAGE N OF M | Title` header it carries no page
number, so match it as an **exact whole line** (`s.strip().lower() == '<domain>'`, and
`re.fullmatch(r'Volume\s+\d+', s, re.I)` for the footer) — never as a substring, or real prose
mentioning the site is eaten.

Three companions come with it, all found in the same set:
- **An illustration filename line** (`QWER - 07_ruidrive.jpeg`) listing the embedded image — a
  filename, not prose. Match the filename *shape* (`\w+\s*-\s*\d+_<domain>\.jpe?g`), not the word.
- **A multi-line PROMO block planted mid-novel** — a greeting to the reader naming the site, a
  donation link, and a closing thank-you, spanning ~9 lines and sitting *inside* a chapter after
  the story. Strip it as a **block bounded by its own first and last lines** (grep for the greeting
  to find its extent once, then one regex from that line through the thank-you with a non-greedy
  `[\s\S]*?`), not line by line — a line-by-line rule leaves the block's prose middle behind.
- **The promo block is sometimes spliced BETWEEN SENTENCES, so the story resumes on the same
  paragraph — count occurrences, do not repair just the first.** <!-- verified: one volume carried
  the block 8× with the surrounding story text left fully intact on both sides, e.g.
  `"…pastikan kau mengantarnya pulang!"` + BLOCK + `"Apakah itu keterlaluan?"` --> Two rules:
  strip it wherever it sits (a single `re.sub` with `re.I|re.S` handles every occurrence — do NOT
  break after the first match), and **before deleting, `repr()` ~180 chars BEFORE and AFTER the
  match** to confirm the story text on both sides is whole. A block that splits a dialogue pair is
  the shape that a "strip the trailing block" rule misses entirely. After the sweep, re-grep the
  deleted block's distinctive words (`ruidrive`, `trakteer`, the greeting) over the WHOLE text and
  require 0 — plus confirm the story line that followed the block now runs on cleanly from the one
  before it.
- **The aggregator's donation URL** (`https://trakteer.id/<handle>`) on its own line.

**The watermark count is NOT uniform across a set** (432 / 408 / 447 / 45 here). One volume
reading clean is a reason to check it, not a reason to skip the sweep on the others. Expect the residue
after stripping to be a small non-zero number (28 of 432 here) and **read those remaining lines**
before declaring done — they are usually the illustration filenames and intro-page marks from the
rules above, but "usually" is exactly what the eye is for.

**c2) A TWO-COLUMN layout breaks the line-to-line join — you must also join ACROSS paragraphs.**
<!-- verified: ruidrive.com PDFs are laid out in two columns, so `-layout` emitted a sentence
split at the column edge with a BLANK line between the two halves — `"…melon soda melalui
sedotan. Sedotan"` / blank / `"plastik itu berubah hijau saat kuhirup…"`. A §3c line-join run on
that input rejoined nothing, because the halves are in separate paragraph blocks. A second
attempt that merged the paragraphs still failed on the page-break case. -->
When the source is **two-column**, treat `\f` (page break) as a paragraph break, merge each
block's lines, then **run the join ONCE MORE across the merged block list** — a block whose
predecessor does not end on terminal punctuation is a column-break artefact, not a paragraph:

```python
def bersih_pdf_2kolom(t):
    t = t.replace('\x0c', '\n\n')                               # page break = paragraph break
    par = [p for p in re.split(r'\n\s*\n', t) if p.strip()]
    par = [' '.join(x.strip() for x in p.split('\n') if x.strip()) for p in par]
    out = []
    for p in par:
        if out and not re.search(r'[.!?"\u201d\u2019:\)\]]$', out[-1]):
            out[-1] = out[-1].rstrip() + ' ' + p                  # <-- the cross-paragraph join
        else:
            out.append(p)
    return '\n\n'.join(out)
```

**How to detect a missed cross-paragraph join, and its false alarm.** Sweep for paragraphs whose
FIRST character is lowercase — a real column break leaves `"… sedotan. Sedotan"` / `"plastik itu
berubah…"`. But lowercase-opening paragraphs are ALSO legitimate content: a chat/message label
(`kohaku: Kalau mau, aku bisa bagi catatanku`) and other non-sentence starts. `repr()` every
candidate before acting. Also sweep for a paragraph ENDING on a dangling conjunction/preposition
(`dan`, `yang`, `di`, `ke`, `dengan`) — zero of those is the clean end state.

**The residual counts are what prove the join, not the raw line count.** On the two-column set,
2,212 wrapped lines → 685 after the line-join (§3c) is the *incomplete* state; the cross-paragraph
pass is what actually closes the gaps. Print the leftover count and READ the leftovers.

**c) Lines wrapped to the PDF's page width — the big one.** `pdftotext -layout` reproduces the
rendered line breaks, so one real paragraph arrives split across many lines that end
mid-sentence:

```
Bukannya aku tidak tertarik dengan lawan jenis. Di sekolah menengah pertama, aku
memiliki seorang gadis yang kucintai tak berbalas dan di sekolah menengah, aku
membayangkan pacar idealku.
```

Join a line to the **next** line when the current line does NOT end on sentence-terminal
punctuation:

```python
AKHIR_OK = re.compile(r'[.!?…""\'"\)\]]\s*$|[—–-]$|:$|“$')
def sambung(t: str) -> str:
    out = []
    for l in t.split("\n"):
        l = l.rstrip()
        if not l:
            out.append(""); continue
        if out and out[-1] and not AKHIR_OK.search(out[-1]) and not l.startswith(("—", "–", "“", "「")):
            out[-1] = out[-1] + " " + l.lstrip()
        else:
            out.append(l.lstrip())
    return "\n".join(out)
```

Blank lines stay paragraph breaks (they are the author's, not the layout's). Measured on a real
volume: **2,212 wrapped lines → 685** after the join. The residual ~685 are NOT defects — they
are **dialogue lines**, which legitimately end on a closing quote the naive terminal set misses,
plus short lines ending on a comma before a speech tag (`… dan berkata,`). Confirm this by
listing the residue and reading it: if every leftover line is a quoted utterance or a
speech-tag lead-in, the join is done. Budget for this check — the raw count after joining looks
alarming and is usually fine.

**c1) A source with NO blank lines at all: reconstruct paragraphs from "the line ends on terminal
punctuation", not from `\n\n`.** <!-- verified: a single-column hard-wrap PDF (a different
aggregator than the two-column one in §3c2) delivered ~95% short lines with only ~28 real `\n\n`
in a whole volume, so a join keyed on blank lines rebuilt ONE giant paragraph per chapter. -->
When the PDF has no paragraph separator to trust, the paragraph boundary IS the sentence end. Do
this pass in a strict order:

1. Walk the lines **first** (before any other join): promote a single `\n` to `\n\n` when the
   line above ends on a terminal mark (`[.!?…”]`), otherwise replace the single `\n` with a
   space to close the hard wrap. Measured: 762 wrapped lines → 234 real paragraphs.
2. **Then** repair the over-splits the rule in (1) creates: a `\n\n` followed by a lowercase
   letter is a sentence continuation, not a new paragraph → join it back with a space, EXCEPT
   when the next block opens with a quote (`“`) — that is a legitimate new dialogue paragraph.
   Without this second pass, mid-sentence breaks remain (`perlahan-lahan` `\n\n` `menerima konsep`).
3. **Do NOT merge a monologue that legitimately spans two paragraphs.** One speaker can legitimately
   own a two-paragraph line (a long speech split for readability); a merged-to-one-paragraph rule
   destroys that shape. It is a *separate* case from a paragraph broken mid-sentence — the tell for
   the break is the sentence cutting mid-clause, whereas the monologue split falls on a sentence end.

**The join direction is the trap: JOIN a line to the PREVIOUS one when the previous line does NOT
end on terminal punctuation — never the reverse.** <!-- verified: on a no-blank-line PDF, a first
script joined lines when the NEXT line did not end on terminal punctuation and produced ONE giant
merged block per chapter; the fix was to test the PREVIOUS accumulated line instead. --> The
correct rule (already written this way in §3c's `sambung()`), restated because it is easy to invert:
append a new line to `out[-1]` only when `out[-1]` does not end on `[.!?…"]`; a line that ends on a
period STARTS a new paragraph. Inverting the test (keying on the incoming line's own ending) yields
the exact opposite of what you want — a single blob — and the char count stays plausible, so nothing
flags it. Symptom to watch for: paragraph count COLLAPSES (e.g. hundreds of lines → a handful of
paragraphs) right after the join. That is the inverted rule, not a source that "has long paragraphs".

**c1b) Blank lines that mark PAGE breaks, not PARAGRAPH breaks — the fourth layout case, and the
one that produces plausible-looking but fused output.**
<!-- verified: a Shinra-sourced PDF delivered one paragraph per page-run of lines with `\n\n`
     ONLY where the page ended (plus a running header between). A `\n\n`-as-paragraph-separator
     rule emitted just 44 paragraphs for a 41k-char chapter (avg 497 chars/paragraph) where the
     correct reconstruction is 534 paragraphs (avg 79). The chapter read as huge monolithic
     blocks and a sentence was split mid-word (`… kafe te` + `luang yang aku punya` = "kafe
     telepon") because the page break AND the stripped header had eaten the join seam. -->
A PDF rendered by a word processor can put a blank line at each page boundary (the natural gap
after the last line before the header) while every real paragraph runs line-after-line with no
separator. The `\n\n`-as-paragraph rule then "succeeds" — no error, a plausible char count, prose
that reads — but the paragraphs are page-sized and the header strip has removed the seam where the
wrapped sentence should have been joined. Three rules, in order:

1. **Decide which meaning `\n\n` has BEFORE writing the split:** count the `\n\n` and compare it to
   the page count (`pdfinfo`). A blank-line count on the order of the page count is a PAGE
   separator, not a paragraph separator — reconstruct paragraphs with §3c1's terminal-punctuation
   walk instead.
2. **Strip the running header by REPLACING it with the blank line it sat on, not with nothing.**
   When the header occupies the only line between two body runs, deleting it (`re.sub(…, '')`)
   consumes the break and welds the two body lines together; substitute a `\n` (or keep the
   surrounding `\n\n`) so the join pass still sees a seam. Then re-run the join — the mid-word
   `'… kafe te'` / `'luang…'` split is the signature of a seam that was eaten, not of a bad source.
3. **Verify by average chars-per-paragraph, not by the total.** The total char count stays
   plausible through this bug; the collapse shows only per-paragraph. Compute
   `total_aksara / jumlah_paragraf` and expect a normal narrative average (roughly 60-120 chars)
   — an average in the hundreds of chars per paragraph means paragraphs are still fused. Print the
   per-part table and read it.

**c1b2) The title rule must know EVERY heading shape the file uses, and a title line that ENDS ON A LETTER gets eaten by the wrapped-line join.**, so the wrapped-line join eats it into the next
paragraph — detect titles BEFORE joining, and name EVERY heading shape the file uses.**
<!-- verified three times in ONE work: `Hari ke-1` / `Prolog` / `Life4-1 Hina Datang Berkunjung` all
     end on a bare letter, so the §3c1 join ("previous line does not end on terminal punctuation")
     appended the first sentence of the chapter to them, producing chapter titles like
     "Prolog pdf ini…" and "Hari ke-1 Aku terbangun…", and the boundary regex then found ZERO
     chapters (all 5 volumes reported as a single `Pembuka`). -->
Any heading that does **not** end on `[.!?…"]` is indistinguishable from a wrapped line by
punctuation alone — and titles are exactly the short lines that end on a letter. Rule order matters:

1. **Match and LIFT the title lines out of the line stream BEFORE the join runs**, not after.
   Keep a placeholder or emit the title as its own paragraph, then join only the body lines.
2. **Match the title on its SHAPE, not on a punctuation ending** — a short line (`<= ~60` chars)
   with no terminal punctuation that also matches the heading vocabulary (`Prolog|Epilog|Penutup|
   Pembuka|Afterword|Bonus …|Hari ke-\d+|Chapter \d+|Life\s*\d+-\d+|Life\s*Sub-?\d*`).
3. **A heading can be glued to its first sentence in the SOURCE, so cut it, don't just skip it.**
   When the PDF line reads `Life4-1 Hina Datang Berkunjung "Jin-san…"`, split at the first quote or
   sentence-start after the title and keep the remainder as the chapter's opening paragraph —
   dropping the whole line loses real prose (verified: 27-paragraph chapters would have lost their
   opening sentence).
4. **Enumerate every heading shape per volume and print the list — styles differ INSIDE one work.**
   This set mixed `Life1-1 <name>`, `Life 2-3 <name>`, `LifeSub-1`, `Life Sub-2`, and bare
   `PROLOG` / `Penutup` / `Bonus E-book …`. A regex covering only the first shape made volumes 3-5
   collapse to one giant chapter, and a `[-–]` character class written before a space silently
   became a RANGE instead of a literal hyphen. Prefer `[-\u2013]` with the hyphen FIRST and test the
   regex against each real heading string before running it over 5 volumes.

Symptom to watch for: a volume reports **1-2 chapters with a huge char count** (200k+ in one
"Pembuka") — that is this bug, not a source without chapters. Fix the title rule and re-run; do not
start inventing `Bab N` splits to compensate.

**The `<Title> ~ <Group>~` form (RueNovel and similar) is another header shape — a tilde-wrapped
group name appended to the work's title on EVERY page.** <!-- verified: a RueNovel PDF stamped
`Maou ni Natta node, Dungeon Tsukutte Jingai Musume to Honobono Suru ~ Rue Novel~` (note the space
before the closing `~`) as the first line of every page. Because the line is the full title, a bare
`<GROUP>` token match misses it; match the trailing `~ <Group>~` suffix, or the whole title line. -->
Treat it as the "full title line" shape already listed above: strip it per page and require the
count to fall to 0. The same PDF family also carries the group's own domain as a bare line
(`https://www.ruenovel.com/p/<slug>.html`) — a source URL, not prose, strip it whole-line.

**A running header can have MORE THAN ONE shape inside a single file — sweep for every shape, and
count each to 0.** <!-- verified: one PDF stamped BOTH `<Novel Title> - Shinra Novel` AND
`[ N ] - Shinra Novel` on different pages; a filter written for the first shape left the second in
the text, and because that residue was a bare bracketed numeral line it silently became a
paragraph break that was never there. The fix was a second pattern for the `[ N ] - <GROUP>` form. -->
Before declaring the furniture sweep clean, print the count of every header shape you know of
(the full-title form, the `GROUP - [ N ] - Novel` form from §3a, the bare `<N> - <GROUP>` form,
a bare group/domain token) plus a residual `re.findall(r'\[\s*\d+\s*\]')` over the whole text —
any non-zero count is a header variant still in the body. See §3a for the shapes.

**A no-blank-line PDF is a THIRD case from §2b's "already one line per paragraph" — measure line
lengths before picking the rule.** <!-- verified: a Shinra-sourced Matcha PDF delivered ~one short
line per PDF line with no interior `\n\n` at all, so paragraph boundaries had to be *created* from
the terminal-punctuation walk above, not preserved. --> §2b's "no join needed" verdict applies only
when the median extracted line is already a normal sentence length. When the median line is short
(a hard-wrapped column), the source is this case: reconstruct paragraphs per steps 1-3 here before
doing anything else.

**Verify by reading a full chapter, not by counting.** The intermediate state after (1) looks
clean by every char/paragraph count yet still reads broken; only reading a whole chapter catches
the residual `\n\n`-mid-sentence cases. This is the class where the user's rule bites hardest:
*"lu jangan ngandelin alat bro, lu harus ngecek sendiri juga."*

**d) The layout's own scene separator and a garbled sound effect.** The PDF uses a bare `|` on
its own line as a scene break (163× here) — convert it to the archive's `***`. And a strip of
repeated separators can arrive as `******`; collapse `\*{4,}` to `***`. A torn sound effect
(`-*sret*`, `— *clack*`) is a PDF artifact on a reversed-syllable onomatopoeia — drop those
lines rather than trying to repair them.

**d1) The per-page number sits at the END of the extracted page text, so a "is the next line long?"
rule never fires — strip it from the page TAIL.**
<!-- verified: a 364-page Word PDF put `12` as the FINAL line of page 12's text
     (`"…senyum lembut.\n\n2\n\n\f"`), and a stripper that inspected the NEXT line after a bare
     number left ~150 page numbers in the body. A second attempt keyed on "the number is followed
     by a long line" also failed, because there is no following line at a page boundary. -->
A bare `^\d{1,3}$` line inside the body is ambiguous — it can be a page number OR a real
standalone numeral the author wrote (a count, a date, a chapter's own scene number). Resolve the
ambiguity **by position, not by shape**: the page numeral is emitted at the tail of that page's
text, immediately before the `\f` page break, whereas the author's numeral sits mid-paragraph
between sentences.

```python
def buang_nomor_halaman(t: str, maks: int) -> str:
    # maks = the PDF's own page count, known from pdfinfo — a number larger than it is content
    return re.sub(r'\n\s*(\d{1,3})\s*\n*\f', '\n\f', t)   # numeral glued to the page break
```

Gate on `int(m) <= page_count` so a real `100000` in the prose is never eaten, then sweep the
finished text for a residual bare-numeral line and **read each survivor** — a leftover that is a
story number stays, a leftover that matches a page index is a miss. Expect the count to go to 0
for a cleanly-numbered source.

**d2) Joining wrapped lines can MINT an ellipsis artefact — normalise `…` in each line BEFORE the join.**
<!-- verified: 175 `....`-shaped defects appeared in the output of a line-joining pass. The cause was
     the join itself: the PDF wrapped mid-ellipsis, so line A ended on `.` and line B began with
     `..`, and `cur += " " + s` fused them into `....`. `rapikan()` on the joined paragraph could not
     reliably repair it because the artefact is born during the join, not before it. -->
A `…` (or `...`) that lands on a line boundary arrives as a trailing `.` plus a leading `..`/`...`.
Any rule that inspects or rewrites ellipses **after** the join is fighting an artefact the join just
created. Normalise the dots **on each line, before joining**:

```python
EL = '\u2026'
def norm_titik(s: str) -> str:
    s = re.sub(r'\.{4,}', EL, s)                 # '....+'  -> '…'   (order matters: longest first)
    s = re.sub(r'\.{3}',    EL, s)               # '...'    -> '…'
    s = re.sub(r'(?<!\.)\.\.(?!\.)', EL, s)     # '..'     -> '…'   (not part of a longer run)
    return s

baris = [norm_titik(b) for b in baris]           # ← BEFORE gabung()/sambung()
par   = [rapikan(p) for p in gabung(baris)]
```

Then sweep the finished text for `\.{4,}` and require **0** — a non-zero count after a line-join
points at the join, not at the punctuation rules. Keep the post-join normaliser as a second net,
but never rely on it alone: the pre-join pass is what makes the fix deterministic.

**A `"… text"` opener is the translator's own style for hesitant speech, not a defect — do NOT
"fix" it.** In the same volume, 400 dialog lines opened `"… Tidak, …"` against 11 that opened
`"…Tidak"`. The `"…<space>` form is how this translator renders the Japanese `「……そう」` beat, so a
sweep that removed the space would rewrite 400 lines of intentional voice. Confirm a high-count
"irregularity" is style (present at scale, consistently) before treating it as damage; only the
cases with a *mechanical* cause (the join artefact above) are bugs.

**e2) A heading can be rendered in STYLED UNICODE, so an ASCII-case regex never matches it.**
<!-- verified: a Word-rendered volume set every chapter heading in the Mathematical Alphanumeric
Symbols block — `𝒫𝑅𝒪𝐿𝒪𝒢`, `𝒞𝐻𝒜𝒫𝒯𝐸𝑅 1` — and `pdftotext` emitted those codepoints verbatim, so a
`re.I` match on the ASCII names found NOTHING. -->
A translation laid out in a word processor can style its headings with **Mathematical Alphanumeric
Symbols** (U+1D400-U+1D7FF: `𝒜-𝒵` script/bold/fraktur, `𝟢-𝟫` digits). Every heading looks like ordinary
uppercase to the eye but is a different codepoint, so `re.compile(r'PROLOG|CHAPTER', re.I)` returns 0
boundaries and you conclude the PDF has no chapter markers. Fix it in two steps, in this order:

1. **Normalise the text BEFORE any boundary regex**: `unicodedata.normalize('NFKC', s)` folds the
   mathematical letters to ASCII, and an explicit `str.translate` map over the block is the belt-and-
   braces fallback for codepoints NFKC leaves alone. Do this on each page's text at extract time, so
   every later rule sees plain ASCII headings.
2. **A near-empty "chapter" is the tell.** When a boundary was found but the slice is only a few
   characters (or the heading line survives into the body), the styled/unnormalised form is the cause
   — not a missing ToC. Re-read the first line of the output as `repr()` and you see the escapes.

The same block turns up in **table-of-contents and page-number digits** (`𝒫𝑅𝒪𝐿𝒪𝒢 ......... 𝟩`), so
normalise before parsing the ToC too. When you print the heading list for the user, print the
normalised form, not the styled one.

**e) The chapter heading is GLUED to the chapter's first body line — and the fix is to DROP the
heading, not to rejoin it.**
<!-- verified: `pdftotext` (plain) emitted `Chapter 1 – Setelah insiden streaming\n1\n"Aduh. …"`,
and a naive "merge the short leading lines" rule rebuilt `Epilog Pada suatu hari libur …` — the
heading eaten into the prose. A second over-broad rule then cut the second line off a 2-line
heading, leaving a bare fragment (`streaming`) as the chapter's first line. -->
A heading can arrive split across physical lines, or run straight into the body with no blank
line between. Two rules that work, in this order:

1. **Get the authoritative heading set from the source's own table of contents, not from the
   heading's shape.** In the ToC the heading appears with a separator glueing its name to a page
   number (`Chapter 1 – Setelah insiden streaming .... 25`), i.e. the **name carries a `–`/`—`**
   in the ToC but the body copy may or may not. Harvest the ToC line, split on the separator, and
   you get the exact chapter name to look for.
2. **In the body, DROP the heading line(s) from the text and keep the chapter's title in the DB
   column only — do not try to merge a 2-line heading back into one line of prose.** The title
   belongs in `bab.judul`; the body should open on the story. Delete every leading line that is
   *either* the bare chapter label (`Chapter N`, `Prolog`, `Interlude N`, `Epilog`) *or* a line
   the ToC-derived name covers, and stop at the first line that is real prose (a quote, a scene
   marker `[Sudut Pandang …]`, or a sentence ending in punctuation).

**Both failure directions are real and opposite:** a rule that merges too eagerly swallows the
heading into the first sentence; a rule that strips by a *fixed* line count cuts a 2-line heading
in half and leaves a fragment. Gate on the ToC name set (rule 1) and on "this line is a label, not
prose" (rule 2), and re-read the first 60 chars of every chapter afterwards.

The DB row can legitimately keep the body's own leading marker (`1`, `[Sudut Pandang Yuno]`) —
those are the translation's own scene numbers / POV tags, not headings. Only the *label* lines go.
Do not strip a bare `1` that opens a chapter's body; it is content the source put there and the
original readers saw it.

## 3f. Pulling the illustrations out of the PDF: pick by SIZE CLASS, and probe per page

### 3f.1 `pdfimages` without `-p` loses the page number, and the whole-file dump mixes every page's images

```bash
pdfimages -f 23 -l 23 -png novel.pdf out/p23     # ONE page -> out/p23-000.png, -001.png …
pdfimages -list novel.pdf                        # page / type / width / height / colour per image
```

A whole-file dump (`pdfimages -png novel.pdf out/x`) produces `x-000.png, x-001.png …` with **no
page attribution at all**, so you cannot tell an illustration from any other page's watermark. Use
`-list` for the map and `-f/-l` per page for the bytes.

### 3f.2 A repost-rip PDF stamps the SAME two watermark images on EVERY page — identify the real
     artwork by SIZE CLASS, never by "the biggest one on the page"

<!-- verified: a 473-page repost-rip carried a 357x223 and a 219x135 watermark (each with a paired
     `smask`) on every single page, and the 9 real illustrations as 1443x2048. A size histogram over
     the whole dump named the classes instantly: 924x 357x223, 924x 219x135, 38x 1801x257,
     4x 1058x1502, 9x 1443x2048. -->

Build a **size histogram of the whole dump** before choosing anything — the counts tell you which
size is furniture and which is content, with no vision needed:

```bash
for f in out/x-*; do identify -format "%wx%h\n" "$f"; done | sort | uniq -c | sort -rn
```

Read it like this:

- **A size present ~once per page is a watermark/logo** (the 357x223 and 219x135 above: 924 hits for
a 924-page-equivalent dump). Discard every size whose count is on the order of the page count.
- **A size present ~once per illustration is the artwork.** Its paired `smask` (identical `WxH`,
type `smask`) is the alpha channel — one `image` + one `smask` per real picture, so the illustration
count is the `image` rows only.
- **A very tall/narrow size (`1801x257`) is a page-edge strip**, and a mid-size portrait
(`1058x1502`) is front matter — both furniture.

**Take the LARGEST image on each candidate page, not the first one.** `pdfimages` writes the
watermark first, so `out/pNN-000.png` is the logo and the illustration is a later index. Selecting
`-000` per page returns 9 logos and silently loses 9 illustrations — the counts look right (9 files)
and the artwork is wrong.

```python
# per candidate page: keep the portrait large-format image, skip watermarks/strips
for f in sorted(glob(f"{tmp}/p{h}-*.png")):
    w, hh = map(int, run(["identify","-format","%w %h",f]).stdout.split())
    if hh >= 1900 and w >= 1300:        # the artwork class found by the histogram
        pilih = f; break
```

**Then LOOK at what you extracted before loading it.** A text-only model cannot judge artwork, but a
cheap ASCII/greyscale render distinguishes "a figure on a background" from "a logo" or "a text
page" — enough to stop a watermark loading as an illustration. Render each candidate small (54x27
via `convert … pgm:-`, parse the P5 header) and read the shapes; report the geometry you measured and
say plainly that the artwork itself was not visually judged.

**Verify the user's poster against the extracted cover with an 8x8 pHash — it answers "same image?"
where the RMS diff of §1 in `mtl-cover-and-assets.md` is unavailable, and it also proves a poster is
DIFFERENT.**
<!-- verified: with the vision tool blind, an 8x8 grayscale bitstring correctly showed one poster was
     md5-different from the PDF cover but bit-identical at pHash (same art, different resolution),
     while two other posters hashed completely differently (genuinely other artwork). -->
```bash
# 64-bit perceptual hash per file: resize to 8x8 gray, binarise at the mean, print as a bitstring
for f in poster-user.jpg cover-dari-pdf.jpg; do
  convert "$f" -resize 8x8! -colorspace Gray txt: 2>/dev/null \
  | awk -F'[(,)]' 'NR>1{s+=$3;a[NR]=$3} END{m=s/(NR-1);r="";
        for(i=2;i<NR;i++) r=r (a[i]>m?1:0); print r}'
done
```

Compare the two 64-char strings, and read the verdict as:

- **Identical strings** = the same artwork. The poster is authentic; only the resolution differs, so
  prefer the larger file (the PDF's cover is usually bigger than a chat-attached poster).
- **Different strings** = a genuinely different image (another edition / official promo art). Still
  valid — the user chose it — but say so explicitly rather than assuming it matches.

A near-identical **mean** (e.g. 0.4584 vs 0.4578) is NOT proof of a match and will mislead you: mean
brightness agrees across any two covers of the same series. Binarise at the per-image mean and compare
the bit PATTERN, not the average. Always confirm the dimensions too — a ratio near 0.70-0.78 is a
normal LN cover, and a resize-and-rehash that flips the verdict means the two files differ in framing.
Do not report "poster verified" from colour statistics alone; the user's rule is to check with your
own eyes, and pHash is the mechanical stand-in when no vision is available.


**A `pdfimages`-extracted `smask` is not a separate picture** — do not count it,
and do not dedupe image/smask pairs as "duplicates".

### 3f.3 The SIZE filter is not enough — `pdfimages` also emits PAGE FRAMES, TABLES and TEXT pages as large images; reject them with the ASCII render, and dedupe by hash

<!-- verified: a Matcha PDF's "portrait >=1400x2000" filter returned 14 candidates; the ASCII render
     showed #01-#03 were decorative page BORDERS (solid `@@@` frame, empty centre), and among the
     landscape candidates three were TABLES (`#@@@` regular grid) and four were TEXT-with-ornament
     pages (letter shapes). Only 11 were real artwork. Separately, page 3 == page 17 and page 4 ==
     page 71 were the SAME image re-stamped, so the raw count overstated the unique set. -->

A large image is not automatically artwork. The size class proves "big", not "picture", and the
counts still look right (14 files, plausible sizes) while the set is wrong. Three shapes pass a naive
size filter and must be rejected by eye:

- **A page frame / decorative border.** A solid `@@@`-block border around an EMPTY centre (the render
  shows a rectangle of `@` with blank inside) is a layout ornament or a blank art page, not an
  illustration. It usually also carries a `*+++`-style rule line. Discard; do not load it as art.
- **A table.** A regular grid of `#@@@` cells in the render is a schedule/stat block, not a picture.
- **A text page.** Letter-shaped blobs in the render = a scanned/rendered TEXT page, not art.

Only a render showing organic shapes (figures, diagonal lines, tonal areas) is artwork. Render each
candidate with the greyscale ASCII probe (`convert <f> -resize 56x22! -colorspace Gray pgm:-`, parse
the P5 header) and read the SHAPE before loading — this is the same "look before you load" rule as
§3f.2, and it is what catches the three non-art shapes above.

**Dedupe by content hash — the same artwork is stamped on more than one page.** Before counting,
run `identify -format '%#' <f>` (SHA-256 of the pixel data) over all candidates and collapse
identical hashes; a PDF can repeat a cover/illustration on a second page, so the raw candidate count
overstates the unique set. Verified: two portrait candidates and two landscape candidates were exact
duplicates. Report the UNIQUE count, and verify a suspected duplicate pair by comparing both hashes
(`identify -format '%#' a.jpg; identify -format '%#' b.jpg`) rather than by page order.

## 4. Keep the translator's notes — they are content, not furniture (`[TN: JK = Joshikousei = gadis SMA]`,
`[TN: Kota Listrik adalah Akihabara.]`) inline in the prose. These are **correct content** and
must survive the cleaning pass: count them before and after and require the same number (12 →
12 verified). Do not add `[TN: …]` to any strip rule — it looks like furniture and is not.

**The same goes for the translator's setup blocks** (`Catatan :` / `Pengingat :` listing the
symbols the chapter uses — `【 】 = bahasa Rusia`, `( ) = monolog`, `“ ( ) ” = bisik-bisik`). They
sit at the top of a chapter and read like furniture, but they are instruction the reader needs;
keep them. A leading `Catatan/Pengingat` block is a signal to STOP stripping, not to strip more.

**And a `Komentar Penerjemah` inside the closing `Kata Penutup` is content, not a watermark.** A
mention of the translator group's name (`… sudah membaca Roshi-dere jilid 2 di <group>`) is the
translator addressing the reader; a furniture sweep that keys on the group name will flag it.
Read the residue and keep the sentence — only the repeated per-page stamp block is furniture.

## 4b. Keep the chapter title VERBATIM once extracted — never re-case it

<!-- verified: an auto "Title Case the ALL-CAPS heading" step turned `AKU BUKAN PENYENDIRI, OKE?`
into `Aku bukan Penyendiri, Oke?` and `SEPERTINYA DIA ITU 5M` into `Sepertinya Dia itu 5m` -->
When the source renders a chapter title in ALL CAPS, the tempting cleanup is to Title-Case it so it
"looks nicer". **Do not** — any casing normaliser you write will corrupt something:

- A naive word-capitaliser lowercases short words it treats as function words, so `AKU`→`aku`,
  `KAMU`→`kamu` — changing the title's own voice.
- It mangles non-words: `5M`→`5m`, `ROM-COM`→`Rom-com`, `CV`→`Cv`.
- The archive's own convention is mixed anyway (some volumes ALL CAPS, some Title Case), so
  "make them consistent" is a change the user did not ask for.

Store the title exactly as the source wrote it (whitespace-normalised only), and if you think a
re-case is wanted, **ask** — do not bake it into the extractor.

## 4c. ONE work's volumes can use DIFFERENT heading styles — normalise, then match both

<!-- verified: in a single 4-volume set, V1-V3 rendered headings as Mathematical-Alphanumeric
`𝒫𝑅𝒪𝐿𝒪𝒢` while V4 rendered plain `Prolog` / `Chapter 1` -->
The heading regex must survive both a styled-unicode volume AND a plain-sentence-case volume of the
same work. Order of operations that works:

1. **NFKC-normalise the text first** (folds `𝒫𝑅𝒪𝐿𝒪𝒢` → `PROLOG`) — see §3e2.
2. **Match case-INSENSITIVELY** (`re.I`) so both `PROLOG` and `Prolog` are found; do not learn the
   style from volume 1 and apply an ALL-CAPS-only regex to volume 4.
3. **Then extract the title lines that follow the label**, and accept BOTH shapes: an ALL-CAPS title
   line, or a Title-Case / sentence-case short line. Reject only lines that are clearly prose
   (long, ending on `.`, or a quote/dialog opener).

A single parameterised extractor per work (see §2d) makes this a per-file assertion rather than a
rewrite when one volume diverges. Verify by printing the heading list for EVERY volume before
splitting any — a volume whose headings come back `0` is the tell that the style differs, not that
the volume has no chapters.

## 5. The four-side verification, adapted for a no-MTL PDF raw

Run all of these and print them per chapter:

- **Chapter count** equals the boundary count from step 2 (and, if the source has a ToC,
  matches it).
- **No empty chapter** — every chapter ≥ a sane minimum (here the smallest legit ones were the
  Prolog at ~3k chars; anything under a few hundred is a bug).
- **Furniture sweep = 0** for `PAGE\d+`, the novel title, the credit block, URLs, and
  `Blogspot`-style source markers.
- **Boundary read-through with your own eyes:** print the first ~95 and last ~95 chars of EVERY
  chapter. Verified at 22/22 chapters opening on a real story line and closing on a complete
  sentence — this is what catches a chapter sliced one beat too early, which no char count can.

Then count `***` separators per chapter as the scene-break sanity check.

### Two verification false alarms that look like real damage

<!-- verified on a 12-chapter volume: both flags below fired and both were the source's own shape -->
- **An ODD number of `"` in a chapter is NOT a missing dialog line.** `pdftotext` wraps a long
  utterance mid-quote, so the opening `"` sits on one line and its closing `"` lands on the next
  — the chapter total can read odd while every line pairs up. Verified: a chapter reported 555
  quotes (odd) and the cause was a single wrapped line
  (`'"Iya! Hari ini cuma ada satu kelas di siang (logat daerah).'` + `'Tokyo)." (Aya)'`).
  Confirm by listing the lines whose own count is odd and reading them; do **not** "repair" a
  count that is a wrapping artifact.
- **A handful of CJK characters can be a SOURCE TYPO, not leakage.** The MTL CJK sweep (a
  *density* test) is for translated output; on an already-translated raw a stray `值得` inside an
  Indonesian sentence is the translator's typo, not a wrong-language chunk. Remove the characters
  and note it, but do not treat it as "this chapter was not translated" — the density gate exists
  precisely to separate these two cases.

## 6. Reported shape when handing this to the user

Report, per chapter: the honest title (`Bab N` per volume, `Prolog` / `Epilog` / `Kata Penutup`
kept verbatim), the char count, and the furniture/scene-break counts. Then state plainly which
of the four sides verified and that the raw was a **third-party human translation, not MTL** —
so the user knows why it waited for their approval rather than loading straight to the main DB.
