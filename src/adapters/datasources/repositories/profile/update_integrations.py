from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Integration
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileIntegrationUpdateError,
    ProfileUpdateNotFoundError
)


def update_integrations(client, user_id: str, integrations: List[Integration]) -> None:
    try:
        integrations_dict = [integration.dict(by_alias=True) for integration in integrations]
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"integrations": integrations_dict}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ProfileUpdateNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ProfileIntegrationUpdateError, e)
