import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain.drive import DriveCredentials
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveCredentialsError

logger = logging.getLogger(__name__)


class SetCredentialsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        try:
            context = self.context_factory()
            creds = DriveCredentials(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
            await context.repositories.drive.save_credentials(creds)
            logger.info("Google Drive credentials saved to MongoDB")
        except Exception as e:
            logger.error(f"Error saving Drive credentials: {e}", exc_info=True)
            raise NewApplicationError(DriveCredentialsError, e)
