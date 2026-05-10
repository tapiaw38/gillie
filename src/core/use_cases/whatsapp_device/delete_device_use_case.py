import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceDeleteError,
    WhatsAppDeviceNotFoundError,
)

logger = logging.getLogger(__name__)


class DeleteDeviceUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, device_id: str, neonize_integration=None) -> None:
        context = self.context_factory()
        device = await context.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        try:
            if neonize_integration is not None:
                await neonize_integration.remove_client(device_id)
            await context.repositories.whatsapp_device.delete(device_id)
        except Exception as e:
            logger.error(f"Error deleting WhatsApp device {device_id}: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceDeleteError, e)
