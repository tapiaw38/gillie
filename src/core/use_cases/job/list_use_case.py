import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobListQueryError
from src.schemas.job import JobListOutput, JobData

logger = logging.getLogger(__name__)


class ListJobsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, profile_id: str) -> JobListOutput:
        try:
            context = self.context_factory()
            jobs = await context.repositories.job.find_all(profile_id)
            return JobListOutput(data=[JobData.from_domain(j) for j in jobs])
        except Exception as e:
            logger.error(f"Error listing jobs: {e}", exc_info=True)
            raise NewApplicationError(JobListQueryError, e)
