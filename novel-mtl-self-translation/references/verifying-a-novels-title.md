# Verifying a novel's true title (and an offered "ATL") before extracting its raw

When the user hands you a title and asks "coba bener apa engga" (check if it's right) before
giving you the raw PDF/TXT, this is the order that settles it fast.

## Order of sources

1. **RanobeDB API — no key, JSON.** Search by romaji, then by the JP title:
   `GET https://ranobedb.org/api/v0/series?q=<title>&limit=5` → list; `GET /api/v0/series/<id>` → detail.
   Detail fields worth having: `title_orig` (JP), `romaji_orig`, `aliases`, `staff[]` (author + artist
   with both JP name and romaji), `publishers[]` (publisher + imprint), `publication_status`,
   `start_date`, `books[]` (per volume: JP title, release date, cover `image.filename`).
   A romaji match scoring 1.0 is your confirmation.
2. The raw PDF's own `pdfinfo` Title (see the main SKILL) — the translator's/publisher's own string.
3. Google Books `?q=isbn:<isbn>` — but **it 429s on a shared IP**; treat a 429 as unavailable, not
   as "no such book", and move on.
4. Web search — use it only to corroborate; a fan-translation group page is not an authority.
   NovelUpdates 403s to plain fetches; Anime-Planet/MangaUpdates are hit-or-miss.

## "ATL" offered by the user can be a fan title, not an official alias

A title the user offers as "ATL" (alternate title) may be the *fan translation group's* own label,
not an official alias. Verified case: the JP romaji resolved cleanly on RanobeDB, while the offered
English ATL appeared on **none** of RanobeDB `aliases`, MangaUpdates, AniList, MAL, Google Books, or
six distinct web queries.

- Report "not found" honestly — do not pick the closest match to please the user.
- Then go prove it a different way: **open the raw and read its own title page / PDF Title metadata.**
  That is what actually settles whether the offered name belongs to this book. In the verified case the
  PDF's Title was the translator's own English rendering of the very same JP work — so the user's ATL
  *was* "right" as a human label even though it is not an official alias. Both facts belong in the report.
- Watch for a title whose "ATL" is actually the name of a **character** plus a theme word (the user's
  "Spring Idol Romance: Himeno Shizuku" — Himeno Shizuku is the heroine). That shape is a tell that it
  is a fan label, not an official alias.

## "Masih ongoing atau udah tamat?" — a SEPARATE question from the volume count

When the user hands over a volume and asks for the status, **do not infer it from the volume count.**
A work with one volume is very often still running; "only 1 volume" and "finished" are independent
facts. RanobeDB's detail object already carries the answer — read it rather than guessing:

- `publication_status` is the authoritative string (`ongoing` / `completed`).
- `start_date` + an **open-ended run** (`Original run: 2025-03-24 – present`) or a
  `latest_release` equal to the first volume's date is the tell for ongoing.

Three further witnesses, in the order that usually settles a disagreement:

1. **A scheduled future release date means ongoing, not finished.** A retailer series page listing a
   second date past today (volume 1 at one date, a second entry months later) is the clearest signal.
   Check for it *before* concluding anything from `books[]` having length 1.
2. **A reader's "will a next volume come out?" is strong evidence of ongoing.** Publisher product
   pages carry dated reader reviews, and a dateless plea like `続刊は出るんですかね…` ("is a next
   volume coming?") dated *after* the latest release means no further volume was announced. This is a
   legitimate second witness when the machine-readable pages are blocked or disagree.
3. **A retailer 403 is not the end of the check** — fall back to `curl` + a text strip, then to the
   publisher's own product page (see `blocked-page-recovery`). The publisher page normally names the
   imprint and carries those dated reviews.

**Report the status honestly and let it change the shelf row.** A one-volume ongoing work goes in
with `status = Ongoing` and a `detail_status` naming the volume ("Volume 1 — seri masih berjalan").
Never label an ongoing work `Tamat` to make the shelf look complete; the user's standing rule is to
state the chapter/volume count truthfully, and a wrong `Tamat` is exactly the dishonesty that rule
forbids.

## What to write down

Persist author / author_jp / illustrator / publisher / status / year / volumes / JP title into the
meta JSON next to the translation output. An illustrator found here is a win — the previously
translated novel had it empty because no source carried it, and this one did.
