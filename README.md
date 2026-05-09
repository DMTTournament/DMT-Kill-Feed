# HLL Webhook Kill Feed - Current UTC Time + Dedupe Fixed

This version uses the actual current UTC time when the webhook embed is created.

Footer example:

```text
DMT #2 (US East) • 07 MAY 26 - 04:58 UTC
```

## Duplicate Fix

The timestamp is NOT included in the dedupe fingerprint.

Dedupe uses:

```text
killer | killer team | victim | victim team | weapon | kill/teamkill
```

Recommended Railway variables:

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10
DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=600
DEBUG_PARSE=false
```

If duplicates still happen:

```env
DEDUP_TTL_SECONDS=900
```
