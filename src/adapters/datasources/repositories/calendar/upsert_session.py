from datetime import datetime
from pymongo.errors import PyMongoError
from src.core.domain.calendar import CalendarSession
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarSessionQueryError


def upsert_session(client, session: CalendarSession) -> str:
    try:
        doc = session.dict(by_alias=True, exclude_none=True)
        doc.pop("_id", None)  # _id is immutable in MongoDB — must not be in replace body
        doc["updated_at"] = datetime.now()
        result = client.replace_one(
            {"user_id": session.user_id},
            doc,
            upsert=True,
        )
        if result.upserted_id:
            return str(result.upserted_id)
        existing = client.find_one({"user_id": session.user_id})
        return str(existing["_id"])
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)


def deactivate_session(client, user_id: str) -> None:
    try:
        client.update_one(
            {"user_id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.now()}},
        )
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)
