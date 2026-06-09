"""
Conversation Domain Error Mappings

Errors related to conversation management operations.
"""

from ..application_error import ErrorDetails


# Conversation Create Errors
ConversationCreateQueryError = ErrorDetails(
    internal_code="conversation:create:query-error",
    status_code=500,
    message="failed to create conversation"
)

ConversationCreateValidationError = ErrorDetails(
    internal_code="conversation:create:validation-error",
    status_code=400,
    message="invalid conversation data"
)

ConversationCreateTitleRequiredError = ErrorDetails(
    internal_code="conversation:create:title-required",
    status_code=400,
    message="conversation title is required"
)

ConversationCreateProfileRequiredError = ErrorDetails(
    internal_code="conversation:create:profile-required",
    status_code=400,
    message="profile ID is required"
)

ConversationCreateProfileNotFoundError = ErrorDetails(
    internal_code="conversation:create:profile-not-found",
    status_code=404,
    message="profile not found for conversation"
)

ConversationCreateNotFoundAfterCreationError = ErrorDetails(
    internal_code="conversation:create:not-found-after-creation",
    status_code=500,
    message="conversation not found after creation"
)

# Conversation Get Errors
ConversationGetQueryError = ErrorDetails(
    internal_code="conversation:get:query-error",
    status_code=500,
    message="failed to retrieve conversation"
)

ConversationGetNotFoundError = ErrorDetails(
    internal_code="conversation:get:not-found",
    status_code=404,
    message="conversation not found"
)

# Conversation Update Errors
ConversationUpdateQueryError = ErrorDetails(
    internal_code="conversation:update:query-error",
    status_code=500,
    message="failed to update conversation"
)

ConversationUpdateNotFoundError = ErrorDetails(
    internal_code="conversation:update:not-found",
    status_code=404,
    message="conversation not found for update"
)

ConversationUpdateValidationError = ErrorDetails(
    internal_code="conversation:update:validation-error",
    status_code=400,
    message="invalid update data"
)

# Conversation Delete Errors
ConversationDeleteQueryError = ErrorDetails(
    internal_code="conversation:delete:query-error",
    status_code=500,
    message="failed to delete conversation"
)

ConversationDeleteNotFoundError = ErrorDetails(
    internal_code="conversation:delete:not-found",
    status_code=404,
    message="conversation not found for deletion"
)

# Conversation List Errors
ConversationListQueryError = ErrorDetails(
    internal_code="conversation:list:query-error",
    status_code=500,
    message="failed to retrieve conversations"
)

# Message Errors
ConversationMessageAddError = ErrorDetails(
    internal_code="conversation:message:add-error",
    status_code=500,
    message="failed to add message to conversation"
)

ConversationMessageDeleteError = ErrorDetails(
    internal_code="conversation:message:delete-error",
    status_code=500,
    message="failed to delete message from conversation"
)

ConversationMessageNotFoundError = ErrorDetails(
    internal_code="conversation:message:not-found",
    status_code=404,
    message="message not found in conversation"
)

ConversationMessageValidationError = ErrorDetails(
    internal_code="conversation:message:validation-error",
    status_code=400,
    message="invalid message data"
)

ConversationMessageContentRequiredError = ErrorDetails(
    internal_code="conversation:message:content-required",
    status_code=400,
    message="message content is required"
)

ConversationMessageImageUnsupportedFormatError = ErrorDetails(
    internal_code="conversation:message:image-unsupported-format",
    status_code=400,
    message="unsupported image format"
)

ConversationMessageImageTooLargeError = ErrorDetails(
    internal_code="conversation:message:image-too-large",
    status_code=400,
    message="image exceeds maximum allowed size"
)

ConversationMessageImageAnalysisError = ErrorDetails(
    internal_code="conversation:message:image-analysis-failed",
    status_code=500,
    message="failed to analyze image"
)
