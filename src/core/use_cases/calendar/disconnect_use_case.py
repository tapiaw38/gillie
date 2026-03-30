import logging
from src.core.platform.appcontext.appcontext import Factory

logger = logging.getLogger(__name__)


class DisconnectUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str) -> None:
        self.context_factory.repositories.calendar.deactivate_session(user_id)
        logger.info(f"Google Calendar session deactivated for user_id={user_id}")
