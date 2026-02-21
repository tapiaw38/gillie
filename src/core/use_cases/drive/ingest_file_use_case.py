import logging
from typing import Dict

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveIngestionError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class IngestFileUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, file_id: str) -> Dict:
        try:
            service = get_drive_service(self.context_factory, user_id)
            return self.context_factory.integrations.google_drive.ingest_file(
                service, user_id, file_id
            )
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error ingesting Drive file {file_id}: {e}", exc_info=True)
            raise NewApplicationError(DriveIngestionError, e)
