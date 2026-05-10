import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceNotFoundError,
    WhatsAppDeviceDisconnectError,
)

logger = logging.getLogger(__name__)


class DisconnectDeviceUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, device_id: str, neonize_integration) -> None:
        context = self.context_factory()
        device = await context.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        try:
            await neonize_integration.disconnect(device_id)
            await context.repositories.whatsapp_device.update_status(device_id, "disconnected")
            logger.info(f"Device {device_id} disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting device {device_id}: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceDisconnectError, e)
