from typing import List, Optional
from pymongo.errors import PyMongoError
from src.core.domain import ApiKey
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileApiKeyCreateError,
    ProfileUpdateNotFoundError
)


def update_api_keys(client, user_id: str, api_keys: List[ApiKey]) -> None:
    try:
        api_keys_dict = [api_key.dict(by_alias=True) for api_key in api_keys]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"api_keys": api_keys_dict}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ProfileUpdateNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ProfileApiKeyCreateError, e)
