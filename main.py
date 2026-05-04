import asyncio
import logging
import os
import re
from collections import deque
from typing import Optional

import aiohttp
from hllrcon import Rcon

RCON_HOST = os.getenv("RCON_HOST", "").strip()
RCON_PORT = int(os.getenv("RCON_PORT", "0") or "0")
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "").strip()
WEBHOOK_URL = os.getenv("KILL_FEED_WEBHOOK_URL", "").strip()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LOOKBACK_SECONDS = int(os.getenv("LOG_LOOKBACK_SECONDS", "60") or "60")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "2") or "2")
RECONNECT_DELAY_SECONDS = float(os.getenv("RECONNECT_DELAY_SECONDS", "5") or "5")
DEDUP_CACHE_SIZE = int(os.getenv("DEDUP_CACHE_SIZE", "500") or "500")

SERVER_NAME_OVERRIDE = os.getenv("SERVER_NAME_OVERRIDE", "").strip()
ALLIES_FACTION_OVERRIDE = os.getenv("ALLIES_FACTION_OVERRIDE", "").strip().upper()
AXIS_FACTION_OVERRIDE = os.getenv("AXIS_FACTION_OVERRIDE", "").strip().upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("hll-webhook-killfeed")

SERVER_NAME = SERVER_NAME_OVERRIDE or "Unknown Server"
CURRENT_MAP = "Unknown Map"
ALLIES_FACTION = ALLIES_FACTION_OVERRIDE or "US"
AXIS_FACTION = AXIS_FACTION_OVERRIDE or "GERMANY"

seen_cache = deque(maxlen=DEDUP_CACHE_SIZE)
seen_set = set()

FACTION_EMOJIS = {
    "US": "🇺🇸",
    "USA": "🇺🇸",
    "UNITED STATES": "🇺🇸",
    "BRITISH": "🇬🇧",
    "UK": "🇬🇧",
    "COMMONWEALTH": "🇬🇧",
    "RUSSIAN": "🇷🇺",
    "RUSSIA": "🇷🇺",
    "SOVIET": "🇷🇺",
    "USSR": "🇷🇺",
    "GERMAN": "🇩🇪",
    "GERMANY": "🇩🇪",
    "AXIS": "🇩🇪",
}

def infer_allies_faction_from_map(map_name: str) -> str:
    m = (map_name or "").lower()

    if any(x in m for x in ["driel", "el alamein", "mortain"]):
        return "BRITISH"

    if any(x in m for x in ["kursk", "stalingrad", "kharkov"]):
        return "SOVIET"

    return "US"

def get_team_emoji(team: str) -> str:
    team_clean = (team or "").strip().lower()

    if team_clean == "allies":
        faction = ALLIES_FACTION_OVERRIDE or ALLIES_FACTION
        return FACTION_EMOJIS.get(faction.upper(), "🇺🇸")

    if team_clean == "axis":
        faction = AXIS_FACTION_OVERRIDE or AXIS_FACTION
        return FACTION_EMOJIS.get(faction.upper(), "🇩🇪")

    return "❔"

COMMANDER_WEAPONS = [
    "precision strike",
    "bombing run",
    "strafe",
    "strafing run",
    "katyusha",
]

TANK_WEAPON_KEYWORDS = [
    "panzer",
    "sherman",
    "tiger",
    "puma",
    "luchs",
    "stuart",
    "greyhound",
    "half-track",
    "halftrack",
    "recon vehicle",
    "medium tank",
    "heavy tank",
    "light tank",
    "75mm",
    "76mm",
    "88mm",
    "37mm",
    "50mm",
    "57mm",
    "cannon",
    "main gun",
]

def get_kill_type(weapon: str):
    w = (weapon or "").lower()

    if any(x in w for x in COMMANDER_WEAPONS):
        return "Commander Ability", "🧠", "🎯"

    if any(x in w for x in TANK_WEAPON_KEYWORDS):
        return "Tank Kill", "🛡️", "💥"

    return "Combat Kill", "⚔️", "🔫"

KILL_RE = re.compile(
    r"(?P<prefix>TEAM\s*KILL|TEAMKILL|KILL)\s*:\s*"
    r"(?P<killer>.+?)\s*\((?P<killer_team>Allies|Axis)\)\s*"
    r"(?:->|killed|team killed)\s*"
    r"(?P<victim>.+?)\s*\((?P<victim_team>Allies|Axis)\)\s*"
    r"(?:with|using)\s*"
    r"(?P<weapon>.+)$",
    re.IGNORECASE,
)

def clean_name(name: str) -> str:
    return (name or "").strip().strip('"').strip("'")

def parse_kill_line(line: str) -> Optional[dict]:
    if not line or "KILL" not in line.upper():
        return None

    match = KILL_RE.search(line)
    if not match:
        logger.debug("Unparsed kill-like log line: %s", line)
        return None

    killer_team = match.group("killer_team").title()
    victim_team = match.group("victim_team").title()
    prefix = match.group("prefix").upper().replace(" ", "")

    return {
        "killer": clean_name(match.group("killer")),
        "victim": clean_name(match.group("victim")),
        "killer_team": killer_team,
        "victim_team": victim_team,
        "weapon": match.group("weapon").strip(),
        "is_teamkill": prefix == "TEAMKILL" or killer_team == victim_team,
    }

async def send_webhook_embed(embed: dict) -> None:
    payload = {"embeds": [embed]}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload) as resp:
                if resp.status not in (200, 204):
                    body = await resp.text()
                    logger.error("Discord webhook failed. status=%s body=%s", resp.status, body[:500])
                else:
                    logger.debug("Posted kill feed embed to Discord webhook.")
    except Exception:
        logger.exception("Failed to post Discord webhook embed.")

def build_embed(event: dict) -> dict:
    is_teamkill = event["is_teamkill"]

    killer_emoji = get_team_emoji(event["killer_team"])
    victim_emoji = get_team_emoji(event["victim_team"])

    kill_type, kill_type_icon, weapon_icon = get_kill_type(event["weapon"])

    if is_teamkill:
        title = "Team Kill"
        action_text = "team killed"
        kill_type = "Team Kill"
        kill_type_icon = "⚠️"
        weapon_icon = "🔫"
        color = 0xF1C40F
    else:
        title = "Kill"
        action_text = "killed"
        color = 0x2ECC71

    description = (
        f"{killer_emoji} **{event['killer']}** {action_text} {victim_emoji} **{event['victim']}**\n"
        f"**Weapon:** {weapon_icon} {event['weapon']}\n"
        f"**Kill Type:** {kill_type_icon} {kill_type}"
    )

    return {
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": SERVER_NAME},
    }

async def refresh_server_state(rcon: Rcon) -> None:
    global SERVER_NAME, CURRENT_MAP, ALLIES_FACTION, AXIS_FACTION

    try:
        session = await rcon.get_server_session()

        SERVER_NAME = SERVER_NAME_OVERRIDE or getattr(session, "server_name", SERVER_NAME) or SERVER_NAME
        CURRENT_MAP = getattr(session, "map_name", CURRENT_MAP) or CURRENT_MAP

        if not ALLIES_FACTION_OVERRIDE:
            ALLIES_FACTION = infer_allies_faction_from_map(CURRENT_MAP)

        if not AXIS_FACTION_OVERRIDE:
            AXIS_FACTION = "GERMANY"

        logger.info(
            "Server state: server=%s map=%s allies_faction=%s axis_faction=%s",
            SERVER_NAME,
            CURRENT_MAP,
            ALLIES_FACTION,
            AXIS_FACTION,
        )

    except Exception:
        logger.exception("Could not fetch server session. Using fallback server/map/faction values.")

async def fetch_admin_log_lines(rcon: Rcon) -> list[str]:
    response = await rcon.get_admin_log(LOG_LOOKBACK_SECONDS, "kill")

    if hasattr(response, "entries"):
        return [entry.message for entry in response.entries]

    if isinstance(response, list):
        lines = []
        for item in response:
            if hasattr(item, "message"):
                lines.append(item.message)
            else:
                lines.append(str(item))
        return lines

    if isinstance(response, str):
        return response.splitlines()

    return [str(response)]

def remember_seen(line: str) -> bool:
    if line in seen_set:
        return False

    if len(seen_cache) == seen_cache.maxlen:
        old = seen_cache.popleft()
        seen_set.discard(old)

    seen_cache.append(line)
    seen_set.add(line)
    return True

async def connect_rcon() -> Rcon:
    rcon = Rcon(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
        logger=logging.getLogger("hllrcon"),
    )
    await rcon.wait_until_connected()
    return rcon

async def run() -> None:
    if not RCON_HOST or not RCON_PORT or not RCON_PASSWORD:
        raise RuntimeError("Missing RCON_HOST, RCON_PORT, or RCON_PASSWORD environment variable.")

    if not WEBHOOK_URL:
        raise RuntimeError("Missing KILL_FEED_WEBHOOK_URL environment variable.")

    logger.info("Starting HLL webhook kill feed.")
    logger.info("Connecting to HLL RCON at %s:%s", RCON_HOST, RCON_PORT)

    rcon = await connect_rcon()
    logger.info("Connected to HLL RCON.")

    await refresh_server_state(rcon)

    while True:
        try:
            lines = await fetch_admin_log_lines(rcon)

            for line in lines:
                if not remember_seen(line):
                    continue

                event = parse_kill_line(line)
                if not event:
                    continue

                embed = build_embed(event)
                await send_webhook_embed(embed)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

        except Exception:
            logger.exception("RCON loop error. Reconnecting after delay.")
            try:
                rcon.disconnect()
            except Exception:
                logger.debug("RCON disconnect failed during error handling.", exc_info=True)

            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

            rcon = await connect_rcon()
            logger.info("Reconnected to HLL RCON.")
            await refresh_server_state(rcon)

if __name__ == "__main__":
    asyncio.run(run())
