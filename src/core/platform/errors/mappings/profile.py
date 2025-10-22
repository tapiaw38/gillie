"""
Profile Domain Error Mappings

Errors related to profile management operations.
"""

from ..application_error import ErrorDetails


# Profile Create Errors
ProfileCreateQueryError = ErrorDetails(
    internal_code="profile:create:query-error",
    status_code=500,
    message="failed to create profile"
)

ProfileCreateNameRequiredError = ErrorDetails(
    internal_code="profile:create:name-required",
    status_code=400,
    message="assistant name is required"
)

ProfileCreateBusinessNameRequiredError = ErrorDetails(
    internal_code="profile:create:business-name-required",
    status_code=400,
    message="business name is required"
)

ProfileCreateDuplicateError = ErrorDetails(
    internal_code="profile:create:duplicate",
    status_code=409,
    message="profile already exists for this user"
)

ProfileCreateNotFoundAfterCreationError = ErrorDetails(
    internal_code="profile:create:not-found-after-creation",
    status_code=500,
    message="profile not found after creation"
)

# Profile Get Errors
ProfileGetQueryError = ErrorDetails(
    internal_code="profile:get:query-error",
    status_code=500,
    message="failed to retrieve profile"
)

ProfileGetNotFoundError = ErrorDetails(
    internal_code="profile:get:not-found",
    status_code=404,
    message="profile not found"
)

# Profile Update Errors
ProfileUpdateQueryError = ErrorDetails(
    internal_code="profile:update:query-error",
    status_code=500,
    message="failed to update profile"
)

ProfileUpdateNotFoundError = ErrorDetails(
    internal_code="profile:update:not-found",
    status_code=404,
    message="profile not found for update"
)

ProfileUpdateValidationError = ErrorDetails(
    internal_code="profile:update:validation-error",
    status_code=400,
    message="invalid update data"
)

# Profile Delete Errors
ProfileDeleteQueryError = ErrorDetails(
    internal_code="profile:delete:query-error",
    status_code=500,
    message="failed to delete profile"
)

ProfileDeleteNotFoundError = ErrorDetails(
    internal_code="profile:delete:not-found",
    status_code=404,
    message="profile not found for deletion"
)

# Profile List Errors
ProfileListQueryError = ErrorDetails(
    internal_code="profile:list:query-error",
    status_code=500,
    message="failed to retrieve profiles"
)

# Profile Status Errors
ProfileChangeStatusQueryError = ErrorDetails(
    internal_code="profile:change-status:query-error",
    status_code=500,
    message="failed to change profile status"
)

ProfileChangeStatusNotFoundError = ErrorDetails(
    internal_code="profile:change-status:not-found",
    status_code=404,
    message="profile not found for status change"
)

# API Key Errors
ProfileApiKeyCreateError = ErrorDetails(
    internal_code="profile:api-key:create-error",
    status_code=500,
    message="failed to create API key"
)

ProfileApiKeyDeleteError = ErrorDetails(
    internal_code="profile:api-key:delete-error",
    status_code=500,
    message="failed to delete API key"
)

ProfileApiKeyNotFoundError = ErrorDetails(
    internal_code="profile:api-key:not-found",
    status_code=404,
    message="API key not found"
)

ProfileApiKeyValidationError = ErrorDetails(
    internal_code="profile:api-key:validation-error",
    status_code=400,
    message="invalid API key data"
)

ProfileApiKeyLimitExceededError = ErrorDetails(
    internal_code="profile:api-key:limit-exceeded",
    status_code=400,
    message="API key limit exceeded"
)

# File Errors
ProfileFileUploadError = ErrorDetails(
    internal_code="profile:file:upload-error",
    status_code=500,
    message="failed to upload file"
)

ProfileFileDeleteError = ErrorDetails(
    internal_code="profile:file:delete-error",
    status_code=500,
    message="failed to delete file"
)

ProfileFileNotFoundError = ErrorDetails(
    internal_code="profile:file:not-found",
    status_code=404,
    message="file not found"
)

ProfileFileInvalidTypeError = ErrorDetails(
    internal_code="profile:file:invalid-type",
    status_code=400,
    message="invalid file type"
)

ProfileFileSizeExceededError = ErrorDetails(
    internal_code="profile:file:size-exceeded",
    status_code=400,
    message="file size exceeds limit"
)

# Integration Errors
ProfileIntegrationCreateError = ErrorDetails(
    internal_code="profile:integration:create-error",
    status_code=500,
    message="failed to create integration"
)

ProfileIntegrationUpdateError = ErrorDetails(
    internal_code="profile:integration:update-error",
    status_code=500,
    message="failed to update integration"
)

ProfileIntegrationNotFoundError = ErrorDetails(
    internal_code="profile:integration:not-found",
    status_code=404,
    message="integration not found"
)

ProfileIntegrationValidationError = ErrorDetails(
    internal_code="profile:integration:validation-error",
    status_code=400,
    message="invalid integration data"
)

# Iteration Limit Errors
ProfileIterationLimitUpdateError = ErrorDetails(
    internal_code="profile:iteration-limit:update-error",
    status_code=500,
    message="failed to update iteration limit"
)

ProfileIterationLimitValidationError = ErrorDetails(
    internal_code="profile:iteration-limit:validation-error",
    status_code=400,
    message="invalid iteration limit value"
)
