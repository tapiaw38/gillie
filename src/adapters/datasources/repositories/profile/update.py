from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileUpdateQueryError,
    ProfileUpdateNotFoundError
)


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
            raise NewApplicationError(ProfileUpdateNotFoundError)

        return id

    except PyMongoError as e:
        raise NewApplicationError(ProfileUpdateQueryError, e)
