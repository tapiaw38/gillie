import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceNotFoundError,
    WhatsAppDeviceConnectError,
)

logger = logging.getLogger(__name__)


class ConnectDeviceUseCase:
    """
    Connects a WhatsApp device and starts listening for incoming messages.
    The message_handler is invoked for every incoming message.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        device_id: str,
        neonize_integration,
        message_handler: Optional[Callable] = None,
    ) -> None:
        context = self.context_factory()
        device = await context.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        try:
            await neonize_integration.connect(device_id, message_handler)
            await context.repositories.whatsapp_device.update_status(
                device_id,
                "authenticated",
                last_connected_at=datetime.now(timezone.utc),
                qr_code=None,
                pair_code=None,
            )
            logger.info(f"Device {device_id} connected and listening")
        except Exception as e:
            logger.error(f"Error connecting device {device_id}: {e}", exc_info=True)
            await context.repositories.whatsapp_device.update_status(device_id, "disconnected")
            raise NewApplicationError(WhatsAppDeviceConnectError, e)
