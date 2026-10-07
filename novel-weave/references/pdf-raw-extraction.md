# Extracting a third-party PDF raw: paragraph structure, headers, chapter titles, stray "illustrations"

The PDF-raw path of the pipeline (steps 2-3, "Extract text" and "Map the structure"). A
PDF from a translation group (Matcha/Shinra/Lui/RueNovel, a Blogger-printed LN) is the common
third-party raw, and it is the shape where a cleaner that *looks* right silently destroys the
book's paragraphing. Read this before writing any PDF cleaner.

## 1. `pdftotext -layout` is mandatory — without it the right edge is cut

<!-- verified: `pdftotext` without `-layout` right-truncated text (one novel gained ~30k chars
once `-layout` was used), so lines ended mid-word and every paragraph join was wrong -->
Always extract with `-layout`:

```bash
pdftotext -layout novel.pdf /tmp/novel.txt     # keep -layout
pdfinfo novel.pdf                              # page count, encryption, Producer
```

`-layout` preserves the visual line structure (including the indentation of a centred heading),
which is what makes the header/structure rules below possible. A `ToUnicode` CMap present means the
text is extractable — do not reach for OCR on a text PDF.

Split the dump into pages first; almost every rule here is per-page:

```python
hal = open("/tmp/novel.txt", encoding="utf-8", errors="replace").read().split("\f")
```

## 2. Paragraph structure is a property of THE FILE, not of the translation group

The same translator label can emit two structurally different PDFs. **Never assume a shape from the
label — read 2-3 RAW pages (`repr()`, not a rendered view) and decide.** There are three shapes:

| Shape | How a paragraph break appears | How to join |
|---|---|---|
| **A. blank-line separators** | a real empty line between paragraphs | blank line = paragraph; join runs of non-blank lines with a space |
| **B. blank lines only at PAGE breaks** | every page's last line is followed by a blank line, but paragraphs run on across line breaks | paragraph break = **previous line ends on `.` `!` `?` `"`** |
| **C. no blank lines at all** | the whole chapter is one run of lines | same rule as B |

The tell for B: the blank lines appear at a *regular* cadence that matches the page height, and a
line before a blank line does **not** end on sentence punctuation (`…menghabiskan waktu di sebuah
kafe te` then blank then `luang yang aku punya`). If a blank line lands mid-sentence, shape B is
the truth and the blank line is a page boundary.

```python
def gabung(baris, bentuk):
    """baris = list of stripped lines from all pages of one chapter."""
    par, buf = [], []
    for s in baris:
        if bentuk == "A":                       # blank line IS the separator
            if s == "":
                if buf: par.append(" ".join(buf)); buf = []
            else:
                buf.append(s)
        else:                                    # B / C: break after sentence-final punctuation
            if s == "":
                continue                         # page boundary — never a separator
            if buf and buf[-1] and buf[-1][-1] in '.!?\u201d"':
                par.append(" ".join(buf)); buf = []
            buf.append(s)
    if buf: par.append(" ".join(buf))
    return par
```

**The wrong shape collapses a whole chapter into a few giant paragraphs** — verified: a chapter of
~42k chars came out as **44 paragraphs (average 497 chars)** where the correct shape gave **534
(average 79)**. The self-check is the same one the cleaning reference uses: **an average paragraph
length above ~300 chars means the join is wrong.** Print the per-chapter average and read one
truncated-looking paragraph with `repr()` — if a paragraph ends mid-word and the next begins with
the rest of the sentence, the break rule is misconfigured.

## 3. A header/title strip MUST become a paragraph separator, not a deletion

<!-- the bug that made shape B look like shape A: deleting the header line removed the ONLY
marker between two paragraphs, gluing them together -->
In shape B, the page boundary is `…end of page…` + blank + `Shinra Novel` (the running header) +
blank. If your cleaner *deletes* the header line, it also deletes the last break marker, and two
paragraphs fuse. So when a header is removed, **emit a separator in its place**:

```python
out = []
for s in baris:
    if RE_HEADER.fullmatch(s):
        out.append("")          # placeholder: keeps the boundary
        continue
    out.append(s)
```

Then the shape-B join sees the blank and breaks the paragraph correctly. Symmetrically, if you feed
the join a list where headers were *dropped* rather than *blanked*, a correct rule still produces
glued text — so the two stages must agree on the convention.

## 4. Enumerate the header's VARIANTS — one pattern is never enough

<!-- verified: a cleaner that only matched `X - Shinra Novel` left `[ 238 ] - Shinra Novel`
untouched, because the file carried BOTH forms -->
A third-party PDF re-stamps its header in more than one shape across a document:

```python
RE_HEADER = re.compile(
    r"^(\[\s*\d+\s*\]\s*-\s*)?"                 # optional '[ 238 ] - ' page marker
    r"(Shinra Novel|Incubus Banishment( Volume \d+)?)$", re.I)
```

- Check for a **second variant** by counting the header string and the numeric-bracket form
  separately over the whole joined text after cleaning; both must be 0.
- **Do NOT strip a header-like string that is embedded in a sentence.** Verified: `Incubus Banishment`
  also appears inside the afterword ("Apa pendapat Anda tentang Incubus Banishment volume dua?") —
  that is the author's own prose. Match the header only as a **whole line** (`fullmatch`), never as a
  substring.
- The header can differ per volume of the same set (`Shinra Novel` in V1-V2, bare `Incubus Banishment`
  in V3) — sweep each volume and add the variant you find.

## 5. Chapter-title detection: multiple separators, multi-line titles, and a ToC page that mimics headings

Headings are the split points, and the raw is inconsistent about them. Handle all of:

```python
RE_BAB = re.compile(r"^(Prolog|Prolog(ue)|Epilog(ue)?|Bab\s+\d+)\s*(?:[-\u2013\u2014]\s*)?(.*)$", re.I)

# a heading is a SHORT line that does NOT end on a period (that would be prose)
def kelihatan_judul(p):
    s = p.strip()
    return len(s) <= 120 and not (s.endswith(".") and s.count("(") <= s.count(")"))
```

- **Two separator variants exist**: `Bab 36 - Judul` (with dash) and `Bab 36 Judul` (no dash at all).
  A regex keyed on the dash alone files chapters 36-43 *inside* chapter 35 — verified: one volume lost
  7 chapters into a single 97k-char blob, and its per-chapter average looked fine because the blob
  was one paragraph.
- **A title can span 2 lines** (`Bab 6 – Bergaul ( Tidak Ada Makna` + `Tersembunyi)`). Detect a
  dangling title (unbalanced `(`/`[` or ending on `-`/`–`) and consume the next short line as its
  continuation.
- **A decorative symbol line (`※`, `※※※`, `***`) can sit immediately above a heading** and makes the
  heading look like ordinary prose to a line-index-based harvester. Strip symbol-only lines BEFORE the
  heading scan.
- **The table-of-contents page looks exactly like real headings.** Verified: a ToC page emitted the
  fake sections `Prologue Bab 1 - 43` and `Bab 1` … `Bab 10 - 27` with **0 chars of body**. Two rules:
  start the body just *after* the ToC page (find the page whose content is ≥2 `Bab N` lines and
  <400 chars total), and **drop any detected section whose body is <50 chars** — a real chapter is
  never empty, and one empty `Bab` remnant otherwise sits at the top of the rack as a phantom chapter.
- **Never invent a title suffix.** A `(Epilog?)` I appended to a chapter title was my own guess, not
  the source's, and it shipped into the `judul` column. Take the title verbatim, or fall back to the
  honest `Bab N` / `Volume N — Ilustrasi` rule.

Verify the found count against the raw's own `DAFTAR BAB` page (`Prolog` + `Bab 1-43` = 44 sections).
If the count is short, a title-variant rule is missing — do not accept it.

## 6. `pdfimages` dumps scanned-TEXT page backgrounds as if they were illustrations

The PDF's *page background* can be an embedded bitmap (a scan or a textured page), so
`pdfimages -list` reports an image for every page and a size filter cannot tell a real illustration
from a page of text. **None of the cheap filters work** — verified, and each failed:

| Filter tried | Why it failed |
|---|---|
| geometry (`width/h == 1120/1600`) | the text-page backgrounds were the SAME size as the real illustrations |
| file size / byte count | text pages ran 180-260 KB, real illustrations 140-500 KB — fully overlapping |
| whiteness (`mean` after `-threshold 88%`) | 47% (illustration) vs 48% (text) — no separation |
| "text-row density" heuristic | fired 72.5% on a genuine illustration with two characters |

**Therefore: extract every candidate, then JUDGE EACH ONE WITH YOUR EYES.** The reliable, cheap
"eye" is a coarse ASCII render of the grayscale thumbnail — a text page shows a regular ladder of
short horizontal runs inside a border, an illustration shows large light/dark masses and character
silhouettes:

```python
def render(p, l=60, t=22):
    import subprocess
    RAMPAK = " .:-=+*#%@"
    subprocess.run(["convert", p, "-resize", f"{l}x{t}!", "-colorspace", "Gray", "/tmp/g.pgm"],
                   capture_output=True)
    d = open("/tmp/g.pgm", "rb").read(); i = 0; tok = []
    while len(tok) < 4:                                  # minimal PGM header parse
        while d[i:i+1].isspace(): i += 1
        if d[i:i+1] == b"#":
            while d[i:i+1] not in (b"\n", b"\r"): i += 1
            continue
        j = i
        while j < len(d) and not d[j:j+1].isspace(): j += 1
        tok.append(d[i:j]); i = j
    w, h = int(tok[1]), int(tok[2]); px = d[i+1:i+1+w*h]
    return "\n".join("".join(RAMPAK[(255-(px[y*w+x] if y*w+x < len(px) else 0))*9//255]
                             for x in range(w)) for y in range(h))
```

Signature of a **text page**: a rectangular border of `-` with a regular vertical rhythm of `===`/
`---` runs inside. Signature of an **illustration**: broad `%%%%`/`###` masses, diagonal gradients,
recognisable silhouettes. Verified across a 3-volume set: 10 of 24 candidate images were text pages
disguised as illustrations, and *only* the eye caught them.

**Discard the text pages from the illustration set, then renumber the survivors `01..N`** so the
shelf's images are a clean sequence. Back up the dropped files (`_buang/v<N>-<NN>.jpg`) first — a
mistaken drop is then one `cp` to undo.

## 7. Long-run hygiene: keep the stages as separate, re-runnable scripts

Each novel gets `bersih-*.py` (text) and `masuk-rak-*.py` (load) so a fix can re-run one stage
without touching the other. Because the paragraph shape is per-file, keep the shape as an explicit
parameter or an auto-detected count printed in the report (`bentuk: B · rata paragraf: 79`) — a
silently-chosen shape is the bug you will ship.
