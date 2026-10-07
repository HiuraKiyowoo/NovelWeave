# Text structure and formatting gate

The translation may improve wording, but it must not silently redesign the source layout. Preserve structure first; normalize only proven layout noise.

## Paragraph contract

Treat each verified RAW paragraph as one output paragraph. Do not merge adjacent RAW paragraphs, even when the sentences look related. Do not split one paragraph merely because it is long. The only exception is a proven PDF/HTML hard-wrap where line endings are layout artifacts rather than paragraph boundaries; prove that with the source's markup, line-length distribution, punctuation, and a sample reconstruction before repair.

Use one blank line between paragraphs. Do not insert blank lines after every sentence. Do not remove an intentional empty paragraph or scene marker without recording why.

## Dialogue and narration

Keep narration and character dialogue in separate paragraphs when the RAW marks them as separate turns or paragraphs. Keep each clearly marked speaker turn as its own paragraph. Do not merge a narration paragraph with the dialogue before/after it.

Do not invent a new dialogue paragraph from punctuation alone. A quote inside a single RAW paragraph remains in that paragraph unless the source clearly marks a speaker turn or the user-approved house style explicitly asks for a structural split. When splitting a verified turn, preserve the exact order and quote content.

## Line-break policy

- Preserve chapter headings, subheadings, epigraphs, `Prolog`, `Epilog`, `Bonus`, and source chapter markers as structural lines/fields.
- Preserve `***`, `＊＊＊`, and approved horizontal-rule markers as a standalone scene-break line.
- Never add line breaks for visual decoration, model preference, or to make a paragraph “look nicer”.
- Never join lines across a scene marker, heading, quote boundary, or explicit speaker turn.
- Never let a whitespace normalizer touch `\n` until paragraph boundaries have been classified.

The rendered HTML may wrap text visually; that is not a reason to insert newline characters into the stored prose.

## Whitespace normalization

Safe normalization is limited to proven noise:

1. convert CRLF/CR to the chosen newline convention;
2. remove trailing spaces/tabs at line ends;
3. collapse repeated spaces/tabs **inside a paragraph** when they are not meaningful;
4. preserve paragraph separators, scene markers, indentation conventions, and intentional spacing in poetry/epigraphs;
5. compare non-whitespace content and first/last paragraph against the RAW after the pass.

Do not run a global `\s+` replacement: it can erase paragraph boundaries, scene breaks, or dialogue formatting. Save the raw output before normalization and run the pass at most once.

## Heading and chapter marker policy

A chapter marker belongs in the chapter title/metadata field when the archive schema has one. If the RAW repeats it as the first body line, remove only that exact leading structural line after confirming it matches the title; never remove a mid-prose mention of “Chapter 3”, “Bab 3”, or “Bonus”. Preserve real epigraphs and story content that merely look short.

## Order and acceptance test

Never reorder paragraphs, dialogue, headings, scene markers, chapters, or volumes. For every chapter, compare an ordered sequence of structural tokens before and after cleanup:

```text
HEADING → PARAGRAPH → DIALOGUE → PARAGRAPH → SCENE_BREAK → PARAGRAPH → END
```

Accept the result only when the token order is identical, every RAW paragraph maps to one output paragraph (except documented hard-wrap repairs), scene-break count is unchanged, and the first/last story text is intact.
