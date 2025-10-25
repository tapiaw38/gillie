"""
Common Error Mappings

Generic errors that can occur across all domains.
"""

from ..application_error import ErrorDetails


# Request/Input Errors (400)
RequestBodyParsingError = ErrorDetails(
    internal_code="common:request-body-parsing-error",
    status_code=400,
    message="invalid request body format"
)

RequestBodyValidationError = ErrorDetails(
    internal_code="common:request-body-validation-error",
    status_code=400,
    message="request validation failed"
)

ValidationError = ErrorDetails(
    internal_code="common:validation-error",
    status_code=400,
    message="validation failed"
)

# Database Errors (500)
DatabaseConnectionError = ErrorDetails(
    internal_code="common:database-connection-error",
    status_code=500,
    message="failed to connect to database"
)

DatabaseQueryError = ErrorDetails(
    internal_code="common:database-query-error",
    status_code=500,
    message="database query failed"
)

# External Service Errors (502)
ExternalServiceError = ErrorDetails(
    internal_code="common:external-service-error",
    status_code=502,
    message="external service unavailable"
)

# Generic Resource Errors
NotFoundError = ErrorDetails(
    internal_code="common:not-found",
    status_code=404,
    message="resource not found"
)

# Authentication/Authorization Errors
UnauthorizedError = ErrorDetails(
    internal_code="common:unauthorized",
    status_code=401,
    message="authentication required"
)

ForbiddenError = ErrorDetails(
    internal_code="common:forbidden",
    status_code=403,
    message="access forbidden"
)
