"""
MCP datetime/context tools — in-process implementation.
Replaces the former HTTP client to the mcp-context-server microservice.
"""
import logging
import os
import socket
import time
import uuid
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import httpx

from src.core.platform.utils.datetime_tools import DatetimeTools

logger = logging.getLogger(__name__)

_AVATAR_PROBE_TTL_SECONDS = 5.0
_AVATAR_PROBE_TIMEOUT_SECONDS = 0.2


class MCPClient:
    """In-process wrapper around DatetimeTools. Mirrors the original async API."""

    def __init__(self, **kwargs):
        self._tools = DatetimeTools()
        self._avatar_url = os.getenv("AVATAR_MCP_URL", "http://127.0.0.1:47850/mcp")
        self._avatar_timeout = float(os.getenv("AVATAR_MCP_TIMEOUT", "2.0"))
        self._avatar_probe_at = 0.0
        self._avatar_probe_result = False
        logger.info("MCPClient initialized (in-process DatetimeTools)")

    def avatar_available(self) -> bool:
        """Whether the companion app is accepting connections right now.

        The app is started and stopped independently of the API, so this is
        probed instead of configured. The result is cached briefly because it
        is consulted once per request while building the prompt and the tools.
        """
        now = time.monotonic()
        if now - self._avatar_probe_at < _AVATAR_PROBE_TTL_SECONDS:
            return self._avatar_probe_result

        parsed = urlparse(self._avatar_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        try:
            with socket.create_connection((host, port), _AVATAR_PROBE_TIMEOUT_SECONDS):
                available = True
        except OSError:
            available = False

        if available != self._avatar_probe_result:
            logger.info("Avatar app %s", "detected" if available else "no longer reachable")
        self._avatar_probe_at = now
        self._avatar_probe_result = available
        return available

    async def _avatar_call(self, tool: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call the avatar's stateless Streamable HTTP MCP endpoint."""
        request_id = str(uuid.uuid4())
        async with httpx.AsyncClient(timeout=self._avatar_timeout) as client:
            initialize = await client.post(
                self._avatar_url,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "gillie", "version": "1.0"},
                    },
                },
                headers={"Accept": "application/json, text/event-stream"},
            )
            initialize.raise_for_status()
            result = initialize.json()
            if "error" in result:
                raise RuntimeError(result["error"].get("message", "Avatar MCP initialize failed"))

            response = await client.post(
                self._avatar_url,
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments or {}},
                },
                headers={"Accept": "application/json, text/event-stream"},
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", f"Avatar MCP tool failed: {tool}"))
            return payload.get("result", {})

    async def avatar_play_animation(self, animation: str) -> bool:
        try:
            await self._avatar_call("play_animation", {"animation": animation})
            return True
        except Exception as exc:
            logger.warning("Avatar MCP unavailable while playing %s: %s", animation, exc)
            return False

    async def avatar_control_window(self, action: str) -> bool:
        try:
            await self._avatar_call("control_window", {"action": action})
            return True
        except Exception as exc:
            logger.warning("Avatar MCP unavailable while controlling window: %s", exc)
            return False

    async def avatar_status(self) -> Dict[str, Any]:
        return await self._avatar_call("get_status")

    async def avatar_set_voice_state(
        self,
        phase: str,
        activity: str,
        microphone_muted: bool = False,
        output_muted: bool = False,
    ) -> bool:
        try:
            await self._avatar_call(
                "set_voice_state",
                {
                    "phase": phase,
                    "activity": activity,
                    "microphoneMuted": microphone_muted,
                    "outputMuted": output_muted,
                },
            )
            return True
        except Exception as exc:
            logger.debug("Avatar MCP unavailable while setting voice state: %s", exc)
            return False

    async def avatar_set_audio_level(self, level: float) -> bool:
        try:
            await self._avatar_call("set_audio_level", {"level": max(0.0, min(1.0, level))})
            return True
        except Exception as exc:
            logger.debug("Avatar MCP unavailable while setting audio level: %s", exc)
            return False

    async def get_current_datetime(
        self, timezone: Optional[str] = None, format_type: str = "rfc3339"
    ) -> Dict[str, Any]:
        return self._tools.get_current_datetime(tz=timezone or "UTC")

    async def parse_natural_date(
        self,
        text: str,
        timezone: Optional[str] = None,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._tools.parse_natural_date(
            text=text, tz=timezone or "UTC", reference_date=reference_date
        )

    async def convert_timezone(
        self, datetime_str: str, from_tz: str, to_tz: str
    ) -> Dict[str, Any]:
        return self._tools.convert_timezone(
            datetime_str=datetime_str, from_tz=from_tz, to_tz=to_tz
        )

    async def calculate_time_difference(
        self, start_datetime: str, end_datetime: str
    ) -> Dict[str, Any]:
        return self._tools.calculate_difference(
            start=start_datetime, end=end_datetime
        )

    async def add_time_to_date(
        self,
        datetime_str: str,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> Dict[str, Any]:
        return self._tools.add_time(
            datetime_str=datetime_str,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )

    async def parse_date_for_workflow(
        self, text: str, user_timezone: str
    ) -> Optional[str]:
        result = await self.parse_natural_date(text, user_timezone)
        if result.get("success"):
            return result.get("parsed_datetime", {}).get("rfc3339")
        logger.warning(f"Failed to parse date '{text}': {result.get('message')}")
        return None

    async def get_user_current_time(
        self, user_id: str, api_key: str, format_type: str = "readable"
    ) -> Optional[str]:
        result = await self.get_current_datetime()
        if result.get("success"):
            return result.get("formats", {}).get(format_type)
        return None

    async def health_check(self) -> bool:
        return True

    async def get_user_profile(self, user_id: str, api_key: str) -> Dict[str, Any]:
        return {"success": False, "message": "Context tools not available in single-user mode"}

    async def get_user_timezone(self, user_id: str, api_key: str) -> Dict[str, Any]:
        return {"success": False, "message": "Context tools not available in single-user mode"}

    async def get_aggregated_context(self, *args, **kwargs) -> Dict[str, Any]:
        return {"success": False, "message": "Context tools not available in single-user mode"}

    async def close(self):
        pass
