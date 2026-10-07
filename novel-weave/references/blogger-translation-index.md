# Harvesting a whole novel from a translation group's Blogger index

Some translated novels (often Indonesian LN fan-translation groups like Kaori Translation) are
published as **one Blogger post per chapter**, with a single index post listing every volume's
table of contents. This is the *cleanest* source you can get: a human translation, already in the
target language, with real chapter headings and volume structure — **no MTL step at all** (see
"A raw that is ALREADY in the target language" in SKILL.md; stage and let the user approve the load).

## Recognising it

The index post reads like a book's own ToC:

```
Judul: <romaji>
Alternatif: <kanji>
Author: <name>
Artist: <name>
Genre: …
Type: Light Novel
Status In COO: Volume 2
Tahun Rilis: …
Sumber: Raw Bookwalker
Penerjemah : …
Sinopsis: …

Volume 1
  Illustrasi
  Prolog
  Chapter 1 … Chapter 7
  Epilog
  Kata Penutup
Volume 2
  …
```

**`Status In COO` is the JAPANESE status, not what the site hosts.** Verified: a work whose COO
status read `Volume 2` had all **4** volumes already translated and linked on the same page. Never
answer a "how many volumes?" question from `Status In COO` — count the volume blocks on the page,
then confirm the true total against the publisher.

## The trap: the volume's links live under DIFFERENT month paths in the URL

<!-- verified: a first pass that grouped links to the nearest `>Volume N<` heading found only
volumes 3 and 4 (18 links) and reported volumes 1-2 as "not published" — they were published, just
filed under other months -->
On Blogger the post's URL carries `/<year>/<month>/`. **Each volume of one novel can be published in
a different month**, so its chapters sit at a *different* path than the volume you started with:

```
/2025/01/shujinkou-…-no_23.html   ← Volume 1 (Illustrasi)
/2025/04/shujinkou-…-no.html      ← Volume 2 (Illustrasi)
/2025/05/shujinkou-…-no_2.html    ← Volume 2 chapters
/2026/02/shujinkou-…-no_75.html   ← Volume 3
/2026/07/shujinkou-…-no_01707354749.html   ← Volume 4
```

Never conclude a volume is missing from a heading-proximity match. Instead **collect every link whose
href contains the work's slug, then group by `/(\d{4}/\d{2})/`**: each month cluster is one volume's
block, and its size tells you which is which. That single change turned 18 found links into the full
41. Also note the suffix styles differ (`_9.html`, `_01372773852.html`, no suffix at all) — match on
the slug substring, not on a filename pattern.

## Extracting a chapter's text

The chapter's prose lives in the Blogger `post-body` div. Strip `script`/`style`/`ins`/`iframe`
(ads are injected there), then convert block tags to newlines:

```python
m = re.search(r'<div class=["\']post-body[^>]*>(.*?)<div class=["\']post-footer', t, re.S)
b = re.sub(r'<(script|style|ins|iframe)[^>]*>.*?</\1>', '', b, flags=re.S|re.I)
b = re.sub(r'<br\s*/?>', '\n', b)
b = re.sub(r'</(p|div|h\d)>', '\n', b)
b = re.sub(r'<[^>]+>', '', b)
text = html.unescape(b)
```

## The furniture is small but it is in EVERY chapter — and one piece has no pipes

Four distinct markers, and the generic "nav bar" regex catches only the first two:

| Marker | Shape |
|---|---|
| Translator credit | `Penerjemah: X` / `Proffreader: X` / `Editor: X` — one line each, at the top |
| Full nav bar | `Previous Chapter \| ToC \| Next Chapter` |
| **Bare trailing token** | `Next Chapter` **or** `ToC \|` alone on the last line — **no pipes** |
| `Related Posts` | Blogger's footer block, from that word to end of text |

**The bare trailing token is the one that survives a first sweep.** Verified: after a pass that
handled the piped forms, 8 chapters still ended in a naked `Next Chapter` and 3 in `ToC |`. Anchor the
strip to end-of-string and run every variant:

```python
for pat in (r'\s*(Previous|Next)\s*(Chapter)?\s*(\|\s*ToC\s*\|?)?\s*$',
            r'\s*(\|\s*)?ToC\s*(\|\s*)?\s*$'):
    t = re.sub(pat, '', t, flags=re.I)
```

Then verify with a residue sweep over the final text for all of
`Penerjemah | Proffreader | Related Posts | Previous Chapter | Next Chapter | ToC` = 0. Do this
*before* the upload; the sweep is cheap and the markers are invisible in a casual read.

## Ordering the chapters by volume, then by role within the volume

The archive wants one global `urutan` running 1..N with `volume` restarting per volume. Build the
sort key from the title's ROLE, not from its position in the page:

```
Prolog / Prologue      → 0
Chapter N              → 1, N
Epilogue 1 / 2         → 8, 9        (epilogue LAST among story content)
Epilog / Epilogue      → 8
Kata Penutup           → 98
Afterword              → 99
```

Sort on `(volume, role_base, n)`. This also handles the fact that volume 3 spells it `Prologue`/
`Epilogue` and volume 1 spells it `Prolog`/`Epilog` — normalise the role before keying on it, or the
volumes sort against each other inconsistently.

## Which chapters are not chapters

The `Illustrasi` entries (one per volume) are image pages with ~30-60 chars of text — they carry no
prose. Drop them from the text load (create `Volume N — Ilustrasi` rows only if the archive stores
illustration pages as chapters; otherwise skip). Everything else — including each volume's
`Kata Penutup` (translator's closing note) and `Afterword` (author's) — is legitimate content the
archive keeps.

## Confirming the print volume count (the user will ask)

The translation site's `Type: Light Novel` + `Sumber: Raw Bookwalker` tells you a **print edition**
exists, and its volume count is a fact about the *work*, answerable only from the publisher. For a
PASH! Books work the series page (`https://pashbooks.jp/series/<slug>/`) prints one row per volume
with its release date, price and ISBN — that is the volume-count witness, and it may show a volume
**newer than the site's `Status In COO`**. Report the count with its evidence, and note plainly that
the volume split is not the same axis as the web chapters if a web raw also exists.
