from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileFileDeleteError,
    ProfileUpdateNotFoundError
)


def delete_file_by_id(client, user_id: str, file_id: str) -> None:
    try:
        result = client.update_one(
            {"user_id": user_id},
            {"$pull": {"files": {"_id": file_id}}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ProfileUpdateNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ProfileFileDeleteError, e)
