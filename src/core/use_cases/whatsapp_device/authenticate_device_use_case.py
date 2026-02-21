import logging
from typing import Callable, Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import ApplicationError, NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceNotFoundError,
    WhatsAppDeviceAuthError,
    WhatsAppDevicePhoneRequiredError,
)

logger = logging.getLogger(__name__)


class AuthenticateDeviceUseCase:
    """
    Initiates WhatsApp device authentication.

    - auth_method="qr"   → Starts neonize QR flow in background; QR stored in DB when ready.
                           The WS /qr-stream endpoint polls the DB and pushes the QR to the UI.
    - auth_method="pair" → Returns 8-digit pair code synchronously (phone_number required).
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(
        self,
        device_id: str,
        auth_method: str,
        neonize_integration,
        phone_number: Optional[str] = None,
        message_handler: Optional[Callable] = None,
    ) -> None:
        device = self.context_factory.repositories.whatsapp_device.find_by_id(device_id)
        if not device:
            raise NewApplicationError(WhatsAppDeviceNotFoundError)

        self.context_factory.repositories.whatsapp_device.update_status(device_id, "connecting")

        try:
            if auth_method == "pair":
                if not phone_number or not phone_number.strip():
                    raise NewApplicationError(WhatsAppDevicePhoneRequiredError)

                pair_code = await neonize_integration.get_pair_code(device_id, phone_number.strip())
                self.context_factory.repositories.whatsapp_device.update_fields(
                    device_id,
                    pair_code=pair_code,
                    phone_number=phone_number.strip(),
                )

            else:  # default: qr
                repo = self.context_factory.repositories.whatsapp_device

                async def on_qr_ready(qr_data_url: str) -> None:
                    repo.update_fields(device_id, qr_code=qr_data_url)
                    logger.info(f"[auth] QR stored in DB for device {device_id}")

                async def on_authenticated() -> None:
                    repo.update_status(device_id, "authenticated")
                    logger.info(f"[auth] Device {device_id} marked as authenticated")

                await neonize_integration.start_qr_auth(
                    device_id,
                    on_qr_ready=on_qr_ready,
                    on_authenticated=on_authenticated,
                    message_handler=message_handler,
                )

        except ApplicationError:
            raise
        except Exception as e:
            logger.error(f"Error authenticating device {device_id}: {e}", exc_info=True)
            self.context_factory.repositories.whatsapp_device.update_status(device_id, "disconnected")
            raise NewApplicationError(WhatsAppDeviceAuthError, e)
