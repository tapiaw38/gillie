from pymongo.errors import PyMongoError
from src.core.domain.calendar import CalendarSession
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarSessionQueryError


def create_session(client, session: CalendarSession) -> str:
    try:
        doc = session.dict(by_alias=True, exclude_none=True)
        result = client.insert_one(doc)
        return str(result.inserted_id)
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)
