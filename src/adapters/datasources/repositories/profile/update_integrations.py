from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Integration


def update_integrations(client, user_id: str, integrations: List[Integration]) -> None:
    try:
        integrations_dict = [integration.dict(by_alias=True) for integration in integrations]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"integrations": integrations_dict}}
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with user_id: {user_id}")

    except PyMongoError as e:
        raise Exception(f"Error updating profile integrations: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")
