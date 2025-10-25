from typing import Optional
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile


class FindWithActiveWhatsAppIntegrationUseCase:
    """
    Find the first profile with an active WhatsApp integration.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self) -> Optional[Profile]:
        """
        Execute the use case to find a profile with active WhatsApp integration.

        Returns:
            Profile if found, None otherwise
        """
        context = self.context_factory.create()

        profiles = context.repositories.profile.find_all()

        for profile in profiles:
            if profile.integrations:
                for integration in profile.integrations:
                    if integration.name == "whatsapp" and integration.activated:
                        return profile

        return None
