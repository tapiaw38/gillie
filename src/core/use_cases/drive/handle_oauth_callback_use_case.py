import logging
from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain import Integration
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOAuthError
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "google_drive"
INTEGRATION_TYPE = "oauth"


class HandleOAuthCallbackUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, code: str) -> dict:
        try:
            context = self.context_factory()
            token_config = context.integrations.google_drive.handle_oauth_callback(user_id, code)

            profile = context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            integrations = profile.integrations or []
            now = datetime.now(timezone.utc)
            existing = next((i for i in integrations if i.name == INTEGRATION_NAME), None)

            if existing:
                updated = [
                    i.copy(update={"config": token_config, "activated": True, "updated_at": now})
                    if i.name == INTEGRATION_NAME else i
                    for i in integrations
                ]
            else:
                new_entry = Integration(
                    _id=str(uuid4()),
                    name=INTEGRATION_NAME,
                    type=INTEGRATION_TYPE,
                    activated=True,
                    config=token_config,
                    created_at=now,
                    updated_at=now,
                )
                updated = integrations + [new_entry]

            context.repositories.profile.update_integrations(user_id, updated)

            return {
                "user_id": user_id,
                "status": "connected",
                "scopes": token_config.get("scopes", []),
            }
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error handling Drive OAuth callback: {e}", exc_info=True)
            raise NewApplicationError(DriveOAuthError, e)
