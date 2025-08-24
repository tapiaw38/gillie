from pymongo.errors import PyMongoError
from src.core.domain.model import ApiKey


def find_by_api_key_value(client, user_id: str, api_key_value: str) -> ApiKey:
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
            raise Exception(f"No API key found for user_id: {user_id}")

        return ApiKey(**document["api_keys"][0])

    except PyMongoError as e:
        raise Exception(f"Error finding API key: {e}")
