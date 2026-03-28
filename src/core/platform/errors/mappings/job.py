from src.core.platform.errors.application_error import ErrorDetails

JobCreateError = ErrorDetails(
    internal_code="job:create:error",
    status_code=500,
    message="Error creating job",
)
JobGetNotFoundError = ErrorDetails(
    internal_code="job:get:not-found",
    status_code=404,
    message="Job not found",
)
JobGetQueryError = ErrorDetails(
    internal_code="job:get:query-error",
    status_code=500,
    message="Error fetching job",
)
JobListQueryError = ErrorDetails(
    internal_code="job:list:query-error",
    status_code=500,
    message="Error listing jobs",
)
JobUpdateError = ErrorDetails(
    internal_code="job:update:error",
    status_code=500,
    message="Error updating job",
)
JobDeleteError = ErrorDetails(
    internal_code="job:delete:error",
    status_code=500,
    message="Error deleting job",
)
JobRunError = ErrorDetails(
    internal_code="job:run:error",
    status_code=500,
    message="Error running job",
)
JobNameRequiredError = ErrorDetails(
    internal_code="job:create:name-required",
    status_code=400,
    message="Job name is required",
)
JobCronExprRequiredError = ErrorDetails(
    internal_code="job:create:cron-required",
    status_code=400,
    message="Cron expression is required",
)
JobInvalidSourceError = ErrorDetails(
    internal_code="job:create:invalid-source",
    status_code=400,
    message="Invalid source_type",
)
JobInvalidDestinationError = ErrorDetails(
    internal_code="job:create:invalid-destination",
    status_code=400,
    message="Invalid destination_type",
)
