# The reader request queue: check, report, wait for ACC, then fill

The site lets readers request a novel. When the user asks "ada request?" this is the
workflow — it is a **report-and-wait** flow, not a do-it flow, and the user's rule is
explicit about the order.

## Data location

The request table is **not** in the novel DB — it lives in the *users* DB (`users.db`),
table `request_novel`. Column names drift between builds, so never assume: read
`PRAGMA table_info(request_novel)` first and select by the columns that actually exist.
The columns seen in practice: `id, pengguna_id, judul, sumber, catatan, halaman, status,
telegram, waktu`. A `status` of `baru` means unhandled.

## The flow, in order

1. **Check the queue** (`status='baru'`) and also list the older rows — you need to tell
the user which are real and which are junk.
2. **Filter junk requests.** Rows whose judul/sumber/catatan are obviously placeholder noise
   (`"Test"`, `"Anu"`, `"Ini anu"`) are not demands. Discard them explicitly in the report so
   they do not inflate the count.
3. **Search the archive DB for each real title BEFORE searching the web** — see step 0 of the
   main pipeline. Do this across **every** DB (main + quarantined/imported + staging), and
   match `judul`, `judul_asli`, AND `slug`. A hit means the novel is *already loaded*; the answer
   is then usually a visibility problem (a NULL cover), not a missing novel.
4. **Find the raw**, and classify it: print origin (raw likely does not exist) vs web-novel
   origin (free official raw — fetch it yourself, don't ask the user). Note the case where the
   free version is a legit one-shot (`1話完結`) and the print edition is longer and different.
5. **Report, with evidence, and STOP.** The user's standing rule: report the details first, and
   only after they say yes (ACC) does anything get uploaded. The report must carry: the title,
   who asked, when, whether the source is new or an existing one, and **whether the novel is
   already in the DB (with its id)** or genuinely absent. Include the raw's chapter count vs the
   DB's, so "already in, and complete" is provable.
6. **On ACC: upload — with the same verification as any other load.** The rule says "verif juga
   biar lengkap ga ke potong dan hasil MTL-nya bagus". Never skip the four-side check because it
   was a request.

## What "already in the DB" usually means

<!-- verified: a requested novel WAS fully loaded (15/15 chapters, illustrations, clean text) and the user could not find it -->
The work being present is not the same as the work being reachable. When the DB hit is real but
DB chapter count == source chapter count and the text is clean, the reader's complaint ("I want to
read it and can't find it") is almost always the **missing-cover filter** hiding it from browse and
search. See `references/mtl-cover-and-assets.md` section 6 — check `cover_webp IS NULL` for that id
before concluding the novel needs anything done to it, and say plainly that the fix is a cover,
not a re-upload.

## Reporting shape (this user)

Casual Indonesian, evidence per claim: per-request block with judul / peminta / waktu / sumber
(new vs existing) / **sudah di db? with id** / raw availability and its chapter count. Then the
choice menu as short options (a/b/c/d) when a judgement call is needed, with your recommendation
marked and the reason one line long. Do not upload, and do not "prepare" an upload, before the ACC.
