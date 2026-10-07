# Safety, rights, and public-output gate

This skill is an operational workflow, not legal advice. Stop when rights are unclear.

## Allowed inputs

Process only text that is one of these:

- owned by the user/project;
- public domain;
- licensed for translation and publication;
- supplied with explicit permission from the rights holder; or
- an official author/publisher web-novel upload whose terms allow the intended use.

A source being publicly reachable does **not** make a full translation publishable.

## Never do

- bypass DRM, paywalls, authentication, robots/access controls, or anti-bot measures;
- defeat a rate limit by rotating identities or flooding endpoints;
- copy or publish a third-party human translation as if it were project MTL;
- include a translator group name, mirror URL, source URL, affiliate link, or download link in public chapter text or synopsis;
- treat a public metadata page as permission to reproduce the manuscript;
- push an unlicensed full translation to the production DB or public site.

## Provenance separation

Keep provenance in a private local manifest, for example:

```json
{
  "work": "verified title",
  "edition": "print or web",
  "rights_basis": "user-owned | public-domain | licensed | authorized | official-author-upload",
  "source_url_private": "do not copy to public fields",
  "translator_or_group_private": "do not copy to public fields",
  "checked_at": "2026-01-01T00:00:00Z"
}
```

Public fields may contain only the work's own metadata and a neutral synopsis. If the user asks to publish credits or links, pause and request a rights/metadata decision; do not silently place them in chapter text.

## Third-party translations

A human Indonesian EPUB/PDF from another group is a **third-party asset**, even if it is free to download. Skip MTL, quarantine it, verify its language and completeness, and require permission before publication. Without permission, use it only as a private reference for identifying metadata—not as the public manuscript.

## Stop/report format

When the gate fails, report:

1. what is known about the source and rights;
2. what cannot be verified;
3. which safe route remains (user-owned file, licensed source, public-domain work, or official author upload);
4. what will not be done (no bypass, no public import, no hidden source credit).
