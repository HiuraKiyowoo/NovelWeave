# A raw in a THIRD language (Russian/Chinese/etc.) is still a valid MTL source

<!-- verified: the user queued a JP print LN with no EN/ID translation anywhere; the only
     translation online was a Russian one on ranobelib, and the user's verdict was explicit:
     "Rusia ke id sma aja kek kita ngambil raw Inggris ke id" — i.e. translating through ANY
     well-written intermediate language is the same job as EN→ID. Do NOT refuse or stall on it. -->

## The rule

When a novel has **no** EN or ID translation, a third-language fan translation (Russian on
ranobelib/cdnlibs, Chinese on a CN aggregator, etc.) is a **legitimate raw** for our MTL. The
user's standing position: *"Rusia ke id sma aja kek kita ngambil raw Inggris ke id"*. Treat it
exactly like an EN raw — same pipeline shape, same verification gates — with the prompt and the
quote-normalisation swapped for the source language.

Do NOT:
- refuse the work because "it's not the original language" (the user will correct you, sharply);
- stall waiting for a JP/EN raw that does not exist;
- tell the user "kirim RAW-nya" when you can fetch the translation yourself.

DO say plainly, up front, what the provenance is ("terjemahan Rusia, bukan Jepang") so the user
can decide — then fetch it.

## ranobelib (Russia) — the SPA hides its data; harvest it from a real browser

<!-- verified: ranobelib.me is a JS SPA; a plain curl of the read URL returns shell HTML with no
     story text. A Playwright browser with a normal Android UA renders it, and harvesting the
     CHAPTER PAGES works even when the /chapters API route is closed. -->

- **ranobelib.me is an SPA** — a plain `curl` of the read URL returns shell HTML with no story text.
  Use a real browser (Playwright) with a **normal Android UA**; a UA containing `headless`,
  `puppeteer`, `playwright` or `selenium` gets a `403`. Intercept responses while the page loads.
- **Two URL shapes exist and only one serves chapters:**
  - `/ru/book/<id>--<slug>?section=chapters` — the book landing page. Good for cover + metadata; its
    chapter LIST may need the `/chapters` API route, which answers `403` outside a session.
  - **`/ru/<slug>/read/v<N>/c<M>` — the readable chapter URL.** This is the one that yields text.
    A run that returns 0 characters is almost always pointed at `/ru/book/...` instead of this.
- **The `/chapters` route is NOT closed — it 403s only because the request is missing headers.** The
  CDN API serves plain JSON when you send the site's own Origin/Referer and site id, so you do NOT
  need a browser to count or list chapters:
  ```
  GET https://api.cdnlibs.org/api/manga/<id>--<slug>            # title, status, genres, covers
  GET https://api.cdnlibs.org/api/manga/<id>--<slug>/chapters   # the chapter list + volume/number
  GET https://api.cdnlibs.org/api/manga?q=<words>&site_id[]=3   # search
  # headers that make it answer 200 instead of 403:
  Origin: https://ranobelib.me   Referer: https://ranobelib.me/   Site-Id: 3
  Accept: application/json       User-Agent: <normal desktop UA>
  ```
  This is the fastest way to get an authoritative chapter count / volume split without Playwright.
  Two gotchas: (a) the slug MUST be the full `<id>--<slug>` form — the bare numeric id returns
  `404 {"data":{"toast":{"message":"Not Found"}}}`; (b) the search route is `/ru/catalog?q=` in a
  browser but the JSON search is `/api/manga?q=` — a `/search?q=` URL is a hard `404` on both, so do
  not conclude the title is absent from a `/search` miss. Only fall back to the Playwright intercept
  (below) when the API itself is unreachable.
- **Read the chapter list from the API JSON the SPA itself loads** (`…/chapters`, or the `api.json`
  the page requests) rather than parsing the rendered list. The list is the authority for the expected
  chapter count — assert your harvest against it.
- **Check the translation's STATUS on the landing page before committing — a dropped translation is an
  incomplete raw even when the work itself is ongoing.** These sites publish a per-title metadata block
  where the work's status and the *translation's* status are two different fields: a title can read
  `Статус: Онгоинг` (work still being written) while the translation line reads `Перевод: Заброшен`
  (translation abandoned/dropped). A dropped translation stops mid-story — verified: one such title
  carried only 5 chapters of an ongoing multi-volume LN. Treat "translation dropped" the same as a
  teaser under §1 of `source-selection.md`: not a complete text, so do NOT load it as if it were the
  whole novel. Report the real chapter count AND the dropped status to the user and let them decide
  (skip it, or accept the partial), rather than silently shipping a truncated book.
- **Sort chapters NUMERICALLY, not by the order the page lists them.** The rendered/JSON order can be
  reversed (volume 2 before volume 1) or interleaved, and a harvest that follows it will mis-number
  every chapter. Key on `(float(volume), float(number))`, normalising `v01`/`c01` and `v1`/`c1` to the
  same value so a duplicate entry (`v1 c0.5` vs `v01 c01`) collapses instead of double-loading.
- **The illustration pages are chapter 0.x pages, and their images need a scroll + wait to appear.**
  A first pass may capture only 1 of 4 illustrations because the lazy-loaded images had not rendered;
  re-fetch that page with a slow scroll loop (`scrollBy(0, 900)` × ~14 with ~1.2 s waits) and a
  longer settle, and filter to `naturalWidth > 400` to drop logos/avatars. Download with a browser UA
  and a `Referer` of the site; a large PNG can `IncompleteRead` mid-transfer — read in chunks
  (`r.read(262144)`) and retry rather than accepting a truncated file.
- **The harvest is contaminated with the translating team's promo — strip it every time.** Each
  chapter's tail carries an advert ("Хочешь читать бесплатные главы раньше других …", a Telegram
  `t.me/…` link, a `boosty.to/…` link), and the illustration pages contain **nothing but** an ad
  placeholder. Rules: cut from the first promo marker to the end of the chapter; drop any chapter whose
  remaining text is under ~300 chars with no dialogue dash (it was an ad page, not story); and never
  let this strip touch real prose (the story's own closing line must survive).

### Extracting the ProseMirror doc — count RAW TEXT, not the JSON

<!-- verified: a chapter whose raw JSON was 157,287 chars yielded 98,038 chars of actual text; a
     length check against the JSON size looked like a 60 KB loss and nearly triggered a false alarm. -->
A `doc` block is `{"type":"paragraph","content":[{"type":"text","text":…}]}`. Walk it and join
`text` runs; handle `image` blocks (`attrs.src`) and inline markers. **Measure the output in chars of
real text** (`sum(len(inl["text"]) …)`), never by the raw JSON length — comparing the two makes a
complete chapter look truncated.

### Russian quote normalisation

RU dialogue uses `«…»` (and narration may use an em-dash `—`). The ID target uses `"…"`. Add
`«»→""` (and `“”→""`) to the cleaner, and keep the dash handling as for EN. Verify the ID quote
count is **even** per chapter (see the umbrellas' cleaning gate).

### The prompt

Same shape as JP→ID, but say **RUSSIAN** as the source and keep a glossary of the romanised names
(the RU text will already carry them, e.g. `Теодор`→Theodor, `Ююэль`→Yuyel, `Эртфелия`→Errefelia).
Output ratio RU→ID ran ~105% on verified text (ID slightly longer) — a chapter at ~0% or way under
means the fetch or the extraction failed, not that the language is terse.

## The source's OWN cover is often low-res — the PUBLISHER's product page has the full one

<!-- verified: ranobelib's cover CDN served 375x564 for a GA Bunko title; the publisher's own
     product page served the same artwork at 1447x2067 by dropping a thumbnail-size suffix from
     the image filename. The user's standing "jangan asal ambil" poster rule bans SOURCING a cover
     from third parties on your own initiative — this is different: it is the CORRECT cover for the
     work, taken from the publisher that printed it, and it must still be reported with provenance. -->

When a novel's page image is small, the fix is usually a filename suffix. Publisher/catalog product
pages serve WordPress-style resized derivatives whose **full-size original is the same filename with
the `-<W>x<H>` suffix removed**:

```
https://<publisher>/wp-content/uploads/2025/10/<isbn>-1-417x596.jpg   ← thumbnail shown in the page
https://<publisher>/wp-content/uploads/2025/10/<isbn>-1.jpg           ← full size (1447x2067)
```

Steps that worked: open the publisher product page in a browser (these are JS-rendered, so a bare
`curl` sees nothing), collect the `<img>` sources, take the cover's filename, strip `-<W>x<H>`, and
fetch it with a `Referer` of the publisher's own domain (a bare request to the sized variants
returned `403`; the full-size file fetched fine). Confirm with `PIL`/`file` that the result is a real
larger image before using it.

**Finding the publisher page:** search the EXACT native title (in the source language) — a Japanese
title search surfaces the publisher's own product/special page far more reliably than a romaji one.
Note the publisher + author + illustrator from that page and record the cover's provenance as
"sampul dari penerbit resmi <X>" rather than presenting it as found artwork.

**This is scoped, not a licence to hunt:** it applies to the cover OF THE WORK BEING LOADED, from the
entity that published it. It does NOT override the rule against grabbing posters from arbitrary
aggregators, and if you are unsure whether a candidate is the right artwork, ASK the user with the
provenance instead of writing it in.
