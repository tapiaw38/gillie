from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import Profile


def find_profile_by_id(client, id: str) -> Optional[Profile]:
    try:
        document = client.find_one({"_id": id})
        if not document:
            raise Exception(f"No profile found with id: {id}")

        return Profile(**document)

    except PyMongoError as e:
        raise Exception(f"Error finding profile by ID: {e}")
