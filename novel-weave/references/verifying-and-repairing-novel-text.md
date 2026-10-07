# Repairing and verifying a novel's text — quote balance and hard-wrap

Use when auditing/repairing an already-loaded novel's chapters (novel-level cleanup, not the first MTL load): balancing dialogue quotes, fixing PDF hard-wrap, or verifying a sub-agent's cleaning work.

## 1. Quote balance: PER PARAGRAPH, with sequential pairing

Whole-chapter quote totals (`count("“") == count("”")`) are NOT a valid quality check — they give false alarms AND false passes:
- **False alarm:** a paragraph using quotes for an in-text term or newspaper headline (`diproklamirkan diri sebagai “monster”`) plus a multi-paragraph dialogue elsewhere can make a correct chapter look unbalanced (e.g. 47 open / 75 close). Do not 'fix' a chapter just because the two totals differ.
- **The real check is PER PARAGRAPH**, but a paragraph is defective only after accounting for **legal multi-paragraph dialogue**.

**Legal multi-paragraph dialogue (do NOT "fix"):** one speaker spanning several paragraphs opens with `“` on the first paragraph and closes with `”` on the last, with NO quotes in between. So paragraph `i` may have `open=1, close=0` and paragraph `i+1` have `open=0, close=1`. Detect with sequential pairing, not per-paragraph equality:

```python
# walk paragraphs; a "defective" paragraph may pair with the next one
while examining paragraph i with imbalance (o-c):
    if (o-c) + (open_{i+1} - close_{i+1}) == 0:   # legal 2-para (or longer) dialogue
        skip both, continue at i+2
    else:
        real defect at i
```

On a 4M-char novel, per-paragraph totals alone reported 169 "defects" that were all legal dialogue; sequential pairing reduced that to 3 genuine defects. Always use sequential pairing before reporting or fixing anything.

**Never repair quotes with blind regex sweeps over the whole corpus.** Repeated `re.sub` passes for `“””…”””`, stray closers, etc. silently ate legitimate quotes in chapters that were already correct — earlier passes destroyed valid dialogue that a later version had to undo. Correct method: build an **explicit per-case list** (quoted exact strings, one per defect), apply exactly those, then re-run the sequential-pairing check and eyeball a sample chapter afterwards.

## 2. Repairing PDF hard-wrap (one `\n` per ~55–80 chars)

A human-translated source extracted from PDF often has HARD-WRAP: every visual line ends in a single `\n`, so a real paragraph is split into dozens of lines. Symptom: single-`\n` count in the hundreds while `\n\n` is tiny (~30). The web renderer splits on `\n`, so this displays as a shattered page.

Repair rule — process **line by line**, deciding per line:
- If the current line does NOT end in a terminal char (`. ! ? ” …`), the sentence continues → join to the next line **with a space**.
- If it DOES end in a terminal char, close the paragraph (`\n\n`) and start fresh.

```python
buf = ""
out = []
for line in [l.strip() for l in text.split("\n") if l.strip()]:
    if buf and buf[-1] in ".!?…”":
        out.append(buf); buf = line
    elif buf:
        buf = buf + " " + line
    else:
        buf = line
out.append(buf)
text = "\n\n".join(out)
```

**Pitfall (cost a full re-do):** the naive variant that joins ALL lines then re-splits on terminal chars merges the entire chapter into ONE giant paragraph — the join step drops the boundary. You must emit `\n\n` at each terminal-char line as you go (as above), not join-then-split. Expect the char count to *rise* slightly (spaces added at joins); verify by reading the first ~600 chars.

## 2b. Mid-word fragmentation — a whole defect class the finder must catch, the eye must judge

A raw whose text was rebuilt from positioned spans (a page-image PDF's text layer, a Scribd
`jsonp` page — see `scribd-page-image-pdf.md`) splits words at a font run boundary, leaving a
space INSIDE the word: `sunggu h aneh`, `mem ilih`, `akhirn ya`, `mulai be rbicara`,
`Suvuetorāna`, `kepalany a`. These read as typos and survive any quote/paragraph check, because
the paragraph structure is perfect — only the letters are broken.

**The finder is a heuristic; only reading the hit is proof.** A blanket regex cannot separate a
fragmented word from a legitimate short word, so use a *frequency* test and then READ each hit:

```python
# a+b is a broken word iff a+b occurs as ONE word far more often than `a` does alone
import re, collections
freq = collections.Counter(re.findall(r'\b[a-zà-ÿ]{3,}\b', teks.lower()))
for m in re.finditer(r'\b([a-zà-ÿ]{2,})\s([a-z]{1,2})\s([a-zà-ÿ]{3,})\b', teks):
    a, b = m.group(1), m.group(2)
    if freq.get(a + b, 0) >= 3 and freq.get(a, 0) <= freq.get(a + b, 0):
        print(repr(m.group(0)), '->', repr(a + b), m.group(0) in teks)
```

This surfaces ~25 candidates on a 210k-char novel and **every one of them is a real break** —
but the *inverse* is the trap that costs the session: a filter built on a "common short words"
stop-list drops the very cases you need. `ya ng terdengar` was MISSED because `ya` was on the
stop list, while `sunggu h aneh` was caught — two instances of the identical defect, split by an
arbitrary word list. **Do not filter with a stop-list of short words.** Instead print the
candidates with ~80 chars of surrounding context and judge each by eye, then also sweep
*backwards*: grep the corrected word (`yang`, `sungguh`, `memilih`) and ask whether any hit
still shows the broken form.

**Repair with an EXPLICIT map, never a regex sweep.** Build `{"sunggu h aneh": "sungguh aneh", ...}`
from the audited hits, `str.replace` exactly those strings, and confirm the map is empty of
residue afterwards. A generic rule like `re.sub(r'(\w)\s+(\w)', r'\1\2')` eats legitimate
spaces; the explicit list cannot. Same lesson as §1's quote rule — the audited case list, not a
pattern. Record the count (e.g. 38 fixes) so the report is honest.

A raw produced this way also carries **font-run PUA glyphs** (`\ue000`/`\ue001` for `“` `”`) and
**stray CJK tildes** (`〜`) used as expressive marks. Map the PUA codepoints to the quotes they
visually stand for; keep a `〜` that IS the utterance (`“〜〜〜っ”`) and only tidy the spaces
around it — do not delete an expressive mark as though it were corruption.

## 3. Sub-agent self-reports are not evidence

When delegating chapter cleaning, a sub-agent may report "all N chapters clean / 0 problems" while a chapter is still hard-wrapped or has an unbalanced paragraph — it can even describe the defect as "structure preserved" in its own summary. Treat every such summary as a claim to verify: after the sub-agent writes to the DB, re-run the per-paragraph sequential-pairing scan and re-check single-`\n` counts YOURSELF before accepting. The eye check + backup is what caught the one chapter a sub-agent reported clean.

## 3b. Quote repair for a mixed-quote source: per LINE, then merge, then a status machine

A human translation can mix straight `"` and curly `“ ”` inconsistently (one shape for normal
dialogue, the other for a quote-within-a-quote), and a page-image raw adds a worse case: the
opening quote is correct and the CLOSING quote arrives as the wrong glyph (`“like this."`).

**The trap that corrupts a whole novel: a GLOBAL state machine ("are we inside a quote?") flips
once on a stray quote and re-labels every dialogue line after it.** Measured: a single narration
line ending on a stray quote (`…kembali ke masa kemarin."`) flipped the state, and 345 dialogue
lines came out open-with-close-quote / close-with-open-quote. Whole-novel the counts still
balanced (1333/1333), so every count-based check PASSED while the text was wrong.

Order that works:

1. **Fix per LINE first, resetting the state at every line** — dialogue is contained in a line, so
   a per-line pass cannot be corrupted by a distant stray quote.
2. **Then repair the stray quotes in NARRATION** (a line that is not dialogue carrying a quote).
   Identify them by reading; do not let a rule guess.
3. Only for a source where one speaker legitimately spans several lines, apply the sequential
   pairing from §1 — and verify by *reading the dialogue*, not by counting.

**A balanced pair count is NOT a pass.** The 345-line corruption balanced perfectly. The pass is
`count('”' at line start) == 0` plus `count('“' at line end) == 0`, AND reading a sample. Print
both of those residuals (here they fell to 5 and 10 — the legitimate line-split dialogue — from
345) rather than the two global totals.

## 4. Always back up before any repair pass

`cp naver.db naver.db.bak-<reason>-$(date +%Y%m%d-%H%M%S)` before each repair. Chapter-level granularity lets you roll back a single chapter (copy that chapter's `teks` back from the backup) without losing the rest — this is how a bad hard-wrap pass was fully reverted mid-session.

## 5. Large 'Babak'/'Bahagian' sections with no chapter headings

A scrape may have no sub-chapter headings — only big sections (~20k words) with no internal `Chapter N` markers. Verify there is genuinely no heading first (`grep` for `Chapter|Bab |^\d+$|***`); if none, split by paragraph groups at scene separators. A big section may be one logical chapter for the shelf, or you may split it into ~8k-char pieces — confirm the desired chapter size with the user.
