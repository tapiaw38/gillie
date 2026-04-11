import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOperationError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class MoveFileUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, file_id: str, new_folder_id: str) -> dict:
        try:
            ctx = self.context_factory()
            service = get_drive_service(ctx, user_id)
            result = ctx.integrations.google_drive.move_file(service, file_id, new_folder_id)
            return {
                "id": result.get("id", file_id),
                "name": result.get("name", ""),
                "parents": result.get("parents"),
            }
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error moving Drive file: {e}", exc_info=True)
            raise NewApplicationError(DriveOperationError, e)
