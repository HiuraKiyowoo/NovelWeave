# Per-chapter manual read-through (the eyes are the judge)

Standing order from the user, verbatim: **"Lu pakai alat cuma sebagai bantuan. Setiap 1 bab, cek dulu secara
manual pakai mata lu."** and **"Jangan cuma mengandalkan hasil dari alat atau parser."**

Applies to EVERY novel through the pipeline (harvest → clean → cut → load) and to MTL output. The tool is
only a FINDER; the eyes are the JUDGE.

## The loop is one chapter at a time, in order, no batching

1. Print the whole chapter (head + tail with `repr()`, so invisible chars show). A one-line `baca.py <n>`
   that prints `judul · char count · open/close quote counts · junk-hit count · glued-word hits` then the
   full text is the workhorse — write it once per session and reuse it for every chapter.
2. Check the six things by eye:
   - **Quotes** — missing, doubled (`““`/`””`), stray-hanging, or mixed straight/typographic.
   - **Truncation** — stops mid-sentence/mid-scene (compare against source).
   - **Junk text** — CSS/JS, HTML, menus, footers, comments, `function getFeedUrl`, ad lists, another
     novel's ToC. **A nav block can sit in the MIDDLE** (verified: line 594 of an ~800-line chapter).
   - **Paragraphs** — merged where a break belongs, or split mid-sentence (`itu\n\nsebelumnya`).
   - **Dialog/narration order** — still makes sense; speakers not scrambled.
   - **Nothing important lost or weirdly changed.**
3. Only after the chapter reads clean, move to the next.

A green tool means the finder found nothing — not that the text is good. Bitten twice: a `rapikan_teks`
reported perfect nets while 29/32 chapters still carried the site footer; a quote-repair script reported
"clean" while a chapter had lost its closing period (`sejati.”` → `sejati”`).

## Quote integrity: balance per PARAGRAPH, and classify before touching

The working method is **split on `\n\n` and compare opening vs closing count per paragraph**. A paragraph
with a residual imbalance (`b=1 t=0` or `b=0 t=1`) is either a real defect or a legitimate multi-paragraph
dialog — classify it with the decision table below, never blind-repair it.

| Signature | Verdict | Action |
|---|---|---|
| `b=1 t=0`, next paragraph is narration/dialog by someone else | **closing quote lost** | append `”` at the paragraph end |
| `b=0 t=1`, paragraph opens with narration text | **opening quote lost** | prepend `“` |
| `b=1 t=0` + `b=0 t=1`, same speaker, sentence runs on | **legit multi-paragraph dialog** | leave alone |
| `b=2 t=1` | two dialogs in one paragraph (`“A.” narration “B!”`) | legible as-is; only fix if a quote is truly unmatched |
| `“”teks”` / `““teks` / `“”“teks` | ghost-open glued to text | single `“` |
| `teks””` / `teks”””` | doubled close | single `”` |
| `“”` as a **standalone paragraph** | ghost paragraph | delete the paragraph |
| `“…”` alone | **legit** (character silent) | keep |

A whole-novel open==close total can still hide per-paragraph defects — always check per paragraph, and
remember a legit multi-paragraph dialog leaves TWO "odd" paragraphs forever. Do not report those as sisa.

## Repair order matters more than the regex

A quote normaliser must, in order: (1) collapse ghost/repeated quotes → one, (2) build the ellipsis form,
(3) do any **splitting LAST**. Splitting first produced `“…"\n\nHah?` — an orphaned dialog with a **missing
opening quote**. Never split `"…"word`: that is a **dramatic-pause marker glued to the dialog after it**
(verified on the Hikikomari source, 111 chapters). It stays one line.

## PDF→text quote corruption has a signature

A closing quote fans out to `”””””`; an ellipsis becomes `“”””””…………””””””`. Repair = collapse runs to one
quote, turn empty-quote-ellipsis into `“…”`. No legitimate `””`/`““` exists in this archive's prose
(verified across 111 chapters) — but **prove that per novel before trusting the collapse.**

## Blind quote-run collapse corrupts valid quotes — stop, do it per case

Collapsing `“{2,}`→`“` and `”{2,}`→`”` looks safe but is NOT: an ambiguous `“` + `””` sequence (ghost-open
followed by a valid close, or vice versa) can lose a legitimate opening quote. Repeated attempts ("balance
per line", "count per block") each deleted a valid quote on a different chapter. Rule: once collapse stops
converging, switch to an **explicit per-case replacement list** derived from reading the actual bytes at each
remaining spot — print `[f"{c!r}/{ord(c):04X}" for c in text[i:i+20]]` to see whether the tail is `.'`,
`.”`, `!'`, `!` etc. before writing the replacement. Verify a synthetic probe (`'“”Apa??” X'`) too — some
"failures" are test-string artifacts, not DB defects.

The trap that eats a run of tool calls: a *synthetic test string* containing `.“”` looks like a defect but
the real DB text is already clean (`“Apa?”`). Always print the bytes from the DB row you are about to edit,
never repair against a probe you typed yourself.

## Donor-site watermark blocks live INSIDE chapters (a junk class, not a footer)

A fan-translation donor (e.g. ruidrive) splices its own promo block between narration paragraphs — not at
chapter top/bottom. Signature: *"Kami dengan sepenuh hati telah menyusun PDF light novel ini… Kunjungi blog
sederhana kami di https://<host>/ … donasi … trakteer.id/<host> … Terima kasih atas perhatian dan
dukungannya!"*. Also appears in a short form as a bare `Ruidrive -` line mid-dialog.

- Search every chapter for donor names, `trakteer`, `https?://`, `blog sederhana`, `donasi` — one occurrence
  means blocks in dozens of chapters (verified: 33 chapters of one novel, 22 of another already published).
- Remove ONLY the matched block (regex under a `re.sub` with `re.S`, anchored on the block's first and last
  sentence); never blank an unbounded region — real narrative can sit immediately before/after.
- The same watermark may be a **sip** form; a second pass is needed. Re-run until the search returns zero.
- Non-breaking-spaces (`\u00a0`) survive in the block — strip them or the match misses.

## Audit sibling novels, not just the one in hand

The donor watermark, glued words, and quote corruption come from the **source/donor**, so one novel's defects
predict the others from the same source. When you find a defect, immediately grep the whole DB (all novels)
for it before reporting done — a published novel carrying the same junk is the higher-priority fix.

## Glued-word sieve (safe rule), and what is NOT a defect

Run a whole-chapter sieve for these, in this order:

- **lowercase→UPPERCASE boundary**: `re.findall(r"[a-z]{2,}[A-Z][a-z]{2,}", t)` catches `akuKerabat`,
  `nasionalKekaisaran`, `tersebutsebelum`-style drops. Verified safe: **zero** of them are legitimate
  compound words (78 hits in one novel, all real defects) → insert a space at the boundary.
- **fused phrase with a common connective**: `\b[a-z]{4,}(?:daripada|sebelum|setelah|dengan|untuk|tidak|akan|saja|juga|dari|kepada|yang|dan|itu)[a-z]{3,}\b`
  catches `lebihbaikdaripada`, `berhasilditerima`, `mengacauposting`.
- **DO NOT touch** Indonesian long words that are legitimate affixed forms — `menyembunyikannya`,
  `kesayanganku`, `mengkhawatirkanmu`, `berteleportasi`, `mengidentifikasi`. A naive "long word = glued"
  rule (e.g. flagging everything `\b[a-z]{16,}\b`) produces a wall of false positives and wastes the read.
  Check the tail: `-nya/-ku/-mu` and `meN-…-kan/-i` are correct morphology.
- **Space-after-hyphen (`teman- teman`, `Kaho- chan`) is PER-SOURCE — TEST the source, never assume.**
  Two opposite cases both verified: one novel (MTL from a live web raw) had ~15 of them and they were
  genuine house style (leave them); a sibling donor (ruidrive PDF) had **643** across 57 chapters
  and every single one was a PDF-extraction artefact (fix them all). The rule is not "always leave" or
  "always fix" — it depends on how the raw was made, so decide per novel with this test:
  - **Extraction artefact** (delivery/PDF raw): the split hits *every* kind of hyphenated token —
    reduplication (`tiba- tiba`), honorifics (`Satsuki- san`, `Kaho- chan`, `SMA- ku`), coinages
    (`tee- hee`). Uniform breakage of the whole hyphen class = the extractor dropped the space, not the
    author. Fix all: `X- Y` → `X-Y`.
  - **House style** (authored/MTL raw): only a *sparse few* appear and they cluster on a specific
    pattern (one author's reduplication tic), while honorifics and normal hyphenated words in the same
    text are joined correctly. Leave them.
  - **Deciding signal: uniformity.** If the same donor also breaks honorifics it never intended to
    break, it is an artefact — fix the class. Prove it by sampling the actual `X- Y` hits with
    `repr()` context before acting, and back up the DB per batch.
  Contrast: a genuinely glued **word** (`berhasilditerima`, no space at all) IS always a defect.

## Proof-of-fix hygiene

Fix on `uji<N>.db` first, read back with eyes, then apply to `naver.db` with a timestamped backup
(`naver.db.bak-bab<NN>-<ts>` per batch). After each apply, re-print the chapter's open/close counts and the
sisa list — the count is the cheap regression check. A `”` eaten from a valid `.”` is content loss the user
spots immediately.

## Other text defects seen in human-translated (not just MTL) sources

- **Glued words**: `menatapternganga`, `menginginkannyaberubah`, `mendapatkannyasebanyak` — dropped-space
  artifacts. Fix from an explicit per-case list, never a blind regex.
- **Extra space after opening quote**: `“ Bagaimana kabarmu?` → `“Bagaimana kabarmu?`.
- **Space before double punctuation**: `AYO KOOO !!` → `AYO KOOO!!`.
- **Straight vs typographic quotes** — count `"` vs `“`/`”` per novel; a volume with tens of thousands of
  straight quotes in an otherwise typographic rack is unnormalised, not stylistic.

## Straight→typographic quote conversion (ONE pass, per paragraph)

A whole novel can arrive with every dialog in straight `"` while the rack standard is `“ ”` (verified:
7,984 straight quotes in a 24-chapter novel whose sibling novels are all typographic). Convert in **one**
pass, per paragraph, and verify balance — do NOT run iterative repair scripts (see
`cleaning-scraped-chapter-text.md` §POST-PROCESSING: N passes leave a mixture and no pass can tell what a
line already received).

- **First prove the pairing is clean**: count paragraphs whose straight-quote count is ODD. If nearly all
  are even (verified: 3,826 of 3,830), alternating pairing from the left is safe — replace the 1st, 3rd, 5th…
  `"` with `“` and the 2nd, 4th, 6th… with `”`, per paragraph.
- **Nested single quotes `‘…’` inside a dialog are CORRECT** — a character quoting another speaker's words.
  Do not convert or strip them; they are not part of the straight-quote defect. (The same shape may be a
  genuine nested quote OR a stray single quote — read the surrounding lines before touching it.)
- **A multi-paragraph dialog leaves odd paragraphs that are NOT defects.** When a speaker talks across two
  or more paragraphs, the opening `“` on the first paragraph has no close until the last, so per-paragraph
  counts are uneven by design. Classify these with the decision table above; do not "fix" them.
- **A whole novel can be MOSTLY typographic and still carry a few hundred straight quotes.** Don't
  assume the file is unnormalised just from a straight-quote count — measure both. Verified: 23,310
  typographic vs only 580 straight in the same novel. Those residuals are usually **one of two
  context-readable cases**, decide by what FOLLOWS the `"`:
  - `"` followed by space / `.` / newline → it is a **closer** mis-typed as straight → `”`
    (the common case: a dialog ends `…berbicara. "` instead of `…berbicara. ”`).
  - `"` followed by a capital letter / `‘` / `“` → it is an **opener** → `“`
    (verified: narration then a fresh dialog: `mekanis berbicara. "Selamat datang!`).
  This rule resolved 573 of 580 with only ~7 genuine ambiguities to read by hand — far safer than
  re-running the full alternating pass, which would corrupt the already-correct typographic quotes.
- **Guard the quote-balance arithmetic AFTER a partial fix**: a novel that had 0 straight quotes left
  still showed open 23,513 vs close 23,483 (off by 30) — the imbalance was in TYPOGRAPHIC pairs, not
  straight ones (a mis-typed closer `hilang.“` again, and paired inline quotes `“pakaian pria” dan
  "pencocokan"`). Fixing straight→typographic does not fix these; find them by scanning per-paragraph
  open/close imbalance, then read each hit.
- **Balance the run-level totals as the cheap check, but resolve every remaining imbalance by eye.** The
  arithmetic will be off by a small number after the pass (verified: 4,010 open vs 4,007 close = 3 missing
  closes). Each of those 3 was a REAL defect found by reading the paragraph: a mis-typed closer at the end
  of a paragraph (`hilang.“` — a `“` used where `”` belongs), a close written as a straight single quote,
  and an opening quote with no close in a one-paragraph dialog. Never silence the imbalance by re-pairing.

## Verifying work a SUBAGENT (or another agent) did — the report is a self-report, eyes still judge

A delegated agent that cleaned/split a novel returns a confident summary ("all quotes balanced, 0
paragraphs lost"). Treat it as a CLAIM (per the tool guidance: subagent summaries are self-reports, not
verified facts) and re-check on the real files before accepting:

- **Re-run the arithmetic yourself** (chars, paragraph count, open/close per chapter) against the source
  file the subagent was given — do not accept its table.
- **Read head + tail of every produced chapter with your own eyes** and confirm no cut lands mid-sentence.
- **Do NOT trust a raw diff total as proof of loss.** A count that went UP (output > source) can be HTML
  entity decode plus added `\n\n` separators; a count that went DOWN can be dropped furniture. Neither
  proves anything until you locate WHERE the difference is. Verified false alarm: a diff-conclusion of "a
  whole 47k-char section is missing" fell apart once content was normalised and a shorter key was probed —
  the section's sentences were present, merged into neighbouring chapters.
- **A cheap universal acceptance test**: normalise whitespace/entities on both sides, then check that every
  source sentence (≥ ~35 chars) is findable in the output — merged or re-ordered is fine; a genuinely
  absent run of sentences is the only real loss signal.

## Never falsely reassure the user

Do not say "bersih semua" while a sisa list still prints. If 5 chapters still have a defect, say so with
the chapter numbers, fix them, and re-read. The user checks — an overstated "clean" costs trust.

## Report progress with a durable file, not just chat

A 100+ chapter manual pass outlives one context window. Keep a `PROGRES-<NOVEL>.md` in the work dir: the
proven-defect list, the not-yet-done list, and a per-chapter status table. Update it as batches complete so
a future session resumes instead of re-deriving. Also record sibling novels still carrying the same defect
(e.g. the donor watermark in an already-published sibling) so the next pass knows the priority.
