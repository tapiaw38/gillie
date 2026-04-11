import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailEmailDeleteError

logger = logging.getLogger(__name__)


class DeleteEmailUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, message_id: str) -> None:
        try:
            context = self.context_factory()
            context.integrations.gmail.delete_email(
                user_id=user_id,
                message_id=message_id,
            )
        except Exception as e:
            logger.error(f"Error deleting Gmail email {message_id}: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailDeleteError, e)
