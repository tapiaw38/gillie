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
from asyncio import to_thread, gather


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

            profile = app.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            if not hasattr(profile, "files") or profile.files is None:
                profile.files = []

            profile.files.extend(results)

            app.repositories.profile.update_files(user_id, profile.files)

            updated_profile = app.repositories.profile.find_by_user_id(user_id)
            if not updated_profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            app.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=updated_profile,
            )

            return FileListOutput.from_output(updated_profile.files)

        except PyMongoError as e:
            raise NewApplicationError(ProfileFileUploadError, e)


class DeleteFileByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, file_id: str):
        try:
            file = self.context_factory.repositories.profile.get_file_by_id(
                user_id, file_id
            )
            if not file:
                raise NewApplicationError(ProfileFileNotFoundError)

            self.context_factory.repositories.profile.delete_file_by_id(
                user_id, file_id
            )
            self.context_factory.store_service.delete_object(file.name)

            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            self.context_factory.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile,
            )

            return FileDeleteOutput.from_output(file_id)

        except PyMongoError as e:
            raise NewApplicationError(ProfileFileDeleteError, e)