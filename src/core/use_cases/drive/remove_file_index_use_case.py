import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveIndexNotFoundError

logger = logging.getLogger(__name__)


class RemoveFileIndexUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, file_id: str) -> None:
        try:
            self.context_factory.integrations.google_drive.remove_file_index(user_id, file_id)
        except Exception as e:
            logger.error(f"Error removing Drive file index {file_id}: {e}", exc_info=True)
            raise NewApplicationError(DriveIndexNotFoundError, e)
