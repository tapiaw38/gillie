import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)


class DatetimeTools:
    """
    Pure-Python datetime utilities.
    Replaces the HTTP calls to the MCP Context Server.
    """

    # ── Current datetime ─────────────────────────────────────────────────────

    def get_current_datetime(self, tz: str = "UTC") -> Dict[str, Any]:
        """Return current datetime in multiple formats."""
        try:
            zone = ZoneInfo(tz)
            now = datetime.now(zone)
            return {
                "success": True,
                "timezone": tz,
                "rfc3339": now.isoformat(),
                "iso8601": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "unix": int(now.timestamp()),
                "readable": now.strftime("%A, %B %d %Y %H:%M:%S %Z"),
                "date_only": now.strftime("%Y-%m-%d"),
                "time_only": now.strftime("%H:%M:%S"),
            }
        except ZoneInfoNotFoundError:
            return {"success": False, "error": f"unknown timezone: {tz}"}
        except Exception as e:
            logger.error(f"get_current_datetime error: {e}")
            return {"success": False, "error": str(e)}

    # ── Natural language parsing ─────────────────────────────────────────────

    def parse_natural_date(
        self,
        text: str,
        tz: str = "UTC",
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parse natural language date/time string."""
        try:
            import dateparser

            settings: Dict[str, Any] = {
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": tz,
            }
            if reference_date:
                settings["RELATIVE_BASE"] = datetime.fromisoformat(reference_date)

            parsed = dateparser.parse(text, settings=settings)
            if not parsed:
                return {"success": False, "error": f"could not parse: '{text}'"}

            return {
                "success": True,
                "rfc3339": parsed.isoformat(),
                "iso8601": parsed.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "unix": int(parsed.timestamp()),
                "readable": parsed.strftime("%A, %B %d %Y %H:%M:%S %Z"),
                "date_only": parsed.strftime("%Y-%m-%d"),
                "time_only": parsed.strftime("%H:%M:%S"),
                "timezone": tz,
            }
        except ImportError:
            return {"success": False, "error": "dateparser library not installed"}
        except Exception as e:
            logger.error(f"parse_natural_date error: {e}")
            return {"success": False, "error": str(e)}

    # ── Timezone conversion ──────────────────────────────────────────────────

    def convert_timezone(self, datetime_str: str, from_tz: str, to_tz: str) -> Dict[str, Any]:
        """Convert a datetime string from one timezone to another."""
        try:
            source_zone = ZoneInfo(from_tz)
            target_zone = ZoneInfo(to_tz)

            dt = datetime.fromisoformat(datetime_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=source_zone)

            converted = dt.astimezone(target_zone)
            return {
                "success": True,
                "original": datetime_str,
                "from_tz": from_tz,
                "to_tz": to_tz,
                "converted": converted.isoformat(),
                "readable": converted.strftime("%A, %B %d %Y %H:%M:%S %Z"),
            }
        except ZoneInfoNotFoundError as e:
            return {"success": False, "error": f"unknown timezone: {e}"}
        except Exception as e:
            logger.error(f"convert_timezone error: {e}")
            return {"success": False, "error": str(e)}

    # ── Time difference ──────────────────────────────────────────────────────

    def calculate_difference(self, start: str, end: str) -> Dict[str, Any]:
        """Calculate the difference between two ISO datetime strings."""
        try:
            dt_start = datetime.fromisoformat(start)
            dt_end = datetime.fromisoformat(end)
            delta = dt_end - dt_start
            total_seconds = int(delta.total_seconds())
            sign = "" if total_seconds >= 0 else "-"
            abs_seconds = abs(total_seconds)
            days = abs_seconds // 86400
            hours = (abs_seconds % 86400) // 3600
            minutes = (abs_seconds % 3600) // 60
            seconds = abs_seconds % 60
            human = f"{sign}{days}d {hours}h {minutes}m {seconds}s"
            return {
                "success": True,
                "total_seconds": total_seconds,
                "days": int(delta.days),
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "human_readable": human,
            }
        except Exception as e:
            logger.error(f"calculate_difference error: {e}")
            return {"success": False, "error": str(e)}

    # ── Add time ─────────────────────────────────────────────────────────────

    def add_time(
        self,
        datetime_str: str,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> Dict[str, Any]:
        """Add a duration to a datetime string."""
        try:
            dt = datetime.fromisoformat(datetime_str)
            result = dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            return {
                "success": True,
                "original": datetime_str,
                "result": result.isoformat(),
                "readable": result.strftime("%A, %B %d %Y %H:%M:%S"),
                "added": {"days": days, "hours": hours, "minutes": minutes, "seconds": seconds},
            }
        except Exception as e:
            logger.error(f"add_time error: {e}")
            return {"success": False, "error": str(e)}
