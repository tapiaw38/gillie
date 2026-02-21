import logging
from typing import Optional, List, Dict

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveListFilesError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class ListFilesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, folder_id: Optional[str] = None) -> List[Dict]:
        try:
            service = get_drive_service(self.context_factory, user_id)
            return self.context_factory.integrations.google_drive.list_files(
                service, user_id, folder_id
            )
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}", exc_info=True)
            raise NewApplicationError(DriveListFilesError, e)
