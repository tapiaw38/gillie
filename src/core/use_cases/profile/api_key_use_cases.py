from src.schemas import (
    ApiKeyInput,
    ApiKeyListOutput,
    ApiKeyDeleteOutput,
)
from src.core.domain import ApiKey
from datetime import datetime, timezone, timedelta
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileGetNotFoundError,
    ProfileApiKeyNotFoundError,
    ProfileApiKeyValidationError
)
from uuid import uuid4
import jwt


class AddApiKeyUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def generate_api_key(
        self, user_id: str, expires_in_minutes: int = 60 * 24 * 365
    ) -> str:
        secret_key = self.context_factory.config_service.server_config.jwt_secret
        payload = {
            "user_id": user_id,
            "type": "api_key",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token

    async def execute(self, api_key: ApiKeyInput, user_id: str):
        default_limit = 1000
        generated_id = str(uuid4())
        new_api_key = ApiKey(
            _id=generated_id,
            user_id=user_id,
            value=self.generate_api_key(user_id),
            description=api_key.description,
            limit=default_limit,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileGetNotFoundError)

        if not hasattr(profile, "api_keys") or profile.api_keys is None:
            profile.api_keys = []

        if any(api_key.id == new_api_key.id for api_key in profile.api_keys):
            raise NewApplicationError(ProfileApiKeyValidationError)

        profile.api_keys.append(new_api_key)

        self.context_factory.repositories.profile.update_api_keys(
            user_id, profile.api_keys
        )

        self.context_factory.repositories.conversation.update_profile_by_user_id(
            user_id,
            profile=profile,
        )

        return ApiKeyListOutput.from_output(profile.api_keys)


class DeleteApiKeyUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, api_key_id: str):
        self.context_factory.repositories.profile.deactivate_api_key(
            user_id, api_key_id
        )

        profile = self.context_factory.repositories.profile.find_by_user_id(user_id)

        self.context_factory.repositories.conversation.update_profile_by_user_id(
            user_id,
            profile=profile,
        )

        return ApiKeyDeleteOutput.from_output(api_key_id)


class FindByApiKeyValueUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, api_key_value: str):
        api_key = self.context_factory.repositories.profile.find_by_api_key_value(
            user_id, api_key_value
        )
        if not api_key:
            raise NewApplicationError(ProfileApiKeyNotFoundError)
        return api_key