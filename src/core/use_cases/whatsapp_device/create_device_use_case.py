import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceCreateError,
    WhatsAppDeviceNameRequiredError,
)
from src.core.domain.whatsapp_device import WhatsAppDevice

logger = logging.getLogger(__name__)


class CreateDeviceUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, device_name: str, phone_number: Optional[str] = None) -> WhatsAppDevice:
        if not device_name or not device_name.strip():
            raise NewApplicationError(WhatsAppDeviceNameRequiredError)

        now = datetime.now(timezone.utc)
        device = WhatsAppDevice(
            id=str(uuid.uuid4()),
            user_id=user_id,
            device_name=device_name.strip(),
            phone_number=phone_number.strip() if phone_number else None,
            status="disconnected",
            created_at=now,
            updated_at=now,
        )

        try:
            self.context_factory.repositories.whatsapp_device.create(device)
            return device
        except Exception as e:
            logger.error(f"Error creating WhatsApp device: {e}", exc_info=True)
            raise NewApplicationError(WhatsAppDeviceCreateError, e)
