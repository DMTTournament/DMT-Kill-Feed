"""Small compatibility wrapper around the hllrcon package.

The public hllrcon package has changed method names across versions. This
wrapper keeps the Discord bot clean and tries the common typed helpers first,
then falls back to generic command methods when present.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Iterable

from hllrcon import Rcon


@dataclass(slots=True)
class HLLConfig:
    host: str
    port: int
    password: str


class HLLClient:
    def __init__(self, config: HLLConfig) -> None:
        self.config = config
        self._rcon = Rcon(host=config.host, port=config.port, password=config.password)

    async def close(self) -> None:
        disconnect = getattr(self._rcon, "disconnect", None)
        if disconnect:
            result = disconnect()
            if inspect.isawaitable(result):
                await result

    async def _call_first(self, names: Iterable[str], *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for name in names:
            method = getattr(self._rcon, name, None)
            if method is None:
                continue
            try:
                result = method(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                return result
            except TypeError as exc:
                # Try the next method name/signature.
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise AttributeError(f"None of these hllrcon methods exist: {', '.join(names)}")

    async def raw(self, command: str) -> Any:
        return await self._call_first(
            ["execute", "execute_command", "command", "send", "raw"], command
        )

    async def broadcast(self, message: str) -> Any:
        return await self._call_first(
            ["broadcast", "server_broadcast", "send_broadcast"], message
        )

    async def get_players(self) -> Any:
        return await self._call_first(
            ["get_players", "players", "get_player_ids", "get_detailed_players"]
        )

    async def get_server_info(self) -> Any:
        return await self._call_first(
            ["get_server_info", "get_server_information", "server_info", "get_info"]
        )

    async def show_log(self, minutes: int = 1, filter_text: str = "KILL") -> Any:
        """Return HLL server logs filtered to kill events when possible.

        Legacy/native HLL RCON supports: ShowLog <timespan_minutes> ["filter"].
        hllrcon method names have varied over time, so this tries helper methods
        first and falls back to a raw ShowLog command.
        """
        minutes = max(1, int(minutes))
        try:
            return await self._call_first(
                ["show_log", "get_logs", "get_log", "get_admin_log"], minutes, filter_text
            )
        except (TypeError, AttributeError):
            safe_filter = filter_text.replace('"', "")
            return await self.raw(f'ShowLog {minutes} "{safe_filter}"')

    async def kick(self, player_name_or_id: str, reason: str) -> Any:
        # Different versions accept name/player_id plus reason either positionally or named.
        try:
            return await self._call_first(
                ["kick", "kick_player"], player_name_or_id, reason
            )
        except TypeError:
            return await self._call_first(
                ["kick", "kick_player"], player=player_name_or_id, reason=reason
            )


def stringify_response(value: Any, limit: int = 1800) -> str:
    if value is None:
        text = "Done."
    elif isinstance(value, str):
        text = value
    else:
        text = repr(value)
    text = text.strip() or "Done."
    return text if len(text) <= limit else text[: limit - 3] + "..."
