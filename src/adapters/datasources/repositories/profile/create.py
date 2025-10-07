from src.core.domain import Profile
from pymongo.errors import DuplicateKeyError, PyMongoError


def create_profile(client, profile: Profile) -> str:
    try:
        profile_dict = profile.dict(by_alias=True, exclude_unset=True, exclude_none=True)
        result = client.insert_one(profile_dict)
        profile_id = str(result.inserted_id)
        return profile_id

    except DuplicateKeyError as e:
        raise Exception(f"Error creating profile: User ID already exists")

    except PyMongoError as e:
        raise Exception(f"Error creating profile: {e}")
