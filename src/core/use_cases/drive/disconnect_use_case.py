import logging
from datetime import datetime, timezone
from src.core.platform.appcontext.appcontext import Factory

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "google_drive"


class DisconnectUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str) -> None:
        profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
        if not profile:
            return
        now = datetime.now(timezone.utc)
        updated = [
            i.copy(update={"config": {"is_connected": False}, "activated": False, "updated_at": now})
            if i.name == INTEGRATION_NAME else i
            for i in (profile.integrations or [])
        ]
        self.context_factory.repositories.profile.update_integrations(user_id, updated)
        logger.info(f"Google Drive integration disconnected for user_id={user_id}")
