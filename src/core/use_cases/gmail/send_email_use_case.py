import logging
from typing import Optional, Dict, Any

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import (
    GmailEmailSendError,
    GmailToRequiredError,
    GmailSubjectRequiredError,
    GmailBodyRequiredError,
)

logger = logging.getLogger(__name__)


class SendEmailUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not to or not to.strip():
            raise NewApplicationError(GmailToRequiredError)
        if not subject or not subject.strip():
            raise NewApplicationError(GmailSubjectRequiredError)
        if not body or not body.strip():
            raise NewApplicationError(GmailBodyRequiredError)
        try:
            return self.context_factory.integrations.gmail.send_email(
                user_id=user_id,
                to=to,
                subject=subject,
                body=body,
                body_html=body_html,
                cc=cc,
                bcc=bcc,
            )
        except Exception as e:
            logger.error(f"Error sending Gmail email: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailSendError, e)
