# HLL Webhook Kill Feed

Webhook-only Hell Let Loose kill feed for Railway.

## Final Discord Embed Format

**Title:** `Kill` or `Team Kill`

```text
🇺🇸 **Killer** killed 🇩🇪 **Victim**
**Weapon:** 🔫 M1 Garand
**Kill Type:** ⚔️ Combat Kill
```

Team kills use yellow embeds and say:

```text
🇺🇸 **Killer** team killed 🇺🇸 **Victim**
**Weapon:** 🔫 Thompson
**Kill Type:** ⚠️ Team Kill
```

## Features

- Discord webhook only
- No Discord bot token required
- No player IDs shown
- Green embeds for kills
- Yellow embeds for team kills
- Combat Kill, Tank Kill, and Commander Ability detection
- Server name in embed footer
- Map-based Allied faction emoji inference
- Railway-ready Dockerfile
- Railway-visible logging

## Railway Variables

Add these in Railway → Service → Variables:

```env
RCON_HOST=your.server.ip.or.hostname
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Optional:

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=60
POLL_INTERVAL_SECONDS=2
RECONNECT_DELAY_SECONDS=5
DEDUP_CACHE_SIZE=500
SERVER_NAME_OVERRIDE=
ALLIES_FACTION_OVERRIDE=
AXIS_FACTION_OVERRIDE=
```

## Important RCON Notes

- `RCON_HOST` should be only the IP/hostname. Do not include `http://`.
- `RCON_PORT` must be the HLL RCON port, not the game port.
- `RCON_PASSWORD` must be the RCON password from your server provider.
- If the bot times out during `ServerConnect`, verify port/password/firewall/allowlist settings with your host.

## Deploy

1. Upload these files to GitHub.
2. Create a Railway project from the GitHub repo.
3. Add the Railway variables above.
4. Redeploy.
5. Watch Railway logs for:
   - `Connected to HLL RCON.`
   - `Server state: server=... map=...`

## Dependency Note

This version uses:

```text
hllrcon==1.2.0.1
```

The code imports:

```python
from hllrcon import Rcon
```

Do not use `from hllrcon import HLLRcon`; that class is not exported by the package.
