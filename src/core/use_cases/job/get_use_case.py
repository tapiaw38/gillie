import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import (
    JobGetQueryError,
    JobGetNotFoundError,
)
from src.schemas.job import JobOutput, JobData

logger = logging.getLogger(__name__)


class GetJobUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, job_id: str) -> JobOutput:
        try:
            context = self.context_factory()
            job = await context.repositories.job.find_by_id(job_id)
        except Exception as e:
            logger.error(f"Error getting job: {e}", exc_info=True)
            raise NewApplicationError(JobGetQueryError, e)

        if not job:
            raise NewApplicationError(JobGetNotFoundError)

        return JobOutput(data=JobData.from_domain(job))
