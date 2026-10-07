# Extracting illustrations from a multi-volume EPUB set

Depth for the EPUB branch of "Assets from the raw" in SKILL.md. A per-volume EPUB set carries the
colour pages and body illustrations as declared image items; getting all of them out is a short,
fully-deterministic pass — but three traps make the naive version return **0 images and no error**.

## 1. Reach the volume folder without keying on its name

A torrent/EPUB-set folder name is vendor text and routinely carries an **apostrophe** and a
**trailing space** before the closing bracket (`… [CleanBookGuy] ` — note the space). `glob('*')` and
a `[... ]` pattern silently fail to match it, and `os.listdir` returns the name WITHOUT the trailing
space, so an exact-string comparison against the printed directory listing also fails.

**Match on content, not on the name:**

```python
FOLDER = None
for x in os.listdir(BASE):
    p = os.path.join(BASE, x)
    if not os.path.isdir(p):            continue
    if [f for f in os.listdir(p) if f.lower().endswith('.epub')]:
        FOLDER = p; break
```

The durable rule: **never key a path on a folder's literal name when you can key it on what the
folder contains.** The same trap bites the harvest, the illustration copy and the transfer script
independently — fix it once at the top.

## 2. Zip member names are CASE-SENSITIVE; the harvest JSON's paths often are not

The harvest records image paths as written in the XHTML/OPF (`OEBPS/Images/Color1.jpg`), while the
zip's real entry may differ in case. `zipfile.read(name)` then raises `KeyError`, and a bare
`except KeyError: continue` turns the whole pass into a silent `TOTAL: 0`.

Build a folded map first and resolve through it:

```python
z    = zipfile.ZipFile(path)
peta = {n.lower(): n for n in z.namelist()}     # folded key -> real member name
real = peta.get(recorded_path.lower())
if not real:
    print('  MISSING:', recorded_path); continue   # never swallow this silently
open(dst, 'wb').write(z.read(real))
```

Rule: **a media-extraction loop must PRINT every path it could not resolve.** An extraction step
whose only output is a total is a step that can fail completely while reporting success. When the
total comes back 0, run the two probes in order — does the archive contain any `/Images/` member at
all, then does the folder even resolve — before touching the matching logic.

## 3. Name the output files yourself

Write `panen/ilust/volNN/001.jpg, 002.jpg, …` incrementing per volume, so the folder holds exactly
the volume's illustration order (1..N). The DB loader then copies positionally, which is what keeps
the on-shelf page order equal to the printed book's.

## 4. Two-pass insert: the folder is NAMED AFTER the chapter id

The destination folder `gambar/<bab_id>/` cannot be computed before the `Volume N — Ilustrasi`
chapter row exists. **Note the id in that path is the BAB id, not the novel id** — writing
`gambar/<novel_id>/` makes the folder and the `file_lokal` agree with each other while agreeing
with nothing the app serves, so every image 404s with no error anywhere.

**Before writing ANY path, read the app's own mounts and folder key out of `web/main.py`.** This is
one `grep` and it removes the whole class of guess-the-path bugs:

```bash
grep -nE "mount\(|StaticFiles|GAMBAR|COVER" web/main.py
```

The decisive line is the mount, not the DB column:

```python
app.mount("/gambar", StaticFiles(directory=str(GAMBAR)), name="gambar")
app.mount("/cover",  StaticFiles(directory=str(COVER)),  name="cover")
```

**The mount root is whatever `GAMBAR`/`COVER` resolve to — do not assume it is `static/`.**
<!-- verified: the app mounted /gambar and /cover from the PROJECT ROOT (/root/naver-web/gambar,
     /root/naver-web/cover) while the loader was copying into <project>/static/gambar/<novel_id>/.
     The novel page returned 200 and the artwork 404'd; the images were on disk the whole time,
     just not under the mounted directory. -->
A project commonly has BOTH `<project>/static/` and the mounted dir, so the wrong one looks plausible.
Resolve `GAMBAR`/`COVER` in the app and copy to *that* path. When they differ, the tell is a fleet
of `404`s on a page that otherwise renders — probe one image URL: `200` means the path is right,
`404` with the file present on disk means you copied into a directory nothing mounts.

```python
cur.execute("INSERT INTO bab(novel_id, nomor, urutan, judul, teks, ada_gambar, volume) …")
bab_id = cur.lastrowid                    # the folder name IS this id
os.makedirs(f"{GAMBAR}/{bab_id}", exist_ok=True)
for i in range(len(gl)):
    shutil.copyfile(f"{BASE}/panen/ilust/vol{vol:02d}/{i+1:03d}.jpg", f"{GAMBAR}/{bab_id}/{i+1}.jpg")
    cur.execute("INSERT INTO bab_gambar(bab_id, urutan, file_lokal) VALUES (?,?,?)",
                (bab_id, i+1, f"gambar/{bab_id}/{i+1}.jpg"))
```

`file_lokal` is rendered **directly as a root-relative URL** by the web tier, so its value must be
the path MINUS whatever prefix the app already supplies — and the correct spelling differs per
host. **Never assume the prefix; read a row that already renders and copy its shape verbatim.**

<!-- verified: on one host a working row read `417582/1.jpg` (no prefix) and a row written as
     `gambar/417593/1.jpg` produced a novel page showing exactly ONE image — the `og:image` meta
     tag — because `gambar/…` resolved relative to the chapter route
     (`/novel/<slug>/bab/gambar/…`) and 404'd. The row "looked" correct and the DB counts all
     passed; only fetching the chapter page and counting `<img src=…gambar…>` tags exposed it. -->

```sql
-- the authority: inspect a row belonging to an illustration chapter you KNOW renders
SELECT bab_id, urutan, file_lokal FROM bab_gambar
 WHERE bab_id = (SELECT id FROM bab WHERE novel_id = <working-id> AND ada_gambar = 1 LIMIT 1);
```

Copy that row's `file_lokal` shape (`<bab_id>/<n>.jpg` vs `gambar/<bab_id>/<n>.jpg`) into every new
row. Because `bab_gambar` columns also vary by host (see below), fold both probes into one step:
`PRAGMA table_info(bab_gambar)` for the columns, and one known-good row for the prefix.

An illustration chapter's `teks` is empty and that is CORRECT — do not let a minimum-length guard
skip it, or the volume loses its artwork page.

## 4b. Inserting the illustration chapter into a novel that ALREADY has chapters

`## 4` above assumes the novel is being loaded from scratch. When the novel is already on the
shelf and only the artwork was missing, the new `Volume N — Ilustrasi` row must go at `urutan = 1`
and **every existing chapter shifts down by one**. This shift is where the ordering gets destroyed.

**SQLite rejects `UPDATE … ORDER BY` without a `LIMIT`:**

```
sqlite3.OperationalError: ORDER BY without LIMIT on UPDATE
```

The natural workaround — a two-phase shift (`SET urutan = 1000+i` then `urutan = urutan - 999`) —
**silently reverses and duplicates the order** when the second phase uses a constant offset. Verified:
after the shift the reader showed `Chapter 16` at `urutan = 1`, `Chapter 15` at `2`, … with the
illustration row colliding at `1`. Nothing errored; the site simply served the book backwards.

**Do the renumber by explicit id, highest first, in ONE transaction** — never by an offset arithmetic
over the whole column:

```python
conn.execute("BEGIN")
ids = [r[0] for r in cur.execute(
    "SELECT id FROM bab WHERE novel_id=? ORDER BY urutan DESC", (ND,)).fetchall()]
for bid in ids:                                   # DESC: highest moves out of the way first
    cur.execute("UPDATE bab SET urutan = urutan + 1 WHERE id = ?", (bid,))
cur.execute("INSERT INTO bab(novel_id, urutan, volume, judul, ada_gambar) VALUES (?, 1, ?, ?, 1)",
            (ND, VOL, f"Volume {VOL} Ilustrasi"))
bab_id = cur.lastrowid
# ... copy images + INSERT INTO bab_gambar (see §4), then COMMIT
```

`ORDER BY urutan DESC` plus `+1` per row is safe because the highest value is bumped first and can
never collide with a value still to be moved.

**Wrap the whole load in ONE transaction and roll back on failure.** Verified: the first attempt
raised `FileNotFoundError` mid-loop (wrong image source path) *after* the shift had already
committed, leaving the shelf half-migrated; recovery required restoring the pre-run `naver.db`
backup. With `BEGIN`/`COMMIT`/`rollback()` the same failure is a no-op. Always `cp naver.db
naver.db.bak-<what>-<stamp>` first regardless.

**Verify order, not just counts,** before declaring success: `SELECT urutan, judul FROM bab WHERE
novel_id=? ORDER BY urutan LIMIT 4` must read `Ilustrasi, Chapter 1, Chapter 2, …`. A row count of
`17` and an `ada_gambar=1` on the new row both pass while the order is upside-down.

**`bab_gambar` columns depend on the host — probe before writing.** Some schemas carry
`(bab_id, urutan, file_lokal)`; this host's also has `url_asli, caption, lebar, tinggi`. Run
`PRAGMA table_info(bab_gambar)` and insert the columns that exist; a hard-coded INSERT dies with
`no such column`, and `teks`/`nomor` on `bab` differ between hosts the same way (`PRAGMA
table_info(bab)`).

## 4c. The illustration chapter must sit at `urutan <= 3`, or a guest never sees it

The web tier gates chapters behind login **by position**, not by content: the chapter route computes
`gerbang_dasar = (not pengguna) and urutan > auth.BATAS_TAMU`, with `BATAS_TAMU = 3`. An
illustration row placed LAST therefore renders as an empty/locked chapter to logged-out visitors
while looking perfect in the DB and to any logged-in check.

This is invisible to every check in §6: the row count is right, `ada_gambar = 1`, and `file_lokal`
is the correct shape. The artwork simply never reaches a guest. Verified: a 9-image illustration
chapter loaded at `urutan = 11` showed exactly one image (the `og:image`) on the public page;
moving it to `urutan = 1` brought all 9 up, with the page flipping from `baca-terkunci` to
`baca-antikopi`.

**Verify as a GUEST.** A logged-in fetch passes either way and proves nothing:

```bash
curl -s "$BASE/novel/$SLUG/bab/$N" | grep -oE 'gambar/[0-9]+/[0-9]+\.jpg' | sort -u | wc -l
curl -s "$BASE/novel/$SLUG/bab/$N" | grep -oE 'baca-terkunci|baca-antikopi' | sort -u
```

The count must equal the `bab_gambar` rows and the marker must be `baca-antikopi`. `grep` the gate
out of the app rather than assuming the threshold: `grep -nE 'BATAS_TAMU|urutan >' web/main.py`.

**Read a working novel's row first when the shelf is already populated** — the established pattern
(`Volume N — Ilustrasi` at `urutan = 1`, chapters following) is the authority, not a fresh guess.

## 5. Transfer them without globbing a shared parent directory

`gambar/` is shared by every novel on the shelf, so a `scp -r gambar/4*` batch ships other novels'
artwork. Build the exact list from the DB and copy folder by folder:

```bash
for i in $(sqlite3 naver.db "SELECT id FROM bab WHERE novel_id=<id> AND ada_gambar=1"); do
  scp -i <key> -P <port> -r gambar/$i root@<host>:/root/naver-web/gambar/
done
```

Then `pm2 restart naver-web` — a new illustration folder is not served until the web tier restarts —
and probe the public hostname for `200 image/jpeg`.

## 6. Verification that the artwork actually landed

- Count on both ends: `find panen/ilust -name '*.jpg' | wc -l` against the harvest's declared total,
  per volume AND overall. A volume that yielded 12 of 13 is the tell, and only the per-volume count
  shows it.
- Read back from the DB: `SELECT COUNT(*) FROM bab_gambar WHERE bab_id IN (SELECT id FROM bab WHERE novel_id=?)`.
- Probe ONE public image URL and assert `200` + `image/*`; assert one too (a wrong prefix or a stopped
  mount shows up as a 404 here and nowhere else).
- **Requesting the image URL directly does NOT prove the page displays it.** A file on disk serves
  `200` even when the stored path is wrong, because you typed the correct URL yourself. Fetch the
  CHAPTER PAGE and count the image tags it actually emits:

  ```bash
  curl -s "$BASE/novel/$SLUG/bab/$N" | grep -oE 'src="[^"]*gambar/[0-9]+/[0-9]+\.jpg"' | sort -u | wc -l
  ```

  The count must equal the `bab_gambar` row count for that chapter. A page emitting exactly ONE
  image for a 9-image chapter is the signature of the `file_lokal` prefix bug above — the single hit
  is the `og:image` meta tag, which the app builds from a DIFFERENT column and therefore still works.
  This is the check that distinguishes "the bytes are on the server" from "the reader sees them".
