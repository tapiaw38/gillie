from typing import Optional
from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileApiKeyDeleteError,
    ProfileApiKeyNotFoundError
)


def deactivate_api_key(client, user_id: str, api_key_id: str) -> Optional[str]:
    try:
        result = client.update_one(
            {
                "user_id": user_id,
                "api_keys._id": api_key_id
            },
            {
                "$set": {
                    "api_keys.$.is_active": False
                }
            }
        )

        if result.modified_count == 0:
            raise NewApplicationError(ProfileApiKeyNotFoundError)

        return api_key_id

    except PyMongoError as e:
        raise NewApplicationError(ProfileApiKeyDeleteError, e)
