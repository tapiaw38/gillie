import logging
from typing import Dict, Any

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailEmailQueryError

logger = logging.getLogger(__name__)


class GetEmailUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, message_id: str) -> Dict[str, Any]:
        try:
            return self.context_factory.integrations.gmail.get_email(
                user_id=user_id,
                message_id=message_id,
            )
        except Exception as e:
            logger.error(f"Error getting Gmail email {message_id}: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailQueryError, e)
