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

    # FAQ errors
    "FAQCreateQueryError",
    "FAQCreateValidationError",
    "FAQCreateNotFoundAfterCreationError",
    "FAQGetQueryError",
    "FAQGetNotFoundError",
    "FAQUpdateQueryError",
    "FAQUpdateNotFoundError",
    "FAQDeleteQueryError",
    "FAQDeleteNotFoundError",
    "FAQListQueryError",
]
