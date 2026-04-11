import logging
from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOperationError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class UploadFileUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(
        self,
        user_id: str,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> dict:
        try:
            ctx = self.context_factory()
            service = get_drive_service(ctx, user_id)
            result = ctx.integrations.google_drive.upload_file(
                service, file_bytes, file_name, mime_type, folder_id
            )
            return {
                "id": result.get("id", ""),
                "name": result.get("name", file_name),
                "webViewLink": result.get("webViewLink"),
            }
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}", exc_info=True)
            raise NewApplicationError(DriveOperationError, e)
