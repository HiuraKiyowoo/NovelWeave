# Choosing and diagnosing the MTL endpoint & model

Depth for the "Model endpoint" section of SKILL.md. Load this when a translate run fails,
stalls, returns nonsense, or when you need to pick a model/endpoint for a new novel.

## Hard rule: the local gateway is not the batch MTL route

`http://localhost:20128/v1` is a local model gateway, not a proven translation service. Do **not** send a novel batch to it because the URL exists or because `/models` returns a model name. In this project it has returned literary continuations and menus instead of translations. A route is usable only after a fresh real-sized prose probe passes the translation-only gate.

Before a batch:

1. `GET <base>/models` or `<base>/v1/models` and record the endpoint + model id;
2. send one real-sized block (not a greeting and not one sentence);
3. reject any continuation, menu, refusal, or source-script output;
4. inspect rate-limit/quota headers and provider allowance status;
5. set a conservative batch cap and save progress per chunk.

If quota is missing or unknown, do not launch a large batch. On 429/402/503 or an allowance message, pause and preserve completed chunks; do not restart the chapter or rotate around a provider limit.

## The model can fail in FOUR distinct ways — identify which before reacting

Each maps to a different fix. Reading the wrong one sends you to fix the wrong thing.

| # | Symptom | Real cause | Fix |
|---|---|---|---|
| 1 | Every chunk fails at once, log says `503` | quota exhausted (body carries `[429] … allowance`) OR model withdrawn | print the BODY; pick another model with quota |
| 2 | A whole content CLASS refuses (`high risk` on every intimate scene) | capability gap | switch model — prompt shortening will not fix it |
| 3 | Output is a coherent ANSWER/menu, not a translation | model answers instead of translating | **switch endpoint/provider** — prompt wording does not fix it |
| 4 | Output is source-language text that ignored the instruction | prompt placed in `system` role on a reasoning model | move the instruction into the USER message |

### #3 in detail — "the model writes fiction back"

<!-- verified: on the local gateway http://localhost:20128/v1, BOTH `cbai/deepseek-v4.1-flash`
     and the `hermes` alias replied to real Russian prose with a Russian literary CONTINUATION
     or a menu ("Похоже, вы начали писать историю… что вам было бы интереснее?") — with an
     explicit "You are a machine translation engine. Output ONLY the translation" instruction,
     in BOTH the system role and the user role, at temperature 0.2. The same chunks translated
     cleanly and fast through a different provider's OpenAI-compatible endpoint, no other change. -->

Detect it mechanically rather than by eye — a translation must (a) not be in the source script and
(b) not contain a question/menu. This one-line gate catches it:

```python
kiril = sum(1 for c in out if "\u0400" <= c <= "\u04FF")   # or CJK range for a JP/CJK source
curiga = "?" in out[:80] or "?" == out.strip()[-1:]
if kiril > 20 or curiga:
    raise ValueError(f"bukan terjemahan: kiril={kiril} curiga={curiga}")
```

**A model name recorded as "works" in a past session is NOT verified for this endpoint.** The same
model id can be served by different providers with different behaviour; re-probe before trusting a
note, and record the ENDPOINT alongside the model name whenever you write one down.

### The endpoint may be swappable at runtime — ask, do not build

When the standard gateway misbehaves, the user may hand you a **replacement OpenAI-compatible base
URL + a key**. Treat it as a drop-in: the request/response shape is identical (`/chat/completions`,
`choices[0].message.content`), so only the base URL, key and model-id list change. Practical rules:
- Probe the new base URL with `GET <base>/v1/models` (or `<base>/models` — the path prefix varies)
  before wiring it in; it answers `{"error":"Invalid API key"}` on a bad key and a model list on a good one.
- Keep the key in its own env file (`~/.hermes/<name>-key.env`), read it in code, never echo it.
- Ask the user for the new endpoint rather than assuming a broken one is permanent — they can and do
  provide an alternative mid-task.

## The chunk SPLITTER must use the delimiter the raw actually has

<!-- verified: a splitter that cut on blank lines (`\n\n`) produced ONE ~25,000-char block for a
     whole chapter, because the harvested raw separated lines with a SINGLE `\n`. That block then
     hit `504 Gateway Timeout` on every attempt, and the run appeared to "fail at bab 1" forever. -->

A block size far larger than intended is the root cause of per-call gateway timeouts. Split on what
the text really uses — usually **single `\n`** for harvested web/API text, not `\n\n` (which only
exists if the source paragraph-encoded its output). Assert it before the run:

```python
def pecah(teks, maks=1500):
    out, buf = [], ""
    for b in teks.split("\n"):                 # ← single newline, NOT "\n\n"
        if len(buf) + len(b) + 1 > maks and buf:
            out.append(buf.rstrip()); buf = ""
        buf += b + "\n"
    if buf.strip(): out.append(buf.rstrip())
    return out or [teks]
```

Always print the resulting block SIZES on a sample chapter before launching the full run; a size list
of `[24827]` instead of `[1442, 1412, …]` is the bug, visible in one line.

**A stale `__pycache__` can make a real fix look ineffective.** After editing the splitter, `rm -rf
<pkg>/__pycache__` and confirm the process you are watching is the NEW one — an old worker from a
previous launch may still be running against the same output file and its log will show the old block
sizes. Kill it explicitly by PID (`ps aux | grep <script>`), never `pkill -f <script>` (it can kill
sibling jobs), then re-launch and read the FIRST lines of the fresh log to confirm the new sizing.

## Cost/speed expectations to set with the user

Measured on a real novel through a working endpoint at ~1500-char blocks: **~2.5-15 s per block when
the endpoint is healthy**, but intermittent `503`s add retries and can drag the average to ~1 min/block.
Report progress by **counting completed blocks from the saved output file**, and quote the ETA as a
range. Save after EVERY chapter so a crash or an exhausted budget resumes instead of restarting.

### Benchmark a candidate model on a REAL block, never on a short sentence

<!-- verified: a 2-line probe made MiniMaxAI/MiniMax-M2.7 look ~4x FASTER than the deepseek model
     (8 s vs 30 s); on real ~1500-char novel blocks the order flipped hard — MiniMax ran 16-31 s/block
     while deepseek ran 2.5-2.8 s/block. The short probe measured connection/queue latency, not
     translation work, and would have picked the wrong model. -->

When choosing between models to save wall-clock, time each on **actual pipeline blocks at the real
chunk size**, on at least two of them, with the real task shape (translate prose — not a chit-chat
completion, which any model answers fast). A one-line probe mostly measures connection and queue
latency and can rank the candidates backwards. Take the per-block number as the decision input; if the
observed steady-state rate later disagrees (e.g. a stretch at ~1 min/block), re-read the block counts
rather than the log's moaning, since intermittent `503` retries inflate the average without the model
being slow.
