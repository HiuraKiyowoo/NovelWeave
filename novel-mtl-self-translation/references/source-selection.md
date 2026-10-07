# Choosing the MTL raw — language, provenance, and wrong-link traps

Applies before ANY translation run. The pipeline is fixed; *which file you feed it* is the
decision that ruins a run.

## 1. The raw must be a COMPLETE text in SOME language — any readable translation is a valid raw

Order of preference (standing): **human ID translation → official EN LN → JP raw + MTL →
any other-language fan translation + MTL**.

**A translation in a THIRD language is a perfectly valid raw. Translate it to Indonesian the
same way you would translate an English fan translation.** The user corrected this rule
directly, verbatim: *"kan klo Rusia ke id sma aja kek kita ngambil raw Inggris ke id"* —
RU→ID is no different from EN→ID; both are one intermediate hop before Indonesian. Do NOT
refuse a Russian/Spanish/Portuguese/Vietnamese/Chinese reader site as "double translation"
and do NOT lecture the user about it — that is the mistake, not the source.

- `ranobelib.me` (and same-family reader sites; URL path carries the language, e.g. `/ru/`)
  ARE usable raws. They are often the newest source for a brand-new LN that has no EN/ID
  translation yet, so refusing them can leave you with nothing.
- The ONLY hard invalidity is a source that is **not a complete text of the novel**: a teaser
  (`…続きを読む`, `試し読み` preview), a wrong work (see §2), or an empty JS shell you never
  actually extracted text from.
- Still do §2 first: read the page `<title>` + 2–3 body lines so you know WHICH language and
  WHICH novel you are holding before staging anything.
- These reader sites are JS SPAs — a bare `curl` returns an empty shell. Extract through a real
  browser instead (intercept the site's own JSON API with Playwright `page.on("response", …)`;
  the REST path will 403 but the SPA has already fetched the data — see `playwright-scraper`).

## 2. A stored "raw" link can be a different novel — verify the title first

Candidate links from memory notes or an earlier session go stale and get mis-copied. **Before
building a scraper or pipeline around a URL, fetch it and print its `<title>`;** compare against
the expected romaji/kanji title.

Observed failure mode: two ncode/slug values recorded for this novel both resolved to *other*
works (a different Syosetu ncode, a different Kakuyomu work). Shipping the pipeline would have
produced a translated novel under the wrong title. One `curl | grep <title>` is the whole cost
of avoiding it.

Also: Japanese web novels frequently have a **web version** and a **published LN version** that
diverge. If the work is a commercial LN with no free web version (check Syosetu/Kakuyomu/Alpha-
polis for the exact title), there is **no free raw** — say so and ask the user to supply a file
rather than substituting a translation.

## 3. If the novel already exists in the target language, skip MTL entirely

If the user hands over an EPUB/PDF already translated to Indonesian, or a human-ID aggregator
(Kaori, zerokaito, ruidrive) carries it, use that path (`naver-panen-sumber-blogger`) and do not
MTL. Confirming the container's own language (`content.opf` `<dc:language>` for EPUB; `<title>`
+ body for a web page) is step zero of every job.


## 4. Metadata is not guaranteed by the raw page

A chapter page may have no synopsis, or only a teaser for a different edition. Check the exact work landing page, official platform metadata, publisher series page, and a licensed catalog separately. If no trustworthy synopsis exists, leave the public field empty and report that it is unavailable; never manufacture a plot summary from a few chapter lines.

When a local Indonesian title is not the official display title, use a verified English title or romanji in the public `judul` field and keep the Indonesian wording as a private alias. Do not guess an ATL. Full rules: `title-metadata-policy.md`.

## 5. Rights are a separate gate from discoverability

A reachable raw or a translation-group mirror is not automatically publishable. Do not bypass access controls or publish a third-party translation without permission. Keep source URLs, group names, and translator credits out of public text and metadata; retain them only in a private rights/provenance manifest. See `safety-and-rights.md`.
