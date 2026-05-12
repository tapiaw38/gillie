import logging

from fastapi import APIRouter, Depends, Request, status

from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
from src.schemas.job import JobInput, JobOutput, JobListOutput, JobRunOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


def _get_user_id(request: Request) -> str:
    return request.state.user.get("user_id", "default-user")


@router.get("/", response_model=JobListOutput)
async def list_jobs(request: Request, usecases: Usecases = Depends(get_usecases)):
    """List all jobs for the current user."""
    user_id = _get_user_id(request)
    return await usecases.jobs.list_usecase.execute(user_id)


@router.post("/", response_model=JobOutput, status_code=status.HTTP_201_CREATED)
async def create_job(request: Request, body: JobInput, usecases: Usecases = Depends(get_usecases)):
    """Create a new cron job."""
    user_id = _get_user_id(request)
    result = await usecases.jobs.create_usecase.execute(body, user_id)

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler and result.data.enabled:
        context = usecases.jobs.create_usecase.context_factory()
        domain_job = await context.repositories.job.find_by_id(result.data.id)
        if domain_job:
            scheduler.schedule_job(domain_job)

    return result


@router.get("/{job_id}", response_model=JobOutput)
async def get_job(job_id: str, usecases: Usecases = Depends(get_usecases)):
    """Get a job by ID."""
    return await usecases.jobs.get_usecase.execute(job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Delete a job by ID."""
    await usecases.jobs.delete_usecase.execute(job_id)

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler:
        scheduler.unschedule_job(job_id)


@router.post("/{job_id}/run", response_model=JobRunOutput)
async def run_job(job_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    """Run a job immediately."""
    result = await usecases.jobs.run_usecase.execute(job_id)

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler:
        context = usecases.jobs.get_usecase.context_factory()
        domain_job = await context.repositories.job.find_by_id(job_id)
        if domain_job and domain_job.enabled:
            scheduler.schedule_job(domain_job)

    return result
