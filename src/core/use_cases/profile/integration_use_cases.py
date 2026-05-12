from src.schemas import (
    IntegrationInput,
    IntegrationListOutput,
)
from src.core.domain import Integration
from datetime import datetime, timezone
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileGetNotFoundError,
    ProfileIntegrationNotFoundError,
)
from uuid import uuid4


class AddIntegrationUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, integration: IntegrationInput):
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileGetNotFoundError)

        if not hasattr(profile, "integrations") or profile.integrations is None:
            profile.integrations = []

        integration_id = str(uuid4())
        new_integration = Integration(
            _id=integration_id,
            name=integration.name,
            type=integration.type,
            activated=integration.activated,
            config=integration.config,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        for integ in profile.integrations:
            match_by_id = integration.id and integ.id == integration.id
            match_by_name = (not integration.id) and integ.name == new_integration.name and integ.type == new_integration.type
            if match_by_id or match_by_name:
                integ.name = new_integration.name
                integ.type = new_integration.type
                integ.activated = new_integration.activated
                integ.config = new_integration.config
                integ.updated_at = datetime.now(timezone.utc)
                await context.repositories.profile.update_integrations(
                    user_id, profile.integrations
                )
                await context.repositories.conversation.update_profile_by_user_id(
                    user_id,
                    profile=profile,
                )
                return IntegrationListOutput.from_output(profile.integrations)

        profile.integrations.append(new_integration)

        await context.repositories.profile.update_integrations(
            user_id, profile.integrations
        )

        await context.repositories.conversation.update_profile_by_user_id(
            user_id,
            profile=profile,
        )

        return IntegrationListOutput.from_output(profile.integrations)


class DeleteIntegrationUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, integration_id: str):
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        if not profile:
            raise NewApplicationError(ProfileGetNotFoundError)

        if not hasattr(profile, "integrations") or not profile.integrations:
            raise NewApplicationError(ProfileIntegrationNotFoundError)

        original_len = len(profile.integrations)
        profile.integrations = [
            i for i in profile.integrations
            if i.id != integration_id
        ]

        if len(profile.integrations) == original_len:
            raise NewApplicationError(ProfileIntegrationNotFoundError)

        await context.repositories.profile.update_integrations(user_id, profile.integrations)
        await context.repositories.conversation.update_profile_by_user_id(user_id, profile=profile)
        return IntegrationListOutput.from_output(profile.integrations)
