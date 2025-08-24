from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain.model import File


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
            raise Exception(f"No file found with id: {file_id}")

        return File(**document["files"][0])

    except PyMongoError as e:
        raise Exception(f"Error finding file by ID: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")
