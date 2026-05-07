# HLL Webhook Kill Feed - Timestamp Final

This version adds the HLL server-log timestamp to each Discord embed footer.

## Footer Format

```text
DMT #2 (US East) • 06 MAY 26 - 14:34 UTC
```

The timestamp is pulled from the HLL admin log line, not generated locally by the bot.

## Discord Embed Format

Title: `Kill` or `Team Kill`

```text
🇺🇸 **Killer** killed 🇩🇪 **Victim**
**Weapon:** 🔫 M1 Garand
**Kill Type:** ⚔️ Combat Kill

DMT #2 (US East) • 06 MAY 26 - 14:34 UTC
```

Team kills use yellow embeds and say:

```text
🇺🇸 **Killer** team killed 🇺🇸 **Victim**
**Weapon:** 🔫 Thompson
**Kill Type:** ⚠️ Team Kill

DMT #2 (US East) • 06 MAY 26 - 14:34 UTC
```

## Railway Variables

Required:

```env
RCON_HOST=your.server.ip.or.hostname
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Recommended:

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10
DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=300
DEBUG_PARSE=false
```

If duplicates happen:

```env
DEDUP_TTL_SECONDS=600
```

If no kills post:

```env
DEBUG_PARSE=true
```

Then send back the `DEBUG admin-log sample` lines from Railway logs.

## Notes

- Webhook only
- No Discord bot token needed
- No player IDs displayed
- Green embeds for kills
- Yellow embeds for team kills
- Tank kill detection
- Commander ability detection
- Server name in footer
- Timestamp from HLL server log in footer
