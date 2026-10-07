# Glossary and consistency gate

Use this reference whenever a novel is translated chunk by chunk or merged from multiple sources. The purpose is to stop name drift, terminology drift, register drift, and quote-style drift before staging.

## 1. Build a fresh glossary per novel

Create `GLOSARIUM` and `NAMA_SALAH` from the current novel's raw text, ruby/furigana, verified metadata, and approved editorial choices. Never reuse either list from another novel.

```python
GLOSARIUM = {
    "原文の名前": "Romanji Name",
    "姓": "Romanji Surname",
    "役職": "jabatan yang disepakati",
}

NAMA_SALAH = ["WrongVariantSeenInThisNovel"]
```

Include full names and surname/given-name parts when both can occur independently. Add honorific policy (`-san`, `-kun`, `-chan`, title translation) explicitly. Keep ordinary words, ranks, and titles out of `NAMA_SALAH`; they may be valid prose in the current novel.

Before translation, print the glossary for review. Before accepting output, require every important glossary entry to appear where the source indicates it should and require every blacklist variant to be absent. A blacklist hit that is a legitimate word is a glossary bug, not a reason to reject the chunk.

## 2. Inject the glossary into every call

Every chunk prompt must carry the same approved glossary and a short instruction:

```text
Use these names and terms exactly. Do not invent alternate romanisation:
- 原文の名前 = Romanji Name
- 役職 = jabatan yang disepakati
```

Do not rely on the model remembering a previous chunk. Save the glossary version/hash with each chunk so a later resume cannot silently mix policies.

## 3. Consistency dimensions

Check these separately:

- **Names:** spelling, surname/given-name order, honorifics, aliases;
- **Terms:** ranks, magic/system terms, locations, organizations, weapons;
- **Register:** `aku/kamu`, `saya/Anda`, formal/informal, pronoun and possessive forms;
- **Tense/voice:** past/present conventions and narration distance;
- **Quotes:** straight `"` versus curly `“ ”`, pairing direction, dialogue markers;
- **Chapter labels:** `Bab N`, `Prolog`, `Epilog`, and volume prefix conventions;
- **Scene separators:** preserve the source's `***`, `＊＊＊`, or approved marker exactly once.

Measure the existing shelf/archive first. Match its majority style rather than imposing a new preference on one novel.

## 4. Validation order

Run checks on the untouched joined output before any destructive normalizer:

1. source-script/CJK/kana sweep;
2. refusal/menu/continuation substring sweep;
3. glossary and blacklist scan;
4. name/term frequency and spelling report;
5. register counts against a known-good neighboring chapter;
6. quote counts and sequential pairing;
7. separator count and placement;
8. first/last paragraph review;
9. only then apply one normalizer pass and save a backup.

Do not run the same quote/register normalizer twice. Always retain the raw chunk output so a suspicious result can be compared against the pre-normalized text.

## 5. Manual splices and mixed sources

Manual translations and chapters assembled from multiple sources must use the same glossary, register, quote style, and separator policy. Store manual splices keyed to the exact chunk key used by the pipeline. A report saying `manual: 0 applied` is a failure, not a successful no-op; stop and fix the key mismatch.

For a new volume, re-check whether a word previously blacklisted is actually valid in that volume. Keep novel-specific exceptions documented in the manifest, not hidden in a global script.

## 6. Acceptance checklist

```text
[ ] glossary rebuilt for this novel
[ ] glossary version/hash stored with chunks
[ ] no stale NAMA_SALAH entries
[ ] every chunk received the same glossary
[ ] names and terminology reviewed across joined text
[ ] register matches the archive
[ ] quote style matches the archive
[ ] scene separators preserved exactly once
[ ] raw output backed up before normalization
[ ] normalizer ran once, then output was re-verified
```
