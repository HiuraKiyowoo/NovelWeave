# NovelWeave

NovelWeave is a safe, resumable novel localization workflow for rights-cleared novels. The skill now uses a dispatcher flow instead of a flat collection of rules:

```text
Intake/Rights
→ DB Preflight
→ Work + Metadata
→ Source Verification
→ Extract
→ Parse
→ Chunk + Glossary
→ Endpoint/Quota
→ Translate + Resume
→ Text QA
→ Stage
→ Staging QA
→ Backup + Promote
→ Public Audit
```

## Install with npx skills

```bash
npx skills add https://github.com/HiuraKiyowoo/NovelWeave
```

Install only the MTL skill to Hermes Agent:

```bash
npx skills add https://github.com/HiuraKiyowoo/NovelWeave \
  --skill novel-weave \
  --agent hermes-agent \
  --global \
  --copy \
  --yes
```

Update an existing installation:

```bash
npx skills update novel-weave
```

## Available skills

- `novel-weave` — dispatcher for the complete 14-phase workflow;
- `novel-split-clean` — split and clean already-extracted novel text.

## Important safety rules

- MTL only text that is owned, licensed, public-domain, authorized, or an official author upload whose terms allow the intended use.
- Do not bypass DRM, paywalls, access controls, anti-bot measures, or rate limits.
- Already-Indonesian or third-party human-translated input follows the verify → quarantine → stage → approval branch; it is not sent through MTL.
- Keep source URLs and translator/group provenance private; never put them in public chapter text, synopsis, HTML, or API output.
- `localhost:20128` is not assumed to be an MTL endpoint. Probe the real endpoint/model and quota before a batch.
- Check title and slug across every DB before insert, back up the DB, stage first, and verify before promotion.

## Repository layout

```text
NovelWeave/
├── README.md
├── novel-weave/
│   ├── SKILL.md                 # dispatcher flow
│   ├── references/              # branch-specific procedures and QA
│   └── scripts/                 # deterministic preflight utilities
└── novel-split-clean/
    └── SKILL.md
```

The skill is a workflow/documentation package. It does not grant permission to copy, translate, or publish copyrighted text.
