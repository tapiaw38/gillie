import logging
from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceGetQueryError,
    WhatsAppDeviceNotFoundError,
)
from src.core.domain.whatsapp import WhatsAppDevice

logger = logging.getLogger(__name__)


class GetDeviceUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, device_id: str) -> WhatsAppDevice:
        try:
            context = self.context_factory()
            device = await context.repositories.whatsapp_device.find_by_id(device_id)
        except Exception as e:
            logger.error(f"Error getting WhatsApp device: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceGetQueryError, e)

        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        return device
