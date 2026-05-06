# HLL Webhook Kill Feed Bot

A Hell Let Loose RCON killfeed bot that posts live kills directly to a Discord webhook.

Features:
- Live kill feed from HLL RCON
- Discord webhook only (no Discord bot token required)
- Green embeds for kills
- Yellow embeds for team kills
- Shows:
  - Killer
  - Victim
  - Weapon
  - Kill Type
  - Team/Faction
  - Server Name
- Detects:
  - Combat Kills
  - Tank Kills
  - Commander Abilities
- Railway compatible
- Automatic reconnect handling
- Duplicate kill suppression
- Error logging in Railway logs
- Supports US / British / Soviet faction detection

---

# Files Included

Your repo should contain:

```text
main.py
requirements.txt
Dockerfile
railway.json
README.md
```

IMPORTANT:
Do NOT place the files inside another folder.
They must be in the ROOT of the GitHub repository.

Correct:
```text
repo/
  main.py
  Dockerfile
```

Wrong:
```text
repo/
  some-folder/
    main.py
```

---

# Requirements

You need:

- A Hell Let Loose game server with RCON enabled
- RCON Host/IP
- RCON Port
- RCON Password
- A Discord server
- A Discord webhook URL
- A Railway account
- A GitHub account

---

# Step 1 — Create Discord Webhook

In Discord:

1. Open your Discord server
2. Open channel settings
3. Go to:
   Integrations → Webhooks
4. Click:
   Create Webhook
5. Copy the webhook URL

Example:

```text
https://discord.com/api/webhooks/xxxxxxxx/xxxxxxxx
```

Save this for Railway variables.

---

# Step 2 — Upload Bot Files to GitHub

1. Extract the ZIP
2. Create a new GitHub repository
3. Upload all files directly into the repo root

The repo root must contain:
- main.py
- requirements.txt
- Dockerfile
- railway.json

---

# Step 3 — Create Railway Project

1. Go to Railway
2. Click:
   New Project
3. Select:
   Deploy from GitHub repo
4. Select your repository

Railway will automatically build the bot.

---

# Step 4 — Add Railway Variables

In Railway:

Go to:

```text
Project → Variables
```

Add these variables.

---

## Required Variables

```env
RCON_HOST=your.server.ip
RCON_PORT=your_rcon_port
RCON_PASSWORD=your_rcon_password

KILL_FEED_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## Recommended Variables

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

# Variable Explanations

## LOG_LOOKBACK_SECONDS

How far back the admin log is checked.

Recommended:
```env
120
```

---

## POLL_INTERVAL_SECONDS

How often the bot checks for new kills.

Recommended:
```env
8
```

If you get frequent:
```text
Connection reset by peer
```

increase this to:
```env
15
```

---

## DEDUP_TTL_SECONDS

How long duplicate kills are suppressed.

Recommended:
```env
300
```

If kills double post:
```env
600
```

---

# Step 5 — Deploy

Click:

```text
Deploy
```

Railway will:
- Build container
- Install dependencies
- Start the killfeed

---

# Successful Startup Logs

You should see:

```text
Starting HLL webhook kill feed.
Connecting to HLL RCON
Connected to HLL RCON
Server state:
```

Example:

```text
Server state: server=DMT #2 map=ELSENBORN RIDGE
```

---

# Example Discord Kill Feed

## Normal Kill

```text
🇺🇸 BigKat killed 🇩🇪 TankHunter
Weapon: 🔫 M1 Garand
Kill Type: ⚔️ Combat Kill
```

Green embed.

---

## Tank Kill

```text
🇺🇸 ShermanAce killed 🇩🇪 PanzerCrew
Weapon: 💥 75mm Cannon
Kill Type: 🛡️ Tank Kill
```

Green embed.

---

## Commander Ability

```text
🇺🇸 Commander killed 🇩🇪 SquadLead
Weapon: 🎯 Precision Strike
Kill Type: 🧠 Commander Ability
```

Green embed.

---

## Team Kill

```text
🇺🇸 BlueBerry team killed 🇺🇸 Friendly
Weapon: 🔫 Thompson
Kill Type: ⚠️ Team Kill
```

Yellow embed.

---

# Faction Detection

The bot automatically detects:
- US
- British
- Soviet
- German

based on the current map.

Examples:
- El Alamein → British
- Kursk → Soviet
- Omaha → US

---

# Troubleshooting

---

## Error:
```text
Missing RCON_HOST
```

You forgot Railway variables.

Go to:
```text
Railway → Variables
```

Add:
- RCON_HOST
- RCON_PORT
- RCON_PASSWORD

---

## Error:
```text
python: can't open file '/app/main.py'
```

Your repo structure is wrong.

Move:
```text
main.py
```

to the root of the GitHub repo.

---

## Error:
```text
ImportError: cannot import name 'HLLRcon'
```

Wrong hllrcon version.

Correct:
```text
hllrcon==1.2.0.1
```

---

## Error:
```text
Connection reset by peer
```

The HLL server closed the RCON socket.

Increase:
```env
POLL_INTERVAL_SECONDS=15
```

and/or:

```env
RECONNECT_DELAY_SECONDS=15
```

---

## No kills posting

Temporarily set:

```env
DEBUG_PARSE=true
```

Then check Railway logs for:

```text
DEBUG admin-log sample
```

Those lines can be used to tune the parser.

After working:
```env
DEBUG_PARSE=false
```

---

## Duplicate Kills

Increase:

```env
DEDUP_TTL_SECONDS=600
```

---

# Updating the Bot

1. Replace files in GitHub
2. Push changes
3. Railway auto-redeploys

---

# Notes

- No Discord bot token needed
- Webhook only
- No player IDs shown
- Works continuously
- Automatically reconnects
- Railway logs all errors
