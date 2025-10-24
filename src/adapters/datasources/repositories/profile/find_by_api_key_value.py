from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import ApiKey
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileApiKeyNotFoundError, ProfileGetQueryError


def find_by_api_key_value(client, user_id: str, api_key_value: str) -> Optional[ApiKey]:
    try:
        document = client.find_one(
            {
                "user_id": user_id,
                "api_keys.value": api_key_value
            },
            {
                "api_keys": {
                    "$elemMatch": {"value": api_key_value}
                }
            }
        )
        if not document or "api_keys" not in document or not document["api_keys"]:
            return None

        return ApiKey(**document["api_keys"][0])

    except PyMongoError as e:
        raise NewApplicationError(ProfileGetQueryError, e)
