from src.adapters.services.conversation.service import ConversationService
from src.adapters.services.profile.service import ProfileService
from src.adapters.services.whatsapp.service import WhatsAppService

class Services:
    _instance = None

    def __init__(
        self,
        profile: ProfileService,
        conversation: ConversationService,
    ):
        self.profile = profile
        self.conversation = conversation
        self._whatsapp = None

    @property
    def whatsapp(self) -> WhatsAppService:
        if self._whatsapp is None:
            self._whatsapp = WhatsAppService(self.conversation)
        return self._whatsapp

    @classmethod
    def create_services(
        cls,
        profile: ProfileService,
        conversation: ConversationService,
    ) -> "Services":
        if cls._instance is None:
            cls._instance = cls(
                profile=profile,
                conversation=conversation,
            )
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Services":
        if cls._instance is None:
            raise Exception("Services has not been initialized. Call `create_services` first.")
        return cls._instance