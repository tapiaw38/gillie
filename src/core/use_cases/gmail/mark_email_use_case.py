import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailEmailQueryError

logger = logging.getLogger(__name__)


class MarkEmailReadUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, message_id: str) -> None:
        try:
            context = self.context_factory()
            context.integrations.gmail.mark_as_read(
                user_id=user_id,
                message_id=message_id,
            )
        except Exception as e:
            logger.error(f"Error marking Gmail email {message_id} as read: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailQueryError, e)


class MarkEmailUnreadUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, message_id: str) -> None:
        try:
            context = self.context_factory()
            context.integrations.gmail.mark_as_unread(
                user_id=user_id,
                message_id=message_id,
            )
        except Exception as e:
            logger.error(f"Error marking Gmail email {message_id} as unread: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailQueryError, e)
