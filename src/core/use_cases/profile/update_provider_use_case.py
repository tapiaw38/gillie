from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileUpdateQueryError,
    ProfileUpdateNotFoundError,
)


class UpdateProviderUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        active_provider: str,
        api_key: str = "",
    ) -> None:
        """Set the active provider and optionally store its API key."""
        try:
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileUpdateNotFoundError)

            provider_keys = dict(profile.provider_keys or {})
            if api_key:
                provider_keys[active_provider] = api_key

            updated = Profile(
                active_provider=active_provider,
                provider_keys=provider_keys or None,
                updated_at=datetime.now(timezone.utc),
            )

            self.context_factory.repositories.profile.update(profile.id, updated)

        except PyMongoError as e:
            raise NewApplicationError(ProfileUpdateQueryError, e)

    def save_custom(
        self,
        user_id: str,
        name: str,
        base_url: str,
        model: str,
        auth_type: str = "api_key",
        api_key: str = "",
    ) -> None:
        """Add or update a custom provider without changing the active provider."""
        try:
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileUpdateNotFoundError)

            custom_providers = dict(profile.custom_providers or {})
            custom_providers[name] = {
                "base_url": base_url,
                "model": model,
                "auth_type": auth_type,
                "api_key": api_key or "",
            }

            provider_keys = dict(profile.provider_keys or {})
            if api_key:
                provider_keys[name] = api_key

            updated = Profile(
                custom_providers=custom_providers,
                provider_keys=provider_keys or None,
                updated_at=datetime.now(timezone.utc),
            )

            self.context_factory.repositories.profile.update(profile.id, updated)

        except PyMongoError as e:
            raise NewApplicationError(ProfileUpdateQueryError, e)
