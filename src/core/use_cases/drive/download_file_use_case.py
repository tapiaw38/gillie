import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOperationError
from ._helpers import get_drive_service

logger = logging.getLogger(__name__)


class DownloadFileUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str, file_id: str) -> dict:
        try:
            ctx = self.context_factory()
            service = get_drive_service(ctx, user_id)
            meta = ctx.integrations.google_drive.get_file_metadata(service, file_id)
            mime_type = meta.get("mimeType", "")
            file_bytes = ctx.integrations.google_drive.download_file(service, file_id, mime_type)
            return {
                "file_id": file_id,
                "file_name": meta.get("name", file_id),
                "mime_type": mime_type,
                "content": file_bytes,
            }
        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error downloading Drive file: {e}", exc_info=True)
            raise NewApplicationError(DriveOperationError, e)
