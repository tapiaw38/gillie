from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileGetQueryError


def find_profile_by_user_id(client, user_id: str) -> Optional[Profile]:
    try:
        document = client.find_one({"user_id": user_id})
        if not document:
            return None

        if "role" not in document or not document["role"]:
            document["role"] = "seller"
        return Profile(**document)

    except PyMongoError as e:
        raise NewApplicationError(ProfileGetQueryError, e)
