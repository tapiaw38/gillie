from pymongo.errors import PyMongoError
from src.core.domain import Profile


def update_profile(client, id: str, profile: Profile) -> str:
    try:
        profile_dict = profile.dict(
            by_alias=True,
            exclude_none=True,
        )
        result = client.update_one(
            {"_id": id},
            {"$set": profile_dict},
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with id: {id}")

        return id

    except PyMongoError as e:
        raise Exception(f"Error updating profile: {e}")
