from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional


LOG_PREFIX_RE = re.compile(r"^\[(?P<ago>[^\]]+)\]\s*(?P<body>.*)$")
KILL_RE = re.compile(
    r"^(?P<kind>TEAM KILL|KILL):\s+"
    r"(?P<killer>.+)\((?P<killer_team>Allies|Axis|None)/(?P<killer_id>[^)]*)\)\s+->\s+"
    r"(?P<victim>.+)\((?P<victim_team>Allies|Axis|None)/(?P<victim_id>[^)]*)\)\s+with\s+"
    r"(?P<weapon>.+)$"
)


@dataclass(frozen=True, slots=True)
class KillEvent:
    raw_line: str
    log_time: str
    kind: str
    killer: str
    killer_team: str
    killer_id: str
    victim: str
    victim_team: str
    victim_id: str
    weapon: str

    @property
    def is_team_kill(self) -> bool:
        return self.kind.upper() == "TEAM KILL"

    @property
    def key(self) -> str:
        # HLL logs include an epoch-like timestamp inside the prefix. The full line is
        # still the safest de-dupe key because many kills can happen in the same second.
        return self.raw_line.strip()


def parse_kill_line(line: str) -> Optional[KillEvent]:
    line = line.strip()
    if not line:
        return None

    prefix = LOG_PREFIX_RE.match(line)
    log_time = ""
    body = line
    if prefix:
        log_time = prefix.group("ago").strip()
        body = prefix.group("body").strip()

    match = KILL_RE.match(body)
    if not match:
        return None

    data = match.groupdict()
    return KillEvent(
        raw_line=line,
        log_time=log_time,
        kind=data["kind"],
        killer=data["killer"].strip(),
        killer_team=data["killer_team"].strip(),
        killer_id=data["killer_id"].strip(),
        victim=data["victim"].strip(),
        victim_team=data["victim_team"].strip(),
        victim_id=data["victim_id"].strip(),
        weapon=data["weapon"].strip(),
    )


def parse_kill_log(raw_log: object) -> list[KillEvent]:
    if raw_log is None:
        return []
    text = str(raw_log).strip()
    if not text or text.upper() == "EMPTY":
        return []
    events: list[KillEvent] = []
    for line in text.splitlines():
        event = parse_kill_line(line)
        if event:
            events.append(event)
    return events
