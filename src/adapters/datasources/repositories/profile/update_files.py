from typing import List
from pymongo.errors import PyMongoError
from src.core.domain.model import File


def update_files(client, user_id: str, files: List[File]) -> None:
    try:
        files_dict = [file.dict(by_alias=True) for file in files]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"files": files_dict}}
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with user_id: {user_id}")

    except PyMongoError as e:
        raise Exception(f"Error updating profile files: {e}")
