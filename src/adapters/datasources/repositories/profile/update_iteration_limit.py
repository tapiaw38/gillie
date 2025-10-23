from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileIterationLimitUpdateError,
    ProfileUpdateNotFoundError
)


def update_iteration_limit(client, user_id: str, iteration_limit: int) -> str:
    try:
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"iteration_limit": iteration_limit}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ProfileUpdateNotFoundError)

        return user_id

    except PyMongoError as e:
        raise NewApplicationError(ProfileIterationLimitUpdateError, e)
