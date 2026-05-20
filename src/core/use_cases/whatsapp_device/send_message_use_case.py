import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ForbiddenError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceNotFoundError,
    WhatsAppDeviceSendError,
    WhatsAppDeviceNotConnectedError,
)

logger = logging.getLogger(__name__)


class SendMessageUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        device_id: str,
        recipient_jid: str,
        text: str,
        neonize_integration,
    ) -> str:
        context = self.context_factory()
        device = await context.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        if device.status not in ("authenticated", "connected"):
            raise NewApplicationError(WhatsAppDeviceNotConnectedError)
        if not device.device_policies.contact_allowed(recipient_jid, "outgoing"):
            raise NewApplicationError(ForbiddenError, Exception("recipient blocked by device policies"))

        try:
            message_id = await neonize_integration.send_text(device_id, recipient_jid, text)
            return message_id
        except Exception as e:
            logger.error(f"Error sending message via device {device_id}: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceSendError, e)
