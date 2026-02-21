"""
Error Mappings Module

Contains all error definitions organized by domain.
"""

from .common import *
from .profile import *
from .conversation import *
from .memory import *
from .calendar import *
from .drive import *
from .whatsapp_device import *

__all__ = [
    # Common errors
    "RequestBodyParsingError",
    "RequestBodyValidationError",
    "ValidationError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "ExternalServiceError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "CommonInternalServerError",

    # Profile errors
    "ProfileCreateQueryError",
    "ProfileCreateNameRequiredError",
    "ProfileCreateDuplicateError",
    "ProfileGetQueryError",
    "ProfileGetNotFoundError",
    "ProfileUpdateQueryError",
    "ProfileUpdateNotFoundError",
    "ProfileDeleteQueryError",
    "ProfileDeleteNotFoundError",
    "ProfileListQueryError",
    "ProfileIterationLimitUpdateError",
    "ProfileApiKeyCreateError",
    "ProfileApiKeyDeleteError",
    "ProfileApiKeyNotFoundError",
    "ProfileApiKeyValidationError",
    "ProfileFileUploadError",
    "ProfileFileDeleteError",
    "ProfileFileNotFoundError",
    "ProfileIntegrationCreateError",
    "ProfileIntegrationUpdateError",
    "ProfileIntegrationNotFoundError",

    # Conversation errors
    "ConversationCreateQueryError",
    "ConversationCreateValidationError",
    "ConversationGetQueryError",
    "ConversationGetNotFoundError",
    "ConversationUpdateQueryError",
    "ConversationUpdateNotFoundError",
    "ConversationDeleteQueryError",
    "ConversationDeleteNotFoundError",
    "ConversationListQueryError",
    "ConversationMessageAddError",
    "ConversationMessageDeleteError",
    "ConversationMessageNotFoundError",
    "ConversationMessageValidationError",

    # Memory errors
    "MemoryFAQNotFoundError",
    "MemoryFAQCreateError",
    "MemoryFAQUpdateError",
    "MemoryFAQDeleteError",
    "MemorySkillNotFoundError",
    "MemoryExtractionError",

    # Calendar errors
    "CalendarSessionNotFoundError",
    "CalendarOAuthError",
    "CalendarTokenRefreshError",
    "CalendarEventTitleRequiredError",
    "CalendarEventInvalidTimesError",
    "CalendarEventNotFoundError",
    "CalendarEventCreateError",
    "CalendarEventUpdateError",
    "CalendarEventDeleteError",
    "CalendarEventQueryError",
    "CalendarSyncError",

    # Drive errors
    "DriveSessionNotFoundError",
    "DriveOAuthError",
    "DriveTokenRefreshError",
    "DriveListFilesError",
    "DriveFileNotFoundError",
    "DriveFileDownloadError",
    "DriveIngestionError",
    "DriveSearchError",
    "DriveSyncError",
    "DriveIndexNotFoundError",

    # WhatsApp Device errors
    "WhatsAppDeviceCreateError",
    "WhatsAppDeviceNameRequiredError",
    "WhatsAppDeviceNotFoundError",
    "WhatsAppDeviceGetQueryError",
    "WhatsAppDeviceListQueryError",
    "WhatsAppDeviceDeleteError",
    "WhatsAppDeviceUpdateError",
    "WhatsAppDeviceAuthError",
    "WhatsAppDeviceConnectError",
    "WhatsAppDeviceDisconnectError",
    "WhatsAppDeviceSendError",
    "WhatsAppDeviceNotConnectedError",
    "WhatsAppDevicePhoneRequiredError",
]
