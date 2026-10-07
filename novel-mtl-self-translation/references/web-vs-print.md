# Web novel versus print light novel

The same title can refer to a web novel, a print LN, or a manga adaptation. Identify the edition before sourcing or counting.

## Web novel

Typical sources: author/platform uploads such as Kakuyomu, Syosetu, or Alphapolis. Count episodes/parts, not print volumes. A one-shot can correctly contain one episode. Use the platform's own metadata and chapter list as the coverage witness. Do not infer print volume boundaries from web episode numbers or release-anniversary posts.

## Print LN

Typical evidence: publisher/product page, ISBN, release date, page count, volume number, authorized file, or a licensed/user-owned scan. Print volumes may be rewritten, condensed, and expanded; web episodes do not map 1:1 to print chapters. A very recent print volume may have no lawful free raw—stop searching and ask for an authorized file instead.

## Reporting rule

Report axes separately:

```text
work_kind: web-novel | print-LN | manga-adaptation
web_episodes: <count or unknown>
print_volumes: <count or unknown>
source_coverage: <what this raw actually contains>
```

Never call web episode groups “Volume 1/2” without a real print TOC or publisher evidence. Use neutral `Bagian N` for an estimated fold and label the estimate.
