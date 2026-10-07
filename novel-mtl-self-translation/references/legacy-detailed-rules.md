> Legacy detailed rules preserved during the v2 dispatcher migration. Use the current `SKILL.md` flow first; consult this file only for an edge case not covered by the dedicated references.

## Contents

This archive contains the previous long-form workflow and diagnostic notes. Search by the relevant phase: rights, endpoint/model, source, parser, chunk, glossary, QA, DB, or repair.

---
name: novel-mtl-self-translation
description: "Safe, resumable machine-translation pipeline for rights-cleared novels, with source verification, quota preflight, parser adaptation, and staging-first DB import."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, android]
metadata:
  hermes:
    tags: [mtl, novel, translation, light-novel, pdf, sqlite, staging]
---

# Self-machine-translation (MTL) of a text novel

Turning a raw novel (a PDF/TXT/HTML dump in the source language, usually English fan-translation) into clean target-language chapters loaded into the project DB. This is the *text* pipeline — for image-based comics use `manga-manhwa-translator` instead.

The user's rule that governs this whole class, verbatim: **"Kita sambil garap novel sendiri juga gimana? Biar ga bergantung nyolong semua, minimal kita ada effort mgetl sendiri lah walaupun 1"** — this is the one workstream where the effort is ours. Treat the recipe below as fixed; do not improvise a new shape per novel.

Related: `web-scraper-builder` (the scrape side of the same archive), `ssr-web-over-own-api` (the site that serves the result).

**Before MTL-ing a new novel, check whether a human Indonesian translation already exists** —
a blogspot aggregator (Kaori, zerokaito, ruidrive) with a chapter list is almost always better
than MTL and free. Order of preference: **human ID translation → official EN LN → JP raw + MTL**.
MTL cannot fully match a human (it loses story context, wordplay, and tone). Recipe:
`naver-panen-sumber-blogger`.

**The raw may be the ORIGINAL language, an official EN translation, OR any other-language fan
translation (e.g. a `ranobelib.me/ru/…` Russian page) — all are one intermediate hop before
Indonesian and are equally valid.** Translate RU→ID exactly as you would EN→ID; do NOT refuse
a third-language reader site as "double translation" (the user corrected this directly). The
raw must only be a COMPLETE text — reject teasers/previews, wrong works, and empty shells.
**And verify a candidate raw link's `<title>` matches the requested novel before
building anything** — stored ncodes/slugs go stale and can point at a different work. Both rules
plus the "no free raw ⇒ ask the user" case: `references/source-selection.md`.

**Support files** (detail lives in the file — read the one the step you are on names): `references/verifying-a-novels-title.md` (source order for confirming a title; proving it from the raw when no authority has the alias). `references/source-selection.md` (choosing the raw: language, provenance, wrong-link traps, the third-language rule). `references/raw-source-map.md` (the whole raw-source landscape: JP-original vs third-party sites, the Syosetu general-vs-adult endpoint split, and the "a 200 is not a source — extract one chapter body and reject the teaser" proof rule). `references/web-novel-raw-sources.md` (pulling a free official Kakuyomu/Syosetu raw; safelink aggregators; Nyaa print scans). `references/third-language-raw-sources.md` (non-JP/non-EN reader sites). `references/jp-to-id-translation.md` (the JP→ID pipeline: prompt, glossary scoping, CJK-leak verification). `references/mtl-endpoint-and-model-selection.md` (which endpoint/model). `references/chunk-failure-handling.md` (interrupted/refused chunks). `references/resumable-mtl-runs.md` (manifest, per-chunk progress, quota pauses, and safe resume). `references/glossary-and-consistency.md` (names, terminology, register, quote style, separators, and one-pass normalization). `references/mtl-cover-and-assets.md` (cover + illustration sourcing and the missing-cover audit). `references/web-request-queue.md` (the reader-facing request queue and its ACC gate). `references/epub-import.md` (the EPUB path — which XHTML docs are NOT chapters, reusing the loader by emitting its input shape). `references/warehouse-volume-assembly.md` (assembling volumes from a warehouse dump whose rows are not chapters). `references/cleaning-scraped-chapter-text.md` (the "rapikan isi novel" pass over archived chapters, incl. the destructive-failure classes). `references/pdf-raw-to-chapters.md` (the PDF-sourced raw: defects, ToC-as-name-source, NFKC normalisation, the multi-volume SET discipline). `references/pdf-raw-extraction.md`, `references/source-shipped-as-volume.md`, `references/epub-illustration-extraction.md`, `references/per-chapter-manual-read.md`, `references/audit-and-repair-loaded-novel.md`, `references/verifying-and-repairing-novel-text.md` (per-paragraph quote balance, PDF hard-wrap repair, sub-agent report verification). `references/blogger-translation-index.md` (a novel published as one Blogger post per chapter behind a ToC index). `references/translation-group-drive-mirrors.md` (a translation-group blog post hosting volumes on **Google Drive**: mirror links over-count volumes, so **dedupe before reporting anything missing**; `file/d/…` file vs `drive/folders/…` folder — a folder id answers HTTP 500 and is NOT a dead link; the `embeddedfolderview` + `flip-entry` folder listing; `%PDF`/`PK\x03\x04` file fetch past the `confirm=` interstitial; the PDF's own `img-000` as the cover when the page lacks it). `scripts/pasang-cover.py` — the batch cover normaliser (`cover-asli/<id>.jpg` → `cover/<id>.webp` + DB row).

**Decide the raw's KIND before anything else** — its language and whether it is already a finished translation — because that choice decides whether this pipeline runs at all (see "A raw that is ALREADY in the target language" below) and where the raw even lives (a phone-storage `Hermes Storage/RAW/` drop, most often).

## A raw that is ALREADY in the target language is a different job — there is no MTL step

<!-- verified: the user handed over an EPUB already translated to Indonesian by another group -->
Before running any translation, **determine the raw's language and whether it is already a finished
translation.** The user supplies PDFs *and* EPUBs, and an EPUB taken from a translation group can
arrive **already in Indonesian** (its own `content.opf` declares `<dc:language>id</dc:language>` and
the title inside is the translated title, not the romaji). When that is the case:

- **Do not MTL it.** Translating an Indonesian translation compounds errors and is wasted work.
  Say so plainly ("ini sudah Bahasa Indonesia, tidak perlu MTL") and move to extract → verify → stage.
- **An EPUB is the better container than the PDF of the same work** — text is already separated into
  per-chapter XHTML files, so structure comes free. Read it with the stdlib, no extra tooling:
  ```python
  import zipfile, re, html
  z = zipfile.ZipFile(path)
  print([n for n in z.namelist() if 'chapter-' in n])      # the chapter list
  opf = z.read('OEBPS/content.opf').decode('utf-8')        # dc:title / dc:creator / dc:language
  ```
  Chapter files that are ~a few bytes are **separators/empty pages**, not chapters — filter by real
  text length before counting, or the chapter count comes out double. **But length alone is not
  enough: a TOC/nav document and an "About This Ebook"/colophon page are also not chapters** (the
  colophon is where the real metadata lives, so harvest it then drop the text). Confirm the count
  against the book's own `nav.xhtml`, which is also the cheapest proof that a front-matter "Start of
  Story" link and the real chapter document are the same scene, not two. When the user also supplies
  the PDF, use its chapter headings as an independent completeness witness (title-set match, not char
  totals — a PDF's per-page running headers inflate its count). Full recipe: `references/epub-import.md`.
- **Provenance changes the load rule.** This is **someone else's translation**, not the user's own
  MTL. The "MTL that is provably perfect goes straight to the main DB" exception below **does not
  apply** — that carve-out is for the project's own MTL output. An externally-translated work is a
  *third-party asset*: stage it, verify it, and **let the user approve** before it enters the main DB.
- **There is no separate no-MTL loader — convert to the translator's input shape and reuse it.** Emit
  `mtl/<slug>-potongan.json` (one record per chapter, each chapter as its single `potongan` with
  `terjemah` set and `selesai: True`) and the existing staging → `verif` → `up` path works unchanged,
  including the staging key `"<slug>:bab{i:02d}"` and the undo-log. Do not hand-write a second insert.
- Still run the full four-side verification (no truncation, no missing chapter, chapter count matches,
  plausible length) plus the CJK sweep — a translation group's EPUB can carry leftover source
  characters, translator notes, or promo pages exactly like MTL output does.
- **A translated EPUB and a one-shot web raw can describe the SAME request.** A reader's request can
  arrive as (a) a free web raw that is a `1話完結` one-shot, or (b) an EPUB from a translation group.
  Always check the container's own `dc:language` first: if it already says `id`, the whole MTL step is
  skipped and only verify+stage remains. Do not assume an offered EPUB needs translating, and do not
  assume a one-chapter raw is broken — read the raw/metadata and say which case it is before choosing.

**Support files:** see the list above. `scripts/pasang-cover.py` is the batch cover normaliser. `references/verifying-and-repairing-novel-text.md` — per-paragraph quote-balance check (sequential pairing), PDF hard-wrap repair, sub-agent report verification.

## Non-negotiable gates before any MTL run

These gates prevent the four most expensive failures: sending a batch to the wrong endpoint, publishing someone else's translation, inventing metadata, and corrupting production data. If a gate fails, stop and report the exact blocker.

1. **Rights and public-output gate.** Only process text the user owns, has permission to transform, is public-domain, or is otherwise licensed/authorized. Do not bypass DRM, paywalls, access controls, rate limits, or anti-bot measures. A third-party human translation is not the project's own MTL: quarantine it and require permission before publication. Keep source URLs, translator/group names, mirror links, and provenance in private/local working notes only; never put them into public synopsis, chapter text, metadata, HTML, or API responses. Do not publish a full translated novel when the permission/license does not allow it. This is an operational copyright/DMCA safeguard, not legal advice; when rights are unclear, stop. See `references/safety-and-rights.md`.

2. **Endpoint and quota gate.** The local gateway at `http://localhost:20128` is not an MTL endpoint; do not send a novel batch there unless a later probe explicitly proves a translation-capable route. Probe the actual OpenAI-compatible endpoint and model with one real-sized sample, confirm the response is a translation, then check quota/rate-limit status before starting a batch. Unknown quota means no large batch. Save a manifest and use resumable chunks; never retry a failed batch from zero. See `references/mtl-endpoint-and-model-selection.md` and `references/resumable-mtl-runs.md`.

3. **Metadata gate.** Verify the original/romanji title, work type, language, author, and edition before extraction. A missing synopsis is not permission to invent one: use an official publisher/platform synopsis, a licensed catalog, or a clearly marked short factual description from verified metadata. If none is available, leave synopsis empty and report it. Convert Indonesian-only titles to an official English title or romanji when verified; never guess an ATL. See `references/source-selection.md` and `references/title-metadata-policy.md`.

4. **Database gate.** Before inserting or updating anything, run exact and normalized searches for the full title, original title, and slug across every relevant DB and staging output. Back up the target DB, record the backup path and schema, and run `PRAGMA integrity_check` before changing it. A slug collision is a stop condition, not a reason to append `(2)` silently. Stage first; production import requires an explicit review. See `references/db-change-safety.md`.

5. **Parser gate.** Inspect the actual raw before choosing delimiters. Parsers must be adaptive per source/volume: test single newline, blank line, `＊＊＊`, form-feed (`\f`), HTML headings, and EPUB `h1`/body structure. Do not trust a TOC or a generic splitter without checking following-content length and a sample of reconstructed text. See `references/parser-adaptation.md`.

## The pipeline, in order

0. **Check the archive DB for the work FIRST, before searching anywhere or asking for the raw.** One `SELECT` over the main DB answers "is this novel already in?" and stops you re-translating a finished book: match the candidate against `judul`, `judul_asli`, `slug` (also staging `mtl.db` and the `mtl/*.json` outputs). `LIKE '%<keyword>%'` on each — a hit means stop and say which id it is. Verified: a title the user asked about returned 0 rows in the main DB, confirming it as a genuinely-new novel. **Search every DB in the archive, not just the main one** (main + any quarantined/imported DBs + staging) — a work can be absent from `naver.db` and still already present in an imported set, and "not in the main DB" alone is a weaker answer than "not anywhere". Also distinguish a **whole-title** hit from a **partial-keyword** hit: a query on a common word (e.g. *tenshi*, *reijou*, *kyoushi*) matches many unrelated works — confirm the full title, and say plainly those are different novels rather than reporting a match. For the *request-queue* variant of this step (reader asked via the site), see `references/web-request-queue.md`.
1. **Identify the work before touching the raw — and settle WHICH KIND of raw it can ever have.** Two shapes exist and they need different answers, so decide this first or you will search the wrong place for hours:
   - **Print origin** (a KADOKAWA/Bunko volume, or anything with a RanobeDB `books[]` row + a BookWalker id): the English/JP raw is a *scan that may not exist yet*. A very recent volume (RanobeDB `start_date` this year) means no fan translation exists and none is coming soon — say so plainly and park it (`CATATAN/<date>-calon-MTL-<slug>.md`: full metadata + JP synopsis + the pipeline steps to run later). Do **not** keep hunting for a raw that cannot be there, and do not ask the user for one they cannot have either.
   - **Web-novel origin** (Kakuyomu / Syosetu / Alphapolis): the raw is published **by the author, free and official** — the best case, and usually *not* indexed in RanobeDB, so don't stop when RanobeDB misses. See `references/web-novel-raw-sources.md`. **A web entry can be a one-shot (`1話完結`)**, in which case the free version is a single chapter and the print book is a longer, different work — a 1-chapter raw is then *correct*, not a broken scrape. Tell the user which they have and let them choose.
   Then get the real original title (JP romaji + English) and confirm it against a metadata source (RanobeDB, KADOKAWA, Google Books, the user's own catalog). **A JP title is often THREE works at once** — a web novel, a print LN, and a manga adaptation, all under the same romaji — so settle which one the user means before hunting a raw, and never answer a volume-count question from the web raw (the web text has episodes/`章`, not volumes). See `references/web-novel-raw-sources.md` ("The SAME title is often THREE works") for the tells and for the publisher's series page, which is the volume-count witness when RanobeDB is empty. See `references/verifying-a-novels-title.md` for the exact source order; a fresh match is a direct `GET https://ranobedb.org/api/v0/series?q=<romaji>&limit=6` (a romaji match is your confirmation, then `GET /api/v0/series/<id>` for detail) — the search hits need `q=`, not a `/search` path. Long `q=` strings can make the API return an empty/invalid body; short and progressively broaden it. Confirm the raw actually matches — read the PDF's own Title metadata and the extracted text; a Google-Docs-rendered PDF carries its Title string in metadata. Do this *before* investing in extraction.
2. **Extract text.** `pdftotext` (poppler) is the reliable tool; a `ToUnicode` CMap present means text is extractable. Check `pdfinfo` first (page count, encryption, fonts). `pypdf` is a fallback; do not reach for a heavyweight OCR stack for a text PDF. `pdfinfo`'s Title field is often the *publisher/translator's own* title string (e.g. `[Main] Is It Okay If I Stay This Close to You? – Starting a Chill Break with the Class Idol`) — a better original-title source than any scraped ATL, and proof the raw matches the work.
3. **Map the structure** — table of contents, part titles, and where chapters begin. Verify the number of parts found against the printed contents list; a naive splitter often produces double the real chapter count by catching both the TOC and the body headings. **Discriminate TOC hits from real chapter starts by following-content length, not by position**: a heading followed by ≥~1200 chars of body is a real chapter; the same heading followed by only its own line is a TOC entry. Filter on the following chunk's size (`Episode 6: The View We Share` → 49,539c real vs 0c TOC) and you get 9, not 18.
4. **Chunk, then translate.** Split the raw on **paragraph boundaries first, sentence boundaries second** — never mid-sentence, never mid-word. Keep the chunk small enough that the model returns the whole thing.
5. **Translate chunk by chunk, saving each result as its own file** as it completes. Long translations get interrupted (host OOM, a hung request); per-chunk files mean a re-run resumes instead of restarting. Count the saved chunk files to measure progress — do not trust a log line.

   **Chunks are translated independently, so a character's name drifts between them.** Each call sees only its own chunk, and a model romanising a Japanese name from scratch picks a different reading every time — verified: one heroine came out as **four** different names across one 6-chunk chapter (`Hijaraki` ×8, `Kadurigi` ×2, the correct `Kaburagi` ×2, plus a bare surname-only form), and the protagonist gained an invented name. A char count, the CJK sweep and a length check all pass. Fix it with a **glossary that is part of every call's prompt**: extract the names (from the source page's ruby/furigana or the work metadata) into a `GLOSARIUM = {jp: romaji}` dict, inject `k = v` for each entry into the prompt with "WAJIB PUKAI NAMA INI PERSIS, jangan dikarang versi lain", and keep a `NAMA_SALAH` list of the wrong variants already seen — reject and retry any response containing one. Verify at the end by counting every correct and every known-wrong variant over the whole joined text.

   **Rewrite `GLOSARIUM` and `NAMA_SALAH` from scratch for EVERY new novel; never leave the previous novel's entries in place.** These two lists are novel-specific vocabulary, and a stale entry is not inert — it actively corrupts the new book. Verified three times in one project: a leftover `"penyihir sihir"` entry rejected a correct rendering, a leftover `"Lest"` entry rejected the new novel's own *protagonist-adjacent character name* on **12 consecutive retries** (28 minutes burned on one chunk before the loop gave up), and `Hakushaku`/`Kouchaku` (伯爵/侯爵 — the ordinary words for *marquis*, which the new novel uses as titles) were sitting in the blacklist as if they were misspellings. Two rules fall out:
   - **A `NAMA_SALAH` entry must be a wrong *romanisation of a name* — never an ordinary word that can legitimately appear in prose.** Before adding one, ask whether the string could be a real word, title, or rank in *any* novel. If yes, it does not belong in a blacklist; fix the glossary instead.
   - **A stale blacklist does not announce itself.** The symptom is not an error — it is a chapter whose chunks each take 20-30× the normal time (a reject-retry loop spinning) while the log reads like ordinary progress. Any wall-clock outlier on a chunk is a blacklist false-positive until proven otherwise; look for `DITOLAK (nama salah: …)` lines and check whether the flagged string is actually correct in this book.
6. **Clean.** `***` (or a horizontal rule) is a scene break — keep it as a separator, do not translate or drop it. Strip translator notes ("Message From Translator"), page numbers, running headers, and PDF artifacts.
7. **Verify on four sides before declaring done:** no truncated tail chunk, no chunk missing from the middle, the joined length is plausible vs the source char count, and the chapter/part count matches the contents list. A single missed chunk in the middle is the failure mode this check exists for.

   **Verify with a script over the whole joined chapter, not by eye and not per-chunk-marker.** The marker (`selesai`) and the chunk count are both written by the same pipeline that can be wrong, so they can agree on a lie. Independently recompute: CJK/kana sweep (`[\u4e00-\u9fff]`, `[\u3040-\u30ff]`) = 0, the refusal-substring list = 0, the length ratio inside the healthy band for that language pair, every glossary name non-zero and every `NAMA_SALAH` variant zero, and the first/last paragraph reading as the story's real opening and ending (not a promo card for another novel). Five checks, all cheap — run them as one pass and print per-chapter, so a mid-novel hole is located by id instead of found later by the user.
8. **Stage, then load.** Put the result in a **temporary/staging DB first** (`antrian.db` / a staging table), never straight into the main `naver.db`. The user's rule: **"kalo semua udah beres, pindahin ke termux db sendiri dlu, jangan di db utama"** and **"lu habis skrep novel baru lu jangan langsung up ke db, bersihin dlu verif… kalo udah bener 100% baru up walaupun 1 novel, 1 novel cicil aja gpp daripada langsung kek 5, tapi salah kan"**.
- **Match the novel's ESTABLISHED voice, and enforce it mechanically — the pipeline's own default voice drifts from the archive's.** The MTL model's default Indonesian register says `saya/kamu`; the archive's chapters (and the reader's expectation) say `aku/kamu`. Verified: 5 chapters of one novel read ~22,000 `aku` against ~120 `saya`, and the 5 MTL chapters inserted into it were the only `saya` in the book — a register no reader asked for, sitting mid-volume. Measure the archive first (`grep -o '\baku\b'` vs `\bsaya\b` over the existing chapters), then force the MTL output to it. **Manual splices are where this bites hardest:** when a chunk is hand-translated around an endpoint refusal, the hand-typed register joins the model's, so a single chapter can carry both — run the normaliser over every chapter you touch, not only the model output.
  Do the replacement with **case-preserving word boundaries** (`\bAku\b`→`Aku`, `\baku\b`→`aku`, same for `ku-`, and for the possessive clitics) so `kamu` is not half-replaced by a `mu` rule. Then **re-scan for the phrasal damage a word-level swap creates** — `milik aku`→`milikku`, ` untuk ku`→`untukku`, `punya aku`→`punyaku` — and re-read a few paragraphs with your own eyes, because `\baku\b` is also the tail of legitimate prose (`milik aku`, `punya aku`). Do NOT regex `terima kasih ku`/`untuk ku` without checking the match: `untuk ku` also matches the tail of `terlambat untuk kursus`, a false alarm that a whole-line `repr()` read resolves in one step. A register normaliser is a whole-novel post-pass, not a per-chapter afterthought.

  **Register is not the only axis — the QUOTE CHARACTER is a second style axis the model does not inherit, and it must be normalised to the archive too.** The MTL model emits straight quotes (`"`); the archive's finished chapters may use curly ones (`“ ”`) — or the reverse. Mixed quote styles in one reader look like a defect even when the prose is perfect. Settle it before loading:
  - **Measure the archive's majority style first** — count `"` vs `“”` over the existing chapters of the same shelf (one pass, `COUNT` not eyeball) — and convert MTL output to whichever dominates, rather than to your own preference. The user's reason is the standing one: it must be *consistent with the other novels on the shelf*.
  - **Convert with a paired-replacement, and assert the pairs stay BALANCED.** Straight→curly cannot be a global find/replace: alternate each `"` between opening and closing, then check `teks.count('“') == teks.count('”')`. Balanced counts before and after are the proof you did not flip a closing quote into an opening one mid-dialog.
  - **Do not convert quotes that are not dialogue** — an inch mark, a code fragment, or an apostrophe inside a word is not a quote pair; scope the pass to the novel's story text and spot-read a dialog-heavy chapter afterwards.
  - Run it in the same pre-load normaliser as the separator and register passes, so it is applied to every chapter you touch (including manual splices) exactly once. **Exactly once — do NOT run a second quote script over the first one's output, and once mutated the file can no longer be diagnosed (restore from the raw chunks first).** The model's OWN quote defects (reversed `”…“` pairs, a pair straddling a chunk seam, an UNTRANSLATED or model-reply chunk) are a different class that no style pass fixes — but **before sweeping for them, prove they exist in the untouched raw chunk output (`print(teks.count('"'))`)**; verified: a long multi-pass detour chased "reversed curly quotes" that the model never emitted — the MTL used straight `"`, correctly paired, and every `“`/`”` in the file (paired wrongly) had been introduced by the first style pass. Chasing a defect on a file you already rewrote is chasing your own pass's output. Rules and the sweep: `references/cleaning-scraped-chapter-text.md` §"Post-processing MTL output".

  **A third axis is the CHAPTER HEADING that sits INSIDE the body text, and the model leaves it in English because it is prose to the model, not a field to you.** A print-derived raw repeats the chapter's own label as the first line of the body (`Prologue`, `Chapter 3: Labyrinth`, `Afterword`, `Bonus`), and MTL renders it verbatim — so the archive gets `Chapter 3` sitting above Indonesian prose, on only the *some* chapters (the ones whose source carried a label). Verified: one volume came out with `Prologue` and `Chapter 3` in English while its siblings read `Bab 1`, `Bab 2`. Fix it in the same pre-load pass with anchored line-start rules — the heading is a whole leading line, never a mid-prose word:
  ```python
  t = re.sub(r"(?m)^\s*Prologue\b", "Prolog", t)
  t = re.sub(r"(?m)^\s*Chapter\s+(\d+)\b", r"Bab \1", t)
  t = re.sub(r"(?m)^\s*Afterword\b", "Catatan Penutup", t)
  t = re.sub(r"(?m)^\s*Bonus\b",      "Cerita Bonus", t)
  ```
  **Anchor on the line start (`(?m)^`) plus the label word — an unanchored `Chapter\s+\d+` also rewrites a mid-sentence mention of chapter numbers, and a bare `Bonus\b` matches ordinary prose.** Then verify per chapter by printing the FIRST LINE of the joined text, not the char count: the ratio can be a healthy 106% while the heading is still English, because a heading is a rounding error in the length. Also note the two label sets are not 1:1 — the *structural* title (`Volume 3 — Chapter 2`, from the count) and the *body* label (`Bab 2: Pertempuran Milista`, from the source) can disagree in numbering; the body label carries the real name, so trust it for the name and derive the structural one from order.

  **A `saya`/`anda` hit in the sweep is damage; a `***` on its own line is NOT — classify before you normalise.** The normaliser's own output has to be checked per hit, not per count: `***` (or `◇◇◇`, `＊ ＊ ＊`) is a legitimate scene separator the pipeline deliberately preserves, and a regex aimed at `saya/anda` or at "stray asterisks" can eat it. Read each hit's surrounding line (`repr()` of ±60 chars) and decide: `***` alone on a line → keep; `saya`/`anda`/`kami` mid-prose → it is a register defect, fix it. `kami` is the trap here — it is correct Indonesian for "we" and must be left alone; only `saya`/`anda` are the drift. And if the source's separator was decorative (`∮ ∮ ∮`), the model may echo it as a bare `***` run, in which case the normaliser SHOULD collapse it — the count check against the raw is what tells you whether it was a real break or an echo.
- **Use the same verb/tense/voice conventions the source novel set.** Once the archive is one register, a new chapter in a different one is a visible defect; the fix belongs in the pipeline, not in a note to the user.**Load one novel at a time** (cicil). Before insert: check for duplicates against the main DB, compute the new id, **confirm the chapter table's actual column names with `PRAGMA table_info(bab)`** (in this project the body column is named **`teks`, not `isi`** — inserting into a guessed name fails or blanks the row), mirror the existing row shape (cover path columns, `cover/1988.webp` + `cover-asli/1988.jpg` style, FTS table name). **Number `urutan` GLOBALLY 1..N across the whole novel, not per volume** — the site reads `ORDER BY urutan`, so a per-volume numbering interleaves the volumes' chapters in the reader. Write an **undo-log** (the inserted novel id + its chapter ids) so the load is reversible, insert, then re-verify counts (novel count, chapter count, FTS hit counts, cover present, no FK violations) and report the undo-log path. If the project has a verification helper (`periksa-rak.py <id>`), run it — it compares chapter count against the stored `jumlah_bab` column and flags empty chapters, gaps and duplicate numbers; counting rows alone does not.
10. **Resolve the cover URL at load time, or the poster column ships a name with no file behind it.** Adding the novel is only half the row — the asset columns hold *relative paths* (`cover/1989.webp`), so writing them without producing the file leaves the detail page with a broken poster and a **404, not a missing-image placeholder**. Before the up: take the cover from the user or the raw, normalise it to the archive's ratio, write **both** files under the project's asset dirs (`cover/<id>.webp` served by the web tier, `cover-asli/<id>.jpg` as the raw archive copy), probe `GET /cover/<id>.webp` for 200 + an image content-type, then insert. Measured on the real archive: **a cover can be at the correct `n_potongan`-equivalent count of metadata and still not exist as a file** — the row recorded both column names and only the probe told the truth. **When the DB is later synced to a separate serving host, the asset file does NOT travel with it** — the row lands with a correct relative path pointing at a file the host lacks, so the page loads and the poster 404s. Ship the cover in the same sync step (or a tool mode that sends both), then probe the PUBLIC hostname (`200 image/webp`); `cover-asli/<id>.jpg` is not served and its 404 is expected. See `ssr-web-over-own-api` for the serving side (mount + public-hostname probe + the Cloudflare edge cache that keeps serving a replaced poster for up to 7 days) and `references/mtl-cover-and-assets.md` §3b for the sync rule and `references/mtl-cover-and-assets.md` here for the paste-source and normalisation recipe.

    **Standing user rule: do NOT go source a poster yourself.** Take a cover only from (a) a URL the user pastes or (b) an image embedded in the raw they supplied — never from Wikipedia/YenPress/AniList/catalog `og:image`, however good the match looks (user, verbatim: *"kalo poster jangan asal ambil soalnya itu di ada 3 novel yg salah"*). When a novel has no cover, record it in the outstanding worklist and wait for the artwork; do not generate placeholders or loosen a filter to hide it. Detail in `references/mtl-cover-and-assets.md` §0.

## Resuming a part-finished novel: `--lanjut` must be idempotent, and it usually is not

<!-- verified: a "continue" run re-translated and OVERWROTE two finished chapters (2,535c → 18c; 41,556c → 18,476c) before it was caught by the char count -->
A resume mode is the highest-risk code in the pipeline, because the failure is silent destruction of already-good work and it looks like normal progress in the log. Three defects to fix together before the first resume run — all three were present at once:

1. **A completed chapter gets translated again and overwritten.** Any gate that infers "not finished" from a single field (e.g. `len(potongan)`), when the finished work lives in a *different* field (`terjemah`), re-translates sound output. Gate on the finishing marker itself and skip outright:
   ```python
   if rec.get("selesai") and rec.get("terjemah"):
       continue          # never touch a chapter already marked done
   ```
2. **More saved chunks than the chapter needs resets the resume point to zero.** `if len(done) >= len(pot): mulai = 0` treats "extra" as "restart", so one stale chunk rewrites the whole chapter. Excess is stale state, not a restart signal — **truncate, then continue**:
   ```python
   if len(done) > len(pot): done = done[:len(pot)]; rec["potongan"] = done
   mulai = len(done)
   ```
3. **The result key does not match the existing file's keys.** If the raw carries no `id`, a fallback like `str(b.get("id") or bi)` writes `"1","2"` while the file uses `"bab01","bab02"` — so a resume silently writes a *parallel* set that never joins the old chapters. Fix the key format to what the file already has (`"bab%02d" % urutan`) and delete the parallel keys.

**Back up `mtl/<slug>-potongan.json` before every `--lanjut` run** (`cp` to a `mtl-cadangan-<ts>/` dir). A resume you cannot undo is a resume you should not start.

### Detecting the damage in one pass — measure, do not read the log

<!-- verified: the corruption was found by a char count, not by the log, which read as normal progress -->
For each chapter compute the ID length against its own EN length and print the ratio. The healthy band is ~95-115% (Indonesian runs slightly longer than English):

```python
idn = len(v.get("terjemah") or "") or sum(len(x["id"]) for x in v["potongan"])
rasio = 100 * idn / v["en_panjang"]      # 0% = never done · ~62% = truncated · 95-115% = normal
```

A ratio alone is not enough for a *partially* damaged chapter — check the chunk boundaries too. **A chunk that opens on a lowercase letter, a bare mid-word fragment, or a continuation like `" lapor di meja…"` is torn, not short.** A resume that had been "interrupted mid-chunk" leaves exactly this. Torn chunks cannot be salvaged by keeping them: reset that chapter (`potongan=[]`, `selesai=False`, `terjemah=""`) and re-translate that ONE chapter (~15 min) rather than the whole novel.

**A chapter's chunk count can be at the full `n_potongan` and still be damaged** (44/44 chunks at 62% of source) — the marker and the count both lied; the ratio and the boundary shape are what told the truth.

**The inverse false alarm: a chapter that is SHORT compared to its neighbours is not thereby truncated — measure it against its OWN source length.** Verified twice in one volume: a Prologue at 2,784c and an Afterword at 1,232c sat beside 160k-char chapters and looked like casualties, but each was 106-110% of its own `en_panjang` (the source chapters really were that short). **The alarm is a cross-chapter size comparison; the verdict comes from the per-chapter ratio** — a front/back-matter chapter is legitimately a fraction of a story chapter, and the honest generated-title rule already treats an empty `Volume N — Ilustrasi` page as correct content for the same reason. Read the short chapter's head and tail with your own eyes to close it out, then move on; do not "repair" or re-translate a chapter whose ratio is healthy.

### Recovering finished chapters from the staging DB

The staging DB (`vps/mtl-masuk-db.py <slug> staging`) is not only a pre-insert checkpoint — it is the **backup of last resort** for finished chapters. When the resume destroyed them:
1. `sqlite3` the staging DB and find the novel by **matching the title**, not by assuming it is the only row (staging accumulates many novels; the wrong one silently returns another book's chapters).
2. Rebuild the per-chunk file from the `bab(urutan, judul, teks, en_panjang)` rows — you may not know the original split, but you do not need to: set `potongan` to the chunks you can reconstruct and let the resume fill the rest.
3. Do not mark reconstructed chapters `selesai` unless the text is provably complete — a wrong `selesai` is worse than a missing one, because it stops the resume that would have fixed it.

The raw source file (`mtl-raw/<slug>.json`) is never touched by the translation, so it is always the final fallback: worst case, re-translate from it.

## Auditing the QUALITY of a human translation — the flaws are human ones, and tool counts lie

<!-- verified: a blogspot/translation-group novel (human-translated) was audited; a "29 repeated words"
     machine flag was 100% false positives, and the correct verdict was "good, no repair needed" -->
When the work is a **finished human translation** (a Blogger/translation-group novel, a translated
EPUB) the audit is not the MTL verification pass — there is no MTL to check, and the defects to look
for are a human's: stiff/unnatural sentences, inconsistent honorifics, non-uniform terminology,
leaked foreign words, broken entities. Two rules keep the verdict honest:

- **Read a chapter or two in full first, then sweep all chapters systematically — with your eyes, not a
  counter** (the standing "lu jangan ngandelin alat" rule). A tool may *nominate* candidates; it never
  delivers the verdict.
- **A machine "repeated word" list is mostly FALSE POSITIVES — classify every entry before reporting it
  as a defect.** Verified big classes that are legitimate, not defects:
  - **Dialog emphasis / shouting:** `"Tidak! Tidak tidak tidak tidak!"`, `"MEMERKOSA MEMERKOSA"`,
    `"Suka suka suka"` — repetition IS the delivery.
  - **Onomatopoeia / laughter:** `"Nyam nyam"`, `"hap hap"`, `"Ho ho ho"`.
  - **Legit Indonesian reduplication the tool misreads as an English repeat** — `was-was` (anxious)
    has nothing to do with the English word `was`; a naive \\b-based detector flags it as a repeat.
    Same class: `sama-sama`, `kapan-kapan`, `tiba-tiba`, `was-was`, `suka-suka`.
  - **A leading space before a quote** (`' …Ugh"'`) is often the source's own style, not a defect.
- **The correct verdict for a good human translation is "BAGUS, tidak perlu diperbaiki" — do NOT
  "improve" it.** Reshaping prose that already flows is the user's own definition of damage; report the
  verdict with a couple of concrete bits of evidence (a flowing sentence, a correctly-used honorific)
  and move on.
- **An empty illustration chapter (`Volume N — Ilustrasi`, 0 chars) is CORRECT content, not a defect** —
  it is an image page. Keep the honest title, leave the body empty, and wait for the artwork; never
  delete the row or fill it with placeholder text.

## Model endpoint

Use the local OpenAI-compatible endpoint the project already standardised on (this user: a local gateway `http://localhost:20128/v1`). **Distinguish "a marginal quality upgrade" from "the model structurally refuses this book"** — the two look similar and need opposite responses:

- **Do not churn models for a marginal quality gain on the same kind of content.** Consistent output matters, and re-verifying a model change costs a full pass.
- **DO swap the model when the current one refuses a whole content CLASS.** A model that answers `high risk` on every intimate scene is not a quality tradeoff — it is a capability gap, and no amount of prompt-shortening fixes it for the whole book. Verified: with the default free-tier model, 72 chunks across two volumes sat empty and re-refused on every retry (hours of retry loops); switching to `cbai/deepseek-v4.1-flash` translated all 72 in ~5 minutes with no other change. Do not treat "the user's project uses model X" as a lock-in when model X cannot do the job — probe the alternative on the refused content and switch, then note it for the next session.

The fix order for a refused chunk is therefore: **(1) bare short prompt retry, (2) switch to a model that does not structurally refuse the content, (3) only then hand-translate.** A refusal that survives (1) across many chunks is a model-selection problem, not a per-chunk accident.

**A chunk that failed after every fallback must NEVER be persisted as the source-language text, and a chapter with any unresolved failed chunk must NOT be marked finished.** A network drop fails every in-flight chunk at once; a last-resort `hasil = teks_asli` branch then writes raw source text into the book while the log looks like normal progress, and the resume skips the corrupted chapter forever. Same family: a `finish_reason` of `abort` with 0 output is a model quirk, not content refusal — retry on the fallback model or split smaller. Full rules, the residue sweep (count source-script chars per chapter), and the why: `references/chunk-failure-handling.md`.

**A free-tier model can be OUT OF QUOTA while the gateway is perfectly healthy — and every chunk then fails at once.** The signature is a `503`, whose BODY carries the real cause: `[429] … "You've used this campaign's own allowance. Use the paid model …"` plus a reset window (e.g. `reset after 1m 18s`). Two traps in reading it:
<!-- verified: 801 consecutive failures across two volumes; the endpoint answered HTTP 200 on /v1/models the whole time -->
- **The status code is `503 Service Unavailable`, not `429`** — the gateway wraps the upstream quota error, so "503" reads like "the endpoint is down" and sends you to restart the wrong thing. **Print the response BODY of a failed call before diagnosing anything else**; a bare `except` that swallows it leaves you guessing at an endpoint that was never broken.
- **Parallelism is what spends the quota.** 8 concurrent workers drained the free allowance in minutes and then every in-flight chunk failed together — the batch failure looks like a hard outage but is just exhaustion. **Probe the candidate models again after a batch failure** rather than assuming the endpoint died, and expect a *mix*: on this gateway the paid names returned `402` (no balance) while two free names still answered — `harbor/deepseek-v4-flash:free` (~3.9 s) and `cbai/deepseek-v4.1-flash` (~2.4 s, fastest). Pick the free one with remaining quota and re-run; the failure is a *model choice*, not a broken run.
- **A quota exhaustion and a withdrawn model look alike from the pipeline** (both: every chunk fails, generic error in the log). Distinguish them with one `curl` that prints the BODY, and keep an ordered `MODEL_CADANGAN` fallback list so the run survives either.

**Discover the models with one call** (`GET /v1/models`) rather than guessing names — the gateway lists what it can serve, with capabilities and context length, and the list already includes stronger models the user may point you at. Read the API key from the approved file, never print it. **A wrapper client's translate function may return a TUPLE**, not a string — `(hasil_teks, pesan_error)`, with `''` on failure. Read its docstring/signature before composing on the return value, or a `.strip()`/`.split()` on it raises `'tuple' object has no attribute 'strip'` and every call looks like a failure.

**Put the translation instruction in the USER message, not a `system` role.** Verified on a reasoning-family model (`cbai/deepseek-v4.1-flash`, 1M context): with the same prompt in a `system` message it answered with **raw Japanese** — and at `reasoning_effort=none` it emitted a Chinese *continuation* note (`（接上一段剧情，延续…）`, i.e. "carrying on from the previous passage") instead of a translation. Sending the identical prompt as the single user message produced clean Indonesian, 0 CJK. Concatenate prompt + `"\n\n=== TEKS YANG HARUS DITERJEMAHKAN ===\n\n"` + chunk into one user turn, and add those continuation strings to the reject list. Treat "a model I was told to use returns source-language text" as a prompt-placement problem to try fixing, not a broken model to give up on.

A local/gateway OpenAI-compatible endpoint can **hang a streaming request** — a call that streams and is iterated (`for raw in r:`) can block far past any sane timeout, because a stalled stream that never closes waits forever. Make translation calls **non-streaming** and set a hard socket timeout (`socket.setdefaulttimeout(240)`) so a stall raises instead of waiting. Treat "the process is alive but produced no new file in N minutes" as a hung request to kill and retry, not as slowness.

Diagnose it in one shot before blaming the endpoint — run the same chunk through `curl`/a script with a deadline while the worker is stuck. If the synchronous call returns fine in seconds while the worker has produced nothing for minutes, the worker is hung, not the endpoint. The session's real timings: a 3330-char chunk returned in ~52 s via curl while the worker had been silent for 9 minutes; after switching to non-streaming, chunks settled at a stable 46-57 s. Progress is measured by **counting saved chunk files**, never by reading a buffered log (`tee`/`nohup` buffer; a log can look frozen while work advances, or look alive while it is stuck) — but a *file mtime* going stale while the loop is alive is the definitive hang signal.

Sizing the chunk matters too: too-large chunks (≥3400c) both slow every call and inflate the blast radius of one failure. Non-streaming also bounds the answer length — set `max_tokens` generously so the tail is not silently cut.

**Throughput comes from PARALLELISM, not from chunk size — the wall-clock is dominated by per-call latency, not by chunk length.** Smaller chunks + many workers beat big serial chunks (measured: serial ~2600c ≈ 127 s/chunk vs 8 workers ~1400c ≈ 5.6 s/chunk, same quality). Probe the endpoint's concurrency with N throwaway chunks before fixing a worker count (this gateway handled 8-10); do not shrink chunks below whole-paragraph size, and keep the model stable while tuning workers.

**A model can also fail in a mode that is neither a refusal nor a quota error — it ANSWERS instead of translating ("writes fiction back"). That is fixed by changing the ENDPOINT/provider, not the prompt.** The chunk splitter must likewise use the delimiter the raw actually has (single `\n`, not `\n\n`), or one oversize block hits `504 Gateway Timeout` forever. The four-way failure taxonomy, endpoint-swap rules, and splitter/`__pycache__` gotchas are in `references/mtl-endpoint-and-model-selection.md`.

## Assets from the raw

The raw PDF usually already carries the cover and the illustrations ("Poster dan ilustrasi nya udah ada di pdf nya"). Extract them from the PDF rather than hunting the web — `pdfimages -all -p <file> <out>/img` (poppler) dumps every embedded image at full resolution. `pdfimages -list` first gives page / width / height / colour / size per image, which is exactly the map you need to identify the cover (page 1-2, portrait 2:3) versus body illustrations (mid-document, some full-bleed landscape). Illustrations are supported in the DB/site — do not drop them. Keep the same asset-column convention as the rest of the archive (relative path + a separate asli/raw copy).

Distinguish cover from illustration **by geometry, not by guessing**: a portrait ~1443×2048 at page 1-2 is the cover poster; landscape (width > height, e.g. 2048×1453) is a two-page spread. Colour statistics also help separate a colour cover from black-and-white text illustrations (identical R=G=B channel means greyscale). For an **EPUB** the cover is *declared*, so read it instead of guessing: follow `cover.xhtml` / `<item properties="cover-image">` in the OPF and take the image it references — file numbering (`01.webp`) is spine order, not a cover signal. Note plainly that a text-only vision model cannot *see* the artwork — report the measured geometry and let the user eyeball the folder, rather than asserting what the picture shows.

To place illustrations against chapters, do **not** re-read the PDF per page (it times out on a 145-page file at 290 s). Read the start-page of each chapter once into a dict, or infer position from the already-known chapter char proportions, then map image page → chapter and store a `caption` per image ("Cover Novel", "Ilustrasi Episode 1: …").

## Proving a work's TOTAL volume count ("is this really only 1 volume?")

When the user hands over a volume and asks whether that is all there is, **do not answer from the file you were given** — a `Volume 1` filename proves nothing. Confirm from sources that would list the rest if it existed, and require agreement:

- **RanobeDB is the cheapest first check** and it states the count numerically: `GET https://ranobedb.org/api/v0/series/<id>` carries `volumes.count`, `c_num_books`, and a `books[]` array. One volume in `books[]` with `volumes.count: 1` is a real answer.
- **The retailer's series page is the second witness.** BookWalker's series list prints `1 ～1件目/全1件` ("1 of 1") — machine-readable, and it counts *products*, so it also catches a later reissue/omnibus. Note that a series page can show **2 book ids for one volume** (a normal edition plus a `冊版`/omnibus); that is still one work, not two volumes.
- **State the count with its evidence** ("1 volume — RanobeDB `volumes.count: 1`, BookWalker `全1件`") rather than asserting it, and say plainly that "only 1 volume" is then a *fact about the work*, not a limitation of the raw.
- Cross-check the *shape* too: a one-volume work is often a **web-manga/web-novel adaptation** (the RanobeDB `staff` list shows a separate `role_type: staff` / `Original work` credit distinct from author and artist) — worth reporting, because it tells the user the web original may run longer than the single print book.

## Mapping a multi-volume EPUB set to the archive's chapter numbers

<!-- verified: 8 EPUB volumes covering Parts 1-229 against an archive that held only Parts 1-102 -->
When the raw is a set of per-volume EPUBs and the archive already holds *part* of the work, the whole job is deciding which parts are genuinely new. Two steps, both cheap, both necessary:

1. **Build the Part→volume map from the EPUBs themselves, not from filenames or the vendor's blurbs.** Each chapter document in these EPUBs opens with a scene marker like `◇◇◇ Part 121 ◇◇◇`; regex it out of every XHTML in the volume and you get exact `Part` ranges per volume (`v5: Part 119-144`, `v6: 145-171`, …). Report the ranges in a table; this is also how you spot that the *last* volume's max Part is the whole set's max.
2. **Subtract the archive's coverage from that map to get the honest gap.** One EPUB chapter can equal several archive chapters (here 1 chapter = 3 parts = 3 archive chapters), so map in *Part* units, never chapter units — and re-derive the archive's max Part from its own chapter text rather than assuming its chapter count equals its part count.

**Do NOT assume the highest volume you hold is the last one.** After the set's Part ranges are known, check whether a `V9+` exists at the source before declaring the work complete — the source's download page is the place to look.

## JP→ID is a *different* pipeline — do not reuse the EN→ID script

<!-- verified: a JP→ID novel went through a separate pipeline because the EN script's prompt, cutters and input keys are wrong for Japanese -->
When the raw is Japanese (a web novel off Kakuyomu/Syosetu, or a JP scan), the EN→ID pipeline is **not** reusable — it will silently produce garbage. Three things differ and each must be its own constant:

- **Prompt**: the system prompt must say "translate Japanese into Indonesian (Bahasa Indonesia)", not EN→ID. A prompt that merely omits the source language lets the model answer in the wrong language entirely (see the CJK-leak pitfall below).
- **Sentence cutters**: split on Japanese terminal punctuation `。！？」` (and `…`), not on `[.!?"]`. Cutting JP text on ASCII periods tears the text.
- **Input keys**: the JP raw carries `episode`/`teks` (or `judul`+`teks`), not `bab`/`en`. Re-key rather than renaming the source file.

Write `mtl-pipeline-jp.py` next to the EN script; keep the two separate. A JP→ID run is ~230% of the source char count (Indonesian runs long) — a chapter at ~100% of its JP length means it was truncated, not translated. Full recipe, prompt shape and verification: `references/jp-to-id-translation.md`.

**MTL that is provably perfect goes straight to the main DB**

This user carved out exactly one exception to the stage-first rule: **a completed, verified, un-truncated MTL chapter set may be loaded straight into the main DB without asking.** Verbatim: **"Yg hasil MTL kalo udah sempurna gada yg kepotong bagus hasilnya, langsung ke db utama aja ini khusus MTL ya"**. The exception is *conditional* — it applies ONLY when all four sides verified clean (no truncation, no missing chunk, plausible ratio, chapter count matches) AND the CJK/error-string sweep is 0. Anything short of that still goes to staging and waits. Harvested content (rsync'd DBs from another host) is a *different* rule: it always sits in a quarantine dir and waits for explicit approval — do not confuse the two.

**"Khusus MTL" means OUR OWN MTL — a third-party translation, even a perfect one, still waits for the user's approval.** The carve-out's own wording scopes it ("khusus MTL ya"), and the parallel rule for externally-sourced content is the quarantine one. A raw that arrived already translated, a harvester's set, or a PDF by another translation group is someone else's asset: stage it, verify it, report it, and load only on the user's word. Do not read "verified clean" alone as the licence to write to the main DB. **A MIXED set is the case this bites hardest:** when a novel's missing volumes come from a third-party PDF/aggregator and the rest is our own MTL, the assembled novel carries both provenances — so the set as a whole is a third-party asset and does NOT ride the carve-out. Report per-volume which is ours and which is theirs, and let the user approve the load.

Also: **keep a running log of every MTL project** the user can read (`CATATAN/DAFTAR-PROJECT-MTL.md`) — id, source, language pair, chapter count, status. The user asked for it directly ("catat juga judul"nya hasil MTL biar kapan-kapan tau project MTL kita sendiri apa aja"), so create it once and append per novel.

## A third-party raw can carry a NON-COMMERCIAL licence — record it and never sell that work

<!-- verified: the raw's own front matter forbade commercialisation, and the user confirmed the
novel is for the personal shelf only -->
A fan-translated raw's front matter (an `Attentions` / `Warning` / copyright page) can state the
work may not be sold or commercialised without the rights holder's permission. **Read that page
and record it** as part of the import, in `CATATAN/ATURAN-LISENSI-<slug>.md` (id, which volumes,
the licence text's gist, and what is allowed). Then hold the rule: that work may sit on the
personal shelf, but it must **never** be listed for sale, uploaded to a paid platform
(Trakteer etc.), or promoted as a purchasable item — regardless of the general
"earn from the archive if anyone wants to buy" direction, which does not override a work's own
licence. Say this plainly to the user when it applies rather than leaving it implicit, and do not
re-surface it as a question once they have answered.

## Running the translate loop on ANOTHER host (reverse SSH tunnel)

<!-- verified: a 404-chapter JP→ID novel was translated on a rented VPS while the model endpoint stayed on the phone -->
The model endpoint is local to the phone; a long MTL run competes with the web server, the tunnel and Telegram for that phone's CPU. Moving the *loop* to a beefier host while the *model* stays put is worth it — but the host cannot dial in, because the phone runs no SSH server (`sshd` absent, port 22 closed). Build the tunnel **outward from the phone** instead:

```bash
# on the phone: offer the local endpoint to the remote host, on the remote's loopback only
ssh -N -R 20128:localhost:20128 -p <port> -i <key> \
    -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes -o BatchMode=yes root@<host>
```

- `-R` binds on the **remote's** `127.0.0.1` by default, which is what you want: the endpoint is reachable from the worker host and **not published to the internet**. Never widen it to `0.0.0.0`/`GatewayPorts` just to "make it work".
- `ExitOnForwardFailure=yes` makes a failed bind fail the whole SSH call, so you do not get a silently tunnel-less connection.
- **Prove the tunnel before trusting it, from the remote side:** `ssh <host> "curl -s -m 20 http://localhost:20128/v1/models"` — a model list means the path works. A "my own curl says Missing API key" result is your test being wrong, not the tunnel.
- The remote worker needs the key file too — copy it, `chmod 600`, and point the script's key path at the copy (`sed -i 's|^BASE = .*|BASE = "<remote workdir>"|'` plus the key path). Check how the script resolves it before copying; it may look in two places.
- **Match the script's expected input directory, do not rename files to suit yourself.** The pipeline reads `mtl-raw/<slug>.json`; dropping the file next to the script instead produces a clean-looking `berkas RAW tidak ada` exit and no work. Read the path out of the script's own error message and place the file there.
- **Leave a keeper loop running** (`while true; do bash jaga-terowongan.sh; sleep 180; done`) that re-establishes the tunnel and restarts the worker if it stopped before the expected chapter count. Per-chunk saving means a restart resumes rather than restarts. Without it, one dropped tunnel silently ends the run overnight.
- **Throughput is not guaranteed to improve, and the honest number is whatever you measure over many chunks.** Early chunks ran 22-44 s here against 155-210 s on the phone (a real 5-7× win), then slowed to 650-1700 s on a loaded free-tier provider. The variance comes from the upstream provider, not the host — the host's own CPU/RAM will look idle throughout. Report a range and a caveat rather than a single optimistic sample, and never quote one fast chunk as the expected rate.

## Cleaning already-archived chapter text is its OWN pass, and it is one-novel-at-a-time

<!-- verified: the user asked for one novel to be cleaned rather than a bulk pass, and a bulk run had
produced visibly worse output days earlier -->
When the work is *repairing* the text of chapters already in the archive (layout-wrapped lines, site
furniture, titles carrying the novel's name, volumes stuck inside the title), that is a different job
from translation or verification. Two standing rules from the user:

- **One novel at a time. Never bulk.** Verbatim: *"kita benerin satu" kalo di bulk bakalan ga sempurna…
  mending lama gpp asal bagus*. Fix one novel, prove it from the DB, report, and wait — do not sweep
  the other 18 because the script can. The user restated it as *"citem satu-satu aja sampe beres dan
  bener"* — a batch of one until it is genuinely finished.
- **Repairing content is allowed; reshaping a finished feature is not.** Clean the text, and only add
  schema (e.g. a `volume` column) when the user asked for it that turn.

### Chapter-title and numbering rule (standing, applies to every novel)

When the source did not preserve real chapter names (the title column is `'0'`, empty, or symbols),
issue an honest generated title rather than leaving the placeholder or inventing a plot name:
**story chapter → `Bab N` counted PER VOLUME (restarting at `Bab 1` each volume); illustration page →
`Volume N — Ilustrasi`.** Keep this in `CATATAN/ATURAN-JUDUL-BAB.md` in the project and apply it
uniformly, because the user's reason is consistency across novels plus honest numbering
(*"kasih Bab brp + Volume Brp Yg Jujur, biar yg baca ga binggung"*) — not the name itself.

### Two non-negotiable gates on this pass

- **Paragraph-count assertion** (`paragraf BERUBAH: 0`): a repair pass that silently changes paragraph
  count has destroyed structure.
- **Never let the cleaned text go blank when the input was not.** A strip-a-title rule empties the row
  when the title *is* the row's only content (illustration pages). Restore the input in that case — it
  is the cheap universal net that also catches any future over-broad rule.

### A green tool is not evidence — read the text yourself

**Per-chapter manual read — one chapter at a time, tool only FINDS, eyes JUDGE**:
`references/per-chapter-manual-read.md` (the user's *"cek dulu secara manual pakai mata lu"* order; six
checks, repair-order, quote-corruption signature, copy-first, and the per-source space-after-hyphen test).
**Repairing a novel ALREADY on the shelf**: `references/audit-and-repair-loaded-novel.md` (web renders one
`<p>` per `\n` → a hard-wrap shows as chopped lines; scope-sweep, `\n`=paragraph repair, FTS rebuild,
rsync+md5 to push the live DB).

<!-- verified: `--uji` reported all nets green while 29 of 32 chapters of one novel still carried the
site footer, because `rapikan_teks` never called the furniture cleaner at all -->
Standing rule from the user, verbatim: **"lu jangan ngandelin alat bro, lu harus ngecek sendiri juga"**.
The nets cover *structure* (paragraph count, separator, length); they do not know that a nav bar is
still sitting in the prose. Before declaring a novel done:

- **Read the head AND tail of the cleaned text of several scattered chapters** (not just #1), as
  `repr()`, and look for the furniture markers with your own eyes.
- **A cleaner function that exists but is never CALLED produces perfect nets.** The nets measure
 "changed vs unchanged", and unchanged input passes them. When text still looks wrong after a green
 run, `grep` for the function's *call site* in `rapikan_teks` before touching any regex — a missing
 call is a different bug from a wrong regex.
 - **Average chars-per-paragraph is the net that catches FUSED paragraphs, and it fires when the total
 char count looks fine.** Print `total_aksara / jumlah_paragraf` per part: an average in the hundreds
 of chars means paragraphs are still welded into page-sized blocks, while normal prose lands near
 60-120. A plausible char total with a huge per-paragraph average means a separator rule trusted
 `\n\n` where `\n\n` only marks page breaks — see `references/pdf-raw-to-chapters.md` §3c1b.
- **Site furniture has THREE positions, not two.** A nav block can sit in the MIDDLE of the chapter
  (after the story, before `Catatan dan Referensi`). Verified: one novel's nav bar sat at line 594 of
  an ~800-line chapter. Scan the whole text, never just the head and tail.
- **`isi BERKURANG` is usually SPACES AND GARBAGE, not lost story.** Prove it per-span with
  `difflib.SequenceMatcher` and read every `delete`/`replace` span: `' '` and `'\n'` are safe (the
  line-join collapsing double spaces, plus dropped furniture); story sentences are danger. Hundreds of
  characters per chapter is NORMAL for a wrapped-layout source once the spans are proven whitespace.
  Do not roll back a backup over an unverified number, and do not claim "0 loss" when it is not 0.

**A title-detector that fires on body prose is the real hazard in this pass, not a missed title.**
Ordinary words (`kata`, `penutup`, `volume`) must never be match keywords, and substring rules need a
length gate — see the verified content-loss case in the reference.

**More title-matcher mechanisms, all in the reference:** a byline/date line can hide *between* the stray
title and the real one (drop AND skip it); a stray-title matcher keys on *all name words + short line + a
unit marker*, never `startswith(<novel name>)`; strip leftover connector words (`ga`,`no`,`wo`) before
the unit test; ORDER removals so the greedy `^[a-z0-9]*` junk-dropper runs **after** the specific
`volume N`/`jilid N` removal (reversed it eats the word `volume`); if harvested titles are still
misshapen, **stop, do not write**; and `--uji`'s change counts are to *diff*, not a damage report.

Recipe, the one-regex re-join, the false "truncated tail" cause, and the two new failure classes
(over-broad matcher, volume overwrite): `references/cleaning-scraped-chapter-text.md` — which also
carries the **batch-scraped-source sort**: a column named like a number (`bagian`) can hold free text,
so build the `(jilid, jenis, sub)` sort key from the title with `Prolog`→-10 · `SS`→5000 ·
`Kata Penutup`→9980 · `Epilog`→9990 (`Bab N`→N) — epilog LAST — and never join a story sentence onto a
type-only line (`Prolog`/`Epilog`) the way you would onto a named `Bab 4 —` head; plus why a UNIFORM
per-chapter `isi BERKURANG` is the header/footer strip working (strip furniture in staging, judge by the
distribution, never widen the net).

## Assembling a novel whose volumes come from TWO different sources

<!-- verified: a 9-volume novel sat in the warehouse as an ARC translation, while OUR MTL covered only the middle volumes (5-8); the two had to be merged into one shelf entry -->
A novel's finished set can be split across sources: some volumes already translated by a third party
and parked in the warehouse, the rest our own MTL (often because the third party's uploads for those
volumes were mislabeled or missing). Merging them is a distinct step from either pipeline:

- **Compare the two versions per volume before picking, and prefer whichever is more COMPLETE, not
  whichever is "ours".** Verified: the warehouse's V7 held 230k chars against our MTL's 292k, and its V5
  was **missing a whole chapter** (`Chapter 3` absent) that our MTL had. A lower chapter *count* in one
  source is not automatically the loser — and a higher count is not automatically the winner either;
  check which chapters exist and which are longer, per volume.
- **A chapter-count difference between the two sources is usually the SOURCE's own gap, not your bug.**
  Do not "reconcile" it by renumbering — find which chapter id is absent, report it, and take the
  version that has it.
- **Splice at the VOLUME level, then renumber `urutan` globally across the whole novel.** The `volume`
  column restarts per volume but `urutan` must run 1..N over the assembled set so the site's reader
  orders correctly.
- **A warehouse row is not a chapter — group its parts by NUMBER before counting or splicing.** The
  source that produced the warehouse dump can split one long chapter into several `Bagian N` rows;
  verified a 102-row dump collapsed to 92 real chapters. Group by the chapter NUMBER (never the title:
  parts share a title, and two *different* chapters can share a truncated one like `Bab 3 —`), and
  concatenate the parts in row order. The real title's tail often sits as the **first line of the
  row's own `teks`** (`judul: 'Bab 3 —'` + `teks: 'Penyelidikan Teman Masa Kecil\n…'`) — harvest it and
  delete the consumed line, or the title stays glued to the story's opening. Full recipe:
  `references/warehouse-volume-assembly.md`.
- **The warehouse `volume` column is a HINT, not a fact — confirm it against the chapter's own content
  and the other source.** Verified: a row labeled `volume 3` held the **Epilog of volume 5** (an epilog
  filed mid-story is the tell), while the real volume 3 was in the PDF set. Report the correction
  plainly (`"Jilid 3 di gudang itu sebenarnya Epilog Jilid 5"`) rather than silently re-filing it.
- **Put the volume's trailing material (Ekstra / Selingan / Interlude / Penutup / Cerita Tambahan)
  LAST, after the numbered chapters** — that is the printed book's order. The warehouse's own row order
  is not trustworthy for this; after assembling, sort the volume's rows by (numbered chapters in order,
  then the extras).
- **Empty (0-char) illustration rows are correct content** and need no text — keep them as
  `Volume N — Ilustrasi` (see `references/cleaning-scraped-chapter-text.md` § empty chapters).
- **Title the volume's chapters in the archive's established style** (`Chapter N — <judul>` when a real
  name exists, `Volume N — Ilustrasi` for image pages), and when the third-party text carried its own
  English-ish chapter names, translate the names — do not leave them in English mid-shelf.

**Do NOT ask the model to INVENT a chapter title when the raw genuinely has none.**
<!-- verified: Kakuyomu raws carry no episode titles; asking the model for "a short Indonesian title for
this chapter" returned the chapter's own first line of prose, a literal 'Judul bab: …' prefix, an
echoed instruction ('Isi bab novel ini. Tulis JUDUL…'), or a leading '#' — a mixed bag needing more
cleaning than the titles were worth -->
A web raw with `episode`/`teks` but no title field means the titles were never published. Use the
archive's honest generated form (`Chapter N` / `Bab N` per volume) rather than prompting a model for a
name — a generated title never lies about being from the source, while an invented one reads as
authoritative and is not. Only reuse REAL names when the source's own ToC/heading carries them.

## Pitfalls

- **A furniture/watermark sweep's end state is "read the residue", not "the counter is 0".** A strip pass over a third-party raw leaves a small non-zero remainder whose *shape* decides whether it is a miss. Verified: 432 per-page domain stamps reduced to 28, and all 28 were the aggregator's illustration filenames plus intro-page marks — a rule I had not written but which a "counter must be 0" gate would have sent me back to fix. Count before/after, then `repr()` the survivors and judge them. Corollary: **the defect count is not uniform across a set** (one volume of four carried 10% of the others' stamps) — one clean volume is a reason to check the next one, not to skip it.
- **Test a text-cleaner FUNCTION on 4-6 tiny probes before running it on a novel.** The failure mode is
  a cleaner that looks plausible in the first few lines and is wrong three paragraphs in, so
  inspecting the head of a chapter's output hides it. Verified: seven consecutive failed fix attempts on
  one cleaner, every one because only the first ~150 chars were read; running the function on small
  probe strings with `repr()` found the real bug (a lookbehind anchored to the wrong neighbour) in one
  step. Before concluding a code change had no effect, also `rm -rf <pkg>/__pycache__` — a stale `.pyc`
  made two real fixes look ineffective. Probe step-by-step (`repr()` after each `re.sub`), and verify
  the write by reading the DB back rather than trusting the script's own success line.
- **A cleaner feature that reports ZERO hits on input you can see it should match is usually an
  un-passed argument, not a broken rule.** Verified: the stray-title stripper never ran on any novel
  because the caller invoked the helper without its `judul_bab`/`nama_novel` arguments (they defaulted
  to `""`), so it reported `teks dirapikan: 0` while stray titles sat there for months. `grep` the
  definition AND every call site; optional-parameter signatures hide this. See the reference.
- **A cleaner that deletes too much is worse than one that deletes too little — gate every strip rule on
  position and length.** Verified: a keyword-based stray-title rule removed a chapter's real closing
  paragraph (~350 chars) because the paragraph contained glossary-common words (`volume`, `kata
  penutup`). Body prose is long and mid-document; a stray title is short and leading. Never key a
  destructive rule on ordinary words, and never match a substring without a length gate.
- **Never let a strip rule overwrite a value the DB already holds correctly.** Verified: a
  forward-inherited volume guess rewrote a novel's correctly-stored `volume = 4` down to `3` because no
  title carried the "Volume 4" marker. Prefer the stored column; only derive when it is NULL.
- **When two normalisation rules collide, protect the intermediate output instead of reordering the
  rules.** Rule order is fragile; a rule whose output can no longer be matched by the losing rule is
  stable. See the date-dash vs word-reduplication case in
  `references/cleaning-scraped-chapter-text.md`.
- **Never declare the worker dead from a `grep` of `ps` output alone — verify with `ps -p <pid>` and the file mtime.** A pattern-grep can miss the process (the command line is truncated, or the match was case/space-different) and the wrong conclusion cost several minutes of rework twice in one session. The reliable triple is: `ps -p <PID> -o pid,etime,stat,cmd`, the output file's mtime (`stat -c %y`), and the per-chunk count. A live process with a stale output file is *hung*, not *dead* — different fix.
- **Killing the worker is not enough when a SUPERVISOR loop launched it — the loop respawns it and the old run appears to come back from the dead.** A batch driver like `for v in …; do python3 mtl.py $v; done` keeps its own PID and restarts the worker on the next iteration, so `pkill -f '<worker>.py'` reports success while the driver immediately relaunches it; minutes later a *new* PID is running the OLD config and the second run collides with the new one on the same output file. **After stopping a run, re-check `pgrep -af <every script in the chain>` — the driver script AND the worker — and kill the driver first** (`kill -9 <driver-pid> <worker-pid>`), then confirm with a *bracketed* pattern (`pgrep -f '[m]tl.py'`) so the check does not match its own command line. Verified: `pkill` on the worker left `mtl-semua.sh` alive, which relaunched Vol 2 at 8 workers while the new 4-worker run was already writing the same JSON.
- **A long `scp` of a big asset dir will time out an interactive tool call — run it as a background loop, and DO NOT glob a shared parent directory.** Verified: a `scp -r` batch that collected the new illustration folders matched every `4*` folder in the shared `gambar/` dir, i.e. other novels' illustrations too. Copy by an exact filename list built from the DB (`SELECT id FROM bab … WHERE ada_gambar=1`), never by a wildcard over a directory shared with other novels.
- **A `pgrep -f '<pattern>'` run over SSH counts its own shell, so "process still alive" is usually a false positive.** The remote command string contains the pattern you are searching for, so the shell running the check matches itself. Verified: a `pkill` that had in fact succeeded still reported `1` survivor, and the follow-up `pgrep -af` printed the checking command itself as the only hit. Bracket the pattern (`pgrep -f '[m]tl-pipeline-jp.py'`) so it cannot match its own command line, or resolve the PID first and assert on `ps -p <pid>` — and re-read the full `pgrep -af` line before concluding anything is running. This is the same self-match trap as a `grep -c` over a pattern it also prints.
- **Do not kill and restart a translation worker just because the log looks quiet.** The log is buffered; the JSON output file is the truth. Check the file first.
- **A model can silently answer in the WRONG language, or embed an error message mid-text, and the chunk count still looks perfect.** Two verified failures from one JP→ID run: (a) several chapters came back in **Chinese** (whole chapters of hanzi) and others carried untranslated kanji in character names — because the prompt did not force the target language; (b) the model put its own refusal string (`"… high risk", "I cannot…"`, translator promos) **into the middle of the text**, so the chapter *looked* full-length and clean. Both are invisible to a char count. **Verify with a script, not by eye:** regex the output for CJK (`[\u4e00-\u9fff]` and kana `[\u3040-\u30ff]`) and for a refusal substrings list, and treat any hit as a failed chunk to re-translate. A prompt that forces the target language ("you must answer in Bahasa Indonesia") plus a reject-and-retry loop fixes the wrong-language case. **The Chinese leakage is intermittent, not uniform — in one run only 2 of 25 chunks came back in Chinese while the other 23 were clean Indonesian**, and every net passed on the bad chunk because its length was right. Sweep every chunk, and reject on a *density* test (`cn > 20 and cn > len(hasil)*0.10`), never on a single CJK character, or a legitimately-quoted CJK term triggers a false rejection.

  **Put ALL THREE reject conditions behind one validity gate inside the translate function, and fall through to a retry — do not return whatever came back.** The filter message, the wrong-language output and the truncation are three faces of the same problem (the call returned, but not a usable translation); fixing one and shipping the others is the default failure. Verified shape:
  ```python
  def _sah(hasil, sumber):
      h = hasil.lower()
      if "high risk" in h or "request was rejected" in h: return False   # (1) filter message
      cn = len(re.findall(r"[\u4e00-\u9fff]", hasil))
      if cn > 20 and cn > len(hasil) * 0.10:               return False   # (2) wrong language
      if len(hasil) < len(sumber) * 0.55:                  return False   # (3) truncated
      return True
  # in the retry loop: if h and _sah(h, teks): return h    # else retry
  ```
  An `if h: return h` guard with no validity test stores the Chinese string or the filter message as if it were a translation. Test the gate on four tiny probes (filter string, Chinese chunk, short result, normal result) before trusting it.
- **A "high risk / cannot comply" refusal is usually induced by YOUR OWN prompt, not the API or the raw.** Verified: after ruling out an API fault and a bad raw, the trigger was the prompt itself containing example offensive/romantic words. Reworking the prompt to be neutral (no example words) made the same chunk pass. Before blaming the endpoint, strip example words from the prompt and retry; keep one fallback model for the cases the neutral prompt still rejects.
- **The endpoint can return its OWN filter message AS the translated text, and it is invisible to every net that looks for English or CJK.** Verified on a kiss scene: the model returned the literal string `The request was rejected because it was considered high risk` for two chunks — and in a third it was **concatenated onto a torn chunk** (`…saat lidahku bergesekan dengan lidahnya, tang` + the message), so the length check and the "chunk opens on lowercase" check both read it as ordinary truncation, and `en_panjang`/ratio looked plausible. Three rules:
  - **Add the filter's literal message to the refusal/reject substring list** and scan for it over the whole joined text (`"high risk"`, `"request was rejected"`, `"cannot comply"`, `"content policy"`, `"I cannot"`) alongside the CJK sweep. A message that arrives *inside* a chunk is the one shape the "did the chunk come back empty/short" guard does not catch.
  - **A short result is not the only symptom — a NORMAL-length result can carry the message glued to half a sentence.** So also check every chunk's id for the message string, not just for emptiness, and re-derive `selesai` from that.
  - **TRY A SHORT NEUTRAL PROMPT BEFORE HAND-TRANSLATING — it is the cheapest fix and it works.** The pipeline's own prompt is long (glossary block, "WAJIB PUKAI NAMA INI PERSIS", elaborate instructions) and its *length and wording* are themselves a rejection trigger. Verified: a chunk the full pipeline prompt refused (`high risk`) translated cleanly on the first try with a one-line user message containing nothing but `"Terjemahkan ke bahasa Indonesia:\n\n" + teks` — same model, same endpoint, same chunk. So the refusal is often about the prompt, not the content. Order of fixes for a refused chunk: **(1) retry with the bare short prompt, (2) if the refusal is content-class-wide across many chunks, switch to a model that does not structurally refuse it (see \"Model endpoint\"), (3) only if that also refuses, hand-translate.** A repair script that re-sends refused chunks with the short prompt (a chunk-by-chunk filler over the stored `en`, with the same validity gate) recovers refused chunks in bulk without any hand-typing.
  - **Only when the short prompt ALSO refuses is the content itself the trigger — then hand-translate.** Verified on a genuinely explicit scene: hand-write the ID in the ARC register (`「」` dialogue, consistent names), splice it in, rebuild `terjemah`/`panjang_id` from `potongan`. Do not delete the scene, do not leave it in English, and do not call the novel broken — translate the chunk and re-run the sweep. Keep every manual splice in its own file (`staging/<slug>-manual.json`) so a re-run of the repair tool re-applies it rather than losing it.
- **Kanji/kana leaking into *names* survives a length check.** A chapter can be the right length and still contain `枫`/`蓮` where a name should be. The CJK regex sweep above is the only reliable catch — run it over every chapter before declaring done.
- **A chunk that failed must not be saved, and must not let the chapter claim "done".** Two coupled defects, both verified: the loop appended an empty result (`0c`) to the chunk list and kept going, and the completion check only compared `len(done) == len(pot)` — so a chapter missing its whole first chunk reported `selesai=True` and the story silently started mid-scene. Guard both ends: skip-and-retry when the answer is empty/too short instead of appending it, and compute `selesai` as *all chunks present AND every chunk ≥ a sane minimum length*. A finished-looking marker with a hole behind it is the worst state, because it stops the resume that would have fixed it.
- **NEVER `break` out of the chunk loop on a failed chunk — and always SAVE THE SOURCE TEXT with each chunk.** Verified: the loop did `if h.startswith("__ERR__"): break`, so one refusal silently abandoned *every remaining chunk of that chapter* (one chapter showed 6 empty chunks where only the first failure was real), and because each saved chunk stored only `{"i", "id"}` a later repair pass had **no source text to retry from** — the chapter was permanently unrepairable by tooling. `continue`, not `break`: append the chunk with an empty `id` **plus its `en`** and move on. The `en` field is what makes the chunk repairable later; without it a refusal costs the whole tail of the chapter.
- **Repair a refused chunk by re-deriving the split from the raw, never by trusting the stored chunk list — but verify the two splits ALIGN before writing.** The raw still holds the full chapter text, so re-run the pipeline's own `potong()` on it to rebuild the chunk list: identical code means an identical split, and each stored chunk can be matched back by its `en` text. Print both counts and per-chunk lengths side by side first (`potongan 18→18`, lengths paired) — if the counts differ, skip that chapter entirely instead of writing a misaligned list.
- **A repair tool must never REBUILD a list that already holds good data — only fill blanks in it.** Verified the hard way: a first-draft repair script replaced each chapter's `potongan` array with a freshly matched one; because the stored chunks carried no `en` to match on, nothing matched, and the run **wiped 167 finished translations in one pass**. The correct shape is to mutate in place — `for k, rec in enumerate(lama): if not rec.get("id"): rec["id"] = baru[k]` — and leave every already-filled field untouched. Write the same rule into any tool that touches a finished `mtl/<slug>-potongan.json`.
- **Never patch a `mtl/<slug>-potongan.json` while the translate process is running against that same slug.** Verified twice in one session: manual splices of refused chunks were silently overwritten by the worker's next periodic save, and the same 6 chunks reappeared as empty. The pipeline rewrites the whole file on every chunk (`simpan(slug, d)`), so any edit made between saves is lost. Stop the worker, or wait for a `=== N/M bab selesai ===` line, then patch; and back the file up (`cp` to `*-potongan.bak.json`) before patching so a bad edit is one `cp` from undone.
- **Hand-translate the refused chunk into the SAME register the rest of the archive uses, and run the register normaliser over the manual splice too.** A hand-typed chunk joins model output inside one chapter, so it is the most likely place for `saya/kamu` to leak into an `aku/kamu` novel. Keep manual translations in their own file (`staging/<slug>-manual.json`, keyed `"<babNN>_<chunkIndex>"`) so a re-run of the repair tool re-applies them rather than losing them, and match the key against the potongan file's OWN key format — a mismatch (`bab07_16` vs `v5_7_16`) silently reports "manual: 0 applied" while looking like it worked.
- **Do not give a refusal-prone model only 2-3 attempts per chunk.** The model here rejected the same chunk on 3 consecutive tries and then succeeded on the 4th — with `coba=3` that chunk was lost outright. Use ~6 attempts and rotate the fallback model list on exhaustion, so a single stubborn chunk cannot cost you a scene.
- **Never load into the main DB on the first pass.** Staging first is a standing rule, not a suggestion; the whole reason is that a bad import of 1 novel is cheap to fix and a bad import of 5 is not.
- **A "continue/resume" run is a destructive operation.** Back up the per-chunk file first, and re-run the char-ratio check afterwards — see the resume section above. Do not start `--lanjut` on a file whose last state you have not measured.
- **A gateway's free-tier model can be withdrawn between runs; verify the model with one probe before a long run.** A model that answered yesterday returns `503 Service Unavailable` on every chunk today, and the pipeline reports it as generic failure. Probe the endpoint with a single curl against the candidate model, and keep an ordered fallback list in the script (`MODEL_CADANGAN`) rather than a single hardcoded name.
- **A naive chapter splitter double-counts** by matching both the table-of-contents and the body headings. Reconcile the found count against the printed contents before translating.
- **Do not translate with a streamed request and no timeout.** See the endpoint section: streaming is the hang source; count output files for progress.
- **A web-novel raw needs no permission and no scraping rigour beyond the site's own published JSON; grab it yourself instead of asking the user for it.** When the work is on Kakuyomu/Syosetu the text is the author's own free upload — telling the user "kirim RAW-nya" when you could fetch it is a wasted round-trip. See `references/web-novel-raw-sources.md`.
- **Do not harvest a translation blog just because it already has the book — source the raw yourself.** Standing project rule, the whole reason the MTL workstream exists: *"biar ga nyolong terus"*. A blogspot/translation-group copy is someone else's translation (third-party → quarantine), and reaching for it whenever a title is hard is the habit the user is telling you to drop. When a title is not on the official platforms, say which raw-source routes exist (`references/raw-source-map.md`, `references/web-novel-raw-sources.md` §2f) rather than falling back to a blog.
- **When the user wants to choose the work themselves, hand over the SOURCE URLs, not a guessed title.** Verbatim ask: *"kirim url web raw nya biar gua pilih"*. Give the browsable entry points (site home + ranking/search page, e.g. `yomou.syosetu.com/rank/list/type/total_total/`, `kakuyomu.jp/rankings/all/weekly`) so they can pick, then fetch the one they name — do not pre-pick a novel for them off a queue when they asked for the source list.
- **A source-title search that returns only *other* works is a signal, not a near-miss.** When several queries for the JP title land on unrelated series that merely share a word (e.g. a different `…天使…` or `…Kudan ni tsuite`), stop guessing at word order and switch sources/site — that pattern means the work is a web novel or under a different platform, not that your query needs one more rewrite. A partial-keyword DB hit (a novel matching only a common word like *tenshi*) is **not** a match: verify the whole title, say plainly it is a different work, and never report it as "found".
- **Before calling a source's coverage incomplete, check the SOURCE's own list — a batch source can start mid-series.** A scraper source (a blog label, a translation group) may have only ever published from volume 4 onward. Read the source's own index (`curl '<label-url>?max-results=150'`, collect the post titles) and compare against the volumes you hold before writing "bab hilang" or "kepotong". Verified: one novel's source carries only Jilid 4-12, so the missing Jilid 1-3 is **not yet translated by that source** — report it as that, and do not title the shelf row as if the set were "Jilid 4-12" or imply the gap is a defect. The user needs to know *which* volumes are genuinely absent from the source so they can decide whether to wait or source them elsewhere.
- **Never fabricate missing metadata.** If a field (an official ATL/English title, a publisher) genuinely cannot be found after honest search, say so and leave it — do not invent one. The user's rule: **"ragu = buang aja"**.
- **Derive a chapter's NAME from the source's own table of contents before inventing one.** A PDF/EPUB whose ToC lists the chapters lets you skip the `Bab N` fallback entirely and puts the *real* name in the title column. Read the ToC deliberately as a data source (each entry is `<name> <separator> <page>` — split on the separator), use that name set to match body headings, and only fall back to the honest generated `Bab N` when the ToC is absent or page-number-only. This also settles which heading lines are labels to drop from the body versus real prose to keep.
- **Do not re-join a heading onto the body — a chapter's title belongs in the title column, and its body should open on the story.** A short leading line that a join rule merges into the first sentence destroys the opening (verified: a 2-line heading became `Epilog Pada suatu hari libur …`). Conversely a strip-by-fixed-line-count rule cuts a 2-line heading in half and leaves a bare fragment. Gate stripping on the ToC name set plus "this line is a label, not prose", then re-read the first 60 chars of every chapter — and keep the translation's own scene markers (a bare `1`, `[Sudut Pandang X]`) which are content, not headings.
- **A volume split is NOT a chapter range, and the web's own volume-release SS posts will mislead you.** The user wants the chapter list folded into labelled groups, and the tempting shortcut is "N chapters per volume" (what other sites do with `1-30, 31-60`). Do not use it. Verified on a 404-chapter web novel: assuming an even split gives ~135 chapters/volume, which is impossible for a bunko volume; and the two `書籍N巻発売記念SS` posts sit at web chapters ~391/~403 — but the publisher's own Vol-3 synopsis names events that occur at web chapters **108-140** (a monster fight, the viscount investiture, the third prince's rebellion). So the release-anniversary SS marks **when the book hit the shelves (the web was already far ahead), not where the book's content ends**. Anchoring on it produced a "Volume 1 = chapters 1-385" answer that was flatly wrong.
  - Confirm a claimed volume boundary by **matching the publisher's own synopsis events to chapter numbers** (search your extracted chapter titles for the named event) — that is real evidence; an SS position is not.
  - **Print volumes are heavily expanded and carry web-absent content**, so web chapters do not map 1:1 onto a volume even in principle (the author says so in the afterword — added date scenes, extra characters, bonus epilogues).
  - **An official table of contents is usually NOT published — but a reader-facing translation site may carry one, and it is the one place worth a look.** Checked and absent on: the label's official site, KADOKAWA's product pages, BookWalker, a LN wiki, and a catalog aggregator — all show only a synopsis. So do not burn hours hunting a publisher ToC. **However, the one place a complete ToC does appear is on sites that translate the PRINT edition** — they list `Volume 1 / Prolog / Chapter 1-7 / Epilog / Short Story` because that is the book's own structure. Read that ToC for the volume *shape*, and note what it proves: a verified print ToC showed **7 / 6 / 6 chapters across the three volumes**, i.e. ~19 chapters total, against ~400 web episodes. That single fact kills the "even split" theory permanently — the print chapters are long-form and the web episodes are short, so the two are not the same text at all.
  - **A volume count does NOT scale with the web episode count — do not reason from one to the other.** Three 326-page bunko volumes (Kadokawa product pages carry `判型: 文庫判／326ページ` per volume, with ISBN and release date — useful, and not a ToC) versus ~400 web episodes is the normal shape: the book is heavily rewritten and condensed. So "pages ÷ average-episode-length" is not a valid conversion either; it was tried and produced ~90 eps/volume, which the publisher's own synopsis contradicted (named Vol-3 events sat at web chapter 108-123).
  - **Watch for a renumbered edition hiding under the same title.** A work can exist as a print reissue with its own volume numbering that has NO relationship to the web numbering the archive holds. When the user asks "does it have volumes?", answer from the publisher's product pages (per-volume ISBN + page count + release date) and say plainly that the volume split is not the same axis as the web chapters — do not imply the web chapters can be bucketed into those volumes.
  - **Therefore label the fold groups neutrally** (`Bagian 1` / `Bagian 2` with honest explicit ranges) rather than asserting `Volume N`, which you cannot source; mark any boundary you do offer as `perkiraan`. Say plainly that the label can be renamed to "Volume" the day a real TOC is known — the fold UI does not need rebuilding for that. Use `Volume` only if the user explicitly accepts a flagged estimate. Cite the rule the user set: **"kasih Bab brp + Volume Brp Yg Jujur, biar yg baca ga binggung"**.
- **Search for the official English title (ATL) can legitimately fail.** One verified case: the JP romaji title resolved cleanly (RanobeDB by title), but an English "ATL" name the user had been given was found on **none** of RanobeDB aliases, MangaUpdates, AniList, MAL, Google Books, or web search (NovelUpdates 403s). That is a real result — report "not found" rather than picking the closest match.
- **`cat`/`od`/`head` of credential files leaks secrets into the transcript.** Read keys only inside a script that uses them, never print them; if a secret is ever exposed, tell the user to revoke it.
- **Check free disk space BEFORE a long multi-hour run; `disk I/O error` from sqlite means the disk is full, not corrupt.** A 147-chapter MTL run writes a per-chunk JSON plus staging and DB copies, and this host runs near-full routinely. When free space runs out mid-run: sqlite raises `disk I/O error` on write, the worker can die, and — worse — the run may look alive while failing to persist, so you only notice at the final count. `df -h /` first; if it is above ~90%, find the big consumers (`du -ah <proj> | sort -h | tail`) and clear **superseded DB backups** first. Verify a candidate backup is a duplicate of a file you still hold (`md5sum` both) before deleting — a stale `.bak` of the warehouse DB can be several GB, and deleting one you still need is unrecoverable.

## Mature (18+) source content: accept it, label it, and pick the model that can translate it

<!-- verified: the user asked whether an "18+" novel could be added, and separately whether
     over-the-top MTL output could be hand-translated; both were accepted with conditions -->
The user does want adult-genre novels on the shelf. Two standing decisions, so this does not get
re-litigated per novel:

- **Accept, but classify by DEGREE and label openly.** Read the source and say which band it is:
  *light* (implied / fade-to-black), *medium* (written, not crude), *explicit*. Report the band with
  evidence rather than a blanket "18+" — a medium romance reads very differently from an explicit
  one, and the label follows the measurement. The user's chosen label for the site is plain **"18+"**.
- **The hard refusals are a legal/operational line, not squeamishness** — content sexualising minors,
  sexual violence played as titillation, and incest-as-fanservice. Say plainly which band a work falls
  in and refuse that one; do not refuse an entire adult romance on the strength of one explicit scene.
- **When MTL output on an intimate scene is over-the-top or broken, hand-translate it** — the user
  asked for exactly this ("kalo berlebihan lu bisa TL in manual kan?"). Hand-translation follows the
  existing refusal-order rule above: short neutral prompt retry → non-refusing model → hand-translate.
  Hand-translate **faithfully to the source**: if the source is implicit, the result stays implicit and
  merely reads more naturally; never add explicit content the source did not have, and never soften a
  scene the source did write.
- **Cite the translation's provenance before loading.** A third-party translation of an adult work
  carries its own translator's watermark/licence; it is a third-party asset (stage + wait for approval),
  and the "never sell" rule applies to it like any other licensed raw.

## Reporting (this user)

Casual Indonesian (lu/gua), evidence per claim: which raw was used and its verified title, the part/chapter count and char count EN vs ID, the per-chunk progress, the four-side verification result, the staging→main load with the new id + chapter-id range + undo-log path, and the FTS spot-checks. Keep a durable recipe note in the project (`CATATAN/RESEP-MTL-sendiri.md`) so the next novel follows the same shape.

**Always name the novel, never the bare id.** Standing user rule, verbatim: *"Lu ngasih tau judulnya jan make id dong kalo lu cuma bilang 1970 gua gatau kampret"*. Write `ShuuKura (id 1987)`, never just `1987` — an id alone is unreadable to the user. Order the report **title first, id second**.

**A per-volume result belongs in a table, not prose** — one row per volume with chapter count and char count, so the user can see at a glance which volumes are new, which were skipped, and which are still held. When volumes come from different sources (third-party warehouse + our own MTL), say which is which in the table; do not let the reader assume the whole set is ours.

**When the user sends a source/dump you already hold, check the archive first and report the match — do not re-import.**<!-- verified: the user sent two volume links for a novel already fully on the shelf; the correct answer was "already there" plus the existing per-volume counts, then act only on their word --> When they then say "kalo udah ada skip aja", skip it and record the closure; do not offer to re-verify unless they ask.
