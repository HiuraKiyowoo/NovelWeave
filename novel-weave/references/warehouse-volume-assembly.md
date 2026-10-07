# Merging a warehouse volume set whose chapters arrive as PARTS

Depth for the assembly step when a novel's later volumes come from a *warehouse* dump (the
scraper's raw rows, `naver-lama.db`) rather than from a finished PDF/EPUB. The warehouse's own
row shape is not a chapter list — it is a **part list**, and the whole job is turning parts back
into chapters without losing or mis-ordering anything.

This is a distinct step from either translation or the PDF split: run it when the raw is already
in the target language and the archive already holds part of the work, so the task is
"assemble the missing volumes from the raw rows".

## 1. A chapter can arrive as several `Bagian N` part-rows — GROUP, do not take the row count

<!-- verified: a warehouse dump held 102 rows for a 12-volume novel; the real chapter count was 92,
because several volumes' chapters each landed as 2-5 separate part-rows -->
The warehouse stores what the scraper found, and a source that paginates a long chapter splits it:

```
'Bab 1 — Karuizawa dan Para Ojou-sama'      ← part 1
'Bab 1 — Karuizawa dan Para Ojou-sama'      ← part 2 (same title, different text)
...
```

So **a row is not a chapter**. Before counting, inserting, or reporting anything, group the volume's
rows by chapter identity and concatenate the parts in row order:

- **Key on the chapter NUMBER, never on the title.** Two parts of one chapter share a title, but two
  DIFFERENT chapters can ALSO share a truncated/generic title (`Bab 3 —` appearing twice). Keying on
  the title silently merges distinct chapters; keying on the number keeps them apart. Extract the
  number with `^(?:Bab|Chapter)\s*(\d+)` and use it as the group key.
- **Concatenate parts with a paragraph break, in `urutan` order.** The parts are one continuous
  chapter; joining them with a blank line reconstructs the author's paragraphing.
- **A row whose key has no number** (`Prolog`, `Epilog`, `SS`, `Chapter Bonus`) is its own group —
  but see §2, because its `N` may be *missing* from the title and recoverable from the text.
- **Expect the merged count to be far below the row count** (102 rows → 92 chapters here). Compare
  the merged count against the source's ToC before trusting it; disagreement means a group key was
  wrong, not that the source is short.

## 2. The title is often INCOMPLETE in the title column and completed on the FIRST LINE of the text

<!-- verified: warehouse rows carried titles like 'Bab 3 —', 'Bab', 'Penantang', 'Ojou-sama yang
Sempurna', 'P rolog' — the real name sat as the first line of the row's own teks -->
The scraper stored a *truncated* title (the heading was split across lines in the HTML) and the
continuation landed at the start of `teks`:

```
judul: 'Bab 3 —'
teks : 'Penyelidikan Teman Masa Kecil\n"Sudah kubilang…'   ← the title's tail, then the story
```

Rules that reassemble it:

- **Before grouping, harvest the title's continuation from the text's leading lines.** Join a
  dash-terminated title (`—`/`–`/`-`) to the following text line(s) while those lines read as a label
  (short, not ending on sentence punctuation, not a quote opener). Then **delete the consumed lines
  from the text**, or the title's tail stays glued to the story's opening sentence.
- **A title that is a bare type word needs its number from ORDER, not from the text.** `'Bab'`,
  `'P rolog'`, `'Chapter'` appear when the number was dropped in scraping: renumber story chapters by
  their position within the volume (see `pdf-raw-to-chapters.md` §2b2, rule 1), and repair the
  mis-split words (`P rolog` → `Prolog`, `Gam e` → `Game`) — a space inserted mid-word is a scraping
  artifact, and it also defeats a `^Prolog$` match.
- **Do NOT join a type-only line to the following prose.** `'Prolog'` + `'Akademi Kekaisaran…'` is a
  title followed by a story sentence — joining it deletes the story's first line. Gate the join on a
  dash-terminated *numbered* head only, exactly as in `cleaning-scraped-chapter-text.md`.
- **A mislabeled row is indistinguishable from a real gap until you read it.** A row titled
  `'Bab 5 Epilog'` filed under `volume 3` was actually the *Epilog of volume 5* (the warehouse's
  volume column was simply wrong — see §3). Read the chapter's own text/first line before trusting
  the stored `volume`.

## 3. The warehouse `volume` column is a HINT, not a fact — verify against the source's own structure

<!-- verified: warehouse rows labeled `volume 3` contained the Epilog of volume 5, while the real
volume 3 sat in the PDF set; the column had been written by a scraper guess -->
Do not map warehouse rows to volumes from the `volume` column alone. Cross-check with an
independent witness — the volumes you hold from the *other* source, or the work's own per-volume
ToC:

- **A volume number that contradicts the chapter's own content is the tell.** An `Epilog` row sitting
  under a volume whose chapters are still mid-story is the classic mislabel: epilogs belong to the
  END of their volume.
- **When two sources both claim a volume, prefer whichever is COMPLETE and correct per volume**, not
  whichever is "ours" — compare chapter counts AND which chapters exist (`SKILL.md`, "Assembling a
  novel whose volumes come from TWO different sources").
- **Report the correction plainly** (`"Jilid 3 di gudang itu sebenarnya Epilog Jilid 5"`) rather than
  silently re-filing it; the user tracks volume coverage and needs the honest map.

## 4. Assemble, then renumber GLOBALLY

After the volumes are merged and combined with the other source's volumes:

- **`urutan`/`nomor` run 1..N across the WHOLE assembled novel**, while `volume` stays per-volume and
  the title's `Bab N` restarts inside each volume — the site orders chapters off the global counter.
- **Put each volume's trailing material (Prolog first, Ekstra/Selingan/Short Story/Epilog last) in
  printed order**, then sort the volume's rows by (numbered chapters ascending, then the extras). The
  warehouse row order is not trustworthy.
- **Sentence-case the assembled set's `Bab N —` label consistently** and keep the number in the
  title; the archive's convention is `Bab N — <judul>` (`Chapter N — <judul>` for some works).

## 5. Provenance gate for the THIRD-PARTY source — it does NOT ride the "khusus MTL" carve-out

When one of the two sources is an **externally-translated** raw (a PDF/EPUB by another group, an
aggregator's set), the whole assembled novel is a third-party asset even when OUR MTL supplies the
other volumes. The user's standing exception ("hasil MTL kalo udah sempurna … langsung ke db utama
aja ini khusus MTL ya") is scoped to the project's OWN MTL output — it does not licence loading
someone else's translation without approval. Stage it, verify it, report per-volume provenance, and
let the user say go. Say which volumes are ours and which are third-party in the report table; do not
let a mixed set read as all-ours.
