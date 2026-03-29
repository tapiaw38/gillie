"""
Gmail Domain Error Mappings
"""
from ..application_error import ErrorDetails

# Session errors
GmailSessionNotFoundError = ErrorDetails(
    internal_code="gmail:session:not-found",
    status_code=404,
    message="no active Gmail session found, please authorize first",
)

GmailSessionQueryError = ErrorDetails(
    internal_code="gmail:session:query-error",
    status_code=500,
    message="failed to access Gmail session",
)

GmailOAuthError = ErrorDetails(
    internal_code="gmail:oauth:error",
    status_code=500,
    message="Gmail OAuth authorization failed",
)

GmailTokenRefreshError = ErrorDetails(
    internal_code="gmail:token:refresh-error",
    status_code=500,
    message="failed to refresh Gmail token",
)

# Email errors
GmailEmailQueryError = ErrorDetails(
    internal_code="gmail:email:query-error",
    status_code=500,
    message="failed to retrieve emails",
)

GmailEmailNotFoundError = ErrorDetails(
    internal_code="gmail:email:not-found",
    status_code=404,
    message="email not found",
)

GmailEmailSendError = ErrorDetails(
    internal_code="gmail:email:send-error",
    status_code=500,
    message="failed to send email",
)

GmailEmailDeleteError = ErrorDetails(
    internal_code="gmail:email:delete-error",
    status_code=500,
    message="failed to delete email",
)

GmailEmailReplyError = ErrorDetails(
    internal_code="gmail:email:reply-error",
    status_code=500,
    message="failed to reply to email",
)

GmailToRequiredError = ErrorDetails(
    internal_code="gmail:email:to-required",
    status_code=400,
    message="recipient email is required",
)

GmailSubjectRequiredError = ErrorDetails(
    internal_code="gmail:email:subject-required",
    status_code=400,
    message="email subject is required",
)

GmailBodyRequiredError = ErrorDetails(
    internal_code="gmail:email:body-required",
    status_code=400,
    message="email body is required",
)
