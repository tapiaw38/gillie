from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.routes.routes_manager import RoutesManager
from src.adapters.web.integrations.integrations import create_integrations
from src.core.platform.config.service import (
    init_config,
    get_config_service
)
from src.core.platform.nosql.client import MongoDBClient
from src.adapters.datasources.datasources import Datasources
from src.core.platform.appcontext.appcontext import new_factory
from src.core.use_cases.use_cases import create_usecases
from src.core.platform.nosql.migrations import execute_migrations
from src.core.platform.objectstorange.s3_session import get_s3_session
from src.adapters.storeservice.storeservice import StoreServiceImpl
from src.core.platform.services.platform_services import PlatformServices
from src.core.platform.errors.exception_handler import register_exception_handlers


app = FastAPI(
    title="Assistant IA API",
    description="API for the Assistant IA",
    version="1.0.0"
)

register_exception_handlers(app)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

init_config()
config_service = get_config_service()


migrations_client = MongoDBClient(
    config_service.nosql_config.migrations.database_uri,
    config_service.nosql_config.migrations.database,
    config_service.nosql_config.migrations.collection,
)
conversations_client = MongoDBClient(
    config_service.nosql_config.conversations.database_uri,
    config_service.nosql_config.conversations.database,
    config_service.nosql_config.conversations.collection,
)
profiles_client = MongoDBClient(
    config_service.nosql_config.profiles.database_uri,
    config_service.nosql_config.profiles.database,
    config_service.nosql_config.profiles.collection,
)
faqs_client = MongoDBClient(
    config_service.nosql_config.faqs.database_uri,
    config_service.nosql_config.faqs.database,
    config_service.nosql_config.faqs.collection,
)

profiles_client.run_migrations(migrations_client.get_collection(), execute_migrations())

s3_session = get_s3_session()
store_service = StoreServiceImpl(
    session=s3_session,
    config=config_service
)

datasources = Datasources.create_datasources(
    no_sql_conversations_client=conversations_client,
    no_sql_profiles_client=profiles_client,
    no_sql_faqs_client=faqs_client,
)

from src.adapters.datasources.repositories.repositories import Repositories
repositories = Repositories.create_repositories(datasources)

integrations = create_integrations(config_service)

platform_services = PlatformServices.create_services(
    integrations=integrations,
    store_service=store_service,
    config_service=config_service,
    faq_repository=repositories.faq
)

context_factory = new_factory(
    datasources,
    integrations,
    store_service,
    config_service,
    platform_services
)
usecases = create_usecases(context_factory)

routes_manager = RoutesManager(app, usecases, config_service)
routes_manager.include_routes()