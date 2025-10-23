from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import File
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileFileUploadError,
    ProfileUpdateNotFoundError
)


def update_files(client, user_id: str, files: List[File]) -> None:
    try:
        files_dict = [file.dict(by_alias=True) for file in files]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"files": files_dict}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ProfileUpdateNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ProfileFileUploadError, e)
