import logging

from src.core.platform.appcontext.appcontext import Factory

logger = logging.getLogger(__name__)


class CheckSessionStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str) -> bool:
        try:
            context = self.context_factory()
            return context.integrations.gmail.check_session_status(user_id)
        except Exception as e:
            logger.error(f"Error checking Gmail session status: {e}", exc_info=True)
            return False
