# HLL Discord Webhook Kill Feed

Webhook-only Hell Let Loose kill feed for Railway. No Discord bot token or slash commands required.

## What it posts

### Kill
Green embed title: **Kill**

🇺🇸 **BigKat** killed 🇩🇪 **PanzerAce**  
**Weapon:** 🔫 M1 Garand  
**Kill Type:** ⚔️ Combat Kill  
Footer: `Your HLL Server Name`

### Tank kill
Green embed title: **Kill**

🇩🇪 **TACO_Tanker** killed 🇺🇸 **101A_Scout**  
**Weapon:** 💥 Panzer IV Cannon  
**Kill Type:** 🛡️ Tank Kill  
Footer: `Your HLL Server Name`

### Commander ability
Green embed title: **Kill**

🇺🇸 **JWT_Commander** killed 🇩🇪 **HLLE_Armor**  
**Weapon:** 🎯 Precision Strike  
**Kill Type:** 🎯 Commander Ability  
Footer: `Your HLL Server Name`

### Team kill
Yellow embed title: **Team Kill**

🇬🇧 **ReconRon** team killed 🇬🇧 **MedicMike**  
**Weapon:** 🔫 Thompson  
**Kill Type:** ⚠️ Team Kill  
Footer: `Your HLL Server Name`

The embed does **not** include a Teams section and does **not** show player IDs.

## Features

- Discord webhook only
- Continuous Railway worker
- HLL RCON admin log polling via `get_admin_log`
- Duplicate protection
- Startup backlog skip option
- Green embeds for kills
- Yellow embeds for team kills
- Server name footer from RCON with manual fallback/override
- Auto map-based faction emojis:
  - United States 🇺🇸
  - British 🇬🇧
  - Soviet 🇷🇺
  - German 🇩🇪
- Tank kill detection
- Commander ability detection
- Railway-visible error logging

## Railway setup

1. Create a GitHub repo.
2. Upload these files to the repo.
3. In Railway, create a new project from the GitHub repo.
4. Add these environment variables:

```env
RCON_HOST=your_server_ip
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
DISCORD_WEBHOOK_URL=your_discord_webhook_url
WEBHOOK_USERNAME=HLL Kill Feed
LOG_LEVEL=INFO
POLL_INTERVAL_SECONDS=5
RECONNECT_DELAY_SECONDS=5
LOG_LOOKBACK_SECONDS=120
SKIP_STARTUP_BACKLOG=true
DEDUP_CACHE_SIZE=500
MAP_REFRESH_SECONDS=60
SERVER_NAME_FALLBACK=HLL Server
SERVER_NAME_REFRESH_SECONDS=300
```

5. Deploy.

Railway will use the included `Dockerfile`.

## Discord webhook setup

1. Open the Discord channel where the feed should post.
2. Go to **Edit Channel > Integrations > Webhooks**.
3. Create a webhook.
4. Copy the webhook URL.
5. Paste it into Railway as `DISCORD_WEBHOOK_URL`.

## Optional server name override

The app tries to detect the server name from RCON. If your provider does not expose it cleanly, set this in Railway:

```env
SERVER_NAME_OVERRIDE=DMT Tournament Server 1
```

If detection fails and no override is set, it uses:

```env
SERVER_NAME_FALLBACK=HLL Server
```

## Optional faction override

If your server uses a map name this app does not recognize, set overrides in Railway:

```env
ALLIES_FACTION=US
AXIS_FACTION=GERMAN
```

Valid values:

- `US`
- `BRITISH`
- `SOVIET`
- `GERMAN`

## Logging

Railway logs will show:

- RCON connection success/failure
- Server name detected
- Current map detected
- Faction mapping
- Parser errors
- Discord webhook errors
- RCON reconnect loops

Use this for more detail:

```env
LOG_LEVEL=DEBUG
```

## Notes

This is near real-time because HLL kill data is pulled from the RCON admin log on an interval. It is not an instant push event stream.

If Railway restarts, kills during downtime may be missed depending on how much admin log history your server returns.
