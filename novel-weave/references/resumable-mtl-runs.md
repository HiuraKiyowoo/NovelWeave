# Resumable MTL runs

A long MTL run must be restartable after quota exhaustion, endpoint failure, OOM, or manual pause.

## Manifest

Create one manifest per novel/edition, outside the public DB:

```json
{
  "slug": "verified-slug",
  "source_sha256": "...",
  "endpoint": "https://provider.example/v1",
  "model": "provider/model",
  "chunk_size": 1500,
  "total_chunks": 0,
  "completed_chunks": [],
  "failed_chunks": [],
  "quota_checked_at": null,
  "paused_reason": null
}
```

Never resume a manifest against a different source hash, endpoint, model contract, or chunking algorithm without rebuilding and reviewing alignment.

## Save protocol

For each chunk, atomically write:

1. source text (`en`/raw);
2. source hash and chunk index;
3. response text or structured failure;
4. endpoint/model and timestamp;
5. validation result.

Write to `chunk-N.json.tmp`, fsync/close, then rename to `chunk-N.json`. A chunk counts as complete only when its response passes the script gate: non-empty, not a menu/refusal, not source-script leakage, and within the calibrated length band.

## Quota and retry behavior

Before a batch, probe quota/rate-limit headers or provider status. If the provider does not expose a reliable remaining quota, run a small canary and cap the batch conservatively. On HTTP 429/402/503 or an allowance message:

- stop launching new chunks;
- save the failure body privately;
- mark the run paused with the exact reason;
- do not delete completed chunks;
- resume only after a fresh quota/endpoint probe.

Never retry a whole chapter from zero when only selected chunk files are missing.

## Resume checklist

```text
source hash unchanged
chunker version unchanged
completed chunk files exist and pass validation
failed chunks retain their source text
no worker is still writing the same output
quota/candidate endpoint re-probed
staging DB backup exists
```

If counts disagree, rebuild the split from the raw and compare source hashes/lengths before filling blanks. Never replace a list containing good translations just to repair missing entries.
