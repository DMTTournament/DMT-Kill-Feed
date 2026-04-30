import asyncio
import inspect
import json
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("hll-webhook-killfeed")

RCON_HOST = os.getenv("RCON_HOST", "").strip()
RCON_PORT = int(os.getenv("RCON_PORT", "0") or 0)
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "").strip()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", os.getenv("KILL_FEED_WEBHOOK_URL", "")).strip()
WEBHOOK_USERNAME = os.getenv("WEBHOOK_USERNAME", os.getenv("KILL_FEED_WEBHOOK_USERNAME", "HLL Kill Feed")).strip()

POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
RECONNECT_DELAY_SECONDS = float(os.getenv("RECONNECT_DELAY_SECONDS", "5"))
LOG_LOOKBACK_SECONDS = int(os.getenv("LOG_LOOKBACK_SECONDS", "120"))
SKIP_STARTUP_BACKLOG = os.getenv("SKIP_STARTUP_BACKLOG", "true").lower() in {"1", "true", "yes", "y"}
DEDUP_CACHE_SIZE = int(os.getenv("DEDUP_CACHE_SIZE", "500"))
MAP_REFRESH_SECONDS = int(os.getenv("MAP_REFRESH_SECONDS", "60"))
SERVER_NAME_REFRESH_SECONDS = int(os.getenv("SERVER_NAME_REFRESH_SECONDS", "300"))
SERVER_NAME_OVERRIDE = os.getenv("SERVER_NAME_OVERRIDE", "").strip()
SERVER_NAME_FALLBACK = os.getenv("SERVER_NAME_FALLBACK", "HLL Server").strip()
SEND_TEST_KILL = os.getenv("SEND_TEST_KILL", "false").lower() in {"1", "true", "yes", "y"}

# Optional manual overrides, useful when a server/map name is not recognized.
# Valid values: US, BRITISH, SOVIET, GERMAN, ALLIES, AXIS
ALLIES_FACTION_OVERRIDE = os.getenv("ALLIES_FACTION", "").strip().upper()
AXIS_FACTION_OVERRIDE = os.getenv("AXIS_FACTION", "").strip().upper()

GREEN = 0x2ECC71
YELLOW = 0xF1C40F

TEAM_EMOJIS = {
    "ALLIES": "🟦",
    "AXIS": "🟥",
    "US": "🇺🇸",
    "USA": "🇺🇸",
    "UNITED STATES": "🇺🇸",
    "BRITISH": "🇬🇧",
    "BRITAIN": "🇬🇧",
    "UK": "🇬🇧",
    "SOVIET": "🇷🇺",
    "USSR": "🇷🇺",
    "RUSSIAN": "🇷🇺",
    "GERMAN": "🇩🇪",
    "GERMANY": "🇩🇪",
}

# HLL maps by faction pairing. Axis is currently German for these maps.
US_ALLIED_MAP_KEYWORDS = [
    "utah", "omaha", "saintemereeglise", "sainte mere eglise", "sme",
    "carentan", "purpleheartlane", "purple heart lane", "phl",
    "hurtgen", "hurtgen forest", "hürtgen", "foy", "hill400", "hill 400",
    "kursk_1945",  # harmless if unused by your server naming
]
BRITISH_ALLIED_MAP_KEYWORDS = [
    "elalamein", "el alamein", "driel", "mortain", "tobruk",
]
SOVIET_ALLIED_MAP_KEYWORDS = [
    "stalingrad", "kursk", "kharkov",
]

COMMANDER_ABILITY_KEYWORDS = [
    "precision strike", "bombing run", "strafing run", "strafe", "commander",
]

TANK_WEAPON_KEYWORDS = [
    "panzer", "sherman", "tiger", "stuart", "luchs", "puma", "greyhound",
    "t-34", "t34", "is-1", "is1", "churchill", "cromwell", "firefly",
    "dingo", "daimler", "half-track", "halftrack", "recon vehicle",
    "tank", "75mm", "76mm", "88mm", "57mm", "37mm", "2 pounder", "6 pounder",
    "cannon", "main gun", "coaxial",
]

@dataclass(frozen=True)
class KillEvent:
    killer: str
    killer_team: str
    victim: str
    victim_team: str
    weapon: str
    is_teamkill: bool
    raw: str


def normalize_map_name(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


def detect_factions_from_map(map_name: Optional[str]) -> tuple[str, str]:
    if ALLIES_FACTION_OVERRIDE:
        allies = ALLIES_FACTION_OVERRIDE
    else:
        clean = normalize_map_name(map_name)
        compact = clean.replace(" ", "")
        allies = "ALLIES"
        for key in US_ALLIED_MAP_KEYWORDS:
            if key.replace(" ", "") in compact or key in clean:
                allies = "US"
                break
        for key in BRITISH_ALLIED_MAP_KEYWORDS:
            if key.replace(" ", "") in compact or key in clean:
                allies = "BRITISH"
                break
        for key in SOVIET_ALLIED_MAP_KEYWORDS:
            if key.replace(" ", "") in compact or key in clean:
                allies = "SOVIET"
                break

    axis = AXIS_FACTION_OVERRIDE or "GERMAN"
    return allies, axis


def emoji_for_team(team: str, allies_faction: str, axis_faction: str) -> str:
    team_upper = (team or "").upper()
    if team_upper == "ALLIES":
        return TEAM_EMOJIS.get(allies_faction.upper(), TEAM_EMOJIS["ALLIES"])
    if team_upper == "AXIS":
        return TEAM_EMOJIS.get(axis_faction.upper(), TEAM_EMOJIS["AXIS"])
    return TEAM_EMOJIS.get(team_upper, "▫️")


def get_kill_type(weapon: str) -> tuple[str, str]:
    weapon_lower = (weapon or "").lower()
    if any(x in weapon_lower for x in COMMANDER_ABILITY_KEYWORDS):
        return "Commander Ability", "🎯"
    if any(x in weapon_lower for x in TANK_WEAPON_KEYWORDS):
        return "Tank Kill", "🛡️"
    return "Combat Kill", "⚔️"


def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def clean_team(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"allied", "allies", "ally", "blue"}:
        return "Allies"
    if v in {"axis", "red"}:
        return "Axis"
    return value.strip().title() if value else "Unknown"


KILL_PATTERNS = [
    # KILL: Killer(Allies/765...) -> Victim(Axis/765...) with Weapon
    re.compile(
        r"(?P<type>TEAM KILL|TEAMKILL|KILL)\s*:?\s*"
        r"(?P<killer>.+?)\s*\((?P<killer_team>Allies|Axis)[^)]*\)\s*"
        r"(?:->|killed|team killed|TK'd|TKed)\s*"
        r"(?P<victim>.+?)\s*\((?P<victim_team>Allies|Axis)[^)]*\)\s*"
        r"(?:with|using|by)\s*(?P<weapon>.+)$",
        re.IGNORECASE,
    ),
    # [KILL] Killer [Allies] killed Victim [Axis] with Weapon
    re.compile(
        r"\[?(?P<type>TEAM KILL|TEAMKILL|KILL)\]?\s*:?\s*"
        r"(?P<killer>.+?)\s*\[(?P<killer_team>Allies|Axis)\]\s*"
        r"(?:->|killed|team killed|TK'd|TKed)\s*"
        r"(?P<victim>.+?)\s*\[(?P<victim_team>Allies|Axis)\]\s*"
        r"(?:with|using|by)\s*(?P<weapon>.+)$",
        re.IGNORECASE,
    ),
    # HLL CRCON/AdminLog common-ish: KILL: Killer(Axis) -> Victim(Allies) with weapon
    re.compile(
        r"(?P<type>TEAM KILL|TEAMKILL|KILL).*?"
        r"(?P<killer>[^\(\[]+?)\s*[\(\[](?P<killer_team>Allies|Axis).*?[\)\]]\s*"
        r".*?(?:->|killed|team killed).*?"
        r"(?P<victim>[^\(\[]+?)\s*[\(\[](?P<victim_team>Allies|Axis).*?[\)\]]\s*"
        r".*?(?:with|using|by)\s*(?P<weapon>[^\n\r]+)",
        re.IGNORECASE,
    ),
]


def parse_kill_line(line: str) -> Optional[KillEvent]:
    raw = line.strip()
    if not raw:
        return None

    # Only spend regex time on likely kill lines.
    upper = raw.upper()
    if "KILL" not in upper:
        return None

    for pattern in KILL_PATTERNS:
        match = pattern.search(raw)
        if not match:
            continue
        data = match.groupdict()
        killer = clean_name(data.get("killer", ""))
        victim = clean_name(data.get("victim", ""))
        weapon = clean_name(data.get("weapon", "Unknown Weapon"))
        killer_team = clean_team(data.get("killer_team", ""))
        victim_team = clean_team(data.get("victim_team", ""))
        is_teamkill = "TEAM" in data.get("type", "").upper() or (
            killer_team != "Unknown" and killer_team == victim_team
        )
        if killer and victim:
            return KillEvent(killer, killer_team, victim, victim_team, weapon, is_teamkill, raw)

    logger.debug("Unparsed likely kill log line: %s", raw)
    return None


def split_log_lines(log_text: Any) -> list[str]:
    if log_text is None:
        return []
    if isinstance(log_text, list):
        return [str(x) for x in log_text]
    if isinstance(log_text, dict):
        for key in ("logs", "entries", "result", "data"):
            if key in log_text:
                return split_log_lines(log_text[key])
        return [json.dumps(log_text)]
    return str(log_text).splitlines()


def dedupe_key(event: KillEvent) -> str:
    # No player IDs are included. Raw line helps prevent duplicates while keeping private IDs out of Discord.
    return f"{event.killer}|{event.killer_team}|{event.victim}|{event.victim_team}|{event.weapon}|{event.is_teamkill}|{event.raw}"


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def call_method(obj: Any, names: list[str], *args, **kwargs) -> Any:
    last_error = None
    for name in names:
        method = getattr(obj, name, None)
        if method is None:
            continue
        try:
            return await maybe_await(method(*args, **kwargs))
        except TypeError as exc:
            last_error = exc
            # Try no kwargs or fewer args below for signature differences.
            try:
                return await maybe_await(method(*args))
            except Exception as exc2:
                last_error = exc2
        except Exception as exc:
            last_error = exc
            raise
    raise RuntimeError(f"Could not call any method from {names}. Last error: {last_error}")


async def connect_rcon() -> Any:
    try:
        from hllrcon import Rcon  # type: ignore
    except Exception:
        try:
            from hllrcon.rcon import Rcon  # type: ignore
        except Exception as exc:
            raise RuntimeError("Could not import hllrcon Rcon. Check requirements.txt install.") from exc

    logger.info("Connecting to HLL RCON at %s:%s", RCON_HOST, RCON_PORT)
    try:
        rcon = Rcon(RCON_HOST, RCON_PORT, RCON_PASSWORD)
    except TypeError:
        rcon = Rcon(host=RCON_HOST, port=RCON_PORT, password=RCON_PASSWORD)

    if hasattr(rcon, "connect"):
        await maybe_await(rcon.connect())
    if hasattr(rcon, "login"):
        await maybe_await(rcon.login())
    elif hasattr(rcon, "authenticate"):
        await maybe_await(rcon.authenticate())

    logger.info("Connected to HLL RCON")
    logger.debug("Available RCON methods: %s", sorted([m for m in dir(rcon) if not m.startswith('_')])[:200])
    return rcon


async def close_rcon(rcon: Any) -> None:
    for name in ("close", "disconnect", "stop"):
        method = getattr(rcon, name, None)
        if method:
            try:
                await maybe_await(method())
            except Exception:
                logger.debug("Error while closing RCON", exc_info=True)
            return


async def fetch_logs(rcon: Any) -> list[str]:
    # hllrcon V2 command wrapper. In timraay/hllrcon this is get_admin_log(seconds_span, filter_).
    method = getattr(rcon, "get_admin_log", None)
    if method:
        try:
            result = await maybe_await(method(LOG_LOOKBACK_SECONDS, "kill"))
        except TypeError:
            try:
                result = await maybe_await(method(seconds_span=LOG_LOOKBACK_SECONDS, filter_="kill"))
            except TypeError:
                result = await maybe_await(method(LOG_LOOKBACK_SECONDS))
        return split_log_lines(result)

    # Fallbacks for other wrappers.
    for name in ("admin_log", "get_admin_logs", "show_log", "get_logs", "get_log"):
        method = getattr(rcon, name, None)
        if not method:
            continue
        try:
            result = await maybe_await(method(LOG_LOOKBACK_SECONDS, "kill"))
        except TypeError:
            try:
                result = await maybe_await(method(LOG_LOOKBACK_SECONDS))
            except TypeError:
                result = await maybe_await(method())
        return split_log_lines(result)

    raise RuntimeError("Could not find a usable HLL admin log method. Expected get_admin_log on the installed hllrcon version.")


async def fetch_current_map(rcon: Any) -> Optional[str]:
    for names in (["get_current_map"], ["current_map"], ["get_map"], ["map"]):
        try:
            result = await call_method(rcon, names)
            if isinstance(result, dict):
                for key in ("current_map", "map", "name", "result"):
                    if key in result:
                        return str(result[key])
            if result:
                return str(result)
        except Exception:
            continue
    return None


async def fetch_server_name(rcon: Any) -> Optional[str]:
    if SERVER_NAME_OVERRIDE:
        return SERVER_NAME_OVERRIDE

    for names in (["get_server_name"], ["server_name"], ["get_name"], ["name"]):
        try:
            result = await call_method(rcon, names)
            if isinstance(result, dict):
                for key in ("server_name", "name", "hostname", "result"):
                    if key in result and result[key]:
                        return str(result[key])
            if result:
                return str(result)
        except Exception:
            continue
    return None


async def post_webhook(
    session: aiohttp.ClientSession,
    event: KillEvent,
    allies_faction: str,
    axis_faction: str,
    server_name: Optional[str],
) -> None:
    killer_emoji = emoji_for_team(event.killer_team, allies_faction, axis_faction)
    victim_emoji = emoji_for_team(event.victim_team, allies_faction, axis_faction)

    if event.is_teamkill:
        action_text = "team killed"
        kill_type = "Team Kill"
        kill_icon = "⚠️"
        weapon_icon = "🔫"
        title = "Team Kill"
        color = YELLOW
    else:
        action_text = "killed"
        kill_type, kill_icon = get_kill_type(event.weapon)
        title = "Kill"
        color = GREEN
        if kill_type == "Tank Kill":
            weapon_icon = "💥"
        elif kill_type == "Commander Ability":
            weapon_icon = "🎯"
        else:
            weapon_icon = "🔫"

    description = (
        f"{killer_emoji} **{event.killer}** {action_text} {victim_emoji} **{event.victim}**\n"
        f"**Weapon:** {weapon_icon} {event.weapon}\n"
        f"**Kill Type:** {kill_icon} {kill_type}"
    )

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "footer": {"text": server_name or SERVER_NAME_FALLBACK},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = {"username": WEBHOOK_USERNAME, "embeds": [embed]}

    async with session.post(WEBHOOK_URL, json=payload, timeout=15) as response:
        body = await response.text()
        if response.status >= 300:
            logger.error("Discord webhook failed: status=%s body=%s", response.status, body[:1000])
            response.raise_for_status()
        logger.debug("Posted kill feed event: %s", description)


async def post_test_kill_webhook(session: aiohttp.ClientSession, server_name: Optional[str]) -> None:
    embed = {
        "title": "Kill",
        "description": (
            "🇺🇸 **Test_Player1** killed 🇩🇪 **Test_Player2**\n"
            "**Weapon:** 🔫 M1 Garand\n"
            "**Kill Type:** ⚔️ Combat Kill"
        ),
        "color": GREEN,
        "footer": {"text": server_name or SERVER_NAME_FALLBACK},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload = {"username": WEBHOOK_USERNAME, "embeds": [embed]}
    async with session.post(WEBHOOK_URL, json=payload, timeout=15) as response:
        body = await response.text()
        if response.status >= 300:
            logger.error("Discord test kill webhook failed: status=%s body=%s", response.status, body[:1000])
            response.raise_for_status()
        logger.info("Test kill webhook sent successfully.")


async def run() -> None:
    if not RCON_HOST or not RCON_PORT or not RCON_PASSWORD:
        raise RuntimeError("Missing RCON_HOST, RCON_PORT, or RCON_PASSWORD environment variable.")
    if not WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL environment variable.")

    seen = set()
    seen_order = deque(maxlen=DEDUP_CACHE_SIZE)
    startup_complete = not SKIP_STARTUP_BACKLOG
    current_map = None
    server_name = SERVER_NAME_OVERRIDE or SERVER_NAME_FALLBACK
    allies_faction, axis_faction = detect_factions_from_map(None)
    last_map_refresh = 0.0
    last_server_name_refresh = 0.0
    test_kill_sent = False

    async with aiohttp.ClientSession() as session:
        while True:
            rcon = None
            try:
                rcon = await connect_rcon()
                while True:
                    now = asyncio.get_running_loop().time()
                    if now - last_map_refresh >= MAP_REFRESH_SECONDS:
                        detected_map = await fetch_current_map(rcon)
                        if detected_map and detected_map != current_map:
                            current_map = detected_map
                            allies_faction, axis_faction = detect_factions_from_map(current_map)
                            logger.info(
                                "Current map detected: %s | Allies faction: %s | Axis faction: %s",
                                current_map,
                                allies_faction,
                                axis_faction,
                            )
                        last_map_refresh = now

                    if now - last_server_name_refresh >= SERVER_NAME_REFRESH_SECONDS:
                        detected_server_name = await fetch_server_name(rcon)
                        if detected_server_name and detected_server_name != server_name:
                            server_name = detected_server_name
                            logger.info("Server name detected: %s", server_name)
                        last_server_name_refresh = now

                    # Sends only once per running Railway process, and only when enabled.
                    if SEND_TEST_KILL and not test_kill_sent:
                        await post_test_kill_webhook(session, server_name)
                        test_kill_sent = True

                    lines = await fetch_logs(rcon)
                    events = []
                    for line in lines:
                        try:
                            event = parse_kill_line(line)
                        except Exception:
                            logger.exception("Parser error for log line: %s", line)
                            continue
                        if not event:
                            continue
                        key = dedupe_key(event)
                        if key in seen:
                            continue
                        seen.add(key)
                        seen_order.append(key)
                        while len(seen) > seen_order.maxlen:
                            old = seen_order.popleft()
                            seen.discard(old)
                        events.append(event)

                    if not startup_complete:
                        logger.info("Startup backlog skipped: %s kill events found but not posted.", len(events))
                        startup_complete = True
                    else:
                        for event in events:
                            await post_webhook(session, event, allies_faction, axis_faction, server_name)

                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
            except Exception:
                logger.exception("RCON loop error. Reconnecting after delay.")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            finally:
                if rcon is not None:
                    await close_rcon(rcon)


if __name__ == "__main__":
    asyncio.run(run())
