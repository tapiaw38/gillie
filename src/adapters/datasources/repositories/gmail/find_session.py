from typing import Optional

from pymongo.errors import PyMongoError

from src.core.domain.gmail import GmailSession
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailSessionQueryError


def find_active_session(client, user_id: str) -> Optional[GmailSession]:
    try:
        doc = client.find_one({"user_id": user_id, "is_active": True})
        if doc:
            doc["_id"] = str(doc["_id"])
            return GmailSession(**doc)
        return None
    except PyMongoError as e:
        raise NewApplicationError(GmailSessionQueryError, e)
