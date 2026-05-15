"""
Microsoft Teams Domain Error Mappings
"""
from ..application_error import ErrorDetails

TeamsIntegrationNotFoundError = ErrorDetails(
    internal_code="teams:integration:not-found",
    status_code=404,
    message="Teams integration not found or not activated, please configure it first",
)

TeamsIntegrationConfigError = ErrorDetails(
    internal_code="teams:integration:config-error",
    status_code=400,
    message="Teams integration configuration is incomplete, app_id and app_password are required",
)

TeamsAuthError = ErrorDetails(
    internal_code="teams:auth:error",
    status_code=401,
    message="Teams authentication failed, check app_id and app_password",
)

TeamsSendMessageError = ErrorDetails(
    internal_code="teams:message:send-error",
    status_code=500,
    message="failed to send Teams message",
)

TeamsProcessMessageError = ErrorDetails(
    internal_code="teams:message:process-error",
    status_code=500,
    message="failed to process Teams message",
)

TeamsVerifyError = ErrorDetails(
    internal_code="teams:verify:error",
    status_code=500,
    message="failed to verify Teams connection",
)
