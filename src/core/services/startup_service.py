import logging
from typing import Optional, TYPE_CHECKING

from src.core.use_cases.use_cases import Usecases
from src.core.platform.config.service import (
    ConfigurationService,
    get_available_providers,
    get_active_provider_name,
)

if TYPE_CHECKING:
    from cli.config.schema import AssistantConfig

logger = logging.getLogger(__name__)


class StartupService:
    """
    Handles single-user startup initialization:
    - Auto-creates the profile on first run
    - Syncs active_provider to the profile if not set
    - Restores the persisted provider to the in-memory LLM on every restart
    """

    def __init__(
        self,
        usecases: Usecases,
        config_service: ConfigurationService,
        profile_repository,
        openai_integration=None,
    ):
        self.usecases = usecases
        self.config_service = config_service
        self.profile_repository = profile_repository
        self.openai_integration = openai_integration

    def initialize(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"] = None,
    ) -> None:
        try:
            self._ensure_profile(user_id, cli_config)
            self._sync_provider(user_id, cli_config)
        except Exception as e:
            logger.warning(f"Startup initialization failed: {e}")


    def _ensure_profile(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"],
    ) -> None:
        """Create the profile on first run when using the CLI."""
        profile = self.profile_repository.find_by_user_id(user_id)
        if profile is None and cli_config:
            from src.schemas import ProfileInput

            profile_input = ProfileInput(
                assistant_name=cli_config.profile.assistant_name,
                business_name=cli_config.profile.business_name,
                functions=cli_config.profile.functions,
                response_language=cli_config.profile.response_language,
            )
            self.usecases.profile.create_usecase.execute(profile_input, user_id)
            logger.info(f"Auto-created profile for user_id={user_id}")

    def _sync_provider(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"],
    ) -> None:
        """Sync active_provider between profile, config, and the LLM client."""
        profile = self.profile_repository.find_by_user_id(user_id)
        if profile is None:
            return

        if not profile.active_provider:
            self._write_provider_to_profile(user_id, cli_config)
        else:
            self._restore_provider_from_profile(profile)

    def _write_provider_to_profile(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"],
    ) -> None:
        """First run: persist the provider from config/CLI into the profile."""
        if cli_config and cli_config.services.openai.active_provider:
            active = cli_config.services.openai.active_provider
        else:
            active = get_active_provider_name()

        if not active or active in ("", "custom"):
            return

        api_key = self.config_service.openai_config.api_key or ""
        self.usecases.profile.update_provider_usecase.execute(
            user_id=user_id,
            active_provider=active,
            api_key=api_key,
        )
        logger.info(f"Synced active_provider={active} to profile")

    def _restore_provider_from_profile(self, profile) -> None:
        """Every restart: apply the profile's stored provider to config and LLM."""
        active = profile.active_provider
        providers = get_available_providers(
            provider_keys=profile.provider_keys,
            custom_providers=profile.custom_providers,
        )
        preset = providers.get(active)
        if not preset:
            logger.info(f"Profile has active_provider={active} but no matching preset found")
            return

        api_key = preset.get("api_key") or self.config_service.openai_config.api_key or ""
        self.config_service.openai_config.base_url = preset["base_url"]
        self.config_service.openai_config.model = preset["model"]
        self.config_service.openai_config.auth_type = preset["auth_type"]
        self.config_service.openai_config.api_key = api_key

        if self.openai_integration is not None:
            self.openai_integration.reload_provider(
                base_url=preset["base_url"],
                model=preset["model"],
                api_key=api_key,
                auth_type=preset["auth_type"],
            )

        logger.info(f"Restored active_provider={active} (model={preset['model']}) from profile")
