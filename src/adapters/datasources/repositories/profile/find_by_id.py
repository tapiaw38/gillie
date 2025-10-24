from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileGetQueryError


def find_profile_by_id(client, id: str) -> Optional[Profile]:
    try:
        document = client.find_one({"_id": id})
        if not document:
            return None

        return Profile(**document)

    except PyMongoError as e:
        raise NewApplicationError(ProfileGetQueryError, e)
