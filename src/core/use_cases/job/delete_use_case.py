import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import (
    JobDeleteError,
    JobGetNotFoundError,
)

logger = logging.getLogger(__name__)


class DeleteJobUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, job_id: str) -> None:
        context = self.context_factory()
        job = context.repositories.job.find_by_id(job_id)
        if not job:
            raise NewApplicationError(JobGetNotFoundError)

        try:
            context.repositories.job.delete(job_id)
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}", exc_info=True)
            raise NewApplicationError(JobDeleteError, e)
