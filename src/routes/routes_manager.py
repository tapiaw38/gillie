from fastapi import FastAPI
from src.adapters.web.controllers import conversation, profile, faq, whatsapp, calendar
from src.adapters.web.controllers.nosql.controllers import router as nosql_router
from src.core.use_cases.use_cases import Usecases
from src.core.platform.config.service import ConfigurationService
from src.adapters.web.middlewares.authorization import AuthorizationMiddleware


class RoutesManager:
    def __init__(self, app: FastAPI, usecases: Usecases, config_service=ConfigurationService):
        self.app = app
        self.usecases = usecases
        self.config_service = config_service

    def include_routes(self):
        # Initialize usecases in controllers
        conversation.controllers.set_usecases(self.usecases)
        profile.controllers.set_usecases(self.usecases)
        faq.controllers.set_usecases(self.usecases)
        whatsapp.controllers.set_usecases(self.usecases)
        calendar.controllers.set_usecases(self.usecases)

        # Override config service dependency
        self.app.dependency_overrides[ConfigurationService] = lambda: self.config_service

        # Add middleware (now using usecases directly)
        self.app.add_middleware(AuthorizationMiddleware, usecases=self.usecases)

        # Include routers
        self.app.include_router(nosql_router)
        self.app.include_router(profile.controllers.router)
        self.app.include_router(conversation.controllers.router)
        self.app.include_router(whatsapp.controllers.router)
        self.app.include_router(faq.controllers.router)
        self.app.include_router(calendar.controllers.router)