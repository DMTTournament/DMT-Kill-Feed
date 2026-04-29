import asyncio
import hashlib
import logging
import os
import re
import sys
from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional

import aiohttp
from dotenv import load_dotenv
from hllrcon import Rcon

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("hll-webhook-killfeed")

HLL_RCON_HOST = os.environ.get("HLL_RCON_HOST", "")
HLL_RCON_PORT = int(os.environ.get("HLL_RCON_PORT", "0") or 0)
HLL_RCON_PASSWORD = os.environ.get("HLL_RCON_PASSWORD", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
WEBHOOK_USERNAME = os.getenv("WEBHOOK_USERNAME", "HLL Kill Feed")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
LOG_LOOKBACK_MINUTES = int(os.getenv("LOG_LOOKBACK_MINUTES", "3"))
SKIP_STARTUP_BACKLOG = os.getenv("SKIP_STARTUP_BACKLOG", "true").lower() in {"1", "true", "yes", "y"}
DEDUP_CACHE_SIZE = int(os.getenv("DEDUP_CACHE_SIZE", "500"))

KILL_EMBED_COLOR = int(os.getenv("KILL_EMBED_COLOR", "5763719"))  # Discord green
TEAMKILL_EMBED_COLOR = int(os.getenv("TEAMKILL_EMBED_COLOR", "16705372"))  # Discord yellow
TANK_KILL_EMBED_COLOR = int(os.getenv("TANK_KILL_EMBED_COLOR", str(KILL_EMBED_COLOR)))
COMMANDER_ABILITY_EMBED_COLOR = int(os.getenv("COMMANDER_ABILITY_EMBED_COLOR", str(KILL_EMBED_COLOR)))

TEAM_EMOJIS = {
    "allies": "🇺🇸",
    "ally": "🇺🇸",
    "axis": "🇩🇪",
    "german": "🇩🇪",
    "germany": "🇩🇪",
    "unknown": "❔",
    "": "❔",
}

# Most HLL kill log lines look like:
# [10:00 min (1639143551)] KILL: Player Name(Axis/765...) -> Other Player(Allies/765...) with MP40
# [10:00 min (1639143551)] TEAM KILL: Player Name(Allies/765...) -> Other Player(Allies/765...) with M1 GARAND
KILL_RE = re.compile(
    r"^\[(?P<age>.+?)\s+\((?P<ts>\d+)\)\]\s+"
    r"(?P<type>TEAM KILL|KILL):\s+"
    r"(?P<killer>.*?)\((?P<killer_team>[^/\)]+)(?:/[^\)]*)?\)\s+->\s+"
    r"(?P<victim>.*?)\((?P<victim_team>[^/\)]+)(?:/[^\)]*)?\)\s+with\s+"
    r"(?P<weapon>.+)$",
    re.IGNORECASE,
)

TANK_KEYWORDS = {
    "tank", "cannon", "coaxial", "hull mg", "75mm", "76mm", "88mm", "37mm", "50mm", "57mm",
    "stuart", "sherman", "jumbo", "panther", "tiger", "panzer", "luchs", "greyhound", "puma",
    "m5a1", "m4a1", "m4a3e2", "pz", "kwk", "ap shell", "he shell",
}

COMMANDER_ABILITY_KEYWORDS = {
    "precision strike", "bombing run", "strafing run", "katyusha", "commander", "artillery",
}

@dataclass(frozen=True)
class KillEvent:
    raw_line: str
    log_timestamp: str
    is_teamkill: bool
    killer: str
    killer_team: str
    victim: str
    victim_team: str
    weapon: str

    @property
    def is_tank_kill(self) -> bool:
        weapon = self.weapon.lower()
        return any(word in weapon for word in TANK_KEYWORDS)

    @property
    def is_commander_ability(self) -> bool:
        weapon = self.weapon.lower()
        return any(word in weapon for word in COMMANDER_ABILITY_KEYWORDS)

    @property
    def fingerprint(self) -> str:
        # No player IDs. Uses visible kill feed content plus server log timestamp.
        base = "|".join([
            self.log_timestamp,
            self.killer,
            self.killer_team,
            self.victim,
            self.victim_team,
            self.weapon,
            "tk" if self.is_teamkill else "kill",
        ])
        return hashlib.sha256(base.encode("utf-8", errors="replace")).hexdigest()


def validate_config() -> None:
    missing = []
    for key, value in {
        "HLL_RCON_HOST": HLL_RCON_HOST,
        "HLL_RCON_PORT": HLL_RCON_PORT,
        "HLL_RCON_PASSWORD": HLL_RCON_PASSWORD,
        "DISCORD_WEBHOOK_URL": DISCORD_WEBHOOK_URL,
    }.items():
        if not value:
            missing.append(key)
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def normalize_player_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip() or "Unknown Player"


def normalize_team(team: str) -> str:
    value = re.sub(r"\s+", " ", team).strip()
    return value or "Unknown"


def team_emoji(team: str) -> str:
    return TEAM_EMOJIS.get(team.strip().lower(), "❔")


def repair_multiline_logs(text: str) -> str:
    text = text.strip("\n")
    # HLL can place unescaped newlines inside some log types. Merge lines that do not start with a log prefix.
    return re.sub(r"\n(?!\[.+?\(\d+\)\])", r"\\n", text)


def parse_kill_line(line: str) -> Optional[KillEvent]:
    match = KILL_RE.match(line.strip())
    if not match:
        return None
    event = KillEvent(
        raw_line=line.strip(),
        log_timestamp=match.group("ts"),
        is_teamkill=match.group("type").upper() == "TEAM KILL",
        killer=normalize_player_name(match.group("killer")),
        killer_team=normalize_team(match.group("killer_team")),
        victim=normalize_player_name(match.group("victim")),
        victim_team=normalize_team(match.group("victim_team")),
        weapon=match.group("weapon").strip() or "Unknown Weapon",
    )
    return event


def parse_kill_events(log_text: str) -> list[KillEvent]:
    events: list[KillEvent] = []
    repaired = repair_multiline_logs(log_text)
    for line in repaired.splitlines():
        try:
            event = parse_kill_line(line)
            if event:
                events.append(event)
        except Exception:
            logger.exception("Failed to parse log line safely. line=%r", line[:500])
    return events


async def fetch_logs(rcon: Rcon, minutes: int) -> str:
    """Fetch logs using hllrcon while tolerating API naming differences across versions."""
    # Preferred / likely method candidates.
    candidates = [
        ("show_log", (minutes,)),
        ("show_logs", (minutes,)),
        ("get_logs", (minutes,)),
        ("get_game_logs", (minutes,)),
    ]
    for method_name, args in candidates:
        method = getattr(rcon, method_name, None)
        if method is None:
            continue
        try:
            result = await method(*args)
            return str(result)
        except TypeError:
            try:
                result = await method()
                return str(result)
            except Exception:
                logger.debug("RCON log method %s exists but failed without args", method_name, exc_info=True)
        except Exception:
            logger.debug("RCON log method %s failed", method_name, exc_info=True)

    # Fallback to generic command execution if exposed by hllrcon.
    command_candidates = ["execute", "execute_command", "command", "send", "send_command"]
    for method_name in command_candidates:
        method = getattr(rcon, method_name, None)
        if method is None:
            continue
        for command in (f"ShowLog {minutes}", f"showlog {minutes}"):
            try:
                result = await method(command)
                return str(result)
            except Exception:
                logger.debug("RCON generic command method %s failed for %s", method_name, command, exc_info=True)

    raise RuntimeError("Could not find a usable hllrcon log method. Check installed hllrcon version.")


def build_embed(event: KillEvent) -> dict:
    killer_display = f"{team_emoji(event.killer_team)} **{event.killer}**"
    victim_display = f"{team_emoji(event.victim_team)} **{event.victim}**"

    if event.is_teamkill:
        title = "🟡 ⚠️ Team Kill"
        color = TEAMKILL_EMBED_COLOR
        type_value = "⚠️ Team Kill"
    elif event.is_commander_ability:
        title = "🟢 🎯 Commander Ability"
        color = COMMANDER_ABILITY_EMBED_COLOR
        type_value = "🎯 Commander Ability"
    elif event.is_tank_kill:
        title = "🟢 💥 Tank Kill"
        color = TANK_KILL_EMBED_COLOR
        type_value = "💥 Tank Kill"
    else:
        title = "🟢 🔫 Kill Feed"
        color = KILL_EMBED_COLOR
        type_value = "⚔️ Combat Kill"

    return {
        "title": title,
        "description": f"{killer_display} eliminated {victim_display}",
        "color": color,
        "fields": [
            {"name": "🔫 Weapon", "value": event.weapon, "inline": True},
            {"name": "Type", "value": type_value, "inline": True},
            {"name": "Teams", "value": f"{event.killer_team} → {event.victim_team}", "inline": True},
        ],
        "footer": {"text": "HLL Live Feed"},
    }


async def post_to_webhook(session: aiohttp.ClientSession, event: KillEvent) -> None:
    payload = {
        "username": WEBHOOK_USERNAME,
        "embeds": [build_embed(event)],
        "allowed_mentions": {"parse": []},
    }
    async with session.post(DISCORD_WEBHOOK_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status >= 300:
            body = await resp.text()
            raise RuntimeError(f"Discord webhook failed with HTTP {resp.status}: {body[:500]}")


class DedupeCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.queue: deque[str] = deque(maxlen=max_size)
        self.items: set[str] = set()

    def add(self, value: str) -> None:
        if value in self.items:
            return
        if len(self.queue) == self.max_size:
            old = self.queue.popleft()
            self.items.discard(old)
        self.queue.append(value)
        self.items.add(value)

    def seen(self, value: str) -> bool:
        return value in self.items

    def seed(self, values: Iterable[str]) -> None:
        for value in values:
            self.add(value)


async def run() -> None:
    validate_config()
    logger.info("Starting HLL webhook kill feed. host=%s port=%s poll=%ss lookback=%sm", HLL_RCON_HOST, HLL_RCON_PORT, POLL_INTERVAL_SECONDS, LOG_LOOKBACK_MINUTES)

    rcon = Rcon(host=HLL_RCON_HOST, port=HLL_RCON_PORT, password=HLL_RCON_PASSWORD)
    dedupe = DedupeCache(DEDUP_CACHE_SIZE)

    async with aiohttp.ClientSession() as session:
        first_poll = True
        while True:
            try:
                async with rcon.connect():
                    logger.info("Connected to HLL RCON")
                    while True:
                        log_text = await fetch_logs(rcon, LOG_LOOKBACK_MINUTES)
                        events = parse_kill_events(log_text)

                        if first_poll and SKIP_STARTUP_BACKLOG:
                            dedupe.seed(event.fingerprint for event in events)
                            logger.info("Startup backlog skipped. seeded_events=%s", len(events))
                            first_poll = False
                            await asyncio.sleep(POLL_INTERVAL_SECONDS)
                            continue

                        first_poll = False
                        posted = 0
                        for event in events:
                            if dedupe.seen(event.fingerprint):
                                continue
                            dedupe.add(event.fingerprint)
                            try:
                                await post_to_webhook(session, event)
                                posted += 1
                                logger.info(
                                    "Posted kill event. type=%s killer=%r killer_team=%s victim=%r victim_team=%s weapon=%r",
                                    "teamkill" if event.is_teamkill else "kill",
                                    event.killer,
                                    event.killer_team,
                                    event.victim,
                                    event.victim_team,
                                    event.weapon,
                                )
                            except Exception:
                                logger.exception("Failed posting Discord webhook for event raw_line=%r", event.raw_line[:500])

                        logger.debug("Poll complete. parsed_events=%s posted_events=%s", len(events), posted)
                        await asyncio.sleep(POLL_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("RCON loop error. Reconnecting after delay.")
                try:
                    rcon.disconnect()
                except Exception:
                    logger.debug("RCON disconnect after error failed", exc_info=True)
                await asyncio.sleep(max(POLL_INTERVAL_SECONDS, 5))


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested")


if __name__ == "__main__":
    main()
