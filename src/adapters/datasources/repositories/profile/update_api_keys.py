from typing import List, Optional
from pymongo.errors import PyMongoError
from src.core.domain import ApiKey


def update_api_keys(client, user_id: str, api_keys: List[ApiKey]) -> None:
    try:
        api_keys_dict = [api_key.dict(by_alias=True) for api_key in api_keys]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"api_keys": api_keys_dict}}
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with user_id: {user_id}")

    except PyMongoError as e:
        raise Exception(f"Error updating profile api_keys: {e}")
