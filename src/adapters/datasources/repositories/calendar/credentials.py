from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain.calendar import CalendarCredentials
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarSessionQueryError

_CREDENTIALS_DOC_ID = "__app_credentials__"


def save_credentials(client, creds: CalendarCredentials) -> None:
    try:
        doc = {
            "user_id": _CREDENTIALS_DOC_ID,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "redirect_uri": creds.redirect_uri,
        }
        client.replace_one({"user_id": _CREDENTIALS_DOC_ID}, doc, upsert=True)
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)


def find_credentials(client) -> Optional[CalendarCredentials]:
    try:
        doc = client.find_one({"user_id": _CREDENTIALS_DOC_ID})
        if not doc:
            return None
        return CalendarCredentials(
            client_id=doc["client_id"],
            client_secret=doc["client_secret"],
            redirect_uri=doc.get("redirect_uri", "http://localhost:8000/api/v1/calendar/oauth/callback"),
        )
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)
