import logging
from typing import Optional, Dict, Any

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailEmailReplyError, GmailBodyRequiredError

logger = logging.getLogger(__name__)


class ReplyEmailUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        message_id: str,
        body: str,
        body_html: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not body or not body.strip():
            raise NewApplicationError(GmailBodyRequiredError)
        try:
            return self.context_factory.integrations.gmail.reply_email(
                user_id=user_id,
                message_id=message_id,
                body=body,
                body_html=body_html,
            )
        except Exception as e:
            logger.error(f"Error replying to Gmail email {message_id}: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailReplyError, e)
