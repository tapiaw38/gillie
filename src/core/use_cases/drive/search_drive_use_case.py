import logging
from typing import Optional, List, Dict
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveSearchError

logger = logging.getLogger(__name__)


class SearchDriveUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        query: str,
        k: int = 5,
        file_id: Optional[str] = None,
    ) -> List[Dict]:
        try:
            return self.context_factory.integrations.google_drive.search(user_id, query, k, file_id)
        except Exception as e:
            logger.error(f"Error searching Drive index: {e}", exc_info=True)
            raise NewApplicationError(DriveSearchError, e)
