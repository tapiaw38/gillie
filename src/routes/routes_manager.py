from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.adapters.web.controllers import conversation, profile, whatsapp
from src.adapters.web.controllers.nosql.controllers import router as nosql_router
from src.adapters.web.controllers.calendar.calendar import router as calendar_router
from src.adapters.web.controllers.gmail.gmail import router as gmail_router
from src.adapters.web.controllers.drive.drive import router as drive_router
from src.adapters.web.controllers.memory.controllers import router as memory_router
from src.adapters.web.controllers.whatsapp.device_controllers import (
    router as whatsapp_device_router,
    set_neonize as set_whatsapp_device_neonize,
    set_app as set_whatsapp_device_app,
)
from src.adapters.web.controllers.slack.controllers import router as slack_router
from src.adapters.web.controllers.telegram.controllers import router as telegram_router
from src.adapters.web.controllers.job.controllers import (
    router as job_router,
    set_scheduler as set_job_scheduler,
)
from src.adapters.web.controllers.system.controllers import (
    router as system_router,
    set_openai_integration,
)
from src.core.use_cases.use_cases import Usecases
from src.core.platform.config.service import ConfigurationService


class RoutesManager:
    def __init__(self, app: FastAPI, usecases: Usecases, config_service=ConfigurationService, neonize_integration=None, scheduler=None, openai_integration=None):
        self.app = app
        self.usecases = usecases
        self.config_service = config_service
        self.neonize_integration = neonize_integration
        self.scheduler = scheduler
        self.openai_integration = openai_integration

    def include_routes(self):
        self.app.state.usecases = self.usecases

        set_whatsapp_device_app(self.app)
        if self.neonize_integration is not None:
            set_whatsapp_device_neonize(self.neonize_integration)
        if self.scheduler is not None:
            set_job_scheduler(self.scheduler)
        if self.openai_integration is not None:
            set_openai_integration(self.openai_integration)

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
        self.app.include_router(system_router)
