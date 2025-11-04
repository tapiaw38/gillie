import requests
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class GoogleCalendarIntegration:
    """
    Integration client for calendar-api-be microservice.

    This class handles communication with the calendar-api-be Go microservice
    which manages Google Calendar OAuth sessions and event operations.
    """

    def __init__(self, calendar_api_url: str):
        """
        Initialize Google Calendar integration.

        Args:
            calendar_api_url: Base URL of calendar-api-be service (e.g., http://calendar-api-be:8084)
        """
        self.calendar_api_url = calendar_api_url.rstrip('/')
        self.base_url = f"{self.calendar_api_url}/api/v1/calendar"

    def get_authorization_url(self, user_id: str, profile_id: str) -> Optional[str]:
        """
        Get Google Calendar OAuth authorization URL.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration

        Returns:
            Authorization URL or None if error
        """
        try:
            url = f"{self.base_url}/oauth/authorize"
            params = {
                "user_id": user_id,
                "profile_id": profile_id
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # calendar-api-be returns auth_url directly, not nested in data
                return data.get("auth_url")
            else:
                logger.error(
                    f"Error getting authorization URL: status={response.status_code}, "
                    f"response={response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Exception getting authorization URL: {str(e)}", exc_info=True)
            return None

    def check_session_status(self, user_id: str, profile_id: str) -> bool:
        """
        Check if user has an active Google Calendar session.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration

        Returns:
            True if session is active, False otherwise
        """
        try:
            url = f"{self.base_url}/oauth/status"
            params = {
                "user_id": user_id,
                "profile_id": profile_id
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # calendar-api-be returns is_active directly, not nested in data
                return data.get("is_active", False)
            else:
                return False

        except Exception as e:
            logger.error(f"Exception checking session status: {str(e)}", exc_info=True)
            return False

    def create_event(
        self,
        user_id: str,
        profile_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict[str, str]]] = None,
        reminders: Optional[List[Dict[str, Any]]] = None,
        jwt_token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a calendar event.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            title: Event title
            start_time: Event start time (ISO 8601 format)
            end_time: Event end time (ISO 8601 format)
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendees with email and name (optional)
            reminders: List of reminders (optional)
            jwt_token: JWT token for authentication (optional)

        Returns:
            Created event data or None if error
        """
        try:
            url = f"{self.base_url}/events"

            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            payload = {
                "user_id": user_id,
                "profile_id": profile_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
            }

            if description:
                payload["description"] = description
            if location:
                payload["location"] = location
            if attendees:
                payload["attendees"] = attendees
            if reminders:
                payload["reminders"] = reminders

            logger.info(f"Creating calendar event: user_id={user_id}, title={title}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                logger.info(f"Calendar event created successfully")
                return response.json().get("data")
            else:
                logger.error(
                    f"Error creating event: status={response.status_code}, "
                    f"response={response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Exception creating calendar event: {str(e)}", exc_info=True)
            return None

    def list_events(
        self,
        user_id: str,
        profile_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        jwt_token: Optional[str] = None
    ) -> List[Dict]:
        """
        List calendar events.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            start_date: Filter events starting from this date (ISO 8601 format)
            end_date: Filter events until this date (ISO 8601 format)
            limit: Maximum number of events to return
            jwt_token: JWT token for authentication (optional)

        Returns:
            List of events or empty list if error
        """
        try:
            url = f"{self.base_url}/events"

            headers = {}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            params = {
                "user_id": user_id,
                "profile_id": profile_id,
                "limit": limit
            }

            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            logger.info(f"Listing calendar events: user_id={user_id}, profile_id={profile_id}")

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json().get("data", [])
                logger.info(f"Retrieved {len(data)} calendar events")
                return data
            else:
                logger.error(
                    f"Error listing events: status={response.status_code}, "
                    f"response={response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Exception listing calendar events: {str(e)}", exc_info=True)
            return []

    def update_event(
        self,
        event_id: str,
        user_id: str,
        profile_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Update a calendar event.

        Args:
            event_id: Event ID to update
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            title: New event title (optional)
            start_time: New start time (ISO 8601 format, optional)
            end_time: New end time (ISO 8601 format, optional)
            description: New description (optional)
            location: New location (optional)
            jwt_token: JWT token for authentication (optional)

        Returns:
            Updated event data or None if error
        """
        try:
            url = f"{self.base_url}/events/{event_id}"

            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            payload = {
                "user_id": user_id,
                "profile_id": profile_id,
            }

            if title:
                payload["title"] = title
            if start_time:
                payload["start_time"] = start_time
            if end_time:
                payload["end_time"] = end_time
            if description:
                payload["description"] = description
            if location:
                payload["location"] = location

            logger.info(f"Updating calendar event: event_id={event_id}")

            response = requests.put(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                logger.info(f"Calendar event updated successfully")
                return response.json().get("data")
            else:
                logger.error(
                    f"Error updating event: status={response.status_code}, "
                    f"response={response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Exception updating calendar event: {str(e)}", exc_info=True)
            return None

    def delete_event(
        self,
        event_id: str,
        user_id: str,
        profile_id: str,
        jwt_token: Optional[str] = None
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            event_id: Event ID to delete
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            jwt_token: JWT token for authentication (optional)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/events/{event_id}"

            headers = {}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            params = {
                "user_id": user_id,
                "profile_id": profile_id
            }

            logger.info(f"Deleting calendar event: event_id={event_id}")

            response = requests.delete(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                logger.info(f"Calendar event deleted successfully")
                return True
            else:
                logger.error(
                    f"Error deleting event: status={response.status_code}, "
                    f"response={response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Exception deleting calendar event: {str(e)}", exc_info=True)
            return False
