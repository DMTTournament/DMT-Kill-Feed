# HLL Webhook Kill Feed - Diagnostics Fixed

This version is for the case where Railway connects to HLL RCON and detects server/map, but no webhook kills post.

## Fixes included

- Slower polling by default to reduce `Connection reset by peer`
- Automatic reconnect loop
- More flexible kill log parser
- Debug admin-log samples in Railway logs
- Webhook-only, no Discord bot token
- No player IDs in Discord embeds
- Green Kill embeds / Yellow Team Kill embeds
- Tank Kill and Commander Ability detection
- Server name footer

## Railway Variables

Required:

```env
RCON_HOST=your.server.ip.or.hostname
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Recommended while testing:

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10
DEBUG_PARSE=true
DEBUG_SAMPLE_LIMIT=8
```

After it posts kills correctly, set:

```env
DEBUG_PARSE=false
```

## If kills still do not post

Look in Railway logs for:

```text
DEBUG admin-log sample
```

Send those sample lines back so the parser can be matched exactly to your server provider's log format.
