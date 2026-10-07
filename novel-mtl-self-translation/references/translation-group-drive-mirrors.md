# Translation-group mirror sites: one page, many Drive mirrors

A whole class of raw sources publishes an Indonesian (or English) translation as **one blog post
per novel**, with the volumes hosted on **Google Drive** — as either `file/d/…` (one PDF) or
`drive/folders/…` (a folder holding every volume). The user hands these over as a `Sumber :`
link plus the Drive links; sometimes only the page, sometimes only the Drive.

Recognise the shape by the page furniture: a WordPress blog (`<slug>.wordpress.com/<year>/<month>/
<day>/<slug>/`), a **`Sinopsis :` block followed by a `Genre(s) :` / `Penulis :` / `Ilustrator :`
block**, and a `Drive` list under it. Covers live as `wp-content/uploads/<year>/<month>/vol.N.jpg`
— the page's own `og:image` is the site's banner, NOT the novel's cover, so scrape the `vol.*`
uploads instead (see "Covers" below).

## 1. Get the ENTIRE list first, and never report a volume count from the link count

**A mirror site serves the SAME file from several hosts at once** (Drive + Mega + Mediafire +
ZippyShare), so the number of links is routinely 2–4× the number of volumes. Verified: a novel
with **24 links held 12 unique files = 7 volumes**, matching the local PDFs exactly.

So before saying "PDF missing, only N of M volumes" — or telling the user anything is missing —
**dedupe**: normalise each link, group by host, and compare the *volume count* (from the page's
`Volume N` mentions, or the official series page) against the files you actually hold. A raw
"8 links but I have 2 PDFs" is a false alarm and wastes a round trip with the user.

```python
# normalise Google Drive share links to a stable key before deduping
m = re.search(r'drive\.google\.com/(?:file/d/|drive/folders/)([\w-]{20,50})', url)
fid = m.group(1) if m else None
```

**`file/d/ID` is a single file; `drive/folders/ID` is a folder.** Probe which by requesting
`https://drive.google.com/uc?export=download&id=<ID>`: a `%PDF` body means file; an HTML body or
**HTTP 500** means it is a FOLDER, not a broken link. Treating a folder id as a file is the
single most common mistake here — it looks like a dead link and is not.

When the user only supplies the page, the page's own Drive links are the source; when they supply
Drive links and no page, fetch the page anyway for the title, synopsis, author, cover, and volume
list. Take the union of both.

## 2. Downloading a PUBLIC Drive FOLDER — the `flip-entry` route that works

`gdown` is often not installed and `drive.google.com/drive/folders/<id>` returns a JS shell whose
ids do not pair with the names. The working route is the **embedded folder listing**:

```python
import urllib.request, re, html
h = urllib.request.urlopen(urllib.request.Request(
        f"https://drive.google.com/embeddedfolderview?id={fid}#list",
        headers={"User-Agent": UA}), timeout=90).read().decode("utf-8", "replace")
blok = re.findall(r'flip-entry"\s+id="entry-([\w-]{20,50})"(.*?)flip-entry-title">([^<]{2,160})', h, re.S)
# blok = [(file_id, junk, display_name), …]  — names and ids PAIR correctly here
```

Then download each id with the plain-file recipe below. Two traps in the returned list:

- **The page also contains Google API keys and analytics ids that look like file ids**
  (`AIzaSy…`, `AA2Yr…`, `GOCSPX…`, `ya29.…`). They appear when you scrape ids and names as two
  separate lists and zip them — the pairing shifts and you get garbage names against key strings.
  Use the `flip-entry` block regex above (name and id come out of ONE match) and additionally
  **filter ids by prefix** (`re.compile(r'^(AA2Yr|AIzaSy|GOCSPX|ya29\.)')` ⇒ reject).
- **Identical volumes can be listed twice** under a `(Hitam)` / `(Putih)` suffix — that is a
  black-background and white-background render of the SAME volume, not two volumes. Dedupe by
  file size/MD5 and keep one; count it once when comparing against the volume list.

## 3. Downloading a Drive FILE — `uc?export=download` plus the confirm step

```python
d = get(f"https://drive.google.com/uc?export=download&id={fid}", timeout=300)
if b"<html" in d[:400].lower() or b"<!DOCTYPE" in d[:200].upper():   # virus-scan interstitial
    m = re.search(rb'confirm=([\w-]+)', d); tok = m.group(1).decode() if m else "t"
    d = get(f"https://drive.usercontent.google.com/download?id={fid}"
            f"&export=download&confirm={tok}", timeout=900)
if d[:4] in (b"%PDF", b"PK\x03\x04") or len(d) > 100_000:
    open(dest, "wb").write(d)
```

Accept `b"PK\x03\x04"` as well as `b"%PDF"` — the same source ships **EPUB** for some volumes and
PDF for others, and an EPUB is the better container when both exist. Skip any destination that
already has the file at a plausible size, and **retry the fetch 3× with a short sleep** — Drive
rate-limits a burst of parallel downloads and returns an HTML error page, which the size guard
above would otherwise write to disk as a corrupt "PDF".

## 4. Covers

Translation-group pages usually carry the covers as their own uploads:

- Scrape `wp-content/uploads/<year>/<month>/vol.*\.(jpg|png|webp)` — dedupe by MD5 (`vol.1.jpg`
  and `vol.1-1.jpg` are frequently the identical file), and expect only the volumes the group
  actually posted (a 3-volume series often has covers for v1–v2 on the page).
- **When the page lacks a volume's cover, the PDF itself starts with it.** `pdfimages -all` on each
  volume yields an `img-000` that is the cover at the cover ratio (~0.70), and its pixel size is
  the resolution to keep. This is the reliable fallback and needs no extra search: verified a
  3-volume set where the page carried v1+v2 only and the missing v3 cover came straight out of
  `img-000` of v3's PDF. Normalise every volume's cover to the same height (e.g. 1000 px) so the
  shelf looks uniform.
- The novel's own `og:image` is a **site banner** (a logo or a promo card for a different novel),
  not a cover. Do not use it.

## 5. Page furniture to strip from the text

The extracted text carries the group's watermark — most commonly a footer of the form
`<Novel Name> Vol.N                      <Group Name>` plus a bare page number. Before any chapter
parse, strip it with an anchored whole-line rule, and **verify the count is 0 afterwards**:

```python
t = re.sub(r'^[^\n]*(?:<Group Name>|<Novel Name>\s*Vol\.?\d*)[^\n]*$', '', t, flags=re.M)
t = re.sub(r'^\s*\d{1,4}\s*$', '', t, flags=re.M)
t = re.sub(r'^.*?(?:Dilarang|dilarang).{0,140}$', '', t, flags=re.M)
t = re.sub(r'^.*?copyright.{0,140}$', '', t, flags=re.M | re.I)
```

After stripping, re-count: a page that yielded **921** occurrences of the group's name is the
signal the rule missed a variant, not that the watermark is unavoidable. Also recall the standing
DMCA rule (see SKILL.md) — the group's name and the source URL must NOT survive into the
synopsis or the public text; only the local working files may carry them.

## 6. Chapter markers in these PDFs vary by volume — parse ADAPTIVELY

The same series will mix formats across volumes, and sometimes within one document:

- `Chapter 1 Penyimpang` (number + name), `Chapter 1` (number only)
- `Prolog:` / `Chapter Terakhir:` / `Extra Chapter …` (with a colon)
- `【Chapter N ...】` or `[Chapter N: ...]` (bracketed)
- `Chapter N / Judul` or `Chapter N／Judul` (slash or fullwidth solidus)

**Build ONE splitter that tries bracketed markers first, then falls back to plain line-start
markers**, and only accept a candidate line of a sane length (roughly 5–80 chars). Discard any
marker that lands within ~200 chars of the previous one — that is a running header repeated on a
page, not a chapter. A per-volume script is the wrong shape; per-novel is right.

Titles that collide across volumes (`Chapter 1` in v1 and v2) are resolved by prefixing the
volume: `Vol N — <title>`, then de-duplicating with an ` (2)` suffix on any remaining collision.
That is what makes the 14-double-title audit come back 0.
