# When the source ships a VOLUME as one post ("Babak") — split before loading

Depth for a human-translation blog (WordPress-style aggregator) that publishes a whole **volume** as a
single page instead of chapter-per-page. The text is good; its *granularity* is wrong for the shelf.

## Detect it: a "chapter" whose length is a volume's, and display markup that looks like chapters

- **A page that is 130k-160k characters (~20k+ words) is a volume, not a chapter.** A normal rack
  chapter is 5k-9k characters. Compute words (`len(re.findall(r'\S+', t))`) on each harvested page and
  flag any page above ~15k words as a container to split.
- **WordPress posts often wrap EVERY line in `<h3>` (or `<h2>`)** so a naive heading scan reports
  "1,005 chapters" and a sub-heading count of 1,005 — that is DISPLAY markup, one heading per rendered
  line, not chapter structure. Confirmed by: the headings are dialog sentences and prose sentences
  ("“Hah?”", "Aku─────malah senang."), and there is no `Chapter N` / `Bab N` / `***` / separator inside.
- **A page labelled `Babak N: <name>` / `Volume N: <name>` is a volume, not a chapter.** The giveaway is
  the *name* ("Babak 1: Nilaimu", "Babak 2: Jalan Cinta yang Sudah Dikenal" — titles, not numbers) plus
  the length. The section names are volume titles.
- **Verify the total against a known volume size before deciding.** ~52k words for the whole set = one
  light-novel volume. That is the confirmation the "Babak" is a volume, not that the source is incomplete.

## Split it: at PARAGRAPH boundaries, targeting rack chapter size

- Extract text first (see `cleaning-scraped-chapter-text.md`), then split the joined text on `\n\n` at
  **paragraph** granularity — never mid-paragraph, never mid-sentence.
- Target **5k-9k characters per output chapter** (matches the rack). A 160k-char container becomes ~20-25
  chapters; a 47k-char one ~6.
- **Prefer a cut that lands after a paragraph that closes a scene** when one is available near the size
  target; fall back to the nearest paragraph boundary. The output must not open or end mid-sentence —
  check the first and last character of every produced chapter.
- **The container's own front/back matter maps to rack titles, not to story chapters:** `Prolog` page →
  `Volume N — Prolog`; a `Cerita Pendek` page → `Volume N — Cerita Bonus`; `Kata Penutup` →
  `Volume N — Catatan Penutup`; an `Ilustrasi` page → no text chapter (image only). Match the existing
  rack title convention (see `cleaning-scraped-chapter-text.md` §titles).
- **A `Ilustrasi` page with ~2 chars is correct** — it is the image slot; do not invent a text chapter and
  do not drop the image. Download the illustrations and keep them for the `bab_gambar` slot.

## Scanner artifact vs real loss — the split is right when the pieces RECONSTRUCT the source

- After splitting, assert **sum(output chars) >= sum(source chars)** is NOT the test (HTML entity
  decode and `"\n"` separators change the count both ways). The test is: **concatenate the outputs,
  normalise whitespace, and confirm every source paragraph is present** — re-ordered or merged is fine,
  absent is not.
- A first-pass diff that says "the whole Babak ■ is missing" can be a **scanner artifact**: the section's
  sentences were merged into the neighbouring chapters' text, so an exact-substring probe for a 45-char
  prefix misses while the content is fully present. Before concluding a section was dropped, normalise
  both sides (collapse `\s+`, strip `&...;` entities and the scrape's `">` residue) and re-probe on a
  shorter key; then count how many source sentences are found in the output (verified: 174/200 sampled
  sentences of the "missing" section were present).
- Separator characters injected by the scraper (a `♦` scene marker) are not story text — they should be
  ABSENT from the output, and their absence is not a defect.

## Do not re-split by sentence — re-join, never re-flow

Same rule as the cleaning pass: the split only cuts at existing paragraph breaks. Do NOT rebuild
paragraphs from sentences (that destroys the author's paragraphing — verified failure mode in
`cleaning-scraped-chapter-text.md`). If the split looks wrong, redo the cut points; do not re-flow the text.
