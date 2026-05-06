# HLL Webhook Kill Feed - Dedupe Fixed

This version fixes double/triple webhook posts.

## What changed

Instead of deduping the raw admin-log line/object, this version dedupes after parsing the event using a stable fingerprint:

```text
killer | killer team | victim | victim team | weapon | kill/teamkill
```

That suppresses repeated admin-log results across polls and reconnects.

## Recommended Railway Variables

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10
DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=300
DEBUG_PARSE=false
```

If duplicates still happen, increase:

```env
DEDUP_TTL_SECONDS=600
```

If you want to see suppression logs:

```env
LOG_LEVEL=DEBUG
```
