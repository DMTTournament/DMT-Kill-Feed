# HLL Webhook Kill Feed

## Important

Upload the contents of this ZIP directly to the root of your GitHub repo.

Your repo root should look like this:

```text
main.py
requirements.txt
Dockerfile
railway.json
README.md
.env.example
```

Do not upload a folder that contains these files one level down, or Railway may not find `main.py`.

## Railway Variables

Required:

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

## Discord Embed Format

Title: `Kill` or `Team Kill`

```text
🇺🇸 **Killer** killed 🇩🇪 **Victim**
**Weapon:** 🔫 M1 Garand
**Kill Type:** ⚔️ Combat Kill
```

Team kills use yellow embeds:

```text
🇺🇸 **Killer** team killed 🇺🇸 **Victim**
**Weapon:** 🔫 Thompson
**Kill Type:** ⚠️ Team Kill
```

## Deploy

1. Extract ZIP.
2. Put all files in your GitHub repo root.
3. Push to GitHub.
4. Connect repo to Railway.
5. Add Railway variables.
6. Deploy.

## If Railway says `/app/main.py` is missing

That means the repo root is wrong or the files were uploaded inside another folder. Move `main.py`, `Dockerfile`, and `requirements.txt` to the top/root level of the repo.
