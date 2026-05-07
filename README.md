# HLL Webhook Kill Feed Bot

A Railway-ready Hell Let Loose RCON kill feed that posts live kills directly to a Discord webhook.

This version is webhook-only. It does **not** require a Discord bot token.

---

## Features

- Posts HLL kills to Discord using a webhook
- No Discord bot account required
- No player IDs shown in Discord
- Green embeds for normal kills
- Yellow embeds for team kills
- 3-line embed format
- Shows:
  - Killer
  - Victim
  - Weapon
  - Kill Type
  - Server Name
  - HLL server-log timestamp
- Detects:
  - Combat Kill
  - Tank Kill
  - Commander Ability
  - Team Kill
- Pulls timestamp from the HLL admin/server log
- Formats timestamp as:

```text
06 MAY 26 - 14:34 UTC
```

- Adds server name + timestamp to embed footer
- Supports US / British / Soviet / German faction emojis
- Uses map-based faction detection where possible
- Railway-ready
- Automatic reconnect handling
- Duplicate kill suppression
- Railway-visible error logging
- Optional parser debug logging

---

## Required Files

Your GitHub repo should contain these files at the **root level**:

```text
main.py
requirements.txt
Dockerfile
railway.json
README.md
.env.example
```

Correct:

```text
repo/
  main.py
  Dockerfile
  requirements.txt
  railway.json
```

Wrong:

```text
repo/
  hll-killfeed/
    main.py
    Dockerfile
```

If Railway says:

```text
python: can't open file '/app/main.py'
```

then your files are probably inside an extra folder instead of the repo root.

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
2. Go to the channel where you want kill feed posts
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

Example format:

```text
https://discord.com/api/webhooks/xxxxxxxx/xxxxxxxx
```

Use that value for:

```env
KILL_FEED_WEBHOOK_URL=
```

---

## GitHub Setup

1. Create a new GitHub repository
2. Extract the bot ZIP
3. Upload all bot files directly to the repo root
4. Commit the files

Your repo should show `main.py` immediately when opened.

---

## Railway Setup

1. Go to Railway
2. Create a new project
3. Select:

```text
Deploy from GitHub repo
```

4. Choose your bot repository
5. Let Railway build the project
6. Add the variables below
7. Redeploy

---

## Railway Variables

Go to:

```text
Railway → Project → Service → Variables
```

---

### Required Variables

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
- `RCON_PORT` is not always the game port
- `RCON_PASSWORD` must match your server provider’s RCON password

Example:

```env
RCON_HOST=40.27.44.10
RCON_PORT=7779
RCON_PASSWORD=YourPasswordHere
KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

### Recommended Variables

```env
LOG_LEVEL=INFO
LOG_LOOKBACK_SECONDS=120
POLL_INTERVAL_SECONDS=8
RECONNECT_DELAY_SECONDS=10

DEDUP_CACHE_SIZE=3000
DEDUP_TTL_SECONDS=300

DEBUG_PARSE=false
DEBUG_SAMPLE_LIMIT=8
```

---

### Optional Override Variables

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

Accepted faction-style values include:

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

Controls how much detail appears in Railway logs.

Recommended:

```env
LOG_LEVEL=INFO
```

For troubleshooting duplicate suppression or parsing:

```env
LOG_LEVEL=DEBUG
```

---

### `LOG_LOOKBACK_SECONDS`

How far back the bot asks the HLL admin log for kill events.

Recommended:

```env
LOG_LOOKBACK_SECONDS=120
```

If you miss kills, you can increase it.

Example:

```env
LOG_LOOKBACK_SECONDS=180
```

---

### `POLL_INTERVAL_SECONDS`

How often the bot checks the HLL admin log.

Recommended:

```env
POLL_INTERVAL_SECONDS=8
```

If you see frequent RCON disconnects or:

```text
Connection reset by peer
```

increase it:

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

If your server resets connections often:

```env
RECONNECT_DELAY_SECONDS=15
```

---

### `DEDUP_CACHE_SIZE`

How many recent kill fingerprints the bot remembers.

Recommended:

```env
DEDUP_CACHE_SIZE=3000
```

---

### `DEDUP_TTL_SECONDS`

How long duplicate kills are suppressed.

Recommended:

```env
DEDUP_TTL_SECONDS=300
```

If kills double or triple post:

```env
DEDUP_TTL_SECONDS=600
```

---

### `DEBUG_PARSE`

Prints sample HLL admin-log entries in Railway logs when the parser cannot match them.

Recommended after setup:

```env
DEBUG_PARSE=false
```

Use only when troubleshooting:

```env
DEBUG_PARSE=true
```

Then look for:

```text
DEBUG admin-log sample
```

Send those lines for parser tuning.

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
DMT #2 (US East) • 06 MAY 26 - 14:34 UTC
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
DMT #2 (US East) • 06 MAY 26 - 14:36 UTC
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
DMT #2 (US East) • 06 MAY 26 - 14:39 UTC
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
DMT #2 (US East) • 06 MAY 26 - 14:41 UTC
```

---

## Timestamp Behavior

The bot pulls the timestamp from the HLL admin/server log line.

It does **not** generate the kill time from Railway’s local clock.

Supported timestamp examples include:

```text
[2026.05.06-14.34.18:123] KILL: ...
[2026-05-06 14:34:18] KILL: ...
```

The bot formats those as:

```text
06 MAY 26 - 14:34 UTC
```

The footer format is:

```text
Server Name • DD MMM YY - HH:MM UTC
```

Example:

```text
DMT #2 (US East) • 06 MAY 26 - 14:34 UTC
```

If the HLL log line does not include a usable timestamp, the bot may show:

```text
Unknown Time
```

or the raw timestamp returned by the server provider.

---

## Kill Type Detection

### Combat Kill

Default type for regular infantry/weapon kills.

Example weapons:
- M1 Garand
- Thompson
- MP40
- Kar98k

Embed line:

```text
**Kill Type:** ⚔️ Combat Kill
```

---

### Tank Kill

Detected from tank-related weapon names.

Examples:
- Sherman
- Panzer
- Tiger
- 75mm
- 76mm
- 88mm
- Cannon
- Main Gun
- Recon Vehicle

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

Detected from commander ability weapon names.

Examples:
- Precision Strike
- Bombing Run
- Strafing Run
- Katyusha

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

Detected when killer and victim are on the same team or when the admin log marks the event as a team kill.

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

HLL RCON usually exposes teams as:

```text
Allies
Axis
```

The bot converts those into faction emojis.

Axis usually becomes:

```text
🇩🇪
```

Allies are inferred from the current map when possible:

```text
US maps → 🇺🇸
British maps → 🇬🇧
Soviet maps → 🇷🇺
```

Examples:
- Driel → British
- El Alamein → British
- Mortain → British
- Kursk → Soviet
- Stalingrad → Soviet
- Kharkov → Soviet
- Most US/German maps → United States

If needed, override manually:

```env
ALLIES_FACTION_OVERRIDE=BRITISH
AXIS_FACTION_OVERRIDE=GERMANY
```

---

## Duplicate Kill Protection

The bot suppresses duplicate posts by creating a fingerprint from:

```text
killer | killer team | victim | victim team | weapon | timestamp | kill/teamkill
```

That prevents the same admin-log kill from posting multiple times across polls or reconnects.

Recommended:

```env
DEDUP_TTL_SECONDS=300
DEDUP_CACHE_SIZE=3000
```

If duplicates still occur:

```env
DEDUP_TTL_SECONDS=600
```

---

## Railway Logs

Successful startup should show something like:

```text
Starting HLL webhook kill feed.
Connecting to HLL RCON at <host>:<port>
Connected to HLL RCON.
Server state: server=<server name> map=<map name> allies_faction=<faction> axis_faction=GERMANY
```

Successful kill parsing should show:

```text
Parsed kill event: killer=... victim=... weapon=... time=...
Posted kill feed embed to Discord webhook.
```

---

## Troubleshooting

### Build Error: `hllrcon==0.2.1 does not exist`

Use:

```text
hllrcon==1.2.0.1
```

Current `requirements.txt` should include:

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

### Runtime Error: Missing RCON variables

Error:

```text
Missing RCON_HOST, RCON_PORT, or RCON_PASSWORD environment variable.
```

Fix:

Add these Railway variables:

```env
RCON_HOST=
RCON_PORT=
RCON_PASSWORD=
```

Then redeploy.

---

### Webhook Not Posting

Check that this is set:

```env
KILL_FEED_WEBHOOK_URL=
```

Make sure the webhook URL is copied from Discord and has not been deleted.

---

### Connected to RCON But No Kills Post

Set:

```env
DEBUG_PARSE=true
```

Redeploy.

Then check Railway logs for:

```text
DEBUG admin-log sample
```

Those samples show the exact log format your server provider returns.

After debugging, set:

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

The bot will automatically reconnect.

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

Increase:

```env
DEDUP_TTL_SECONDS=600
```

Also keep:

```env
DEBUG_PARSE=false
```

---

### `/app/main.py` Missing

Error:

```text
python: can't open file '/app/main.py'
```

Fix your GitHub repo layout.

`main.py` must be in the repo root.

---

## Recommended Stable Railway Config

Use this as your baseline:

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
DEDUP_TTL_SECONDS=300

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
DEDUP_TTL_SECONDS=600
```

---

## Updating the Bot

1. Replace files in GitHub
2. Commit changes
3. Push to GitHub
4. Railway will auto-redeploy

Or manually redeploy in Railway.

---

## Notes

- This is webhook-only
- No Discord bot token is needed
- No player IDs are included in Discord messages
- The bot must remain running in Railway to post kills
- Kills during downtime may be missed
- HLL RCON polling is near-real-time, not instant
- The timestamp comes from the HLL server/admin log when available
