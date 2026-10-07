# Getting a free, official raw from a web-novel site (Kakuyomu / Syosetu)

When the candidate is a **web novel**, you do not need the user to supply a raw and you do not
need to fight a paywall: the author publishes it on the platform themselves. Prefer this over
asking, and prefer it over any aggregator mirror.

The catch: these works are usually **absent from RanobeDB** (they are not print volumes), so a
RanobeDB miss is not a dead end — it just means "check the web platforms next".

## 1. Find the work

- **Kakuyomu** (Kadokawa) and **Syosetu** (Shōsetsuka ni Narō) are the two to check. A plain web
  search for the JP title usually surfaces the exact work page; the platform is the authority.
- **Syosetu has a real JSON API** — use it, do not scrape the HTML:
  ```bash
  curl -s 'https://api.syosetu.com/novelapi/api/?out=json&lim=6&word=<url-encoded JP keyword>'
  ```
  `out=json` → `[{allcount:N}, {…novel…}, …]`; fields include `ncode`, `title`, `writer`, `story`,
  `genre`, `general_all_no` (episode count). Japanese keywords must be url-encoded.
  **`general_all_no` is the authority for the expected chapter total — assert the fetched count
  against it (see §2c item 2), because the work page only lists the first 100 rows.**
  **`allcount: 0` for a title is a real answer** — it means this work is not on Syosetu, so move to
  Kakuyomu. Confirm the API itself is alive with a common word (e.g. `天使` returns ~15k) so you do
  not mistake a request-shape error for "no such novel". Also beware: Ryuu (romaji) keyword searches
  against the JP-only corpus return 0 — search in Japanese.
- **Kakuyomu has no public JSON API**, but the work page is a Next.js app and the whole work record
  is embedded in the page (next section). A plain `curl` with a normal browser UA returns 200.

### A web novel that went to PRINT is deleted from Syosetu — and the API still answers `allcount: 0`

<!-- verified: a listing site linked ncode N0955GD; the API returned allcount 0 and the work page
returned HTTP 200 with body "この作品は作者によって削除されました" -->
A widely-print-published web novel is routinely **taken down** from Syosetu by its author (the
print edition supersedes it — this is normal practice, not a takedown for cause). The failure shape
is confusing because nothing 404s:

- **The Syosetu JSON API returns `allcount: 0` for a deleted ncode**, exactly as it does for a title
  that never existed. So `allcount: 0` has TWO meanings: "not on Syosetu" **and** "was on Syosetu,
  now removed". Do not report the second as the first.
- **The work page URL still returns HTTP 200** — the body is a short error page
  (`この作品は作者によって削除されました` / "this work was deleted by the author"), not a 404. A status-code
  check alone says the page is fine.
- **The ncode you are holding is still real.** A listing site's outbound anchor points at the
  author's original ncode even after deletion, so a link that "leads nowhere" is confirming the work
  existed rather than proving your search was wrong.

**Recovering the ncode when a title search finds nothing:** the Syosetu API's `title=`/`word=` search
will not surface a deleted work, and a plain web search for the JP title often returns only
retailer/Amazon/wiki pages. The reliable path is a **listing site that links out to the official
page** (a なろう reader-index site) — fetch its page for the work and grep the outbound hrefs:

```bash
curl -sL -A "$UA" "<listing-site page for the work>" -o /tmp/list.html
grep -oE 'https?://ncode\.syosetu\.com/[A-Za-z0-9]+' /tmp/list.html | sort -u
```

Confirm the ncode is *this* work by the anchor's own text (the full JP title) before trusting it, and
re-state the deleted-work finding to the user rather than reporting a bare "not found".

### When the web version is gone, the raw route changes shape — decide which one applies

A print-origin work whose free web raw was deleted has THREE possible routes, and they are not
interchangeable:

1. **The print LN itself as a scan** (Nyaa / dlraw — see §2f). This is the *only* route that yields
the actual print volumes; it covers the volumes the fan translation skipped.
2. **A human-translation aggregator** (ruidrive-style safelink blog — see §2e). Yields translated
   volumes as PDF/RAR, but it is third-party content (quarantine + approval).
3. **The official English publisher's translation** (e.g. a licensed EN release). Also third-party,
   and EN→ID is a two-hop translation.

Say which routes exist and which volumes each covers **before** picking one, because they disagree:
verified on one work, the fan-translation blog covered volumes 1-12, the aggregator covered 1-8, and
the Nyaa print-raw upload covered only 1-2.

## 2. Kakuyomu — decode the work page in ONE request

The page embeds an Apollo/Next.js cache. Do not walk the table of contents page by page — it all
comes down in the initial HTML:

```python
import re, json
h = open('/tmp/kaku.html', encoding='utf-8', errors='ignore').read()
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
d = json.loads(m.group(1))
A = d['props']['pageProps']['__APOLLO_STATE__']
```

Then read what you need out of `A` — the keys are flat strings of the form
`Work:<id>`, `Episode:<id>`, `Chapter:<id>`, `UserAccount:<id>`:

- `A['Work:<workId>']` → `title`, `genre`, `catchphrase`, `introduction` (= the description/
  synopsis), `publishedAt`, `lastEpisodePublishedAt`, `publicEpisodeCount`.
- Every `A['Episode:<id>']` → `title` (e.g. `第1話　公園で天使様を拾う`) and `publish`. **These are
  the raw's chapter list** — count them and compare to `publicEpisodeCount`.
- Every `A['Chapter:<id>']` → the larger divisions (`第一章　出会い`, `第二章`, …) — this is the
  part/chapter structure for step 3 of the pipeline.
- `A['UserAccount:<id>'] → name` / `activityName` / `screenName` gives the author.

A longer alternative that also works: walk every `key,value` in `A` and collect the ones whose key
contains `title|author|episodeCount|publishedAt|tag|genre|introduction` — but the direct key lookups
above are far cheaper to read.

**Watch the payload size.** The dump includes a large amount of unrelated scaffolding (feature
flags, an entire `MediaFranchisedWorkProvider` catalog of every Kadokawa imprint, gift items) that
runs to tens of KB. Filter to the keys you want and print only those, or you will dump ~80 KB of
noise into the transcript for one synopsis.

## 2b. Kakuyomu — fetching the EPISODE TEXT (a different page shape)

<!-- verified: the work page has __NEXT_DATA__, the episode page does NOT — the fetch that works is id="content"/episodeBody -->
The `__NEXT_DATA__` decode above works for the **work** page (metadata, episode list). It does **not**
work on an individual **episode** page — that page carries no `__NEXT_DATA__`, so the regex returns
`None` and `json.loads(None)` blows up. Fetch the chapter body from the rendered HTML instead: the
story text sits in the element with `id="content"` (and the `episodeBody` structure). A plain `curl`
with a normal browser UA returns 200.

Flow that works end to end:
1. Decode the **work** page's `__NEXT_DATA__` to get every `Episode:<id>` and its `title` (the chapter
   list).
2. For each episode id, fetch `https://kakuyomu.jp/works/<workId>/episodes/<epId>` and extract the
   text from `id="content"`.
3. Strip the author's promos/afterword (see the raw-cleaning step; on Kakuyomu these often attach
   **inside** a paragraph, not as their own paragraph — a paragraph-only filter misses them).

Verify one episode end to end before pulling all of them: a healthy JP episode was ~2,600 chars of
clean prose, 0 empty. Count the fetched episodes against `publicEpisodeCount` before translating.

## 2c. Syosetu — the text page has a different shape again (and 短編 has no TOC)

<!-- verified: the episode count read off the work page was the RECOMMENDATION box's, not the work's; and /ncode/1/ 404s for a 短編 -->
Syosetu's rendered work page is **not** parseable the way Kakuyomu's is. Three traps:

1. **A 短編 (one-shot) has no table of contents and no chapter URLs.** `https://ncode.syosetu.com/<ncode>/1/`
   returns **404** — the whole story is on the work page itself. Detect the shape first: the page
   carries a `1話完結` tag and its `og:description`/genre block lists `短編`. If it is a 短編, fetch
   the work page and take the body from there; do not loop over chapter URLs that do not exist.
2. **The episode count you scrape off the page is probably not this work's.** The work page embeds a
   large recommendation/"other works" block, and a blanket `全(\d+)エピソード` regex happily matches a
   *recommended* novel's count (172, 578, 112 — three different wrong numbers from the same page).
   Take the count only from the block that also carries this work's own title/author, or better,
   take it from the Syosetu JSON API (`general_all_no`), which is per-work by construction.
3. **The body is bounded by two class names, and everything outside them is junk.** Extract only the
   content div, and cut the page at the recommendation block before parsing:
   - body: `<div class="js-novel-text p-novel__text">…</div>` (the real story)
   - **exclude** `js-novel-text p-novel__text--preface` (a `※…受賞につき、書籍化企画進行中` award/print notice)
     and `…--afterword`
   - end-of-content sentinel: the next `p-recommend` marker
   Also strip the site furniture that lands inside the extraction: the placement-notice lines
   (`※「…」受賞につき…`, `※書籍版では内容が大幅に加筆されています`), the copyright disclaimer (`特に記載なき場合…`,
   `作者以外の方による…`), the Google Analytics `dataLayer`/`gtag` script text, and the mobile action
   row (`作者マイページ`, `誤字報告`, `情報提供`, `Tweet`, `LINEで送る`, `コピー`, `+注意+`).
   Verify the cut by asserting the text **starts** on the first real sentence and **ends** on the
   story's closing line, and that `p-recommend`/`作者マイページ`/`dataLayer` all count 0.

A useful cross-check when the work page is confusing: the row of "other works" cards on a Syosetu
page can be mistaken for the work's own chapters, so confirm any chapter title you extract actually
appears in the body you captured.

### A multi-page scraper that fetches ONE page reports success — verify the fetched count

<!-- verified: a 147-episode Syosetu work was harvested as 147 files, but the scraper had only read
page 1 (100 episodes); episodes 101-147 were fetched separately by hand -->
Seen on a novel >100 episodes: the harvester walked `?p=1` only, yet its log read `SELESAI` with a
plausible count, so nothing looked wrong. **The work page lists ~100 rows per page**, so any harvest
of a longer work must loop `?p=1,2,3…` until a page yields fewer rows than the page size, and then
assert `len(fetched) == general_all_no` from the JSON API. If they disagree, do NOT proceed — the
scraper stopped early. Do this check per work; the silent short-read is the failure shape, not a
crash. Re-fetch the missing range and merge (`staging/<slug>-tambahan.json`) before translating, and
re-count after the merge.

## The SAME title is often THREE works — settle which one the user means first

<!-- verified: one romaji title resolved to a web novel on Syosetu, a print LN on PASH! Books
     (4 volumes), and a manga adaptation in the same magazine — three different works, one name -->
A Japanese title can exist as, simultaneously and independently:

- the **WEB NOVEL** (Syosetu / Kakuyomu) — the author's own free upload, often the *original* and
  usually the longest (100s of short episodes);
- the **PRINT LIGHT NOVEL** (a bunko/imprint edition) — rewritten, condensed, longer chapters, its
  own volume count, and usually *not* free anywhere;
- the **MANGA ADAPTATION** (a different magazine, different author credit for the art).

A search returns all three mixed together, and the manga's chapter numbering looks like a novel's.
Decide which the user wants **before** searching for a raw, and say which one you found:
- the manga is credited to `漫画：<artist>` (or an author+artist pair) — that credit is the tell;
- the print LN carries an **imprint name** in the search result (`PASH!ブックス`, `角川スニーカー文庫`, …)
  plus a price; the web novel carries a platform URL and no price.
- **The volume count answers a DIFFERENT question per work.** "Berapa volume?" for the web novel is
  meaningless (it has episodes, not volumes — see the `章` note below); it is only answerable for the
  print LN. Do not answer the volume question from the web raw, and do not let the web raw's episode
  count stand in for volumes.

### The imprint's own series page is the volume-count witness when RanobeDB is empty

<!-- verified: RanobeDB had no series row for a web-novel-origin work; the publisher's series page
     listed volumes 1-4 with release dates, prices and per-volume ISBNs -->
Web-novel-origin works are often absent from RanobeDB (they are not catalogued as print series there),
so the "Proving a work's TOTAL volume count" route in SKILL.md comes up empty. The publisher's own
series page is then the authority and it is machine-readable in practice:

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
curl -sL --max-time 40 -A "$UA" "https://<imprint>.jp/series/<slug>/" -o /tmp/s.html
# the series page lists every volume title with its release date, price and ISBN, e.g.
#   <title>４  2026年08月07日発売  定価：870円＋税  978-4-391-16...
```

Look for the JP volume-number suffix (`…３`, `…４`), `発売` dates, `定価`, and ISBNs. Grep for the
volume-title suffix rather than a naive `1巻`/`第1巻` (imprints often write the number as a trailing
full-width digit in the title, not as `巻`). Also check the **manga** volume list separately — the
same imprint or a sister site lists those, and a `（コミック）` filename marker means the manga, not
the novel.

### A print edition that EXISTS and is still on sale has no free raw — "belum ada yang nge-rip" is the answer, not a failed search

<!-- verified: a work with a live 124-episode web raw AND 4 print volumes at an imprint; Nyaa had only
the MANGA vol 1, Anna's Archive returned 0 bytes (Cloudflare), a raw-index site was a Cloudflare wall,
and every one of ~8 queries returned manga pages — zero print-LN results -->
When the user says "cari light novel nya dong yg gratis" for a work whose print edition exists, run the
search honestly and then **say which of these it is** rather than reporting an empty result:

- **A print LN that is still being published and still on sale has no free raw.** Fan rips lag the
  release by roughly 1-2 years and mostly exist for the big imprints (Kadokawa, GA Bunko, Dengeki);
  a small imprint (PASH!ブックス / 主婦と生活社, HJ文庫, etc.) is ripped far less often. A volume
  released this year is simply not out there yet — say so plainly instead of implying your search
  was weak. This is the same finding as the SKILL.md print-origin rule ("do not keep hunting for a
  raw that cannot be there"), applied after the search rather than before it.
- **Know the real sources before declaring there is none**, because the user will ask ("orang kalo ga
  beli dapet raw LN dari mana?"): torrent indexes (Nyaa `Literature - Raw`, see §2f), Anna's Archive
  / Libgen ebook scans, a purchase-then-DeDRM route (BookWalker / honto / Kindle — still a *purchase*),
  and invite-only Discord/Telegram raw dumps (unreachable from here — say so rather than pretending).
- **The web raw covers the SAME story, so the missing print raw is not a blocker.** A print LN is the
  *rewritten* edition of its web novel (see the print-vs-web rules in SKILL.md) — the free 124-episode
  web raw carries the complete story, minus the illustrations and the editor's rewrite. Say that
  explicitly so the user can decide: "the story is complete from the web raw; what the print edition
  adds is illustrations and polish." Do not let "no print raw" read as "we cannot do this novel".
- **Do not offer to grab the publisher's `試し読み` (free preview) as the raw.** It is a marketing
  excerpt of one volume, not the book; it would produce a mangled partial shelf entry.

### Sweep order for a title with no web raw — and how to prove it is licensed, not merely unfound

<!-- verified: a publisher-original LN (OVERLAP Bunko, 3 vols) returned 0 hits on Syosetu, Kakuyomu,
     ruidrive, Nyaa and sukebei; `bookwalker.jp/search/?word=<JP title>` resolved it in one request
     with imprint + volume list + author from the paid listings. -->

Run the routes in this order and stop at the first hit; the point is to reach a *verdict* fast, not
to keep trying things:

1. **Syosetu API** — use `word=`, NOT `keyword=`. `keyword=` silently ignores the term and returns
   unrelated top hits (a bogus `allcount: 1254491`); `word=` returns the true count, where
   `allcount: 0` is a real answer.
2. **Kakuyomu search** — a hit on a shared trope word (幼なじみ, 転生, …) is usually a DIFFERENT
   novel; compare the actual returned title, never the keyword count.
3. **ruidrive / human-ID aggregators** — `<blog>/feeds/posts/default?q=<slug>&alt=json` (also try the
   JP title). `0` entries = absent under that name, not absent from the world.
4. **Nyaa / sukebei** with the JP title (§2f) — `0` results is normal for a new or small-imprint LN.
5. **ranobedb / NovelUpdates** — metadata only; a miss there is not evidence either way.

**Then confirm the work's identity on a PAID store, not a free one: `bookwalker.jp/search/?word=<JP title>`.**
It answers for titles that exist only as paid editions, and the search HTML hands you the three facts
that make the report actionable:

- the **publisher imprint** — `オーバーラップ文庫`, `MF文庫J`, `GA文庫`, `角川スニーカー文庫` …
- the **volume list** — titles ending in a bare volume number (`… 1`, `… 2`, `… 3`)
- the **author/illustrator** — `著者-<name>` anchors

That turns "tidak ketemu" into a final answer: *licensed by <imprint>, N volumes, author <name>, no
free raw anywhere → queued.* Amazon JP also lists these but frequently connection-resets scripted
fetches; BookWalker is the one that stays reachable. **Report the verdict (imprint + volume count +
author + sources checked), never the dead-end sweep** — the sweep is not a workflow to hand back.

### A web raw's own structure is `章` (parts), not volumes — and it is ONGOING more often than not

<!-- verified: a 124-episode Syosetu work carried 一章…九章 headings (9 parts), with 四章 marked
     「第一部最終話」 and a trailing 九章 epilogue — no volume structure at all -->
Read the chapter-list headings before mapping the work to the archive's volume column. A Syosetu work
commonly groups its episodes under `一章`/`二章`/`三章` ("part"/chapter-of-the-book) headings, with
trailing `章エピローグ` rows and a `第一部最終話` marker at the end of the first book-part. None of
that is a *volume*: the print edition's volumes do not correspond to `章` either (print is rewritten
and condensed, see the volume-vs-web note in SKILL.md).

So when the work is a live web novel:
- report the episode count and the `章` count as **facts about the web raw**, and say the volume
  split is the print edition's and not derivable from the web text;
- check the work's status (`連載中` = ongoing) — an ongoing work means the raw will keep growing, so
  the honest shelf label is `Bab N` per the archive rule, and say plainly that later episodes are
  not yet written;
- if the user later supplies a print volume count, treat it as a *separate* axis and do not bucket
  web episodes into it (same rule as the print-vs-web reissue case in SKILL.md).

## 3. Record the result

A completed web novel reports its own end: `publication_status`/last-episode date plus a final
episode titled `最終話` (and often a `完結` marker). Say explicitly whether the work is finished or
ongoing — it decides how much text there is to translate in one sitting, and it is the first thing
the user wants to know.

Keep the platform URL, work id, author handle, episode count, and the raw JP synopsis in the
project note next to the other pipeline steps, so the translation run does not have to re-derive any
of it.

## 4. Legal/„effort" framing the user cares about

A web-novel raw is the author's own free upload — the same category as the original PDF raws the
user already supplies. It is *not* an aggregator scrape, and that distinction matters in this
project (the MTL workstream exists precisely so the archive is not "nyolong semua"). Say which it is
when reporting, so the provenance is on the record.

## 2d. Do NOT scrape a third-party translation site for its "API" — the volume list is a FACT, the chapter text is a COPYRIGHTED WORK

<!-- verified: the user found a human-translation blogspot with a full Volume 1/2/3 table of contents and asked to pull from it ("ada apinya keknya sih") -->

When hunting for a work, a **translation blog / aggregator will often surface first** and look like a
gift: it carries a hand-written table of contents with real `Volume 1 / Prolog / Chapter 1-7 / Epilog /
Short Story` structure, which is exactly the information the official sites do NOT publish. Treat it as
two separate things, with opposite rules:

- **INFORMATION (structure, volume names, release dates, chapter list) — read it, use it, cite it.**
  This is often the only public source for a volume split. Getting the real structure from a translator's
  ToC is legitimate research.
- **KARYA (the translated chapter text, or the chapter bodies behind its endpoints) — never take it.**

The distinction is not merely legal — for THIS project it is a project rule. The MTL workstream exists
so the archive is not "nyolong semua" (see §4 and the SKILL.md carve-out). A human translation is
**someone else's work**, which puts it squarely under the **third-party / harvested-content** rule:
quarantine, report, and wait for explicit approval — the "MTL that is provably perfect goes straight to
the main DB" exception does **not** apply. So when the user proposes pulling from such a site:

1. **Say what taking it would actually cost, in this order:** (a) it is another person's translation,
   not our MTL; (b) many of these sites carry an explicit `Dilarang Copy Terjemahan Dari Sini` notice;
   (c) their chapter numbering is the **PRINT** edition's (19 chapters over 3 volumes) while our web raw
   has ~400 episodes — mixing them produces duplicates, not a longer book; (d) the print version is the
   paid BookWalker/DMM product, i.e. the scraper would be pulling a paid edition.
2. **Then give the better option, because there usually is one:** we already hold the free official web
   raw. Taking less text from a worse source while removing our clean provenance is a straight loss. Say
   that plainly rather than leaving it as a judgement call.

Confirm which edition a candidate site holds by its **own `Source:` line** (e.g. `Raw Bookwalker` = the
print book) and by the chapter count vs the web episode count. A 19-chapter "complete" listing against a
397-episode web novel is the print edition, full stop — do not assume it is a mirror of the web text.

## 2e. Safelink aggregators: the gate is theatre — read the volume page's HTML for the mirrors

<!-- verified: a ruidrive.com page presented a 6-step "click Continue, wait for countdown" safelink
     tutorial; the real Google-Drive/Mega/MediaFire/Terabox links sat in plain hrefs on the volume page -->
A **safelink** aggregator (ruidrive, ruisafe, ouo.io, linkvertise, work.ink) dresses a download behind
layered "Continue" buttons and countdowns. Two facts make the gate irrelevant:

1. **The landing/index page usually carries only the safelink anchor.** The mirrors live on the
   **detail/volume** page (`...-volume-1.html`). Fetch THAT page, then grep every absolute URL:
   ```bash
   UA="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Mobile Safari/537.36"
   curl -sL --max-time 40 -A "$UA" "<url-volume-1>" -o /tmp/vol.html
   grep -oE 'https?://[^\s"'\''<>]+' /tmp/vol.html | sort -u | \
     grep -iE 'drive\.google|usercontent|mega\.nz|mediafire|terabox|drop\.download|icedrive'
   ```
   The mirrors appear as plain `href` values (`drive.google.com/file/d/<ID>/view`,
   `mega.nz/file/<ID>#<key>`, `mediafire.com/file/<key>/<name>/file`, `<n>terabox.com/s/<ID>`,
   `drop.download/<ID>`). Download straight from them; never load the safelink.
2. **The artifact is one RAR per volume containing a PDF** (+ `Readmore.txt`, `Kunjungi <site>.url`),
   `Encrypted = -`. That PDF is still a scan → it needs OCR/`pdftotext` before the MTL pipeline, unlike
   the already-textual EPUB. (One EPUB chapter can equal several archive chapters — see
   `references/epub-import.md`.)

### Enumerate a safelink blog's volumes from BOTH its RSS feed and its site-search — each one drops a different part

<!-- verified twice, in opposite directions: (a) `?q=<title>&max-results=30` surfaced volumes 1-6 and 8
     but silently omitted volume 7; (b) on another run the RSS feed carried volumes 6-8 but NOT 1-5,
     because the feed is newest-first and the older volumes had already fallen out of its window -->
Neither index is complete, and they fail in **opposite directions**: the on-site search is paginated
and stops short mid-series, while the Atom/RSS feed is newest-first and drops the **oldest** volumes
once the blog has enough newer posts. Run BOTH and take the union:

```bash
BLOG="https://<blog>"
# (1) site search — paginated; follow the next-page link until it stops
curl -sL --max-time 45 -A "$UA" "$BLOG/search?q=<romaji+title>&max-results=30" -o /tmp/s.html
# (2) Atom/RSS feed — newest-first window
curl -sL --max-time 45 -A "$UA" "$BLOG/feeds/posts/default?alt=rss&max-results=500" -o /tmp/f.xml
grep -oE '<title>[^<]*</title>|<link>[^<]*</link>' /tmp/f.xml | grep -iE '<your romaji title>'
```

Each `<item>` carries the post `<title>` and the absolute post `<link>`; regex the `<item>` blocks and
filter on the work's name. The union then gives you every volume post, including **per-volume
ILUSTRASI posts** (a separate post type on these blogs — collect them too, they are the illustration
asset source) and the site's own naming variants (`volume-1-<slug>.html` vs
`light-novel-<slug>-volume-6.html` — the URL shape is NOT uniform across volumes, so match on the
post TITLE, not a URL pattern).

**A volume the blog never posted is not recoverable from either index** — before reporting a gap,
compare the union against the work's real volume count and say which volumes are absent from the
source rather than implying your enumeration missed them. Verify you have a contiguous 1..N (or an
explained hole) before reporting coverage.

### Mirror quirks that cost a re-download
- **Google Drive small files**: `drive.google.com/uc?export=download&id=<ID>` or
  `drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t` returns the file directly,
  **but a truncated transfer yields a valid-looking RAR whose members extract to 0 bytes**. ALWAYS
  `7z l file.rar` (lists members + uncompressed sizes) and compare against the extracted sizes; a
  mismatch = cut short → fetch from a different mirror, never "repair" the archive.
- **`7z` cannot extract every RAR5 — when members come out 0 bytes, retry with `unrar`.**
  <!-- verified: `7z x` on three RAR5 archives reported `ERROR: Unsupported Method` for every member and
       wrote 0-byte files, while `unrar x -o+` extracted all three cleanly. `7z l` listed the members fine,
       so the listing looked healthy and only the extraction failed. -->
  A RAR5 whose header reads `Method = v6:8M:m0:m3` is beyond `7z`'s RAR decoder. The tell is exactly the
  shape that also looks like a truncated download — 0-byte extracted members — so distinguish them
  **before** re-downloading: if `7z l` lists correct uncompressed sizes but `7z x` yields 0 bytes, the
  archive is fine and the extractor is the problem. Use `unrar` (`unrar x -o+ <file> <outdir>/`), and
  only treat 0-byte output as a bad transfer when the listed sizes are also wrong. This maps to the
  Google-Drive truncation case above — same symptom, opposite cause.
- **MediaFire**: the page embeds the download in an anchor with `aria-label="Download file"` whose
  `href` ends `?dkey=<key>` — extract that `dkey` and fetch it. Fetching the `/file/...` page itself
  returns **HTML**, so assert `%{content_type}` is `application/octet-stream` (or `file` says
  RAR/EPUB/PDF), not merely that bytes arrived. A `200` + `text/html` is the classic trap.
  **A second, simpler route works on the same page and needs no `dkey`:** the volume page's HTML also
  carries an absolute direct link of the form `https://download<NNNN>.mediafire.com/<opaque>` (grep the
  page for `href="(https://download[^"]+)"`). Fetch it with `curl -L` **plus `-e <the mediafire
  page url>`** (the referer is required) and it returns the archive directly. Verified on three
  volumes in one session: all three returned HTTP 200 with real byte counts (2.5/2.4/4.7 MB), no
  `dkey` dance. Prefer whichever of the two the page hands you first; keep the other as fallback.
- **MEGA can refuse with EBLOCKED** — `megadl` (megatools) fails as
  `API call 'g' failed: Server returned error EBLOCKED` when the egress IP is quota/geo-blocked, which
  is common from a datacenter/phone-network IP. **Do not retry MEGA and do not report the volume as
  unavailable** — pivot to another mirror. A translation blog's mirror block typically offers per-volume
  **several Google Drive ids alongside MEGA and MediaFire**, and GDrive `uc?export=download&id=<ID>`
  fetched the same file fine in the same session that MEGA blocked. Verified: one volume's three
  distinct GDrive ids all returned an identical 9.6 MB PDF (same `md5`), so any one is enough — assert
  `%PDF` as the first bytes rather than trusting the size.
- **Pick the mirror whose content-type is a real archive**; verify with `file` + `7z l` before use.
- **A translation blog's per-volume mirror block is uniform** — the same set (2 MediaFire + 1 MEGA + N
  GDrive) repeats for every volume page, with only the ids differing. Grep the volume page for
  `mediafire.com/file/`, `mega.nz/file/`, and `drive.google.com/file/d/` once and loop the ids; do not
  hand-copy links from the rendered page.

**Rules 2d still apply to the TEXT.** These sites often bundle a human translation, or their PDF is a
scanned paid volume — read structure/metadata freely, but treat a translated manuscript as
third-party content (quarantine + user approval), never as our own MTL output.

## 2f. Print-LN raws: Nyaa's `Literature - Raw` category — and the anime/manga that drown the search

<!-- verified: a search for one LN title returned 75 results, of which ~73 were the anime
      (SubsPlease/Erai-raws/ASW) and manga, and exactly one was the novel -->
When the work is a **print light novel** (a bunko volume, no live web raw), the scan route is a
torrent index. Nyaa carries a dedicated literature category and it is the one to filter on:

```bash
curl -sL --compressed -A "$UA" "https://nyaa.si/?f=0&c=0_0&q=<romaji+title>&s=seeders&o=desc" -o /tmp/n.html
```

- **Filter on the category cell, not the title.** Read each result row's category — the LN uploads
  carry `Literature - Raw`, while everything else in the hit list is `Anime - English-translated`,
  `Anime - Raw`, or `Literature - Manga`. A title-only match returns ~95% anime for any novel that
  got an anime adaptation, because the anime is titled with the same romaji.
- **`[Novel]` in the uploader's own filename is the other reliable signal** (`[Novel] <JP title>
  第01-02巻 [<romaji> vol 01-02]`) — the anime uploads are named `[SubsPlease] <name> - 12 (1080p)`.
- **Carry the volume range into the report.** The upload's own filename states exactly which volumes
  it covers (`第01-02巻` = volumes 1-2), which is what decides whether the route fills your gap.
  A `[Comic]` upload of the same work is the **manga** adaptation — same title, wrong medium.
- **The `Information` field names the upstream** (often `https://dlraw.net`). That site is a
  dedicated LN-raw index and is worth checking directly for a fuller volume range.

Fetching a torrent is out of scope here; the point of this step is to establish *whether* the print
raw exists, over which volumes, and from which upstream — then report it before spending a download.

## Cover & metadata for web novels

RanobeDB has no cover for a web novel and `books[]` may be empty. If the work was later released in
print, the cover exists on Amazon JP / BookWalker — search there. Otherwise say the cover is
unavailable rather than substituting one. For the normalisation + dual-write + probe steps, follow
`mtl-cover-and-assets.md` unchanged.
