from src.schemas import (
    IntegrationInput,
    IntegrationListOutput,
)
from src.core.domain import Integration
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from uuid import uuid4


class AddIntegrationUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, integration: IntegrationInput):
        try:
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise Exception(f"No profile found with user_id: {user_id}")

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
            # Check for existing integration with same name and type
            for integ in profile.integrations:
                if integ.name == new_integration.name and integ.type == new_integration.type:
                    integ.activated = new_integration.activated
                    integ.config = new_integration.config
                    integ.updated_at = datetime.now(timezone.utc)
                    self.context_factory.repositories.profile.update_integrations(
                        user_id, profile.integrations
                    )
                    self.context_factory.repositories.conversation.update_profile_by_user_id(
                        user_id,
                        profile=profile,
                    )
                    return IntegrationListOutput.from_output(profile.integrations)

            profile.integrations.append(new_integration)

            self.context_factory.repositories.profile.update_integrations(
                user_id, profile.integrations
            )

            self.context_factory.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile,
            )

            return IntegrationListOutput.from_output(profile.integrations)

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing AddIntegrationUseCase: {e}")