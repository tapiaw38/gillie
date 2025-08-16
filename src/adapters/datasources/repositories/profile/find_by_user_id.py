from pymongo.errors import PyMongoError
from src.core.domain.model import Profile


def find_profile_by_user_id(client, user_id: str) -> Profile:
    try:
        document = client.find_one({"user_id": user_id})
        if not document:
            raise Exception(f"No profile found with user_id: {user_id}")
        # Ensure 'role' is always present for Pydantic validation
        if "role" not in document or not document["role"]:
            document["role"] = "seller"
        return Profile(**document)

    except PyMongoError as e:
        raise Exception(f"Error finding profile by user_id: {e}")
