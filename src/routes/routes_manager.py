from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.adapters.web.controllers import conversation, profile, whatsapp
from src.adapters.web.controllers.nosql.controllers import router as nosql_router
from src.adapters.web.controllers.calendar.calendar import router as calendar_router, set_usecases as set_calendar_usecases
from src.adapters.web.controllers.gmail.gmail import router as gmail_router, set_usecases as set_gmail_usecases
from src.adapters.web.controllers.drive.drive import router as drive_router, set_usecases as set_drive_usecases
from src.adapters.web.controllers.memory.controllers import router as memory_router, set_usecases as set_memory_usecases
from src.adapters.web.controllers.whatsapp.device_controllers import (
    router as whatsapp_device_router,
    set_usecases as set_whatsapp_device_usecases,
    set_neonize as set_whatsapp_device_neonize,
)
from src.adapters.web.controllers.slack.controllers import (
    router as slack_router,
    set_usecases as set_slack_usecases,
)
from src.adapters.web.controllers.telegram.controllers import (
    router as telegram_router,
    set_usecases as set_telegram_usecases,
)
from src.adapters.web.controllers.job.controllers import (
    router as job_router,
    set_usecases as set_job_usecases,
    set_scheduler as set_job_scheduler,
)
from src.core.use_cases.use_cases import Usecases
from src.core.platform.config.service import ConfigurationService


class RoutesManager:
    def __init__(self, app: FastAPI, usecases: Usecases, config_service=ConfigurationService, neonize_integration=None, scheduler=None):
        self.app = app
        self.usecases = usecases
        self.config_service = config_service
        self.neonize_integration = neonize_integration
        self.scheduler = scheduler

    def include_routes(self):
        conversation.controllers.set_usecases(self.usecases)
        profile.controllers.set_usecases(self.usecases)
        whatsapp.controllers.set_usecases(self.usecases)
        set_calendar_usecases(self.usecases)
        set_drive_usecases(self.usecases)
        set_gmail_usecases(self.usecases)
        set_memory_usecases(self.usecases)
        set_whatsapp_device_usecases(self.usecases)
        if self.neonize_integration is not None:
            set_whatsapp_device_neonize(self.neonize_integration)
        set_slack_usecases(self.usecases)
        set_telegram_usecases(self.usecases)
        set_job_usecases(self.usecases)
        if self.scheduler is not None:
            set_job_scheduler(self.scheduler)

        self.app.dependency_overrides[ConfigurationService] = lambda: self.config_service

        # Mount local storage as static files if configured
        storage_cfg = getattr(self.config_service, "storage_config", None)
        if storage_cfg and storage_cfg.backend == "local" and storage_cfg.local_path:
            import os
            os.makedirs(storage_cfg.local_path, exist_ok=True)
            self.app.mount(
                "/api/storage",
                StaticFiles(directory=storage_cfg.local_path),
                name="storage",
            )

        self.app.include_router(nosql_router)
        self.app.include_router(profile.controllers.router)
        self.app.include_router(conversation.controllers.router)
        self.app.include_router(whatsapp.controllers.router)
        self.app.include_router(whatsapp_device_router)
        self.app.include_router(calendar_router)
        self.app.include_router(drive_router)
        self.app.include_router(gmail_router)
        self.app.include_router(memory_router)
        self.app.include_router(slack_router)
        self.app.include_router(telegram_router)
        self.app.include_router(job_router)
