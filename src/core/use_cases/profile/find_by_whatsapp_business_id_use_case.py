from typing import Optional
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile


class FindByWhatsAppBusinessIdUseCase:
    """
    Find a profile by WhatsApp business account ID.
    Searches through all profiles and their integrations to find a matching WhatsApp configuration.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, business_account_id: str) -> Optional[Profile]:
        """
        Execute the use case to find a profile by WhatsApp business account ID.

        Args:
            business_account_id: The WhatsApp business account ID to search for

        Returns:
            Profile if found, None otherwise
        """
        context = self.context_factory()

        profiles = context.repositories.profile.find_all()

        for profile in profiles:
            if profile.integrations:
                for integration in profile.integrations:
                    if (
                        integration.name == "whatsapp"
                        and integration.activated
                        and integration.config.get("businessAccountId")
                        == business_account_id
                    ):
                        return profile

        return None
