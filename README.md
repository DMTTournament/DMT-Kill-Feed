# HLL Discord Webhook Kill Feed

Webhook-only Hell Let Loose kill feed for Railway. No Discord bot token or slash commands required.

## What it posts

### Normal kill
Green embed:

🇺🇸 **BigKat** killed 🇩🇪 **PanzerAce**  
⚔️ M1 Garand • ⚔️ Combat Kill

### Tank kill
Green embed:

🇩🇪 **TACO_Tanker** killed 🇺🇸 **101A_Scout**  
🛡️ Panzer IV Cannon • 🛡️ Tank Kill

### Commander ability
Green embed:

🇺🇸 **JWT_Commander** killed 🇩🇪 **HLLE_Armor**  
🎯 Precision Strike • 🎯 Commander Ability

### Team kill
Yellow embed:

🇬🇧 **ReconRon** team killed 🇬🇧 **MedicMike**  
⚠️ Thompson • ⚠️ Team Kill

The embed does **not** include a Teams section and does **not** show player IDs.

## Features

- Discord webhook only
- Continuous Railway worker
- HLL RCON admin log polling via `get_admin_log`
- Duplicate protection
- Startup backlog skip option
- Green embeds for kills
- Yellow embeds for team kills
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
```

5. Deploy.

Railway will use the included `Dockerfile`.

## Discord webhook setup

1. Open the Discord channel where the feed should post.
2. Go to **Edit Channel > Integrations > Webhooks**.
3. Create a webhook.
4. Copy the webhook URL.
5. Paste it into Railway as `DISCORD_WEBHOOK_URL`.

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
