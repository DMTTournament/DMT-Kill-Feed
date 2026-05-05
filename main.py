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
LOG_LOOKBACK_SECONDS = int(os.getenv("LOG_LOOKBACK_SECONDS", "120") or "120")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "8") or "8")
RECONNECT_DELAY_SECONDS = float(os.getenv("RECONNECT_DELAY_SECONDS", "10") or "10")
DEDUP_CACHE_SIZE = int(os.getenv("DEDUP_CACHE_SIZE", "1000") or "1000")

DEBUG_PARSE = os.getenv("DEBUG_PARSE", "true").lower() == "true"
DEBUG_SAMPLE_LIMIT = int(os.getenv("DEBUG_SAMPLE_LIMIT", "8") or "8")

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
debug_logged_samples = 0

FACTION_EMOJIS = {
    "US": "🇺🇸", "USA": "🇺🇸", "UNITED STATES": "🇺🇸",
    "BRITISH": "🇬🇧", "UK": "🇬🇧", "COMMONWEALTH": "🇬🇧",
    "RUSSIAN": "🇷🇺", "RUSSIA": "🇷🇺", "SOVIET": "🇷🇺", "USSR": "🇷🇺",
    "GERMAN": "🇩🇪", "GERMANY": "🇩🇪", "AXIS": "🇩🇪",
}

def infer_allies_faction_from_map(map_name: str) -> str:
    m = (map_name or "").lower()
    if any(x in m for x in ["driel", "el alamein", "mortain"]):
        return "BRITISH"
    if any(x in m for x in ["kursk", "stalingrad", "kharkov"]):
        return "SOVIET"
    return "US"

def get_team_emoji(team: str) -> str:
    t = (team or "").strip().lower()
    if t == "allies":
        return FACTION_EMOJIS.get((ALLIES_FACTION_OVERRIDE or ALLIES_FACTION).upper(), "🇺🇸")
    if t == "axis":
        return FACTION_EMOJIS.get((AXIS_FACTION_OVERRIDE or AXIS_FACTION).upper(), "🇩🇪")
    return "❔"

COMMANDER_WEAPONS = ["precision strike", "bombing run", "strafe", "strafing run", "katyusha"]
TANK_WEAPON_KEYWORDS = [
    "panzer", "sherman", "tiger", "puma", "luchs", "stuart", "greyhound",
    "half-track", "halftrack", "recon vehicle", "medium tank", "heavy tank",
    "light tank", "75mm", "76mm", "88mm", "37mm", "50mm", "57mm", "cannon",
    "main gun", "coaxial",
]

def get_kill_type(weapon: str):
    w = (weapon or "").lower()
    if any(x in w for x in COMMANDER_WEAPONS):
        return "Commander Ability", "🧠", "🎯"
    if any(x in w for x in TANK_WEAPON_KEYWORDS):
        return "Tank Kill", "🛡️", "💥"
    return "Combat Kill", "⚔️", "🔫"

SIMPLE_KILL_RE = re.compile(
    r"(?P<prefix>TEAM\s*KILL|TEAMKILL|KILL)\s*:\s*"
    r"(?P<killer>.+?)\s*\((?P<killer_team>Allies|Axis)\)\s*"
    r"(?:->|killed|team killed)\s*"
    r"(?P<victim>.+?)\s*\((?P<victim_team>Allies|Axis)\)\s*"
    r"(?:with|using)\s*(?P<weapon>.+)$",
    re.IGNORECASE,
)

TEAM_IN_PARENS_RE = re.compile(
    r"(?P<prefix>TEAM\s*KILL|TEAMKILL|KILL)\s*:\s*"
    r"(?P<killer>.+?)\s*\((?P<killer_team>Allies|Axis)(?:[/|, ][^)]+)?\)\s*"
    r"(?:->|killed|team killed)\s*"
    r"(?P<victim>.+?)\s*\((?P<victim_team>Allies|Axis)(?:[/|, ][^)]+)?\)\s*"
    r"(?:with|using)\s*(?P<weapon>.+)$",
    re.IGNORECASE,
)

def get_attr_any(obj, names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj.get(name)
        if hasattr(obj, name):
            return getattr(obj, name)
    return default

def clean_name(name: str) -> str:
    return (name or "").strip().strip('"').strip("'")

def normalize_team(team: str) -> str:
    t = (team or "").strip().lower()
    if "all" in t or t in ["us", "usa", "british", "uk", "soviet", "russian"]:
        return "Allies"
    if "axis" in t or "german" in t:
        return "Axis"
    return team.title() if team else ""

def parse_entry_object(entry) -> Optional[dict]:
    action = str(get_attr_any(entry, ["action", "type", "event_type", "event"], "") or "")
    message = str(get_attr_any(entry, ["message", "text", "raw", "description"], "") or "")

    if "kill" not in action.lower() and "kill" not in message.lower():
        return None

    killer = get_attr_any(entry, ["player", "player_name", "killer", "attacker", "attacker_name", "source_player_name"])
    victim = get_attr_any(entry, ["victim", "victim_name", "target", "target_name", "target_player_name"])
    weapon = get_attr_any(entry, ["weapon", "weapon_name", "weapon_id", "cause"])
    killer_team = get_attr_any(entry, ["player_team", "killer_team", "attacker_team", "source_team"])
    victim_team = get_attr_any(entry, ["victim_team", "target_team"])

    if killer and victim and weapon and killer_team and victim_team:
        killer_team = normalize_team(str(killer_team))
        victim_team = normalize_team(str(victim_team))
        return {
            "killer": clean_name(str(killer)),
            "victim": clean_name(str(victim)),
            "killer_team": killer_team,
            "victim_team": victim_team,
            "weapon": str(weapon).strip(),
            "is_teamkill": "team" in action.lower() or killer_team == victim_team,
        }
    return None

def parse_kill_line(line: str) -> Optional[dict]:
    if not line or "KILL" not in line.upper():
        return None

    for pattern in [TEAM_IN_PARENS_RE, SIMPLE_KILL_RE]:
        match = pattern.search(line)
        if match:
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
    logger.debug("Unparsed kill-like log line: %s", line)
    return None

async def send_webhook_embed(embed: dict) -> None:
    payload = {"embeds": [embed]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload) as resp:
                if resp.status not in (200, 204):
                    body = await resp.text()
                    logger.error("Discord webhook failed. status=%s body=%s", resp.status, body[:500])
                else:
                    logger.info("Posted kill feed embed to Discord webhook.")
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

    return {"title": title, "description": description, "color": color, "footer": {"text": SERVER_NAME}}

async def connect_rcon() -> Rcon:
    rcon = Rcon(host=RCON_HOST, port=RCON_PORT, password=RCON_PASSWORD, logger=logging.getLogger("hllrcon"))
    await rcon.wait_until_connected()
    return rcon

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
        logger.info("Server state: server=%s map=%s allies_faction=%s axis_faction=%s",
                    SERVER_NAME, CURRENT_MAP, ALLIES_FACTION, AXIS_FACTION)
    except Exception:
        logger.exception("Could not fetch server session. Using fallback server/map/faction values.")

async def fetch_admin_log_entries(rcon: Rcon):
    response = await rcon.get_admin_log(LOG_LOOKBACK_SECONDS, "kill")
    if hasattr(response, "entries"):
        return list(response.entries)
    if isinstance(response, list):
        return response
    if isinstance(response, str):
        return response.splitlines()
    return [response]

def entry_to_line(entry) -> str:
    if isinstance(entry, str):
        return entry
    message = get_attr_any(entry, ["message", "text", "raw", "description"])
    return str(message) if message else str(entry)

def remember_seen(key: str) -> bool:
    if key in seen_set:
        return False
    if len(seen_cache) == seen_cache.maxlen:
        old = seen_cache.popleft()
        seen_set.discard(old)
    seen_cache.append(key)
    seen_set.add(key)
    return True

def log_debug_sample(entry) -> None:
    global debug_logged_samples
    if not DEBUG_PARSE or debug_logged_samples >= DEBUG_SAMPLE_LIMIT:
        return
    debug_logged_samples += 1
    logger.warning("DEBUG admin-log sample #%s: %r", debug_logged_samples, entry)
    if not isinstance(entry, str):
        attrs = {}
        for name in [
            "action", "type", "event_type", "event", "message", "player", "player_name",
            "killer", "attacker", "victim", "target", "weapon", "weapon_name",
            "player_team", "killer_team", "victim_team", "target_team"
        ]:
            if hasattr(entry, name):
                attrs[name] = str(getattr(entry, name))
        logger.warning("DEBUG admin-log entry attrs #%s: %s", debug_logged_samples, attrs)

async def run() -> None:
    if not RCON_HOST or not RCON_PORT or not RCON_PASSWORD:
        raise RuntimeError("Missing RCON_HOST, RCON_PORT, or RCON_PASSWORD environment variable.")
    if not WEBHOOK_URL:
        raise RuntimeError("Missing KILL_FEED_WEBHOOK_URL environment variable.")

    logger.info("Starting HLL webhook kill feed.")
    logger.info("Connecting to HLL RCON at %s:%s", RCON_HOST, RCON_PORT)

    while True:
        rcon = None
        try:
            rcon = await connect_rcon()
            logger.info("Connected to HLL RCON.")
            await refresh_server_state(rcon)

            while True:
                entries = await fetch_admin_log_entries(rcon)
                for entry in entries:
                    line = entry_to_line(entry)
                    if not remember_seen(line):
                        continue

                    event = parse_entry_object(entry) or parse_kill_line(line)
                    if not event:
                        log_debug_sample(entry)
                        continue

                    logger.info("Parsed kill event: killer=%s victim=%s weapon=%s type=%s",
                                event["killer"], event["victim"], event["weapon"],
                                "teamkill" if event["is_teamkill"] else "kill")
                    await send_webhook_embed(build_embed(event))

                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        except Exception:
            logger.exception("RCON loop error. Reconnecting after delay.")
            if rcon is not None:
                try:
                    rcon.disconnect()
                except Exception:
                    logger.debug("RCON disconnect failed during error handling.", exc_info=True)
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

if __name__ == "__main__":
    asyncio.run(run())
