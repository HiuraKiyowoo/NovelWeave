# Novel MTL Skill

Safe, resumable machine-translation workflow for rights-cleared novels. The package covers source verification, title/synopsis metadata, adaptive PDF/EPUB/web parsing, endpoint and quota preflight, chunk resume, staging-first SQLite import, and post-import verification.

## Install with npx skills

Interactive install:

```bash
npx skills add https://github.com/HiuraKiyowoo/novel-mtl-skill
```

Choose the skill you need in the terminal UI:

- `novel-mtl-self-translation` — end-to-end novel MTL pipeline;
- `novel-split-clean` — inspect and clean already-extracted novel text.

Install only the MTL skill globally to Hermes Agent:

```bash
npx skills add https://github.com/HiuraKiyowoo/novel-mtl-skill \
  --skill novel-mtl-self-translation \
  --agent hermes-agent \
  --global \
  --copy \
  --yes
```

List available skills without installing:

```bash
npx skills add https://github.com/HiuraKiyowoo/novel-mtl-skill --list
```

Update an existing installation:

```bash
npx skills update novel-mtl-self-translation
```

## Important safety rules

- MTL only text that is owned, licensed, public-domain, authorized, or an official author upload whose terms allow the intended use.
- Do not bypass DRM, paywalls, access controls, anti-bot measures, or rate limits.
- Do not publish a third-party human translation without permission.
- Keep source URLs and translator/group provenance private; never put them in public chapter text, synopsis, HTML, or API output.
- `localhost:20128` is not assumed to be an MTL endpoint. Probe the real endpoint/model and quota before a batch.
- Check title and slug across every DB before insert, back up the DB, stage first, and verify before promotion.
- A missing synopsis stays empty; never fabricate one.

## Repository layout

```text
novel-mtl-skill/
├── README.md
├── novel-mtl-self-translation/
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
└── novel-split-clean/
    └── SKILL.md
```

This project is a workflow/documentation skill. It does not grant permission to copy, translate, or publish copyrighted text.
