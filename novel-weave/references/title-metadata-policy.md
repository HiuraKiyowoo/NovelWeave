# Title, romanji, and synopsis policy

## Title hierarchy

Store the strongest verified title, not the first title found:

1. official publisher/platform title;
2. official English title or licensed catalog title;
3. verified romanji derived from the original title;
4. original native title in a separate `judul_asli` field.

If an Indonesian title is only a local description, replace it with the verified English title or romanji in the public `judul` field. Keep the Indonesian wording only as a private search alias unless the project explicitly chooses it as a display title. Never invent an English title or romanise by intuition; write `ATL tidak ditemukan` in the report and leave the field unresolved.

## Synopsis fallback order

A synopsis is optional. When it is missing, use this order:

1. official publisher or author synopsis for the exact edition;
2. official platform description (Kakuyomu/Syosetu/etc.);
3. licensed catalog metadata;
4. a short factual description derived from verified metadata, clearly marked as an internal draft until reviewed.

Do not assume the source page has a synopsis. Check the work landing page, metadata/API payload, publisher series page, and catalog record separately. If none contains a usable synopsis, leave the public synopsis empty and report `sinopsis: tidak tersedia` rather than fabricating one.

Do not copy a third-party translator's blurb into public metadata. Keep its URL/name private under the rights manifest.

## Verification record

Before staging, record:

```text
judul_display: <verified English/romanji>
judul_asli: <native title>
source_kind: web-novel | print-LN | authorized-file
edition: <which work/version>
author: <verified or unresolved>
synopsis_status: official | platform | catalog | draft-review | unavailable
```

A title match must identify the same work and edition, not merely a shared keyword or a manga adaptation with the same series name.
