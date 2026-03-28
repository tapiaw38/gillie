import logging
from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOperationError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class CreateFolderUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, name: str, parent_id: Optional[str] = None) -> dict:
        try:
            ctx = self.context_factory
            service = get_drive_service(ctx, user_id)
            result = ctx.integrations.google_drive.create_folder(service, name, parent_id)
            return {
                "id": result.get("id", ""),
                "name": result.get("name", name),
            }
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error creating Drive folder: {e}", exc_info=True)
            raise NewApplicationError(DriveOperationError, e)
