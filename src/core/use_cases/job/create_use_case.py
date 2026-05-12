import logging
import uuid
from datetime import datetime, timezone

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import (
    JobCreateError,
    JobNameRequiredError,
    JobCronExprRequiredError,
    JobInvalidSourceError,
    JobInvalidDestinationError,
)
from src.core.domain.job import Job
from src.schemas.job import JobInput, JobOutput, JobData

logger = logging.getLogger(__name__)

VALID_SOURCES = {"system_command", "http_get", "db_query", "static"}
VALID_DESTINATIONS = {"whatsapp", "telegram", "slack", "none"}


class CreateJobUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, job_input: JobInput, profile_id: str) -> JobOutput:
        if not job_input.name or not job_input.name.strip():
            raise NewApplicationError(JobNameRequiredError)

        if not job_input.cron_expr or not job_input.cron_expr.strip():
            raise NewApplicationError(JobCronExprRequiredError)

        if job_input.source_type not in VALID_SOURCES:
            raise NewApplicationError(JobInvalidSourceError)

        if job_input.destination_type not in VALID_DESTINATIONS:
            raise NewApplicationError(JobInvalidDestinationError)

        now = datetime.now(timezone.utc)
        job = Job(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            name=job_input.name.strip(),
            description=job_input.description,
            cron_expr=job_input.cron_expr.strip(),
            source_type=job_input.source_type,
            source_params=job_input.source_params,
            destination_type=job_input.destination_type,
            destination_params=job_input.destination_params,
            message_template=job_input.message_template,
            enabled=job_input.enabled,
            status="idle",
            created_at=now,
            updated_at=now,
        )

        try:
            context = self.context_factory()
            await context.repositories.job.create(job)
            return JobOutput(data=JobData.from_domain(job))
        except Exception as e:
            logger.error(f"Error creating job: {e}", exc_info=True)
            raise NewApplicationError(JobCreateError, e)
