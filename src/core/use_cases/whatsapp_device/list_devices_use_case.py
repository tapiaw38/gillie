import logging
from typing import List

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceListQueryError
from src.core.domain.whatsapp import WhatsAppDevice

logger = logging.getLogger(__name__)


class ListDevicesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str) -> List[WhatsAppDevice]:
        try:
            context = self.context_factory()
            return context.repositories.whatsapp_device.find_by_user_id(user_id)
        except Exception as e:
            logger.error(f"Error listing WhatsApp devices: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceListQueryError, e)
