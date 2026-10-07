# Public-output audit

Run this after staging and again immediately before promotion or deployment.

## Keep private

The following belong only in a local/private manifest:

- raw/source URLs and mirror links;
- translator or translation-group names;
- download links, scrape notes, local paths, API keys, and endpoint details;
- private rights correspondence;
- model prompts and failure bodies.

## Scan public fields

Check synopsis, title aliases, chapter body, author field, cover metadata, HTML, JSON/API payloads, and search indexes for:

- source URLs or mirror domains;
- “translated by”/group credits copied from a third-party source;
- internal paths or staging IDs;
- source-language paragraphs or model refusal text;
- unsupported claims of license/ownership;
- accidental raw metadata that identifies a private file.

Do not delete legitimate story content merely because it contains a URL-like string; inspect the surrounding text and classify it. If provenance appears in a public field, remove it from the public copy and retain it only in the private manifest.

## Final decision

Publish only if the rights basis is clear, QA is pass, DB integrity is `ok`, and the public scan has no private provenance or unsupported rights claim. Otherwise keep the item staged/quarantined and report the blocker.
