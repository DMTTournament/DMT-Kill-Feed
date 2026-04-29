# HLL Webhook Kill Feed for Railway

A lightweight Hell Let Loose kill feed that posts directly to a Discord webhook. There are no Discord bot commands, no Discord bot token, and no bot invite.

## What it posts

- Standard kills: green embed
- Team kills: yellow embed
- Team emojis: 🇺🇸 Allies, 🇩🇪 Axis, ❔ unknown
- Tank kill detection from vehicle/tank weapons
- Commander ability detection, including Precision Strike, Bombing Run, Strafing Run, and Artillery-style log weapons
- Killer name, killed player name, weapon, and teams
- No player IDs in Discord messages

## How it works

The app connects to your HLL server RCON using `hllrcon`, polls `ShowLog`, parses kill lines, deduplicates them, and sends embeds to Discord through your webhook.

HLL logs are returned by the `ShowLog` command as a wall of text with each line representing a server event, including `KILL` and `TEAM KILL` entries. The `hllrcon` library is an async Python implementation of the HLL RCON protocol.

## Railway setup

1. Create a new GitHub repository.
2. Upload these files to the repository root.
3. In Railway, create a new project from that GitHub repo.
4. Add the environment variables from `.env.example`.
5. Deploy.

## Required Railway variables

```env
HLL_RCON_HOST=your.server.ip
HLL_RCON_PORT=your_rcon_port
HLL_RCON_PASSWORD=your_rcon_password
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

## Optional variables

```env
WEBHOOK_USERNAME=HLL Kill Feed
POLL_INTERVAL_SECONDS=5
LOG_LOOKBACK_MINUTES=3
SKIP_STARTUP_BACKLOG=true
DEDUP_CACHE_SIZE=500
LOG_LEVEL=INFO
```

## Discord webhook setup

1. In Discord, go to the channel where you want the kill feed.
2. Edit Channel → Integrations → Webhooks.
3. Create Webhook.
4. Copy Webhook URL.
5. Paste it into Railway as `DISCORD_WEBHOOK_URL`.

## Railway logs

The app logs startup, RCON connection attempts, parsed kill counts, webhook failures, and parsing errors to stdout/stderr. Railway will show these under the service logs.

Use `LOG_LEVEL=DEBUG` if you need more detail.

## Example posts

### Standard kill

🟢 🔫 Kill Feed  
🇺🇸 **BigKat** eliminated 🇩🇪 **PanzerAce**  
🔫 Weapon: M1 Garand  
⚔️ Type: Combat Kill

### Team kill

🟡 ⚠️ Team Kill  
🇺🇸 **ReconRon** eliminated 🇺🇸 **MedicMike**  
🔫 Weapon: Thompson  
⚠️ Type: Team Kill

### Tank kill

🟢 💥 Tank Kill  
🇩🇪 **TACO_Tanker** eliminated 🇺🇸 **101A_Scout**  
🔫 Weapon: 75MM CANNON [Panzer IV]

### Commander ability

🟢 🎯 Commander Ability  
🇺🇸 **JWT_Commander** eliminated 🇩🇪 **HLLE_Armor**  
🔫 Weapon: Precision Strike

## Notes

- This is near real-time because HLL RCON logs are polled.
- If Railway or RCON is down, kills during downtime can be missed depending on log history returned by the server.
- Keep your RCON password private. Use Railway variables, not hardcoded code.
