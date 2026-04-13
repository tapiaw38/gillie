from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.config.service import get_available_providers
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileUpdateQueryError,
    ProfileUpdateNotFoundError,
    ProfileProviderUnknownError,
)


class UpdateProviderUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(
        self,
        user_id: str,
        provider_name: str,
        api_key: str = "",
    ) -> dict:
        """Validate provider, persist the selection, and reload the integration."""
        try:
            context = self.context_factory()
            profile = context.repositories.profile.find_by_user_id(user_id) if user_id else None

            profile_keys = (profile.provider_keys if profile else None) or {}
            profile_custom = (profile.custom_providers if profile else None) or {}

            providers = get_available_providers(
                provider_keys=profile_keys,
                custom_providers=profile_custom,
            )
            if provider_name not in providers:
                raise NewApplicationError(ProfileProviderUnknownError)

            preset = providers[provider_name]
            resolved_key = api_key or preset.get("api_key", "")

            if profile:
                provider_keys = dict(profile_keys)
                if resolved_key:
                    provider_keys[provider_name] = resolved_key

                updated = Profile(
                    active_provider=provider_name,
                    provider_keys=provider_keys or None,
                    updated_at=datetime.now(timezone.utc),
                )
                context.repositories.profile.update(profile.id, updated)

            config = context.config_service
            config.openai_config.base_url = preset["base_url"]
            config.openai_config.model = preset["model"]
            config.openai_config.auth_type = preset["auth_type"]
            config.openai_config.api_key = resolved_key

            context.integrations.openai.reload_provider(
                base_url=preset["base_url"],
                model=preset["model"],
                api_key=resolved_key,
                auth_type=preset["auth_type"],
            )

            return {"provider": provider_name, "model": preset["model"]}

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
            context = self.context_factory()
            profile = context.repositories.profile.find_by_user_id(user_id)
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

            context.repositories.profile.update(profile.id, updated)

        except PyMongoError as e:
            raise NewApplicationError(ProfileUpdateQueryError, e)
