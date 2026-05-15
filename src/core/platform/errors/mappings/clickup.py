"""
ClickUp Domain Error Mappings
"""
from ..application_error import ErrorDetails

ClickUpIntegrationNotFoundError = ErrorDetails(
    internal_code="clickup:integration:not-found",
    status_code=404,
    message="ClickUp integration not found or not activated, please configure it first",
)

ClickUpIntegrationConfigError = ErrorDetails(
    internal_code="clickup:integration:config-error",
    status_code=400,
    message="ClickUp integration configuration is incomplete, api_token is required",
)

ClickUpTaskNotFoundError = ErrorDetails(
    internal_code="clickup:task:not-found",
    status_code=404,
    message="ClickUp task not found",
)

ClickUpTaskCreateError = ErrorDetails(
    internal_code="clickup:task:create-error",
    status_code=500,
    message="failed to create ClickUp task",
)

ClickUpTaskUpdateError = ErrorDetails(
    internal_code="clickup:task:update-error",
    status_code=500,
    message="failed to update ClickUp task",
)

ClickUpTaskDeleteError = ErrorDetails(
    internal_code="clickup:task:delete-error",
    status_code=500,
    message="failed to delete ClickUp task",
)

ClickUpTaskQueryError = ErrorDetails(
    internal_code="clickup:task:query-error",
    status_code=500,
    message="failed to retrieve ClickUp tasks",
)

ClickUpCommentCreateError = ErrorDetails(
    internal_code="clickup:comment:create-error",
    status_code=500,
    message="failed to add comment to ClickUp task",
)

ClickUpWorkspaceQueryError = ErrorDetails(
    internal_code="clickup:workspace:query-error",
    status_code=500,
    message="failed to retrieve ClickUp workspace data",
)

ClickUpTaskNameRequiredError = ErrorDetails(
    internal_code="clickup:task:name-required",
    status_code=400,
    message="task name is required",
)

ClickUpListIdRequiredError = ErrorDetails(
    internal_code="clickup:task:list-id-required",
    status_code=400,
    message="list_id is required to create a task",
)
