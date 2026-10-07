# Auditing and repairing a novel ALREADY LOADED on the shelf

Depth for the case where the defect is not in an incoming raw but in text **already sitting in
`naver.db` and visible on the web** (the "rak"/shelf). Different from the harvest/clean pipeline:
the whole novel is live, the reader sees the damage, and every fix must be applied to the live DB
with a backup rather than to a staging file.

## 0. The web renders ONE `<p>` PER `\n` — line structure is what the reader actually sees

The site's chapter view splits the body on newlines (`teks.split("\n")`, one `<p>` per element). So a
raw that stored one paragraph per *rendered line* (a PDF hard-wrap) shows the reader a wall of
chopped ~55-char lines, while the DB text "looks fine" in a plain dump. **Diagnose from the render,
not the byte-count:** count single `\n` vs `\n\n` in the stored text; a chapter with hundreds of
single-`\n` breaks and few `\n\n` is hard-wrapped on the shelf even though it reads plausibly in the
source file. Verified: one published novel was 762 `<p>` lines where it should be ~234 paragraphs.

A clean sibling from the same pipeline (0 single `\n`) is the control that proves the defect is real,
not a property of the renderer.

## 1. Sweep the WHOLE loaded novel for the defect class before fixing anything

Run the finder over every chapter of the novel and print a per-chapter table (count of the defect).
Do not fix chapter-by-chapter blind — you need the scope to know whether this is a handful of
chapters or all of them, and to report an honest count. Tools are FINDERS (see
`per-chapter-manual-read.md`); the eyes judge each fix.

Separate the defect classes and check each independently:

- **Hard-wrap / paragraph structure** — single `\n` count, paragraph count, and how many paragraphs
  open on a lowercase letter (an artefact of a join that did not run).
- **Glued words** — the lowercase→UPPERCASE sieve (`akuKerabat`) and the connective sieve
  (`lebihbaikdaripada`).
- **Space-after-hyphen class** — see the per-source test in `per-chapter-manual-read.md` (artefact →
  fix the class; house style → leave). This is the one people get wrong by assuming a blanket rule.
- **Watermark/promo blocks** — donor name, `trakteer`, `https?://`, `donasi`, `blog sederhana`.

## 2. The hard-wrap repair rule for this donor family (`\n` = paragraph, not line)

For a raw produced by a PDF/Word layout, once it is in the DB, the reconstruction is:

1. **`\n` tunggal (single) = a paragraph boundary**, then re-expand it to `\n\n` — but only after the
   line-join below, or you fork a sentence across two paragraphs. A blind "single `\n` → `\n\n`" fixes
   the render and *breaks the prose* by turning one paragraph into 762 of them.
2. **Join a line to the next when the current line does not end on terminal punctuation**
   (`. ! ? ” …`) — the `sambung()` logic in `pdf-raw-to-chapters.md` §3c. Apply it to the stored text.
3. **A `\n\n` followed by a lowercase word is a paragraph SPLIT mid-sentence** (the previous join step
   over-split) — merge with a space. Verified: hundreds of these appear right after a naive join.
4. Re-count paragraphs and read the head/tail of sample chapters before trusting it.

The failure mode to avoid: running step 1 (or a "merge everything" pass) without steps 2-3 — one
attempt welded *all* paragraphs into a single blob (narration + dialog fused), another produced 275
"paragraphs" that were really 762 lines re-labelled. Fix, then READ.

## 3. Apply to the live DB with a per-batch backup, then re-verify the class is at zero

- Back up once per batch: `cp naver.db naver.db.bak-<what>-<ts>` (timestamped, so a rollback target
  exists for the exact change).
- Apply with one parameterised script (`<tool> --uji` on a copy first, then `--terap` on the real DB).
- Re-run the FINDER after the apply and require **0** for the repaired class, then rebuild the FTS
  index (the full-text index goes stale after a bulk text write).
- A non-zero residue is read, not assumed: some "remaining" hits are legitimate source prose (e.g.
  `sepenuh hati` is a normal Indonesian phrase, not the donor watermark that also used those words).

## 4. The publish is not done until the WEB shows the fix — the DB write and the live page are two things

- Pushing a ~70 MB SQLite to the VPS with a plain `scp` over a long transfer can TIME OUT and leave a
  **truncated, malformed** DB on the server (the page then 500s with `database disk image is
  malformed`). Use `rsync -avz --progress` in the background for a DB of this size.
- **Always compare md5 local vs remote after the transfer** — a byte-diff means the copy failed even
  when the tool exited 0. Then `pm2 restart naver-web` (the process keeps the old file handle open).
- Verify the change on the rendered page (fetch a chapter and confirm the `<p>` structure / content),
  not just in the DB — the user reads the web, not the file. If the page still shows the old shape,
  restart the web tier before concluding the write failed.

## 4b. Two ways a CORRECT page looks broken — rule them out before "fixing" anything

When the browser check on a freshly-loaded novel shows a chapter MISSING its images (or a chapter
looking locked), the page is usually fine. Both of these produced a false "images broken" verdict
in one session before the real cause was found:

- **LAZY-LOAD: the images are in the HTML but `naturalWidth` is 0 because they never entered the
  viewport.** A long chapter (tens of thousands of chars) is not scrolled by the default load, so a
  naive `querySelectorAll('img')` reports the first 1-2 as loaded and the rest as broken. **Prove it
  by scrolling to the bottom** (`scrollBy(0,600)` × ~50-60 with short waits, then optionally set
  `img[loading=lazy]` to `eager`) and re-counting — 8/8 loaded after the scroll, 0 behind it. Never
  report missing images from a non-scrolled check.
- **The LOGIN GATE (`gerbang_dasar`) is a FEATURE, not a bug.** The chapter template renders images
  with `{{% if g.urutan <= 2 and not gerbang_dasar %}}`, so a logged-out visitor sees only the first
  two illustrations of a chapter and a "Lanjut baca perlu akun" block; on some novels the later
  chapters are gated whole. Check the served HTML for `baca-terkunci` / "Lanjut baca perlu akun"
  before declaring anything missing — if it is the gate, the content is present and working as
  designed. **Do NOT "fix" the template** (the standing rule forbids changing the UI to chase a
  non-bug); report it as the gate.

The finder for both: fetch the page HTML and count `<img` tags and check for the gate marker — if the
`<img>` tag is in the HTML and the gate is absent, it is lazy-load; if the gate marker is present, it
is the login gate. Only when the `<img>` tag is genuinely absent from the HTML while the file exists
on disk is there a real loading bug.

## 5. Report honestly, per chapter, in Indonesian

Give the before→after numbers for each defect class (lines→paragraphs, `X- X` count→0, watermark→0),
name a specific fixed chapter as the sample, and state plainly which novels still carry the defect
class so the next pass has its priority. Never say "bersih" while a sisa list still prints.
