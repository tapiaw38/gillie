from fastapi import FastAPI
from src.adapters.web.controllers import conversation, profile, whatsapp
from src.adapters.web.controllers.nosql.controllers import router as nosql_router
from src.adapters.web.controllers.calendar.calendar import router as calendar_router, set_usecases as set_calendar_usecases
from src.adapters.web.controllers.drive.drive import router as drive_router, set_usecases as set_drive_usecases
from src.adapters.web.controllers.memory.controllers import router as memory_router, set_usecases as set_memory_usecases
from src.adapters.web.controllers.whatsapp.device_controllers import (
    router as whatsapp_device_router,
    set_usecases as set_whatsapp_device_usecases,
    set_neonize as set_whatsapp_device_neonize,
)
from src.core.use_cases.use_cases import Usecases
from src.core.platform.config.service import ConfigurationService


class RoutesManager:
    def __init__(self, app: FastAPI, usecases: Usecases, config_service=ConfigurationService, neonize_integration=None):
        self.app = app
        self.usecases = usecases
        self.config_service = config_service
        self.neonize_integration = neonize_integration

    def include_routes(self):
        conversation.controllers.set_usecases(self.usecases)
        profile.controllers.set_usecases(self.usecases)
        whatsapp.controllers.set_usecases(self.usecases)
        set_calendar_usecases(self.usecases)
        set_drive_usecases(self.usecases)
        set_memory_usecases(self.usecases)
        set_whatsapp_device_usecases(self.usecases)
        if self.neonize_integration is not None:
            set_whatsapp_device_neonize(self.neonize_integration)

        self.app.dependency_overrides[ConfigurationService] = lambda: self.config_service

        self.app.include_router(nosql_router)
        self.app.include_router(profile.controllers.router)
        self.app.include_router(conversation.controllers.router)
        self.app.include_router(whatsapp.controllers.router)
        self.app.include_router(whatsapp_device_router)
        self.app.include_router(calendar_router)
        self.app.include_router(drive_router)
        self.app.include_router(memory_router)
