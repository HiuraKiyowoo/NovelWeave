# JP→ID MTL: the separate pipeline and its verification

The EN→ID pipeline (`mtl-pipeline.py`) does not translate Japanese. Keep a parallel script
(`mtl-pipeline-jp.py`) — a separate prompt, separate cutters, separate input keys. This file is the
recipe and the failure catalogue for the JP→ID case.

## Why it must be separate

| | EN→ID | JP→ID |
|---|---|---|
| Prompt | "Translate English to Indonesian" | "Translate Japanese into Bahasa Indonesia" (force the target) |
| Cutters | `[.!?"]` | `。！？」…` |
| Input keys | `bab` / `en` | `episode` / `teks` (or `judul` + `teks`) |
| Healthy ID:souce ratio | ~95-115% | ~225-240% |

**Emit the raw in exactly the key names the pipeline reads, or the run exits silently with 0 work.**
<!-- verified: a hand-built raw used `jp` instead of `teks`; the pipeline printed
"12 episode" in its header then "0/12 episode selesai · 0s" and exited with no error at all -->
The header prints `len(eps)` from `raw.get("episode") or raw.get("bab")` — so a wrong *inner* key
(`b["jp"]` instead of `b["teks"]`) still counts the episodes and then skips every one in the loop
(`jp = (b.get("teks") or "").strip(); if not jp: continue`). The tell is a run that finishes in
seconds having translated nothing, with no traceback. Before a run, assert the shape: every episode
has a non-empty `teks`, and print the total source chars you expect (`sum(len(b['teks']))`). A
zero-char total means the keys are wrong, not that the raw is empty.

## Prompt shape that survives

State the **target language explicitly and only** — "Terjemahkan teks Bahasa Jepang berikut ke
**Bahasa Indonesia**. Balas HANYA dengan terjemahan." A prompt that names the *source* but not the
target, or that includes example words (offensive/romantic) to illustrate tone, is the cause of both
failure modes below.

## Failure catalogue (all verified in one run)

1. **Wrong output language — whole chapters of Chinese / hanzi.** The prompt did not force the target
   language; the model drifted. Fix: force Bahasa Indonesia in the prompt, and reject any response
   containing CJK characters.
2. **Untranslated kanji in names** (`枫` for Kaede, `蓮` for Ren). Same CJK check catches it; the
   retry re-translates and renders the name in Latin.
3. **Refusal string embedded mid-text.** `"… high risk", "I cannot translate that"`, or an English
   translator promo appeared *inside* a chapter. The chapter was full length, so a char count did NOT
   flag it — only a substring sweep did. Everything after the refusal is usually lost too.
4. **Prompt-induced refusal.** A `"high risk"` rejection that looks like an API fault is often the
   prompt's own example words. Rework the prompt neutral and retry before blaming the endpoint.
5. **Truncated chapter** — ID length ~100% of JP source instead of ~230%. Re-translate that chapter.

## The verification sweep (run before any load)

```python
import re
HAN = re.compile(r"[\u4e00-\u9fff]")           # hanzi
try:
    import regex as _r; KANA = _r.compile(r"[\u3040-\u30ff]")
except ImportError:
    KANA = re.compile(r"[\u3040-\u30ff]")
BATAS_ERR = ("high risk", "rejected because", "i cannot", "i can't", "i'm sorry", "as an ai")

for k, v in chapters.items():
    idn = len(v.get("terjemah") or "") or sum(len(x["id"]) for x in v.get("potongan", []))
    rasio = 100 * idn / max(1, v["jp_panjang"])
    cacat = []
    if HAN.search(v.get("terjemah", "")) or KANA.search(v.get("terjemah", "")):
        cacat.append("CJK")
    if any(e in (v.get("terjemah") or "").lower() for e in BATAS_ERR):
        cacat.append("pesan error")
    if rasio < 180:
        cacat.append(f"pendek {rasio:.0f}%")
    if cacat:
        print(k, cacat)
```

A chapter that passes the sweep AND is in the 225-240% band is done. Anything else is re-translated
by a small fix script (`paksa-bersih-jp.py` shape): re-translate, reject if the retry still shows
CJK / error / short length, and keep retrying through the `coba`/`MODEL_CADANGAN` loop below until a
clean result lands — never save a failing retry just to move on.

## Attempts and model rotation (a stubborn chunk is not a lost scene)

A refusal-prone model rejects the *same* chunk several times in a row and then succeeds — so a small
retry count silently drops a scene. Set `coba=6` and, on exhaustion of one model, **rotate to the next
in `MODEL_CADANGAN` and retry the same chunk there rather than returning an error**. The failure was a
real lost opening chunk (`0c`) that reported `selesai=True`; with 3 attempts the model gave up on a
chunk it accepted on the 4th try.

**But when a whole content CLASS is refused, rotation is rote retrying — switch the model instead.**
<!-- verified: 72 chunks across two JP->ID volumes sat empty, re-refused on every attempt with the
default free-tier model, and translated in ~5 minutes once a different model was used -->
Distinguish the two shapes of refusal, because they need opposite fixes:

| Symptom | Cause | Fix |
|---|---|---|
| Same chunk fails 3-5x, then succeeds | stochastic / prompt-length | keep retrying, `coba=6`, short bare prompt |
| EVERY chunk with a given kind of content (romance, intimacy) refuses, forever | the model refuses that content class | switch model |

Diagnose it by counting: if refusals cluster on chunks that share a content type rather than spread
randomly, it is the model, not the prompt. Probe one refused chunk against a candidate model before a
long run — one call answers it. Verified: `harbor/mimo-v2.6-flash:free` structurally refused intimate
scenes while `cbai/deepseek-v4.1-flash` translated the whole set cleanly. Do not burn hours of retry
loops on a model that cannot do the book.

**A wrapper client's translate function may return a TUPLE, not a string** — read its signature first.
Verified: `mtl-klien.py`'s `terjemah(teks, coba, jeda, model)` returns `(hasil_teks, pesan_error)` with
`''` on failure, so composing on the return value raises `'tuple' object has no attribute 'strip'` on
every call and the batch looks like a total failure while the endpoint is fine.

Rejection list to keep in one place (substring match, case-insensitive): `high risk`,
`rejected because`, `i cannot`, `i can't`, `saya tidak bisa`, `as an ai`, `maaf, saya tidak`, plus the
Chinese continuation tells `接上一段`, `延续`, `（续`, `续写`. Plus: any CJK/kana left, any length below
the floor, and any `NAMA_SALAH` variant.

## Cutting the raw at the story's real end, not the page's end

A Syosetu work page wraps the story in `<div class="js-novel-text p-novel__text">`; the `--preface`
and `--afterword` variants and a following `p-recommend` block (cards for *other* novels) are all still
inside the same document. Take the content div explicitly, and treat `p-recommend` as the hard cut:
anchoring on the first `js-novel-text` and reading to the end of the page drags in the disclaimer,
Google Analytics, and other novels' blurbs — a raw that looks 15k chars but ends with another book's
synopsis. Verify the tail is the story's last line, not a promo.

The author's afterword/promo (`あとがき`, `後書き`, `この度…完結`, `読者(の皆様|様)…`) frequently attaches
**inside** a paragraph, so a paragraph-boundary filter misses it. Cut it by marker substring and
re-verify that only the intended episodes changed: keep the pre-clean copy as `-asli.json`, then
compare cleaned vs original ignoring whitespace and the full-width space `U+3000` — only the promo
episodes should differ.

## A one-shot web version is not a truncated novel

<!-- verified: a requested novel's free web raw was one chapter, and the user chose to translate exactly that -->
A novel can legitimately have **two different works** under one title: a free web version and a print
version. A `1話完結` web entry is a complete one-shot short story (often a contest winner later
expanded into a book), and the print notice itself says so (`書籍版では内容が大幅に加筆されています`).

So a 1-chapter raw is **not** evidence of a broken scrape — check which it is before deciding:
- Confirm the raw is internally complete: the last paragraph is a story ending, not a promo for
  another work.
- State plainly to the user that the free version is N chapters and the print version is longer and
different, then let them choose. Do not silently pad it, and do not refuse it as "incomplete".
- Record it as `Completed` with the real chapter count.

The same shape shows up when the RAW's own tail is a **promo for a different novel** (a recommendation
card's blurb): cut at the story's real ending, never include it.

## Character names must be forced, not inferred per chunk

The prompt must carry an explicit glossary, because each chunk is translated in isolation:

```python
GLOSARIUM = {"鏑木美春": "Kaburagi Miharu", "鏑木": "Kaburagi", "美春": "Miharu",
             "日宮友樹": "Himiya Tomoki", "日宮": "Himiya", "友樹": "Tomoki"}
NAMA_SALAH = ["Hijaraki", "Kadurigi", "Tokiwa", "Hinomiya"]   # drift seen before
```

Put both the full and the surname/given halves in `GLOSARIUM` — a chunk that uses only the surname
will otherwise re-romanise it. Inject the map into every call ("⚠️ WAJIB PAKAI NAMA INI PERSIS…") and
reject a response containing any `NAMA_SALAH` entry. Final check across the joined text: the correct
forms have a non-zero count and **every known-wrong variant is 0**, per character.

Source the names from the raw's own ruby/furigana or the work metadata rather than transliterating
yourself — that is the authority the glossary is supposed to reproduce.

### Scope: rebuild both lists per novel, and keep the blacklist to *names* only

`GLOSARIUM` and `NAMA_SALAH` are per-novel vocabulary. Carrying the previous novel's entries into a
new one corrupts it, and the corruption is quiet:

- A leftover blacklist entry that happens to be a **correct name in the new novel** makes every chunk
  containing it fail. Verified: `"Lest"` sat in the list from an earlier book, rejected the new
  novel's own character name on **12 consecutive retries**, and cost 28 minutes on a single chunk
  before the loop gave up (`1/2 potongan`, chapter left incomplete).
- Ordinary words got blacklisted the same way — `Hakushaku` / `Kouchaku` (伯爵 / 侯爵, the words for
  *marquis*) were treated as misspellings even though the new novel uses those ranks in prose.

So: **a `NAMA_SALAH` entry is only ever a wrong romanisation of a person's name.** If the string could
be a real word, rank or title in any book, it does not belong in a blacklist — fix `GLOSARIUM`
instead. Rebuild both dicts from the new novel's own raw before the first chunk.

The symptom to watch for is **elapsed time, not an error message**: the chapter still completes, so
the log reads like progress, but each chunk takes 20-30× the normal wall clock. Any chunk-time
outlier is a blacklist false-positive until proven otherwise — grep the log for
`DITOLAK (nama salah: …)` and verify the flagged string really is wrong *in this book*.

**The flagged string can be the NOVEL'S OWN PROTAGONIST — a hard stop, not a slowdown.**
<!-- verified: `Haruto-kun` was rejected on every attempt and the run had to be killed; the name was
correct, and it had been carried over in the blacklist from an earlier novel -->
A second symptom is a rejection that refuses to clear however many times you retry, because the
blacklist entry is a *correct* name in this book. Before blaming the endpoint, timeout, or prompt on
a stuck chunk: grep the log for the rejected string, then check whether that string is a character
name in THIS raw (it usually is — often the protagonist). The fix is to delete the entry from
`NAMA_SALAH`, never to weaken the check or force-save the failing chunk. Treat any `DITOLAK (nama
salah)` whose string appears in the work's own episode titles or glossary as a blacklist bug and
stop the run to fix the list first.

Blacklisting a **`-kun`/`-chan` form** is a frequent cause: a romanised `Haruto` in the glossary is
correct, but the prose's `Haruto-kun` is not a misspelling of it, so the bare-name entry must never
be expanded into an honorific-bearing blacklist pattern.

### The one inherited blacklist entry can kill the WHOLE run, not just slow one chunk

<!-- verified: a leftover blacklist from the previous novel rejected the new novel's own
protagonist on every attempt; the run stalled and then died mid-book at chapter 41 of 147, hours in -->
The earlier "slow chunk" symptom is the *mild* form. The severe form is a **dead process**: the
rejection loop retries forever or the wrapper aborts, and the run stops mid-novel with no error you
notice until you poll it. Before starting any novel's run, do this **preventive sweep** — do not wait
to diagnose it from the log:

1. Rebuild `GLOSARIUM` and `NAMA_SALAH` from THIS novel's raw (its `ruby`/furigana, episode titles,
   metadata) — never reuse the previous dict.
2. Grep the raw for every `NAMA_SALAH` entry. **Any entry that appears in this raw is a bug** — it is
   either this book's own character or an ordinary word; delete it before the first chunk.

When a run dies mid-novel, the first check is the rejected string in the log: if it is a name in this
novel, the blacklist is the cause, not the endpoint. Restarting from the failed chapter is fine once
the list is fixed (the already-translated chapters are keyed, so a `start=N` resume skips them) — but
fix the list first or the restart dies at the same chapter.

### Rejection matching must be WORD-BOUNDARY, or a correct name trips it

A blacklist entry checked with plain `substring in text` fires on the correctness case: an entry
`Charlott` matches the correct `Charlotte`, rejecting valid output with no real misspelling present.
Match whole tokens, not substrings:

```python
import re
def ada_nama_salah(teks, daftar):
    for nm in daftar:
        if re.search(r'(?<![A-Za-z])' + re.escape(nm) + r'(?![A-Za-z])', teks, re.I):
            return nm
    return None
```

If you must keep substring matching, order matters — but word boundaries are the correct fix.

## Non-story episodes on the work page: 解説 and the bonus SS

<!-- verified: a 404-episode Kakuyomu work carried 7 non-story entries alongside 397 numbered episodes -->
A web work's episode list is not all story. Two shapes appear, and both should be translated and
**labelled honestly** rather than dropped or dressed up as chapters:

- **`解説` / `設定` (worldbuilding explainers)** — e.g. `解説　王立学園について`. Real content, not a
  chapter. Label it `Penjelasan: <judul>`.
- **`発売記念ＳＳ` / `書籍N巻発売記念SS` (publisher bonus short stories)** — side stories written to
  promote a print volume (`ヴィオラと受験勉強`, `プリムラとショッピング`). These ARE story; translate
  them, labelled `SS Buku: <judul>`.

Numbering rule: **take the chapter number from the episode's own `第N話` marker, never from the file
index.** The two diverge as soon as one non-story entry exists, and file order also shifts if an entry
is added later. Verified: 404 files held 397 numbered episodes with `第N話` running 1…397 without a
gap, plus 7 unnumbered inserts — indexing by file position would have mis-numbered every chapter after
the first insert. Keep the author's number and let the non-story entries carry a label instead of a
number.

When a work is ongoing and its print volumes are ahead of the web, say so plainly: bonus SS attached
to volumes sometimes DO appear on the free web (so take them), while print-only bonus chapters do not.
Do not describe the web version as missing what it never had.

## Prompt placement: user turn, not system

A reasoning-family model can ignore or mis-handle a `system` prompt here and answer *in the source
language* (Japanese) or continue in Chinese. Sending the same instruction as the single **user**
message fixed it. See the model-endpoint section in SKILL.md.

## Titles

Translate the 70-ish episode titles in a batch (`tl-judul-jp.py`), then lint the result: every title
must match `Bab N: <judul>`, contain **zero** Japanese characters, and have no doubled punctuation.
Expect ~10 needing a manual pass (`rapikan-judul-manual.py`) — a model translating titles in batch
will slip a few back into Japanese or mangle the number/colon.

### Strip the `第N話` marker with an explicit ideographic-space class, not `\s`

<!-- verified: 15 chapter titles went into the DB still in Japanese while the health checks all read green -->
A Kakuyomu/Syosetu episode title is `第27話　対面の日` — **the separator after `第N話` is an
IDEOGRAPHIC SPACE `U+3000`, not a plain space.** In Python `re`, `\s` does match `U+3000` on a `str`,
but a hand-written `re.sub(r'^第\d+話\s*', '', j)` in a *different* toolchain, or a `trim()`/`split(' ')`
based stripper, does not — and the failure is silent: the title keeps its `第N話` prefix and the whole
string stays Japanese, yet no length, CJK-in-body or separator check looks at the title column. Write
the class explicitly:

```python
judul = re.sub(r'^第\d+話[\s\u3000]*', '', judul).strip()
```

Then **verify the title column itself**: every loaded chapter title must contain zero
`[\u3040-\u30ff\u4e00-\u9fff]` and zero `U+3000`. A DB read straight after the load is the only place
this shows up — `SELECT nomor, judul FROM bab WHERE novel_id=?` and eyeball the list. Translate the
bare titles (batch or via the model) only after the marker is gone, or you translate the marker too.

### Titles must also match the archive's established style, not just be Japanese-free

The archive's existing volumes use `Chapter N — <judul>` (em dash, per volume), so a freshly loaded
volume opening with `Bab 1` reads as a different book on the same shelf. Reuse the style the novel's
own earlier volumes already carry, and re-read the full chapter list from the web afterwards to
confirm it renders.

## Scene separators: normalise to ONE `***` line, and keep the COUNT

<!-- verified: a raw's `∮ ∮ ∮ ∮` came through as `*** *** *** ***` and its `＊ ＊ ＊ ＊` as `*  *  *  *` -->
A JP raw marks scene breaks with a decorative line (`∮ ∮ ∮`, `＊ ＊ ＊`, `◇◇◇`, `———`). The model does
not drop it and does not translate it — it echoes the *number of symbols* it saw, so one break becomes
`*** *** *** ***` (four on one line, not a real separator) or `*  *  *  *` (ASCII asterisks with double
spaces, which a `\*\*\*`-only regex misses). Two rules:

1. **Collapse any run of asterisk-ish separator tokens on one line into a single `***` line.** Match on
a class, not the literal: `re.sub(r'(?:[\*＊∮◇※—–~・]{1,4}[\s\u3000]*){2,}', '***', teks)`, then
   collapse a resulting `\*\s*\*\s*\*` to `***` and strip blank lines around it. Do NOT replace a
   bare single `*` (that is prose, or a footnote marker).
2. **Verify the separator COUNT per chapter against the raw, not just its presence.** The count is the
   real signal: if the raw chapter holds 2 breaks and the translation shows 1, one break was swallowed
   (usually the second fell at a chunk boundary and the model merged it away). Compare
   `len(re.findall(r'∮|＊|◇', raw))`-derived break count to `terjemah.count('***')` per chapter and
   re-translate any chapter where they differ — a chapter whose separator count is off is the marker
   that a scene was merged across a chunk seam.

A separator sweep is part of the pre-load normaliser, alongside the register normaliser, not a
one-time manual fix.

## Staging keys

When several MTL novels share a staging table, key by `"{SLUG}:bab{i:02d}"`, not `"bab{i:02d}"` — the
bare form collides with the previous novel's chapters and the load silently mixes two books.
