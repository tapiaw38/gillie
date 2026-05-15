"""
Jira Domain Error Mappings
"""
from ..application_error import ErrorDetails

JiraIntegrationNotFoundError = ErrorDetails(
    internal_code="jira:integration:not-found",
    status_code=404,
    message="Jira integration not found or not activated, please configure it first",
)

JiraIntegrationConfigError = ErrorDetails(
    internal_code="jira:integration:config-error",
    status_code=400,
    message="Jira integration configuration is incomplete, domain, email and api_token are required",
)

JiraIssueNotFoundError = ErrorDetails(
    internal_code="jira:issue:not-found",
    status_code=404,
    message="Jira issue not found",
)

JiraIssueCreateError = ErrorDetails(
    internal_code="jira:issue:create-error",
    status_code=500,
    message="failed to create Jira issue",
)

JiraIssueUpdateError = ErrorDetails(
    internal_code="jira:issue:update-error",
    status_code=500,
    message="failed to update Jira issue",
)

JiraIssueDeleteError = ErrorDetails(
    internal_code="jira:issue:delete-error",
    status_code=500,
    message="failed to delete Jira issue",
)

JiraIssueQueryError = ErrorDetails(
    internal_code="jira:issue:query-error",
    status_code=500,
    message="failed to retrieve Jira issues",
)

JiraTransitionError = ErrorDetails(
    internal_code="jira:issue:transition-error",
    status_code=500,
    message="failed to transition Jira issue",
)

JiraTransitionQueryError = ErrorDetails(
    internal_code="jira:issue:transition-query-error",
    status_code=500,
    message="failed to retrieve Jira transitions",
)

JiraCommentCreateError = ErrorDetails(
    internal_code="jira:comment:create-error",
    status_code=500,
    message="failed to add comment to Jira issue",
)

JiraProjectQueryError = ErrorDetails(
    internal_code="jira:project:query-error",
    status_code=500,
    message="failed to retrieve Jira projects",
)

JiraIssueSummaryRequiredError = ErrorDetails(
    internal_code="jira:issue:summary-required",
    status_code=400,
    message="issue summary is required",
)

JiraProjectKeyRequiredError = ErrorDetails(
    internal_code="jira:issue:project-key-required",
    status_code=400,
    message="project_key is required to create an issue",
)
