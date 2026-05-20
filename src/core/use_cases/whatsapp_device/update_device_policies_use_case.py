import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceForbiddenError,
    WhatsAppDeviceNotFoundError,
    WhatsAppDeviceUpdateError,
)
from src.core.domain.whatsapp import WhatsAppDevicePolicies

logger = logging.getLogger(__name__)


class UpdateDevicePoliciesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, device_id: str, device_policies: WhatsAppDevicePolicies, user_id: str):
        context = self.context_factory()
        device = await context.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)
        if device.user_id != user_id:
            raise NewApplicationError(WhatsAppDeviceForbiddenError)

        try:
            sanitized = WhatsAppDevicePolicies(
                allowed_numbers=WhatsAppDevicePolicies.normalized_list(device_policies.allowed_numbers),
                blocked_numbers=WhatsAppDevicePolicies.normalized_list(device_policies.blocked_numbers),
                incoming_filter_mode=device_policies.incoming_filter_mode,
                outgoing_filter_mode=device_policies.outgoing_filter_mode,
            )
            await context.repositories.whatsapp_device.update_fields(
                device_id,
                device_policies=sanitized.dict(),
            )
            device.device_policies = sanitized
            return device
        except Exception as e:
            logger.error(f"Error updating WhatsApp device policies: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceUpdateError, e)
