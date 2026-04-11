from src.schemas import (
    ApiKeyInput,
    ApiKeyListOutput,
    ApiKeyDeleteOutput,
)
from src.core.domain import ApiKey
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileGetNotFoundError,
    ProfileApiKeyNotFoundError,
    ProfileApiKeyValidationError,
    ProfileApiKeyCreateError,
    ProfileApiKeyDeleteError
)
from uuid import uuid4


class AddApiKeyUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, api_key: ApiKeyInput, user_id: str):
        try:
            context = self.context_factory()
            generated_id = str(uuid4())
            api_key_value = f"sk-{str(uuid4()).replace('-', '')}"

            new_api_key = ApiKey(
                _id=generated_id,
                user_id=user_id,
                value=api_key_value,
                description=api_key.description,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )

            profile = context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            if not hasattr(profile, "api_keys") or profile.api_keys is None:
                profile.api_keys = []

            if any(existing.id == new_api_key.id for existing in profile.api_keys):
                raise NewApplicationError(ProfileApiKeyValidationError)

            profile.api_keys.append(new_api_key)

            context.repositories.profile.update_api_keys(
                user_id, profile.api_keys
            )

            context.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile,
            )

            return ApiKeyListOutput.from_output(profile.api_keys)

        except PyMongoError as e:
            raise NewApplicationError(ProfileApiKeyCreateError, e)


class DeleteApiKeyUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, api_key_id: str):
        try:
            context = self.context_factory()
            profile = context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            if profile.api_keys is None or not any(k.id == api_key_id for k in profile.api_keys):
                raise NewApplicationError(ProfileApiKeyNotFoundError)

            context.repositories.profile.deactivate_api_key(
                user_id, api_key_id
            )

            updated_profile = context.repositories.profile.find_by_user_id(user_id)

            context.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=updated_profile,
            )

            return ApiKeyDeleteOutput.from_output(api_key_id)

        except PyMongoError as e:
            raise NewApplicationError(ProfileApiKeyDeleteError, e)
