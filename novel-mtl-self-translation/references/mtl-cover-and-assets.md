# Cover & illustration assets for an MTL novel

Depth for step 10 of the pipeline ("resolve the cover before upserting"). The poster
is the one field where a *correct DB row* still ships a broken page, because the row
stores a **relative path** and nothing in the insert verifies the bytes exist.

## 0. The user supplies the posters — do NOT go source them yourself

<!-- verified: the user's standing correction after covers were hunted from Wikipedia/YenPress:
"kalo poster jangan asal ambil soalnya itu di ada 3 novel yg salah" -->
**Standing rule for this user: never acquire a novel's poster on your own initiative.** Do not fetch
covers from Wikipedia, YenPress, AniList, a catalog page's `og:image`, or any other third-party
source, however confident the match looks. The user's own word is *"jangan asal ambil"* — because a
plausible-but-wrong poster is worse than no poster: it sits on the shelf misrepresenting the work,
and the user has already had three novels get the wrong artwork this way.

This overrides the source ladder below. The ladder is the **technique** for the case where the user
hands you a URL (or a PDF that already contains the cover); it is NOT an invitation to search. So:

- **A poster comes from one of exactly two places: (a) a URL the user pastes, or (b) an image embedded
  in the raw file the user supplied.** Nothing else.
- **When a novel has no cover, say so and wait.** Do not fill the gap. The correct action is to note
  the novel id in the outstanding worklist (§6) and ask the user for the artwork — they have said they
  source covers by hand ("cover gua cari manual").
- **Never "fix" a missing cover by loosening a filter or generating placeholder art** — that changes a
  working feature; ask first (§6).
- If you genuinely believe an externally-found image is right, **offer it as a question with the
  provenance and let the user accept or reject** — do not write it into `cover/` first.

## 1. Where the cover comes from, in order

1. **The user's own link.** If they hand you a URL, that URL is the cover. Download it
   with a normal browser UA (a bare `curl` gets blocked by CDNs that gate on UA):
   ```bash
   curl -sL --max-time 60 -A "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36" \
        -o /tmp/cov/nu.png -w 'HTTP %{http_code} %{size_download}B %{content_type}\n' '<url>'
   ```
   Verify the download is an image and not an HTML error page (check
   `content_type` and that `Image.open` succeeds), then read the real dimensions.
   **Settle WHICH work the picture belongs to before writing it** — a URL alone does not prove it
   matches the novel. When the URL contains a provider id (an AniList CDN filename
   `…/bx<seriesId>-<hash>.jpg` carries the series id), confirm it against that provider's API and
   compare **title (romaji + native) AND author AND illustrator** to your row; a wrong-but-plausible
   poster is worse than none. A direct GraphQL query works without auth:
   ```python
   q = '{ Media(id:<seriesId>) { id title { romaji native english } format status startDate { year }
         coverImage { large } staff(perPage:4){edges{role node{name{full}}}} } }'
   # POST https://graphql.anilist.co, JSON {"query": q} — a browser UA avoids the 403 a bare one gets
   ```
   `format: NOVEL` plus matching `Story`/`Illustration` staff is the confirmation. Report it as
   verified (or explicitly unverified) rather than assuming.
   **When the raw YOU already hold contains the cover, prove the user's URL matches it by PIXEL
   DIFF — this beats any metadata lookup and needs no external API, and it is the only check that
   works when the vision tool is unavailable.** Extract the raw's own cover (PDF `pdfimages -all -p`
   page 1-2 portrait, or the EPUB's declared cover image), then compare geometry AND grey pixels:
   ```python
   from PIL import Image, ImageChops
   a = Image.open(user_poster).convert("RGB").resize((256, 364))
   b = Image.open(raw_cover).convert("RGB").resize((256, 364))
   diff = ImageChops.difference(a, b).convert("L")
   rms = (sum(x*x for x in diff.getdata()) / (256*364)) ** 0.5   # 0 = identical
   ```
   **Interpret before declaring:** RMS near 0 (verified ~2.4, i.e. re-encode/JPEG noise only) =
   the SAME artwork; RMS in the tens-to-hundreds = a different picture, do not write it. Also require
   the ratios to agree (`w/h` within ~0.01) and the unique-colour count of the 60x85 thumbnail to be
   in the thousands (a few hundred = a blank/near-solid page, not a cover). Report the RMS number as
   the evidence ("identik dengan sampul di raw, RMS 2,4") — same standard of proof the user expects
   from a text check.
   **A user link REPLACES the cover already in place — it does not add a second one.** When they
   paste a poster URL for a novel that already has an extracted cover, overwrite **both** files
   (`cover-asli/<id>.jpg` then re-run the normaliser to `cover/<id>.webp`) and re-probe the served
   path; leaving the old file behind ships the picture they rejected. On a Google-hosted image
   (`blogger.googleusercontent.com/…/s1600/name.jpeg`) the `/s<NNNN>/` path segment sets the
   delivered pixel width — raise it (e.g. `/s1600/`) to get the full-size artwork instead of a
   thumbnail, and check the `curl` download's dimensions before normalising.

   **The user's link is often a DOWNSCALED variant and the original is one substitution away — always
   try to up-size before accepting the small one.** Blogger/Googleusercontent URLs come in two shapes:
   a `/s<NNNN>/` segment (replace the number) **and** a `w<NNN>-h<NNN>` segment. The second is the one
   you meet when the link arrived through an ad-gate: `…/w494-h640/<name>.jpg`. Try, in order,
   `s2048` · `s1600` · `s1024` · `s800` · `w1200-h1554`, and keep the largest that returns a real image.
   Verified this session: `w494-h640` (494×640, ratio 0.77) → **`s2048` returned 1236×1600**, the actual
   poster. A poster that is "too small/square to be a LN cover" is a signal you are holding the
   thumbnail, not the artwork — do not ship the thumbnail, and never conclude the source only has a
   small image until you have tried the substitutions.
   **An ad-gate (`ouo.io/st/<code>/?s=<url-encoded>`) is not a wall — the real URL is IN the link.**
   `urllib.parse.unquote` the `s=` parameter and fetch that directly; there is no need to pass through
   the gate at all. The decoded URL usually points at `blogger.googleusercontent.com`, i.e. straight
   into the substitution ladder above, which is then how you get from the gated 494px thumbnail to the
   1236px poster. Watch for **spaces in the decoded filename** (`class de 2 banme 10_1.jpg`): percent-encode
   them (`%20`) before the request, or the fetch fails on a link that looks fine in a browser.
2. **The cover already inside the raw PDF.** `pdfimages -all -p <file> <out>/img` dumps
   every embedded image; the cover is page 1-2 and portrait. When a page map exists
   (`peta-ilustrasi.json`, built once while reading the PDF), it may already carry a
   `caption` string — `"Cover Novel"` on page 1 is the cover, no vision needed.
3. **An image-metadata page** (a light-novel catalog) as the fallback. Keep the source
   URL in the note so the provenance is honest. Do **not** fabricate a cover.

### When the supplied cover URL 403s: pivot to the catalog PAGE, not the image CDN

<!-- verified: one cover URL returned 403 to every direct attempt while the same artwork fetched fine from a catalog page's og:image -->
An image URL that 403s is usually not gone — the *host* is gating the referer/hotlink,
and the same artwork is embedded on a catalog page that serves it happily. Working ladder:

1. Retry with a browser UA and a `Referer` of the image's own origin — fixes some gates.
2. **Fetch the catalog/series page HTML and pull its `og:image` / `twitter:image`**
   (`<meta property="og:image" content="...">`). This is the highest-yield step: the page is
   built to be link-previewed, so its meta image is un-gated. Catalog sites with good hit rates:
   NovelList, VortexScans, Roliascan, RanobeDB, AniList (via its GraphQL `coverImage.large`).
   Search `"<exact title>" cover` to find the pages, then grep each for `og:image`.
3. Only then fall to a generic image-proxy relay — and never through one for anything the user
   relies on (see `blocked-page-recovery`: relays are MITM by construction, provenance unverifiable).
   A `wsrv.nl`/`images.weserv.nl` call for a URL that is *hotlink-gated rather than dead* just
   returns the gate's 404 back to you.

Confirm the picture you got is the right work before writing it (compare title/author against
whatever provider id you can see), and record which route produced it.

## 2b. Bulk drop-in: the user supplies MANY covers at once — automate the batch

<!-- verified: the user pasted eight cover URLs in one message, then said the rest would follow -->
The user accumulates covers and delivers them in a pile (a list of URLs, or files already saved
into `cover-asli/`). Do **not** walk the per-novel manual path eight times. Batch it:

1. Download every URL into `cover-asli/<id>.jpg` with a browser UA, in one loop; report
   per-id success/failure rather than aborting the run on the first 403, and apply the
   catalog-page pivot above to the failures only.
2. Run **one** normalise+register pass for the whole batch — `scripts/pasang-cover.py <ids…>`
   or `--semua` — which writes `cover/<id>.webp` at the measured ratio and updates the row.
3. Probe each served path for 200 + an image content-type, and re-run the hidden-novel count
   from section 6 so the reported delta ("27 → 20 sisa") is measured, not asserted.
4. Regenerate the outstanding-work list (`CATATAN/<n>-novel-butuh-cover.json`) minus the ids just
   filled, so the user's next batch is a drop-in and you never re-ask for a cover you already have.

Hand the user the exact destination filename per id (`cover-asli/1740.jpg`) — they pick covers by
browsing, not by id, so a filename-list keyed to titles is what makes their side easy.


An external page may be unreachable from the host even when the user can open it in a
browser. Report the failure plainly and name the fallbacks above rather than silently
substituting a different picture.

## 2. Normalise to the archive's ratio — measure it, do not assume 2:3

**First measure what the archive already uses.** Count the existing covers' width/height
ratios before choosing a target:

```python
ratios = []
for f in os.listdir(cover_dir):
    im = Image.open(os.path.join(cover_dir, f))
    ratios.append(im.width / im.height)
```

On the real archive **395 of 474 covers sat at ~0.70-0.71 (≈5:7), not 0.667 (2:3)**.
Forcing the new cover to 2:3 would have made it the odd one out. Match the majority.

**Resize by scaling to fill the height, then trimming a strip off the sides.** Do not
letterbox onto a canvas: a paste offset can come out **negative**, which silently crops
the picture instead of centring it, and the arithmetic still "succeeds":

```python
im = Image.open(src).convert("RGB")
w = round(im.height * target_ratio)          # scale so HEIGHT is the binding edge
im = im.resize((w, im.height), Image.LANCZOS)
if im.width > w:                             # trim the surplus, centred
    x0 = (im.width - w) // 2
    im = im.crop((x0, 0, x0 + w, im.height))
im.save(webp, "WEBP", quality=90, method=6)
im.save(jpg,  "JPEG", quality=93, optimize=True, progressive=True)
```

A 0.7047 source → 0.70 target trims ~1.5% of the width. Anything past a few percent
means the ratios are too far apart and the crop will eat artwork or the title — say so
instead of shipping it.

**Prove the crop did not cut the picture.** Read pixels down the vertical centre line
and assert they are *content*, not the canvas/filler colour:

```python
px = final.load()
warna = [px[final.width // 2, y] for y in (5, final.height // 2, final.height - 5)]
assert warna[0] != CANVAS_COLOR, "bar kosong di atas — gambar terpotong"
```

That one assertion is what distinguishes "resized" from "cropped into a bar", and it is
cheaper than re-doing the poster after the user reports it.

## 3. Write BOTH files, and probe the served one

The archive convention is a served copy plus a raw copy, in **two different directories**:

```
<project>/cover/<id>.webp        ← served by the web tier at /cover/<id>.webp
<project>/cover-asli/<id>.jpg    ← raw archive copy, NOT served (a 404 here is correct)
```

The web tier's static mount typically covers only `/cover`, so a 404 on `/cover-asli/...`
is expected for **every** novel and is not the defect. Probe the served path and check the
body is bytes, not a status code alone:

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download} %{content_type}\n' http://127.0.0.1:8100/cover/<id>.webp
# want: 200 <size> image/webp   — not: 404 4074 text/html
```

Then confirm the detail page actually references it (`grep -o 'src="/cover/[^"]*"'`), so
a correct file with a template still pointing elsewhere is caught.

**Then probe the PUBLIC hostname too, and compare the BODY bytes.** A correct file on origin can still
serve stale for days: a Cloudflare-fronted tunnel caches `/cover/*` (default 7-day TTL), so
`127.0.0.1:8100` returns the new image while the domain keeps returning the old one with
`cf-cache-status: HIT`. Both answer `200`, so only the byte size / `md5` tells them apart:

```bash
curl -s -o /tmp/l.webp -w 'local : %{size_download}\n' http://127.0.0.1:8100/cover/<id>.webp
curl -sL -o /tmp/p.webp -w 'public: %{size_download}\n' https://site.example/cover/<id>.webp
md5sum /tmp/l.webp /tmp/p.webp      # differ = stale edge copy, not a wrong file
curl -sIL https://site.example/cover/<id>.webp | grep -iE 'cf-cache-status|age|cache-control'
```

When the edge is stale and the local file is right, the fix is invalidation (purge the CF cache with a
Cache-Purge-scoped token, or serve the new bytes under a versioned filename) — and **ask the user which
route they want before changing the web tier's URL builder**, given the standing "never change what
already works" rule. Full diagnosis and the token-permission tell are in `ssr-web-over-own-api`,
section "A Cloudflare tunnel DOES cache your static paths".

### The purge token usually CANNOT purge — cache-bust the URL instead, WITH the site's own existing pattern

<!-- verified: an existing token in the env returned 1000 Invalid API Token / 9109 Unauthorized on
     purge_cache; the token had been mangled by a newline and lacked the Cache-Purge scope, and no
     CF credential existed on the serving host at all. A `/cover/` file replaced on origin kept
     serving the OLD bytes (a 2 KB placeholder, not the 94 KB poster) for over 20 minutes. -->
Do not plan on cache purging. On this project the CF token in `~/.hermes/cf-token.env` typically lacks the
Cache-Purge permission (`errors[0].code` 1000 or 9109), sometimes has a stray leading line that makes the
file un-sourceable, and the serving host has no CF credential at all. Escalating to the user for a new
token is one option, but there is a fix that needs **no credential and no purge** and is the better
default:

**Give the asset URL a `?v=<mtime>` query — a changed URL is a cache MISS by definition.**

```
PITFALL SIGNATURE (what you will see when this is the problem):
  curl -sI https://<site>/cover/<id>.webp   →  cf-cache-status: HIT · age: >1000 · content-length: <OLD SIZE>
  curl -s  https://<site>/cover/<id>.webp   →  <OLD SIZE>            (tiny; the placeholder)
  curl -s  https://<site>/cover/<id>.webp?x=1  →  cf-cache-status: BYPASS · <NEW SIZE>   ← the tell
The `?x=1` probe is the diagnosis: new bytes under a new query string, old bytes without. That proves
origin is correct and ONLY the edge is stale.
```

The fix must **reuse the pattern the site already has**, not invent one. A site that solved this for CSS
usually already carries a `_versi_aset()` helper (returning `str(int(mtime))` of its CSS/JS) wired into
the templates as `?v=` — extend that exact shape to the cover:

```python
# the existing pattern to mirror (its docstring already says why: CF cached stale CSS for hours)
def _versi_aset() -> str: ...          # returns str(int(mtime)) of the static files

def _versi_cover(nid) -> str:          # NEW, same shape, keyed on the cover file
    try:
        for ekst in (".webp", ".jpg", ".png"):
            f = COVER / f"{nid}{ekst}"
            if f.exists():
                return str(int(f.stat().st_mtime))
    except Exception:
        pass
    return "1"
```

Then replace every builder site that emits the URL, e.g. `f"/cover/{r['id']}.webp"` →
`f"/cover/{r['id']}.webp?v={_versi_cover(r['id'])}"`. Do **all** of them — the detail page, the shelf
list, and the `og:image`.

Why this is allowed under "jangan nambah/ubah yg udah jadi": this is a **bug fix that follows an existing
in-repo pattern**, not a new feature. Say exactly that when reporting it, and keep a `.bak` of the file
(`web/main.py.bak-cover-v`) before the edit. Still preserve the rule's spirit: do not redesign the URL
scheme or rename the asset path; mirror `_versi_aset` and change nothing else.

**Same run, also fix the TTL so the next replacement lands in minutes, not hours:** add `"/cover/"` to the
static-cache middleware with `public, max-age=300, must-revalidate` (the sibling of the `/static/` branch).
Without it the edge holds a replaced poster for the full 4-hour TTL even after the file changed.

**When the user says "the poster is still broken" and your local probe looks fine, believe the user and
probe BOTH paths for size.** A localhost `200` says nothing about the edge; the whole failure here was
`127.0.0.1` returning the new image while the domain kept returning the placeholder. Comparing
`size_download` / `md5` between origin and public host is the only check that catches it.

## 3b. When the DB is synced to a SEPARATE serving host, the cover file needs its OWN transfer

<!-- verified: a newly-loaded novel's DB row was synced to the VPS and the detail page returned 200,
     but /cover/<id>.webp was 404 on the public site while the file existed on the phone -->
A DB-sync tool that rsyncs/copies `naver.db` to the serving host transfers **rows, not assets**. The
row holds a relative path (`cover/<id>.webp`), so after the sync the host has a correct row pointing
at a file it does not have — the novel page loads and the poster 404s. This is the same failure as
section 3 (a row without bytes behind it), one host removed.

- **After every DB sync, send the new asset files separately** — one `scp` of `cover/<id>.webp` into the host's cover dir, or a `--paksa`/`--cover` mode on the sync tool that ships both. Do it in the same step, never "later".
- **Probe the PUBLIC host after the sync, not the origin.** `curl -o /dev/null -w '%{http_code} %{content_type}' https://<site>/cover/<id>.webp`
  → `200 image/webp`. A 404 there with a matching file on the origin host means the file never crossed.
- **`cover-asli/<id>.jpg` is not served on either host** — a 404 on `/cover-asli/…` is expected for every
  novel and is not the defect (same as section 3). Only the served path matters for the probe.

### The sync tool's "already in sync" check must count the ASSET TABLES too

<!-- verified: a newly-added illustration set was never transferred because the sync tool compared only
     novel+bab counts, which were unchanged; the rows sat on the phone, absent on the serving host -->
A count-based sync guard (`if HP_novel == VPS_novel and HP_bab == VPS_bab: exit "SUDAH SAMA"`) is the
natural shape and it is **wrong the moment assets exist**, because adding illustrations changes no
novel and no chapter count. The sync then reports success and skips the push. Fix the guard, and add a
force mode:

```bash
HP_GMB=$(sqlite3 "$HP/naver.db"  "SELECT COUNT(*) FROM bab_gambar;")
VPS_GMB=$(ssh … "sqlite3 …/naver.db \"SELECT COUNT(*) FROM bab_gambar;\"")
# compare novel + bab + bab_gambar; on any mismatch, or when --paksa is passed, transfer
```

- **Any table holding asset references belongs in the sync's comparison set** (`bab_gambar` here; the
  cover columns live on `novel`, which is why covers were caught and illustrations were not).
- **Keep a `--paksa` override** so a transfer can be forced when counts alone look equal but a file was
  replaced in place.
- When the sync has already silently skipped, you will see the evidence as a **count mismatch between
the two DBs** — check `SELECT COUNT(*) FROM bab_gambar` on BOTH sides before assuming the rows are
missing from the source.

## 3c. Writing the cover into the WRONG directory is the classic "icon foto rusak" — and the app ignores the DB filename

<!-- verified: two newly-loaded novels shipped a broken-image icon while every older novel was fine;
     the covers had been written to `web/static/cover/<id>.webp` — a directory that exists, looks
     plausible, and is never read. The served copy must be at the project ROOT's `cover/<id>.webp`,
     i.e. `<project>/cover/`, NOT `<project>/web/static/cover/`. -->

**The served cover directory is `<project>/cover/`, mounted as `/cover`.** A project may contain
*sibling* directories that all look like a cover dir — `<project>/cover/`, `<project>/web/static/cover/`,
`<project>/static/cover/`, `<project>/upload-<x>/cover/`. Only one is mounted and served; writing to
any other produces a **correct-looking file that 404s**, i.e. the user's "poster masih belum muncul,
icon foto rusak" while the file is sitting right there on disk.

**Read the app's mount lines before writing ANY asset**, never infer the path from where an older
cover happens to sit:

```bash
grep -nE 'mount\(|StaticFiles|COVER *=|GAMBAR *=' <project>/web/main.py
#   COVER = ROOT / "cover"
#   app.mount("/cover",  StaticFiles(directory=str(COVER)),  name="cover")
#   app.mount("/gambar", StaticFiles(directory=str(GAMBAR)), name="gambar")
```

That gives you the one true directory for each asset class. Write there, then probe
`/cover/<id>.webp` for `200 image/webp`.

### The app builds the URL from the ROW ID, not from the `cover_webp` string

<!-- verified: the novel rows' `cover_webp` values were a mix of `<slug>.webp`, `cover/<id>.webp`,
     and `<id>.webp`; all rendered fine because the builder ignores the string. Only the file's
     EXISTENCE at `/cover/<id>.webp` matters. -->
The card builder is typically:

```python
"cover": f"/cover/{r['id']}.webp?v={_versi_cover(r['id'])}" if r["cover_webp"] else None
```

So the `cover_webp` column is used as a **boolean flag** ("has a cover") and the filename is derived
from `id`. Consequences:
- A row whose `cover_webp` holds a slug, `cover/<id>.webp`, or `<id>.webp` all work **as long as
  `cover/<id>.webp` exists on disk**. Do NOT mass-rewrite those values chasing consistency — the
  value is cosmetic; the FILE is what matters. (Rewriting is a harmless tidy, but never the fix.)
- **The real check is a `os.path.exists` loop over `cover/<id>.webp` for every row with a non-empty
  cover column** — a row can look set and still 404. Run it and report the count.
- **Don't trust a local-`200` only.** A `curl` from the serving host proves the file crossed; a
  "still broken" from the user then means cache (see §3) — believe the user and probe size/md5 on
  the public host before re-uploading.

### Two files written to the wrong dir is a LOCALIZED bug — check the handful of newest ids first

When only the **most recent** novels show broken posters and older ones are fine, the cause is almost
always a one-off path mistake in the newest load, **not** a systemic serving fault. Diff the newest
novels' cover files against the app's mount line before touching backup/restore or the web tier. Do
not "fix" a working archive — the fix is one `cp` into the right directory.

## 4. Put the cover step INSIDE the loader, not beside it

The recurring cause of an empty poster is that the loader (`vps/mtl-masuk-db.py up`)
writes the column names and never touches the assets. Add the copy/normalise to the
loader so the next novel cannot hit the same gap: if `meta.json` carries the cover, the
loader materialises `cover/<id>.webp` itself and the insert and the file land together.

## 5. Illustrations: map page → chapter once, store a caption

Do not re-read the PDF per page (a 145-page file times out). Read each chapter's start
page into a dict once, or infer position from the already-known per-chapter char
proportions, then map image page → chapter and store a `caption` per image
(`"Cover Novel"`, `"Ilustrasi Episode 1: …"`). Illustrations are supported by the site —
do not drop them. Keep the same two-directory convention.

A text-only vision model cannot *see* the artwork. Report the **measured geometry**
(dimensions, ratio, channel stats, which page, which caption) and let the user eyeball
the folder, rather than asserting what the picture depicts. If an image-analysis tool comes back
unable to accept images, say the artwork was not inspected and fall back to the measurements — do
not describe art you never saw.

## 6. A missing cover hides the novel from the whole site — it is not cosmetic
<!-- verified: 27 of 498 novels had no cover row, and the browse/search query filtered them out entirely -->
The browse/search page commonly filters on the cover column (`WHERE cover_webp IS NOT NULL`), so a
novel with a NULL cover is **invisible to the user's search** while its detail page still returns
200. Symptom the user reports: "I requested this novel and it isn't on the site", when the work is
in fact fully loaded and readable.

So after any bulk import, run this audit and report the number — do not wait for the user to
notice:

```sql
SELECT COUNT(*) FROM novel;                                             -- total
SELECT COUNT(*) FROM novel WHERE cover_webp IS NULL OR cover_webp='';   -- hidden
-- and for rows that DO have a path, confirm the file exists on disk:
```

Loop the non-empty `cover_webp` values through `os.path.exists` — a row can point at a file that
was never written (see section 3). Then either get the covers or, if the user will supply them,
**hand them a ready-made list** (`CATATAN/<n>-novel-butuh-cover.json`: id, title, source URL, and
the exact `cover-asli/<id>.jpg` destination) so the fix is a drop-in, not another round of lookup.
Do **not** silently generate placeholder art or loosen the filter to make them appear — that changes
a working feature; ask first.

