# Importing a light-novel EPUB (already-translated or as a raw container)

Depth for the "raw is ALREADY in the target language" path in SKILL.md. An EPUB is the
best container the user supplies — per-chapter XHTML, embedded images, and an OPF that
declares the language — but its *structure* lies about chapter count until you filter it.

## 1. Read the container's own metadata first

`dc:language` decides whether the MTL step runs at all.

```python
import zipfile, re, html
z = zipfile.ZipFile(path)
opf = [n for n in z.namelist() if n.endswith('.opf')][0]
meta = z.read(opf).decode('utf-8')
lang = re.search(r'<dc:language[^>]*>([^<]+)', meta).group(1)   # 'id' => do NOT translate
```

The book's own `nav.xhtml` (the EPUB3 TOC) is the authority on which documents are real
chapters. Read it, do not count XHTML files:

```python
nav = z.read([n for n in z.namelist() if n.endswith('nav.xhtml')][0]).decode('utf-8')
hrefs = re.findall(r'<a[^>]+href="([^"]+)"', nav)   # the real spine order
```

**`nav.xhtml` also resolves the duplicate-prolog trap directly**: when a TOC entry and a
"Start of Story" entry link to the *same* document, they are one chapter, not two. That is
the cheapest proof that you are not dropping or doubling a scene.

## 2. Extraction: what is NOT a chapter

`baca-epub.py` (stdlib `zipfile` + an HTML-to-text pass) gives clean per-chapter text, but
the XHTML document list contains non-story pages that must be dropped before you count
chapters or translate:

- **`Table of Contents` / `nav` document** — a list of chapter titles, no prose.
- **`About This Ebook` / colophon / copyright page** — human-readable, so a length filter
  keeps it. It is usually the richest *metadata* source (original JP title, author,
  illustrator, translator, publisher, genre), so **harvest the metadata and then drop the
  text**, do not drop the whole page blindly.
- **A second copy of the opening chapter** when the book carries both a front-matter
  "Start of Story" link and the real chapter document.

Filter by *content*, not by filename: a document whose text is a bare list of titles, or
that matches `about this ebook` / colophon markers, is not a chapter.

## 3. Two text defects the extraction pass creates

Both appear after a naive XHTML→text conversion and both are the pipeline's fault, not
the book's:

1. **Markdown remnants in the body** — a heading rendered as `## Prolog` surviving into the
   chapter text (extractor emitted the heading tag's text with a markdown-ish prefix). Strip
   leading `#`/`##` heading lines from each chapter's body.
2. **The chapter title duplicated** — the text can open with `Prolog\n\n## Prolog\n\n…` or
   `School 1-1: …\n\nSchool 1-1: …` because the extractor captured both the title element
   and the body heading. Detect it by comparing the first two non-empty lines (normalised:
   strip a leading `##`/`#`, collapse whitespace) and drop the duplicate.

After both fixes, assert every chapter body **starts on the story's prose**, not on a
heading string.

## 4. Cross-check the EPUB against the PDF of the same work — this is the "not truncated" proof

When the user supplies both a `.epub` and a `.pdf` of the same novel, use the PDF as the
independent completeness witness: extract the PDF's text (`pdftotext`), collect its chapter
headings, and assert **every** EPUB chapter title appears in the PDF text.

<!-- verified: a 13-chapter EPUB matched all 13 PDF headings, proving no chapter was lost in extraction -->

Do not compare raw char totals — a PDF's text layer repeats running headers/footers per
page and is always longer than the EPUB (measured: 354k PDF chars vs 200k EPUB story chars
for the same 13 chapters). Compare the *chapter title set*, which is page-furniture-proof.

## 5. Which image is the cover — read the spine, do not guess geometry

In an EPUB the cover is declared, so you do not need `pdfimages`' page-1 heuristic. Find the
`cover.xhtml` (or `<item properties="cover-image">` in the OPF) and read which image **it**
references:

```python
cov = [n for n in z.namelist() if 'cover' in n.lower() and n.endswith(('.xhtml', '.html'))]
src = re.search(r'<img[^>]+src="([^"]+)"', z.read(cov[0]).decode('utf-8')).group(1)
```

<!-- verified: the OPF/nav spine pointed at 01.webp as the cover; 02-11.webp were interior illustrations -->

Files named `01.webp…11.webp` are just spine order — `01` is the cover only because the
cover page points at it, not because of its number or its aspect ratio. Write the cover to
`cover-asli/<id>.jpg` and let `scripts/pasang-cover.py` normalise it like any other source
(see `mtl-cover-and-assets.md`). The remaining images are illustrations — keep them.

## 6. Reuse the MTL loader by converting to its input shape

There is no separate DB loader for a no-MTL import. Emit the same
`mtl/<slug>-potongan.json` shape the translator produces and the existing
`vps/mtl-masuk-db.py <slug> {staging|verif|up}` path works unchanged:

```python
# mtl/<slug>-potongan.json  — one record per chapter, each a single 'potongan'
{"bab": [{"id": "bab01", "judul": "…", "selesai": True,
          "jp_panjang": <source len>, "terjemah": "<full chapter text>"}, …]}
```

Key the staging rows `"<slug>:bab{i:02d}"` exactly as the MTL path does (see
`jp-to-id-translation.md` → Staging keys) so a second import does not collide with the
first. Then stage → `verif` → back up `naver.db` → `up`, and record the undo-log path.

**The four-side verification still runs** (no truncation, no missing chapter, chapter count
matches the container's nav, plausible length) even though no translation happened — the
cleaning in sections 2-3 is where a chapter can go missing.

## 7. Provenance: this is a third-party translation, so the MTL fast-path does NOT apply

An EPUB translated by another group (its own `dc:language: id`, a translator/group credit in
the colophon) is **not the user's own MTL output**. The "provably-perfect MTL goes straight
to the main DB" carve-out in SKILL.md is for the project's own work only. Stage it, verify
it, and **let the user approve** before the main load — and record the translation group as
` sumber_terjemah` in the meta so the provenance is honest.

## 8. Loading a multi-volume set volume-by-volume into ONE shelf entry

A 6-volume set is one shelf row, but the volumes arrive far apart (each MTL'd and verified
separately), so the loader runs repeatedly against a **live** archive. It must append, never
re-insert the novel row.

- **Volume 1 creates the row; volumes 2+ only append chapters.** Branch on whether the novel
  id already exists — a second `INSERT INTO novel` either collides or silently overwrites the
  shelf row (metadata, cover columns) that volume 1 established.
- **Continue `urutan`/`nomor` from the DB, not from a counter that starts at 1:**
  `SELECT COALESCE(MAX(urutan),0) FROM bab WHERE novel_id=?` before the loop. This is what
  keeps the reader's order correct as volumes land one at a time (the same global-`urutan`
  rule as SKILL.md, restated for the incremental case).
- **Assets must be loaded in a TWO-PASS insert, because the illustration folder is NAMED
  AFTER the chapter id — which does not exist until the row is inserted.** Insert the
  `Volume N — Ilustrasi` chapter row first, read `last_insert_rowid()`, then
  `os.makedirs('gambar/<bab_id>')`, copy the images in, and write the `bab_gambar` rows:
  ```python
  c.execute("INSERT INTO bab(novel_id,nomor,urutan,judul,teks,tanggal,waktu_ubah,ada_gambar,volume) …")
  bid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
  folder = f"{GAMBAR_DIR}/{bid}"          # the folder name IS the chapter id
  ```
  You cannot pre-compute the path; a loader that builds the folder before the insert writes
  to a guessed (wrong) directory.
- **Match the archive's exact `bab_gambar` shape, and CHECK ONE EXISTING ROW before writing.**
  Verified mismatch: this session's first loader wrote `file_lokal = '416565/1.jpg'` while
  every other novel in the shelf stored `'gambar/416565/1.jpg'` — the prefix is part of the
  stored value, so the new novel's 13 illustrations would have 404'd while the rows "looked"
  correct. One `SELECT … FROM bab_gambar WHERE bab_id=<some-existing-illustration-chapter>`
  settles the convention in a single step; correct in place with
  `UPDATE bab_gambar SET file_lokal='gambar/'||file_lokal WHERE … AND file_lokal NOT LIKE 'gambar/%'`.
  Populate `url_asli` with the honest provenance (`'J-Novel Club (EPUB resmi)'`), not NULL.
- **Keep the per-volume label style identical to the volumes already loaded** (`Volume N —
  Ilustrasi / Prolog / Chapter K / Cerita Bonus / Catatan Penutup`), so a shelf entry whose
  volumes landed weeks apart still reads as one consistent work.
- **Back up `naver.db` before the append** (`naver.db.bak-sebelum-<slug>`) even though the run
  is additive — an aborted append can leave a half-loaded volume, and the backup is one `cp`
  from clean.
