# Adaptive parser checklist

A parser is chosen per source and per volume, not once for the whole project. Before a full run, print a small sample and test the delimiters that actually occur.

## Delimiter probes

Check all of these before splitting:

- single `\n` versus paragraph `\n\n`;
- HTML headings (`h1`, `h2`, semantic chapter containers);
- EPUB XHTML `h1`/heading plus body, not the navigation document alone;
- form-feed `\f` in PDF-to-text output;
- `＊＊＊`, `***`, `---`, or other scene markers — these are scene breaks, not chapter boundaries;
- explicit `Chapter N`, `Episode N`, `Bab N`, `Prolog`, `Epilog`, and localized equivalents.

Print candidate block sizes and inspect at least the first, middle, and last reconstructed chapter. A single block near the entire chapter size is a failed split, not a valid result.

## TOC is a hint, not the body

EPUB `nav.xhtml` and PDF TOC entries can be misleading. Treat a heading as a real chapter only when its following body has plausible content (use the project's calibrated threshold, commonly around 1200 characters for prose). A heading followed by its own line or a short link is a TOC entry. For EPUB, use real XHTML `h1`/body documents after dropping `nav.xhtml`, package metadata, colophon, and empty separators.

## Scene separators

Preserve `＊＊＊`, `***`, or the source's horizontal-rule marker as a scene break in the chapter body. Do not translate it into a chapter, do not discard it as noise, and do not merge text across it without a deliberate review.

## Rule E warning

A "merge short lines" rule can destroy dialogue, poetic fragments, epigraphs, or intentional one-line beats. Before applying it:

1. show the candidate lines with `repr()`;
2. detect open dialogue/quote state;
3. preserve lines ending in dialogue punctuation, scene markers, or a speaker turn;
4. apply only within a paragraph whose neighboring lines prove it is a hard wrap;
5. re-read a sample after the merge and compare normalized text against the source.

Never run Rule E globally over an unknown source.

## Volume and chapter naming

If the source provides no chapter title, use `Bab N` **within that volume**, restarting the fallback counter for each volume. Keep a separate global `urutan` for site ordering. If a source provides a real title, preserve it in the title field and do not replace it with a generated number. Prefix with `Jilid N —` only when the archive convention needs disambiguation.
