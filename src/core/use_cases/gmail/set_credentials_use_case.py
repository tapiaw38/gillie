import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.domain.gmail import GmailCredentials
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailSessionQueryError

logger = logging.getLogger(__name__)


class SetCredentialsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        try:
            creds = GmailCredentials(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
            self.context_factory.repositories.gmail.save_credentials(creds)
            logger.info("Gmail credentials saved to MongoDB")
        except Exception as e:
            logger.error(f"Error saving Gmail credentials: {e}", exc_info=True)
            raise NewApplicationError(GmailSessionQueryError, e)
