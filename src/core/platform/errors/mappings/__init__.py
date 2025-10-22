"""
Error Mappings Module

Contains all error definitions organized by domain.
"""

from .common import *
from .profile import *
from .conversation import *
from .faq import *

__all__ = [
    # Common errors
    "RequestBodyParsingError",
    "RequestBodyValidationError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "ExternalServiceError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",

    # Profile errors
    "ProfileCreateQueryError",
    "ProfileCreateNameRequiredError",
    "ProfileGetQueryError",
    "ProfileGetNotFoundError",
    "ProfileUpdateQueryError",
    "ProfileUpdateNotFoundError",
    "ProfileDeleteQueryError",
    "ProfileDeleteNotFoundError",
    "ProfileListQueryError",
    "ProfileApiKeyCreateError",
    "ProfileApiKeyDeleteError",
    "ProfileApiKeyNotFoundError",
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
    "ConversationDeleteQueryError",
    "ConversationMessageAddError",
    "ConversationMessageDeleteError",
    "ConversationMessageNotFoundError",

    # FAQ errors
    "FAQCreateQueryError",
    "FAQCreateValidationError",
    "FAQGetQueryError",
    "FAQGetNotFoundError",
    "FAQUpdateQueryError",
    "FAQUpdateNotFoundError",
    "FAQDeleteQueryError",
    "FAQDeleteNotFoundError",
    "FAQListQueryError",
]
