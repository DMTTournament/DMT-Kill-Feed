# HLL Discord RCON Bot for Railway

A Railway-ready Discord slash-command bot for a Hell Let Loose server using RCON. It can also post a live Discord kill feed from HLL server logs using either a Discord webhook or a normal bot channel.

## What it includes

- `/hll_ping` - confirms the Discord bot is online
- `/hll_status` - reads server info from HLL RCON
- `/hll_players` - lists current players from HLL RCON
- `/hll_broadcast message:` - broadcasts a message in game
- `/hll_kick player: reason:` - kicks a player by exact name or ID
- `/hll_killfeed_status` - shows kill feed settings and loop status
- `/hll_killfeed_test` - posts a sample kill feed embed to your kill feed channel
- `/raw_rcon command:` - optional raw RCON command runner, disabled by default

Admin commands are limited to Discord Administrators or members with the role in `DISCORD_ADMIN_ROLE`.

## Kill feed behavior

The bot polls HLL `ShowLog` with a `KILL` filter, parses new kill lines, de-duplicates them, and posts each kill to your configured Discord webhook. If no webhook URL is set, it posts to `KILL_FEED_CHANNEL_ID` instead.

Each kill feed post includes:

- Killer name
- Killer team
- Killed player name
- Killed player team
- Weapon used
- Team-kill warning when the event is a team kill

By default, the bot skips the startup backlog so it does not dump the previous minute of kills every time Railway redeploys. Set `KILL_FEED_POST_STARTUP_BACKLOG=true` if you want it to post recent kills immediately after startup.

## Discord setup

1. Go to the Discord Developer Portal.
2. Create an application.
3. Open **Bot** and create a bot.
4. Copy the bot token. This becomes `DISCORD_TOKEN` in Railway.
5. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`.
6. Recommended bot permissions: `Send Messages`, `Use Slash Commands`, and `Embed Links`.
7. Invite the bot to your Discord server.
8. For webhook mode: open your kill feed channel settings, go to **Integrations > Webhooks**, create a webhook, and copy its URL for `KILL_FEED_WEBHOOK_URL`.
9. Optional fallback: turn on Discord Developer Mode, right-click your kill feed channel, and copy the channel ID for `KILL_FEED_CHANNEL_ID`.

## HLL RCON info you need

From your game server provider, get the RCON host/IP, TCP port, and password. Many HLL hosts expose RCON as the game port + 2. Example: game port `7777` usually means RCON port `7779`, but use whatever your provider shows.

## Railway deploy

1. Put this folder in a GitHub repository.
2. In Railway, create a new project from that GitHub repo.
3. Railway will use the included `Dockerfile` and `railway.json`.
4. Add these Railway Variables:

```env
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_discord_server_id_optional_but_recommended
HLL_RCON_HOST=your_server_ip_or_hostname
HLL_RCON_PORT=7779
HLL_RCON_PASSWORD=your_rcon_password
DISCORD_ADMIN_ROLE=HLL Admin
ENABLE_RAW_RCON=false
KILL_FEED_ENABLED=true
KILL_FEED_WEBHOOK_URL=your_discord_webhook_url
KILL_FEED_WEBHOOK_USERNAME=HLL Kill Feed
KILL_FEED_CHANNEL_ID=your_discord_kill_feed_channel_id_optional_fallback
KILL_FEED_POLL_SECONDS=10
KILL_FEED_LOOKBACK_MINUTES=1
KILL_FEED_INCLUDE_TEAM_KILLS=true
KILL_FEED_POST_STARTUP_BACKLOG=false
```

5. Deploy.
6. In Discord, run `/hll_ping`, then `/hll_status`, then `/hll_killfeed_test`.

## Recommended first test

```text
/hll_ping
/hll_status
/hll_players
/hll_killfeed_status
/hll_killfeed_test
```

Only test `/hll_broadcast` once you know the bot is connected to the correct server.

## Security notes

- Never commit `.env` or your RCON password.
- Keep `ENABLE_RAW_RCON=false` unless you trust every admin role holder.
- Use a dedicated Discord admin role like `HLL Admin` instead of giving everyone Administrator.
- Rotate your RCON password if the token or Railway variables are accidentally exposed.

## Troubleshooting

### Slash commands do not show up

Set `DISCORD_GUILD_ID` to your server ID and redeploy. Guild command sync is usually much faster than global command sync.

### Kill feed is not posting

Check these first:

1. `KILL_FEED_ENABLED=true`
2. `KILL_FEED_WEBHOOK_URL` is a valid Discord webhook URL, or `KILL_FEED_CHANNEL_ID` is a real text channel ID from the same Discord server
3. If using channel fallback, the bot has `Send Messages` and `Embed Links` permissions in that channel
4. `/hll_killfeed_test` works
5. `/raw_rcon command:ShowLog 1 "KILL"` works if you temporarily set `ENABLE_RAW_RCON=true`

### RCON connection fails

Check the RCON port, not the game port; the RCON password; whether your provider allows external RCON connections; and whether the server is online.

### `/hll_status` works but `/hll_kick` does not

Some RCON libraries and server versions use different argument formats. Try using the exact player name from `/hll_players` or the player ID.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```


## Discord webhook mode

Set this Railway variable to post kill feed embeds through a Discord webhook:

```env
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
KILL_FEED_WEBHOOK_USERNAME=HLL Kill Feed
```

When `KILL_FEED_WEBHOOK_URL` is set, webhook mode is used first. `KILL_FEED_CHANNEL_ID` is optional and only used as a fallback when no webhook URL is configured.

Webhook mode is useful because the kill feed can appear with a custom name and avatar configured in Discord, while the bot still handles slash commands and RCON polling.
