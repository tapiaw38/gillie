import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SchedulerManager:
    def __init__(self, job_repository, context_factory):
        self.job_repository = job_repository
        self.context_factory = context_factory
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """Load all enabled jobs and start the scheduler."""
        jobs = self.job_repository.find_all_enabled()
        for job in jobs:
            self._schedule_job(job)
        self.scheduler.start()
        logger.info(f"[scheduler] Started with {len(jobs)} jobs")

    def _schedule_job(self, job):
        """Parse 5-field cron expr and add to APScheduler."""
        try:
            parts = job.cron_expr.strip().split()
            if len(parts) != 5:
                logger.error(f"[scheduler] Invalid cron expr for job {job.id}: {job.cron_expr}")
                return
            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
            )
            self.scheduler.add_job(
                self._run_job,
                trigger=trigger,
                args=[job.id],
                id=job.id,
                replace_existing=True,
            )
            logger.info(f"[scheduler] Scheduled job {job.id} ({job.name}) with cron={job.cron_expr}")
        except Exception as e:
            logger.error(f"[scheduler] Failed to schedule job {job.id}: {e}")

    async def _run_job(self, job_id: str):
        """Actually execute a job when the cron fires."""
        logger.info(f"[scheduler] Triggered job {job_id}")
        try:
            from src.core.use_cases.job.run_use_case import RunJobUseCase
            run_uc = RunJobUseCase(self.context_factory)
            result = await run_uc.execute(job_id)
            logger.info(f"[scheduler] Job {job_id} completed: {result}")
        except Exception as e:
            logger.error(f"[scheduler] Job {job_id} failed: {e}", exc_info=True)

    def schedule_job(self, job):
        """Add or update a job in the running scheduler."""
        self._schedule_job(job)

    def unschedule_job(self, job_id: str):
        """Remove a job from the running scheduler."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"[scheduler] Unscheduled job {job_id}")
        except Exception:
            pass

    async def stop(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("[scheduler] Stopped")
