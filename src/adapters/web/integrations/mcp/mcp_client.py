"""
MCP datetime/context tools — in-process implementation.
Replaces the former HTTP client to the mcp-context-server microservice.
"""
import logging
from typing import Dict, Any, Optional

from src.core.platform.utils.datetime_tools import DatetimeTools

logger = logging.getLogger(__name__)


class MCPClient:
    """In-process wrapper around DatetimeTools. Mirrors the original async API."""

    def __init__(self, **kwargs):
        self._tools = DatetimeTools()
        logger.info("MCPClient initialized (in-process DatetimeTools)")

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
