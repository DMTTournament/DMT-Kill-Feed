# HLL Webhook Kill Feed Bot

A Railway-ready Hell Let Loose RCON kill feed that posts live kills directly to a Discord webhook.

This version is webhook-only. It does **not** require a Discord bot token.

---

## Current Version Summary

This build includes:

- Discord webhook posting only
- No Discord bot account/token required
- No player IDs shown in Discord
- Green embed for normal kills
- Yellow embed for team kills
- 3-line embed body
- Server name in footer
- Current UTC timestamp in footer
- Timestamp format: `DD MMM YY - HH:MM UTC`
- Duplicate kill/team-kill suppression
- Tank kill detection
- Commander ability detection
- US / British / Soviet / German faction emojis
- Map-based Allied faction detection
- Railway-ready Docker deploy
- Railway-visible logging and reconnect handling

---

## Required Files

Your GitHub repo root should contain:

```text
main.py
requirements.txt
Dockerfile
railway.json
README.md
.env.example
```

Correct layout:

```text
repo/
  main.py
  requirements.txt
  Dockerfile
  railway.json
  README.md
  .env.example
```

Wrong layout:

```text
repo/
  hll-killfeed/
    main.py
    requirements.txt
```

If Railway says:

```text
python: can't open file '/app/main.py'
```

your files are likely inside an extra folder. Move them to the repo root.

---

## Requirements

You need:

- Hell Let Loose server with RCON enabled
- RCON host/IP
- RCON port
- RCON password
- Discord webhook URL
- GitHub account
- Railway account

---

## Discord Webhook Setup

1. Open Discord
2. Go to the channel where kill feed posts should appear
3. Open Channel Settings
4. Go to:

```text
Integrations → Webhooks
```

5. Click:

```text
Create Webhook
```

6. Copy the webhook URL

Example:

```text
https://discord.com/api/webhooks/xxxxxxxx/xxxxxxxx
```

Use this as:

```env
KILL_FEED_WEBHOOK_URL=
```

---

## GitHub Setup

1. Extract the ZIP
2. Create a new GitHub repository
3. Upload all files directly into the repository root
4. Commit the files
5. Confirm `main.py` is visible immediately when you open the repo

---

## Railway Setup

1. Go to Railway
2. Create a new project
3. Select:

```text
Deploy from GitHub repo
```

4. Pick your bot repository
5. Railway will build the Dockerfile
6. Add the Railway variables below
7. Redeploy the service

---

## Required Railway Variables

Go to:

```text
Railway → Project → Service → Variables
```

Add:

```env
RCON_HOST=your.server.ip.or.hostname
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Important:

- `RCON_HOST` should be only the IP or hostname
- Do **not** include `http://`
- `RCON_PORT` must be the HLL RCON port
- The RCON port may be different from the game port
- `RCON_PASSWORD` must be the RCON password from your server provider

Example:

```env
RCON_HOST=40.27.44.10
RCON_PORT=7779
RCON_PASSWORD=YourPasswordHere
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## Recommended Railway Variables

Use this as the stable baseline:

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10

DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=600

DEBUG_PARSE=false
DEBUG_SAMPLE_LIMIT=8
```

---

## Optional Override Variables

```env
SERVER_NAME_OVERRIDE=
ALLIES_FACTION_OVERRIDE=
AXIS_FACTION_OVERRIDE=
```

Use these only if auto-detection is wrong.

Examples:

```env
SERVER_NAME_OVERRIDE=DMT Tournament Server #2
ALLIES_FACTION_OVERRIDE=BRITISH
AXIS_FACTION_OVERRIDE=GERMANY
```

Accepted faction values include:

```text
US
USA
UNITED STATES
BRITISH
UK
SOVIET
RUSSIAN
USSR
GERMAN
GERMANY
AXIS
```

---

## Variable Explanations

### `LOG_LEVEL`

Controls Railway log detail.

Recommended:

```env
LOG_LEVEL=INFO
```

For troubleshooting:

```env
LOG_LEVEL=DEBUG
```

---

### `LOG_LOOKBACK_SECONDS`

How far back the bot checks the HLL admin log.

Recommended:

```env
LOG_LOOKBACK_SECONDS=120
```

If kills are missed, try:

```env
LOG_LOOKBACK_SECONDS=180
```

---

### `POLL_INTERVAL_SECONDS`

How often the bot polls RCON for kill events.

Recommended:

```env
POLL_INTERVAL_SECONDS=8
```

If you see frequent RCON disconnects or:

```text
Connection reset by peer
```

try:

```env
POLL_INTERVAL_SECONDS=15
```

---

### `RECONNECT_DELAY_SECONDS`

How long the bot waits before reconnecting after an RCON error.

Recommended:

```env
RECONNECT_DELAY_SECONDS=10
```

For unstable RCON connections:

```env
RECONNECT_DELAY_SECONDS=15
```

---

### `DEDUP_CACHE_SIZE`

How many recent kill fingerprints are remembered.

Recommended:

```env
DEDUP_CACHE_SIZE=3000
```

---

### `DEDUP_TTL_SECONDS`

How long duplicate kills/team kills are suppressed.

Recommended:

```env
DEDUP_TTL_SECONDS=600
```

If duplicates still happen:

```env
DEDUP_TTL_SECONDS=900
```

---

### `DEBUG_PARSE`

Shows sample HLL admin-log entries in Railway logs when the parser cannot match them.

Normal setting:

```env
DEBUG_PARSE=false
```

Troubleshooting setting:

```env
DEBUG_PARSE=true
```

Then look for:

```text
DEBUG admin-log sample
```

After troubleshooting, set it back to:

```env
DEBUG_PARSE=false
```

---

## Discord Embed Format

### Normal Kill

Green embed.

```text
Title:
Kill

Description:
🇺🇸 **BigKat** killed 🇩🇪 **TankHunter**
**Weapon:** 🔫 M1 Garand
**Kill Type:** ⚔️ Combat Kill

Footer:
DMT #2 (US East) • 07 MAY 26 - 04:58 UTC
```

---

### Tank Kill

Green embed.

```text
Title:
Kill

Description:
🇺🇸 **ShermanAce** killed 🇩🇪 **PanzerCrew**
**Weapon:** 💥 75mm Cannon
**Kill Type:** 🛡️ Tank Kill

Footer:
DMT #2 (US East) • 07 MAY 26 - 04:59 UTC
```

---

### Commander Ability

Green embed.

```text
Title:
Kill

Description:
🇺🇸 **Commander** killed 🇩🇪 **SquadLead**
**Weapon:** 🎯 Precision Strike
**Kill Type:** 🧠 Commander Ability

Footer:
DMT #2 (US East) • 07 MAY 26 - 05:00 UTC
```

---

### Team Kill

Yellow embed.

```text
Title:
Team Kill

Description:
🇺🇸 **BlueBerry** team killed 🇺🇸 **Friendly**
**Weapon:** 🔫 Thompson
**Kill Type:** ⚠️ Team Kill

Footer:
DMT #2 (US East) • 07 MAY 26 - 05:01 UTC
```

---

## Timestamp Behavior

This version does **not** use the HLL admin-log timestamp.

The footer timestamp is generated from the actual current UTC time when the webhook embed is created.

Format:

```text
DD MMM YY - HH:MM UTC
```

Example:

```text
07 MAY 26 - 04:58 UTC
```

Footer format:

```text
Server Name • DD MMM YY - HH:MM UTC
```

Example:

```text
DMT #2 (US East) • 07 MAY 26 - 04:58 UTC
```

---

## Duplicate Kill Protection

The bot suppresses duplicates using this fingerprint:

```text
killer | killer team | victim | victim team | weapon | kill/teamkill
```

The timestamp is **not included** in the fingerprint.

This is important because the timestamp changes every poll. Including it would cause the same kill to repost repeatedly.

Recommended:

```env
DEDUP_TTL_SECONDS=600
DEDUP_CACHE_SIZE=3000
```

If kills still double or triple post:

```env
DEDUP_TTL_SECONDS=900
```

If you want to see suppressed duplicates:

```env
LOG_LEVEL=DEBUG
```

Look for:

```text
Duplicate kill suppressed
```

---

## Kill Type Detection

### Combat Kill

Default for normal weapons.

Examples:

```text
M1 Garand
Thompson
MP40
Kar98k
```

Embed line:

```text
**Kill Type:** ⚔️ Combat Kill
```

---

### Tank Kill

Detected from tank-related weapon names.

Examples:

```text
Sherman
Panzer
Tiger
75mm
76mm
88mm
Cannon
Main Gun
Recon Vehicle
```

Embed line:

```text
**Kill Type:** 🛡️ Tank Kill
```

Weapon line uses:

```text
💥
```

---

### Commander Ability

Detected from commander ability names.

Examples:

```text
Precision Strike
Bombing Run
Strafing Run
Katyusha
```

Embed line:

```text
**Kill Type:** 🧠 Commander Ability
```

Weapon line uses:

```text
🎯
```

---

### Team Kill

Detected when killer and victim are on the same team, or if the HLL admin log marks it as a team kill.

Embed title:

```text
Team Kill
```

Embed line:

```text
**Kill Type:** ⚠️ Team Kill
```

---

## Faction Emoji Detection

HLL RCON normally returns:

```text
Allies
Axis
```

The bot converts those into faction emojis.

Axis usually becomes:

```text
🇩🇪
```

Allies are inferred from map name when possible:

```text
US maps → 🇺🇸
British maps → 🇬🇧
Soviet maps → 🇷🇺
```

Examples:

```text
Driel → British
El Alamein → British
Mortain → British
Kursk → Soviet
Stalingrad → Soviet
Kharkov → Soviet
Most US/German maps → United States
```

If needed, use:

```env
ALLIES_FACTION_OVERRIDE=BRITISH
AXIS_FACTION_OVERRIDE=GERMANY
```

---

## Successful Railway Logs

Startup should show:

```text
Starting HLL webhook kill feed.
Connecting to HLL RCON at <host>:<port>
Connected to HLL RCON.
Server state: server=<server name> map=<map name> allies_faction=<faction> axis_faction=GERMANY
```

Successful kill post:

```text
Parsed kill event: killer=... victim=... weapon=... type=kill
Posted kill feed embed to Discord webhook.
```

Successful team kill post:

```text
Parsed kill event: killer=... victim=... weapon=... type=teamkill
Posted kill feed embed to Discord webhook.
```

---

## Troubleshooting

### Build Error: `hllrcon==0.2.1 does not exist`

Use:

```text
hllrcon==1.2.0.1
```

Current `requirements.txt`:

```text
aiohttp==3.9.5
hllrcon==1.2.0.1
```

---

### Import Error: `cannot import name 'HLLRcon'`

The code should use:

```python
from hllrcon import Rcon
```

Not:

```python
from hllrcon import HLLRcon
```

---

### Missing RCON Variables

Error:

```text
Missing RCON_HOST, RCON_PORT, or RCON_PASSWORD environment variable.
```

Fix by adding:

```env
RCON_HOST=
RCON_PORT=
RCON_PASSWORD=
```

in Railway Variables.

---

### Missing Webhook URL

Error:

```text
Missing KILL_FEED_WEBHOOK_URL environment variable.
```

Fix by adding:

```env
KILL_FEED_WEBHOOK_URL=
```

---

### `/app/main.py` Missing

Error:

```text
python: can't open file '/app/main.py'
```

Fix:

- Make sure `main.py` is in the GitHub repo root
- Make sure `Dockerfile` is in the GitHub repo root
- Do not upload the files inside another folder

---

### Connected to RCON But No Kills Post

Set:

```env
DEBUG_PARSE=true
```

Redeploy.

Look in Railway logs for:

```text
DEBUG admin-log sample
```

Those logs show the exact kill-log format your server provider returns.

After debugging:

```env
DEBUG_PARSE=false
```

---

### Connection Reset By Peer

Error:

```text
Connection reset by peer
```

This means the HLL RCON server closed the socket.

Try:

```env
POLL_INTERVAL_SECONDS=15
RECONNECT_DELAY_SECONDS=15
LOG_LOOKBACK_SECONDS=180
```

The bot automatically reconnects.

---

### Timeout During ServerConnect

Error may include:

```text
ServerConnect
TimeoutError
```

Check:

- RCON port is correct
- RCON password is correct
- RCON is enabled
- Server provider allows external RCON access
- Railway is not blocked by an RCON firewall or allowlist

---

### Double or Triple Posts

Use:

```env
DEDUP_TTL_SECONDS=900
DEDUP_CACHE_SIZE=3000
```

Also keep:

```env
DEBUG_PARSE=false
```

---

## Recommended Stable Railway Config

```env
RCON_HOST=your.server.ip.or.hostname
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...

LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10

DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=600

DEBUG_PARSE=false
DEBUG_SAMPLE_LIMIT=8
```

If RCON resets often:

```env
POLL_INTERVAL_SECONDS=15
RECONNECT_DELAY_SECONDS=15
LOG_LOOKBACK_SECONDS=180
```

If duplicates happen:

```env
DEDUP_TTL_SECONDS=900
```

---

## Updating the Bot

1. Replace files in GitHub
2. Commit changes
3. Push to GitHub
4. Railway auto-redeploys

Or manually redeploy from Railway.

---

## Notes

- Webhook-only
- No Discord bot token needed
- No player IDs are included in Discord embeds
- The bot must be running in Railway to post kills
- Kills during downtime may be missed
- HLL RCON polling is near-real-time, not instant
- Footer timestamp is current UTC time when the embed posts
- Timestamp is intentionally excluded from dedupe logic
