from src.schemas import (
    FileListOutput,
    FileInput,
    FileDeleteOutput,
)
from src.core.domain import File
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileGetNotFoundError,
    ProfileFileNotFoundError,
    ProfileFileUploadError,
    ProfileFileDeleteError
)
from uuid import uuid4
from typing import List, Tuple, Optional
from asyncio import to_thread, gather, create_task
import logging

logger = logging.getLogger(__name__)


def _detect_file_type(filename: str) -> Optional[str]:
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        return "xlsx"
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".docx", ".doc")):
        return "docx"
    return None


async def _ingest_into_qdrant(config_service, file_url: str, file_type: str, user_id: str, filename: str):
    """Background task: init RAG processor and ingest into Qdrant. Never raises."""
    try:
        from src.core.platform.fileprocessor.rag_processor import RAGDocumentProcessor
        rag_processor = RAGDocumentProcessor(config_service)
        result = await rag_processor.process_and_store_document(
            file_url, file_type, profile_id=user_id
        )
        logger.info(
            f"[Qdrant] ingested '{filename}' → "
            f"{result.get('vector_count', 0)} vectors "
            f"storage={result.get('storage', '?')} "
            f"status={result.get('status', '?')}"
        )
    except Exception as e:
        logger.warning(f"[Qdrant] ingestion failed for '{filename}': {e}")


async def _delete_from_s3(store_service, file_name: str, file_id: str):
    """Background task: delete file from S3. Never raises."""
    try:
        await to_thread(store_service.delete_object, file_name)
        logger.info(f"[S3] deleted file {file_id} ({file_name})")
    except Exception as e:
        logger.warning(f"[S3] failed to delete file {file_id}: {e}")


async def _delete_from_qdrant(config_service, file_url: str, file_id: str, user_id: str):
    """Background task: remove file vectors from Qdrant. Never raises."""
    try:
        from src.core.platform.fileprocessor.rag_processor import RAGDocumentProcessor
        rag_processor = RAGDocumentProcessor(config_service)
        if not rag_processor.use_qdrant:
            logger.warning(f"[Qdrant] adapter not available, skipping vector cleanup for file {file_id}")
            return
        collection = f"profile_{user_id}"
        rag_processor.qdrant_adapter.delete_by_metadata(collection, {"source": file_url})
        logger.info(f"[Qdrant] removed vectors for file {file_id} from collection '{collection}'")
    except Exception as e:
        logger.warning(f"[Qdrant] failed to remove vectors for file {file_id}: {e}")


class AddFilesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, input_files: List[FileInput]):
        try:
            app = self.context_factory()

            results: List[File] = []
            errors: List[Exception] = []

            async def process_file(
                file: FileInput, user_file: str
            ) -> Tuple[Optional[File], Optional[Exception]]:
                try:
                    file_id = str(uuid4())

                    file_name = await to_thread(
                        app.store_service.put_object,
                        file.file,
                        user_file,
                        file.filename,
                        file.filesize,
                        file_id,
                    )
                    file_url = await to_thread(app.store_service.generate_url, file_name)

                    # Fire-and-forget: init + ingest runs fully in background
                    file_type = _detect_file_type(file.filename)
                    if file_type:
                        create_task(
                            _ingest_into_qdrant(app.config_service, file_url, file_type, user_id, file.filename)
                        )
                        logger.info(f"[Qdrant] ingestion task queued for '{file.filename}'")

                    return (
                        File(
                            _id=file_id,
                            name=file_name,
                            url=file_url,
                            created_at=datetime.now(timezone.utc),
                        ),
                        None,
                    )
                except Exception as e:
                    return None, e

            tasks = [process_file(f, user_id) for f in input_files]
            results_and_errors = await gather(*tasks)

            for result, error in results_and_errors:
                if error:
                    errors.append(error)
                elif result:
                    results.append(result)

            if errors:
                raise NewApplicationError(ProfileFileUploadError, errors[0])

            profile = await app.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            if not hasattr(profile, "files") or profile.files is None:
                profile.files = []

            profile.files.extend(results)

            await app.repositories.profile.update_files(user_id, profile.files)

            updated_profile = await app.repositories.profile.find_by_user_id(user_id)
            if not updated_profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            await app.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=updated_profile,
            )

            return FileListOutput.from_output(updated_profile.files)

        except PyMongoError as e:
            raise NewApplicationError(ProfileFileUploadError, e)


class DeleteFileByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, file_id: str):
        try:
            context = self.context_factory()
            file = await context.repositories.profile.get_file_by_id(
                user_id, file_id
            )
            if not file:
                raise NewApplicationError(ProfileFileNotFoundError)

            await context.repositories.profile.delete_file_by_id(
                user_id, file_id
            )

            create_task(_delete_from_s3(context.store_service, file.name, file_id))
            create_task(_delete_from_qdrant(context.config_service, file.url, file_id, user_id))
            logger.info(f"[Delete] background tasks queued for file {file_id} (S3 + Qdrant)")

            profile = await context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            await context.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile,
            )

            return FileDeleteOutput.from_output(file_id)

        except PyMongoError as e:
            raise NewApplicationError(ProfileFileDeleteError, e)
