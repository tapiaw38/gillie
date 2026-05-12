from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from src.core.domain import Integration
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError

INTEGRATION_NAME = "notion"
INTEGRATION_TYPE = "notion"


async def get_notion_profile(context, user_id: str):
    profile = await context.repositories.profile.find_by_user_id(user_id)
    if not profile:
        raise NewApplicationError(ProfileGetNotFoundError)
    return profile


def get_notion_integration(profile) -> Optional[Integration]:
    for integration in profile.integrations or []:
        if integration.name == INTEGRATION_NAME:
            return integration
    return None


async def save_notion_config(
    context,
    user_id: str,
    config: Dict[str, Any],
    *,
    activated: Optional[bool] = None,
) -> Integration:
    profile = await get_notion_profile(context, user_id)
    now = datetime.now(timezone.utc)
    integration = get_notion_integration(profile)
    if integration:
        integration.config = config
        if activated is not None:
            integration.activated = activated
        integration.updated_at = now
    else:
        integration = Integration(
            _id=str(uuid4()),
            name=INTEGRATION_NAME,
            type=INTEGRATION_TYPE,
            activated=True if activated is None else activated,
            config=config,
            created_at=now,
            updated_at=now,
        )
        profile.integrations = (profile.integrations or []) + [integration]

    await context.repositories.profile.update_integrations(user_id, profile.integrations or [])
    await context.repositories.conversation.update_profile_by_user_id(user_id, profile)
    return integration
