import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
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

_BRAIN_STATE_FILE = Path.home() / ".gillie" / "brain_state.json"
_MAINTENANCE_INTERVAL_HOURS = 24


class StartupService:
    """
    Handles single-user startup initialization:
    - Auto-creates the profile on first run
    - Syncs active_provider to the profile if not set
    - Restores the persisted provider to the in-memory LLM on every restart
    - Schedules brain maintenance if due (startup-triggered, safe for local envs)
    """

    def __init__(
        self,
        usecases: Usecases,
        config_service: ConfigurationService,
        profile_repository,
        openai_integration=None,
        brain=None,
        skill_manager=None,
    ):
        self.usecases = usecases
        self.config_service = config_service
        self.profile_repository = profile_repository
        self.openai_integration = openai_integration
        self.brain = brain
        self.skill_manager = skill_manager

    async def initialize(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"] = None,
    ) -> None:
        try:
            await self._ensure_profile(user_id, cli_config)
            await self._sync_provider(user_id, cli_config)
            self._ensure_brain_skill(cli_config)
            self._schedule_brain_maintenance(user_id)
        except Exception as e:
            logger.warning(f"Startup initialization failed: {e}")


    async def _ensure_profile(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"],
    ) -> None:
        """Create the profile on first run when using the CLI."""
        profile = await self.profile_repository.find_by_user_id(user_id)
        if profile is None and cli_config:
            from src.schemas import ProfileInput

            profile_input = ProfileInput(
                assistant_name=cli_config.profile.assistant_name,
                functions=cli_config.profile.functions,
                response_language=cli_config.profile.response_language,
            )
            await self.usecases.profile.create_usecase.execute(profile_input, user_id)
            logger.info(f"Auto-created profile for user_id={user_id}")

    async def _sync_provider(
        self,
        user_id: str,
        cli_config: Optional["AssistantConfig"],
    ) -> None:
        """Sync active_provider between profile, config, and the LLM client."""
        profile = await self.profile_repository.find_by_user_id(user_id)
        if profile is None:
            return

        if not profile.active_provider:
            await self._write_provider_to_profile(user_id, cli_config)
        else:
            self._restore_provider_from_profile(profile)

    async def _write_provider_to_profile(
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
        await self.usecases.profile.update_provider_usecase.execute(
            user_id=user_id,
            provider_name=active,
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

    def _schedule_brain_maintenance(self, user_id: str) -> None:
        """Schedule brain maintenance as a background task if it's due."""
        if self.brain is None or self.skill_manager is None:
            return

        last = self._read_last_maintenance()
        if last is not None:
            elapsed = datetime.now(timezone.utc) - last
            if elapsed < timedelta(hours=_MAINTENANCE_INTERVAL_HOURS):
                logger.info(
                    "Brain maintenance skipped — last run %.1fh ago (interval=%dh)",
                    elapsed.total_seconds() / 3600,
                    _MAINTENANCE_INTERVAL_HOURS,
                )
                return

        logger.info("Brain maintenance due — scheduling in background (60s delay)")
        asyncio.create_task(self._deferred_maintenance(user_id, delay_seconds=60))

    async def _deferred_maintenance(self, user_id: str, delay_seconds: int = 60) -> None:
        """Run consolidate + prune after a short delay so startup isn't blocked."""
        await asyncio.sleep(delay_seconds)
        try:
            result = await self.brain.consolidator.consolidate(
                user_id=user_id,
                auto_prune=True,
            )
            self._write_last_maintenance()
            logger.info(
                "Brain maintenance complete — written=%d pruned=%d",
                result.get("written", 0),
                result.get("pruned", 0),
            )
        except Exception as exc:
            logger.warning("Brain maintenance failed: %s", exc)

    @staticmethod
    def _read_last_maintenance() -> Optional[datetime]:
        try:
            if not _BRAIN_STATE_FILE.exists():
                return None
            data = json.loads(_BRAIN_STATE_FILE.read_text())
            ts = data.get("last_maintenance")
            if not ts:
                return None
            return datetime.fromisoformat(ts)
        except Exception:
            return None

    @staticmethod
    def _write_last_maintenance() -> None:
        try:
            _BRAIN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"last_maintenance": datetime.now(timezone.utc).isoformat()}
            _BRAIN_STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.warning("Failed to write brain_state.json: %s", exc)

    def _ensure_brain_skill(self, cli_config: Optional["AssistantConfig"]) -> None:
        """Inject brain knowledge block into rules.skill.md when brain is enabled."""
        if cli_config is None or not cli_config.services.brain.enabled:
            return

        try:
            from src.core.platform.managers.skill_manager import (
                SkillManager, BRAIN_SKILL_MARKER, BRAIN_SKILL_BLOCK,
            )
            skill_manager = SkillManager()
            rules_content = skill_manager.load_skill("rules")

            if BRAIN_SKILL_MARKER in rules_content:
                return

            skill_manager.save_skill("rules", rules_content.rstrip() + "\n" + BRAIN_SKILL_BLOCK)
            logger.info("Injected brain knowledge block into rules.skill.md")
        except Exception as exc:
            logger.warning("Failed to inject brain skill block: %s", exc)
