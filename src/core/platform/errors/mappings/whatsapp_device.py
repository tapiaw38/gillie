"""
WhatsApp Device Domain Error Mappings
"""
from ..application_error import ErrorDetails

WhatsAppDeviceCreateError = ErrorDetails(
    internal_code="whatsapp-device:create:query-error",
    status_code=500,
    message="failed to create WhatsApp device",
)

WhatsAppDeviceNameRequiredError = ErrorDetails(
    internal_code="whatsapp-device:create:name-required",
    status_code=400,
    message="device name is required",
)

WhatsAppDeviceNotFoundError = ErrorDetails(
    internal_code="whatsapp-device:get:not-found",
    status_code=404,
    message="WhatsApp device not found",
)

WhatsAppDeviceGetQueryError = ErrorDetails(
    internal_code="whatsapp-device:get:query-error",
    status_code=500,
    message="failed to retrieve WhatsApp device",
)

WhatsAppDeviceListQueryError = ErrorDetails(
    internal_code="whatsapp-device:list:query-error",
    status_code=500,
    message="failed to list WhatsApp devices",
)

WhatsAppDeviceDeleteError = ErrorDetails(
    internal_code="whatsapp-device:delete:query-error",
    status_code=500,
    message="failed to delete WhatsApp device",
)

WhatsAppDeviceUpdateError = ErrorDetails(
    internal_code="whatsapp-device:update:query-error",
    status_code=500,
    message="failed to update WhatsApp device",
)

WhatsAppDeviceAuthError = ErrorDetails(
    internal_code="whatsapp-device:authenticate:error",
    status_code=500,
    message="failed to start WhatsApp device authentication",
)

WhatsAppDeviceConnectError = ErrorDetails(
    internal_code="whatsapp-device:connect:error",
    status_code=500,
    message="failed to connect WhatsApp device",
)

WhatsAppDeviceDisconnectError = ErrorDetails(
    internal_code="whatsapp-device:disconnect:error",
    status_code=500,
    message="failed to disconnect WhatsApp device",
)

WhatsAppDeviceSendError = ErrorDetails(
    internal_code="whatsapp-device:send:error",
    status_code=500,
    message="failed to send WhatsApp message",
)

WhatsAppDeviceNotConnectedError = ErrorDetails(
    internal_code="whatsapp-device:send:not-connected",
    status_code=409,
    message="WhatsApp device is not connected",
)

WhatsAppDevicePhoneRequiredError = ErrorDetails(
    internal_code="whatsapp-device:authenticate:phone-required",
    status_code=400,
    message="phone number is required for pair code authentication",
)

WhatsAppDeviceForbiddenError = ErrorDetails(
    internal_code="whatsapp-device:update:forbidden",
    status_code=403,
    message="you do not have permission to modify this device",
)
