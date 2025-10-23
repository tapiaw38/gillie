from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import File
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileFileNotFoundError,
    ProfileGetQueryError
)


def get_file_by_id(client, user_id: str, file_id: str) -> Optional[File]:
    try:
        document = client.find_one(
            {
                "user_id": user_id,
                "files._id": file_id
            },
            {
                "files": {
                    "$elemMatch": {"_id": file_id}
                }
            }
        )
        if not document or "files" not in document or not document["files"]:
            raise NewApplicationError(ProfileFileNotFoundError)

        return File(**document["files"][0])

    except PyMongoError as e:
        raise NewApplicationError(ProfileGetQueryError, e)
