"""
MCP Client for Assistant IA API
Provides integration with the MCP Context Server for datetime and context tools
"""
import logging
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP Context Server"""

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize MCP Client

        Args:
            base_url: Base URL of the MCP Context Server (e.g., http://mcp-context-server:8085)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"MCP Client initialized with base_url: {base_url}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    # DateTime Tools

    async def get_current_datetime(
        self, timezone: Optional[str] = None, format_type: str = "rfc3339"
    ) -> Dict[str, Any]:
        """
        Get current date and time in specified timezone

        Args:
            timezone: Timezone name (e.g., 'America/Argentina/Buenos_Aires')
            format_type: Output format ('rfc3339', 'iso8601', 'unix', 'readable')

        Returns:
            Dictionary with datetime information
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/datetime/current",
                json={"timezone": timezone, "format_type": format_type},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting current datetime: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get current datetime",
            }

    async def parse_natural_date(
        self,
        text: str,
        timezone: Optional[str] = None,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse natural language date/time into structured format

        Args:
            text: Natural language date string (e.g., "tomorrow at 3pm", "next Monday")
            timezone: Timezone for interpretation
            reference_date: Reference date for relative dates (ISO format)

        Returns:
            Parsed datetime information in multiple formats
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/datetime/parse",
                json={
                    "text": text,
                    "timezone": timezone,
                    "reference_date": reference_date,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error parsing natural date: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to parse natural language date: {text}",
            }

    async def convert_timezone(
        self, datetime_str: str, from_tz: str, to_tz: str
    ) -> Dict[str, Any]:
        """
        Convert datetime from one timezone to another

        Args:
            datetime_str: ISO format datetime string
            from_tz: Source timezone
            to_tz: Target timezone

        Returns:
            Converted datetime information
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/datetime/convert-timezone",
                json={"datetime_str": datetime_str, "from_tz": from_tz, "to_tz": to_tz},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error converting timezone: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to convert timezone",
            }

    async def calculate_time_difference(
        self, start_datetime: str, end_datetime: str
    ) -> Dict[str, Any]:
        """
        Calculate the difference between two datetimes

        Args:
            start_datetime: Start datetime (ISO format)
            end_datetime: End datetime (ISO format)

        Returns:
            Time difference in various units
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/datetime/difference",
                json={"start_datetime": start_datetime, "end_datetime": end_datetime},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error calculating time difference: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to calculate time difference",
            }

    async def add_time_to_date(
        self,
        datetime_str: str,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> Dict[str, Any]:
        """
        Add time duration to a datetime

        Args:
            datetime_str: Base datetime (ISO format)
            days: Days to add
            hours: Hours to add
            minutes: Minutes to add
            seconds: Seconds to add

        Returns:
            New datetime after adding the duration
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/tools/datetime/add-time",
                json={
                    "datetime_str": datetime_str,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error adding time to date: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to add time to date",
            }

    # Context Tools

    async def get_user_profile(
        self, user_id: str, api_key: str
    ) -> Dict[str, Any]:
        """
        Get user profile information

        Args:
            user_id: User identifier
            api_key: API key for authentication

        Returns:
            User profile data
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/tools/context/profile/{user_id}",
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve user profile",
            }

    async def get_user_timezone(
        self, user_id: str, api_key: str
    ) -> Dict[str, Any]:
        """
        Get user's preferred timezone

        Args:
            user_id: User identifier
            api_key: API key for authentication

        Returns:
            User's timezone information
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/tools/context/timezone/{user_id}",
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting user timezone: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve user timezone",
            }

    async def get_aggregated_context(
        self,
        user_id: str,
        api_key: str,
        include_calendar: bool = True,
        include_whatsapp: bool = True,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated user context from multiple services

        Args:
            user_id: User identifier
            api_key: API key for authentication
            include_calendar: Whether to include calendar data
            include_whatsapp: Whether to include WhatsApp data
            authorization: Authorization header for protected endpoints

        Returns:
            Aggregated context from all relevant services
        """
        try:
            headers = {"X-API-Key": api_key}
            if authorization:
                headers["Authorization"] = authorization

            response = await self.client.post(
                f"{self.base_url}/tools/context/aggregated",
                headers=headers,
                json={
                    "user_id": user_id,
                    "include_calendar": include_calendar,
                    "include_whatsapp": include_whatsapp,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting aggregated context: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve aggregated context",
            }

    # Helper Methods

    async def parse_date_for_workflow(
        self, text: str, user_timezone: str
    ) -> Optional[str]:
        """
        Convenience method to parse natural language date and return RFC3339 format
        Useful for workflow execution where RFC3339 dates are needed

        Args:
            text: Natural language date string
            user_timezone: User's timezone

        Returns:
            RFC3339 formatted datetime string or None if parsing fails
        """
        result = await self.parse_natural_date(text, user_timezone)
        if result.get("success"):
            return result["parsed_datetime"]["rfc3339"]
        logger.warning(f"Failed to parse date '{text}': {result.get('message')}")
        return None

    async def get_user_current_time(
        self, user_id: str, api_key: str, format_type: str = "readable"
    ) -> Optional[str]:
        """
        Get current time in user's timezone

        Args:
            user_id: User identifier
            api_key: API key for authentication
            format_type: Desired format

        Returns:
            Formatted datetime string or None if fails
        """
        # First get user's timezone
        tz_result = await self.get_user_timezone(user_id, api_key)
        if not tz_result.get("success"):
            logger.warning(f"Could not get timezone for user {user_id}")
            return None

        user_tz = tz_result.get("timezone", "UTC")

        # Get current time in that timezone
        time_result = await self.get_current_datetime(user_tz, format_type)
        if time_result.get("success"):
            return time_result["formats"].get(format_type)

        return None

    async def health_check(self) -> bool:
        """
        Check if MCP server is healthy

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"MCP health check failed: {str(e)}")
            return False
