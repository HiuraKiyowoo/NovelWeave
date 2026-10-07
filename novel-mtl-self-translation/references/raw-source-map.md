# Raw-source map: where a free official raw lives, and how to PROVE you got the full text

Two things this file settles so a session does not re-explore them:

1. **Which sites carry a usable raw**, what each one is (JP original vs EN translation vs EPUB
   file), and which is the right default.
2. **The proof rule:** a source that answers HTTP 200 is NOT a source that gives you the book.
   Before reporting a site as usable, extract ONE chapter's body and measure it — the user will
   say "jangan yg preview doang" and a reachability list is not evidence.

## The map (ordered by preference for OUR pipeline)

| Source | URL | Raw kind | What it is |
|---|---|---|---|
| **Syosetu (narou)** | `api.syosetu.com/novelapi/api/` | ✅ JP original | ~1.25M works, real JSON API, full episode text. **The default.** |
| **Syosetu R18** | `api.syosetu.com/novel18api/api/` | ✅ JP original 18+ | ~160k adult works — **a SEPARATE endpoint** (see below). |
| **Kakuyomu** | `kakuyomu.jp` | ✅ JP original | Kadokawa's platform; print-origin LNs live here too. |
| **AlphaPolis** | `alphapolis.co.jp` | ✅ JP original | Publisher's own web-novel arm; episode text is on the site. |
| Hameln | `syosetu.org` | (JP original) | Often 403 to a plain UA — a fetch-fix problem, not a dead source. |
| Jnovels | `jnovels.com` | 📦 EPUB/PDF (EN) | Whole LN volumes as files; not a per-chapter reader. |
| MPL | `mpl.live` | EN translation (licensed) | Third-party/licensed → quarantine rule. |
| AsianHobbyist | `asianhobbyist.com` | EN fan translation | Third-party → quarantine rule. |
| Novelight | `novelight.net` | EN fan translation | Third-party → quarantine rule. |
| Baka-Tsuki | `baka-tsuki.org` | EN community translation | Third-party, mostly older works. |
| RanobeDB | `ranobedb.org/api/v0/…` | metadata only | Volume counts, `books[]`, aliases — NOT a text source. |

**Default order:** Syosetu → Kakuyomu → the print route (`§2f` Nyaa / a translation aggregator).
Everything in the EN-translation half of the table is **third-party content** — read it for
structure/metadata, never load its prose as our own MTL (same rule as `§2d` here).

## When every free source misses: the sweep order, and how to tell "licensed" from "not found yet"

<!-- verified: a publisher-original LN (OVERLAP Bunko, 3 vols) returned 0 hits on Syosetu,
     Kakuyomu, ruidrive, Nyaa and sukebei; BookWalker search resolved it immediately with
     publisher + author + volume count from paid listings. -->

A novel being absent from Syosetu/Kakuyomu does NOT mean it does not exist — it usually means
it is a **publisher-original** (no free web-novel edition ever released). Sweep in this order,
stop at the first hit, and record the miss list so the next session does not repeat it:

1. **Syosetu API** — `word=` not `keyword=`; `keyword=` ignores the term and returns unrelated
top hits (a bogus `allcount: 1254491`). `word=` returns the true count (`allcount: 0` = really absent).
2. **Kakuyomu search** — filter hard: a hit on a shared trope word (e.g. 幼なじみ) is usually a
   DIFFERENT novel. Confirm the returned title matches, never the keyword count.
3. **ruidrive / human-ID aggregators** — via `<blog>/feeds/posts/default?q=<slug>&alt=json`
   (`0` entries = truly absent *by that name*; try the JP title too).
4. **Nyaa + sukebei** with the JP title — `0` results is common for new/niche LNs.
5. **ranobedb / NovelUpdates** — metadata only; absence there is not evidence either way.

**Then confirm the work's identity on the paid store, not a free one: `bookwalker.jp/search/?word=<JP title>`.**
It answers for titles that exist *only* as paid editions and returns, in the search HTML, the
**publisher imprint** (`オーバーラップ文庫` / `MF文庫J` / `GA文庫` …), the **volume list**
(`… 1`, `… 2`, `… 3`) and the **author/illustrator** (`著者-<name>` anchors). That is what
makes the report actionable: "licensed by <imprint>, N volumes, no free raw anywhere" — a
final answer, not a shrug. Amazon JP also works but frequently connection-resets to scripted
fetches; BookWalker does not.

**Report the verdict, not the attempts.** For a licensed-original with no free raw, the correct
end state is: name the imprint + volume count + author, list the sources checked, and mark the
novel **queued** — do not present the dead-end sweep as a workflow, and do not substitute a
lesser source. Same class as the `試し読み` preview rule above: a preview is not the raw.

## Syosetu's two corpora are two endpoints — do not cross them

<!-- verified: the general corpus and the adult corpus answer on different paths and site hosts -->

| | General | Adult (R18) |
|---|---|---|
| API | `https://api.syosetu.com/novelapi/api/?out=json…` | `https://api.syosetu.com/novel18api/api/?out=json…` |
| Reader host | `ncode.syosetu.com/<ncode>/<n>/` | `novel18.syosetu.com/<ncode>/<n>/` |

The request shape (`out=json`, `lim=`, `order=hyoka`, `word=`, `of=…`) is identical — only the
path segment (`novelapi` → `novel18api`) and the reader host change. **An adult work is absent
from the general API** (`allcount: 0` there) even though it is live, so `allcount: 0` on the
general endpoint is not proof of a deleted work until you also try `novel18api`. The episode
text uses the same `js-novel-text` div class and the same 短編/《`p-recommend`》 traps as `§2c`.

## The proof rule: extract ONE chapter body and measure it

<!-- verified: a reachability sweep listed ten "live" sources; the ones that actually returned a
     full chapter body were Syosetu, Kakuyomu, Syosetu R18 and AlphaPolis — Jnovels answers 200 but
     carries EPUB FILES, not chapter text -->
A site `200`-ing means its home page loaded. That says nothing about whether you can get the book.
Before calling a source usable, do ALL of:

1. **Request one concrete chapter**, not the index. Syosetu/Kakuyomu: the `js-novel-text` div /
   `id="content"` (see `§2b`/`§2c`). AlphaPolis: an episode page. Jnovels: an EPUB file link.
2. **Print the length AND the head/tail as `repr()`** — `len(isi)` plus `isi[:120]` and `isi[-120:]`.
   A real chapter is thousands of chars opening on prose and closing on a sentence, not a teaser
   cut mid-thought. Verified healthy samples: 5,387 / 3,817 / 1,489 / 3,938 chars.
3. **Reject the teaser shapes explicitly:** a body that is one short paragraph, ends with `…続きを読む`
   / `続きを読む`, or is a `試し読み` (free-preview) excerpt of a paid edition. A publisher's free preview
   is a marketing excerpt of ONE volume — never the raw.
4. **Only then report the source as usable**, and report it with the measured number as evidence
   (`"Syosetu: 5,387 aksara dari Mushoku bab 1"`) rather than "bisa diakses".

**A list of sources you merely contacted is a preview-grade answer**, and the user will (rightly)
call it out. The cheap fix is one extraction per candidate before writing the report.

## Reporting a source landscape to this user

- Report in **two tiers**: RAW JP original (usable, becomes our own MTL) vs third-party/EN
  (quarantine — read structure only). Never present them as interchangeable.
- Give the **exact URLs** the user can open and pick from themselves (`syosetu.com`,
  `yomou.syosetu.com/rank/list/type/total_total/`, `kakuyomu.jp/rankings/all/weekly`). The user's
  phrasing when they want this: *"kirim url web raw nya biar gua pilih"* — they want to browse and
  name the work, not have you guess it.
- **Do not treat "a blog already has it" as a reason to harvest the blog.** Standing project rule,
  user's words: *"biar ga nyolong terus"* — the point of the whole MTL workstream is self-effort
  from the author's own free upload, not lifting another group's translation.
