import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from src.adapters.bootstrap.startup_service import StartupService
from src.adapters.datasources.datasources import Datasources
from src.adapters.datasources.repositories.repositories import Repositories
from src.adapters.storeservice.local_storeservice import LocalStoreService
from src.adapters.storeservice.s3_storeservice import S3StoreService
from src.adapters.web.integrations.integrations import create_integrations
from src.adapters.web.integrations.neonize.neonize_integration import NeonizeIntegration
from src.adapters.web.middlewares.authorization import SingleUserMiddleware
from src.core.platform.appcontext.appcontext import new_factory
from src.core.platform.errors.exception_handler import register_exception_handlers
from src.core.platform.managers.platform_manager import PlatformServices
from src.core.platform.managers.skill_manager import SkillManager
from src.core.platform.nosql.client import AsyncMongoDBClient, MongoDBClient
from src.core.platform.nosql.migrations import execute_migrations
from src.core.platform.objectstorange.s3_session import get_s3_session
from src.core.platform.config.service import (
    get_config_service,
    init_config,
    init_config_from_json,
)
from src.core.use_cases.use_cases import create_usecases
from src.routes.routes_manager import RoutesManager

logger = logging.getLogger(__name__)


@dataclass
class AppRuntime:
    cli_config: Any
    config_service: Any
    usecases: Any
    repositories: Any
    scheduler: Any
    user_id: str
    neonize_integration: NeonizeIntegration
    openai_integration: Any
    profiles_client: MongoDBClient
    mongo_clients: list[MongoDBClient]
    async_mongo_clients: list[AsyncMongoDBClient]


def _load_runtime_config() -> tuple[Any, Any]:
    cli_config = None

    try:
        from cli.config.manager import config_exists, load_config

        if config_exists():
            cli_config = load_config()
            init_config_from_json(cli_config)
            logger.info("Loaded config from CLI config.json (user_id=%s)", cli_config.user_id)
        else:
            init_config()
            logger.info("Loaded config from .env (no CLI config found)")
    except ImportError:
        init_config()
        logger.info("CLI module not available, loaded config from .env")

    return cli_config, get_config_service()


def _build_runtime() -> AppRuntime:
    cli_config, config_service = _load_runtime_config()

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
    whatsapp_devices_client = MongoDBClient(
        config_service.nosql_config.whatsapp_devices.database_uri,
        config_service.nosql_config.whatsapp_devices.database,
        config_service.nosql_config.whatsapp_devices.collection,
    )
    jobs_client = MongoDBClient(
        config_service.nosql_config.jobs.database_uri,
        config_service.nosql_config.jobs.database,
        config_service.nosql_config.jobs.collection,
    )

    async_conversations_client = AsyncMongoDBClient(
        config_service.nosql_config.conversations.database_uri,
        config_service.nosql_config.conversations.database,
        config_service.nosql_config.conversations.collection,
    )
    async_profiles_client = AsyncMongoDBClient(
        config_service.nosql_config.profiles.database_uri,
        config_service.nosql_config.profiles.database,
        config_service.nosql_config.profiles.collection,
    )

    mongo_clients = [
        migrations_client,
        conversations_client,
        profiles_client,
        faqs_client,
        whatsapp_devices_client,
        jobs_client,
    ]
    async_mongo_clients = [async_conversations_client, async_profiles_client]

    calendar_sessions_client = None
    async_calendar_sessions_client = None
    if config_service.nosql_config.calendar_sessions:
        calendar_sessions_client = MongoDBClient(
            config_service.nosql_config.calendar_sessions.database_uri,
            config_service.nosql_config.calendar_sessions.database,
            config_service.nosql_config.calendar_sessions.collection,
        )
        async_calendar_sessions_client = AsyncMongoDBClient(
            config_service.nosql_config.calendar_sessions.database_uri,
            config_service.nosql_config.calendar_sessions.database,
            config_service.nosql_config.calendar_sessions.collection,
        )
        mongo_clients.append(calendar_sessions_client)
        async_mongo_clients.append(async_calendar_sessions_client)

    drive_sessions_client = None
    async_drive_sessions_client = None
    if config_service.nosql_config.drive_sessions:
        drive_sessions_client = MongoDBClient(
            config_service.nosql_config.drive_sessions.database_uri,
            config_service.nosql_config.drive_sessions.database,
            config_service.nosql_config.drive_sessions.collection,
        )
        async_drive_sessions_client = AsyncMongoDBClient(
            config_service.nosql_config.drive_sessions.database_uri,
            config_service.nosql_config.drive_sessions.database,
            config_service.nosql_config.drive_sessions.collection,
        )
        mongo_clients.append(drive_sessions_client)
        async_mongo_clients.append(async_drive_sessions_client)

    gmail_sessions_client = None
    async_gmail_sessions_client = None
    if config_service.nosql_config.gmail_sessions:
        gmail_sessions_client = MongoDBClient(
            config_service.nosql_config.gmail_sessions.database_uri,
            config_service.nosql_config.gmail_sessions.database,
            config_service.nosql_config.gmail_sessions.collection,
        )
        async_gmail_sessions_client = AsyncMongoDBClient(
            config_service.nosql_config.gmail_sessions.database_uri,
            config_service.nosql_config.gmail_sessions.database,
            config_service.nosql_config.gmail_sessions.collection,
        )
        mongo_clients.append(gmail_sessions_client)
        async_mongo_clients.append(async_gmail_sessions_client)

    notion_sessions_client = None
    async_notion_sessions_client = None
    if config_service.nosql_config.notion_sessions:
        notion_sessions_client = MongoDBClient(
            config_service.nosql_config.notion_sessions.database_uri,
            config_service.nosql_config.notion_sessions.database,
            config_service.nosql_config.notion_sessions.collection,
        )
        async_notion_sessions_client = AsyncMongoDBClient(
            config_service.nosql_config.notion_sessions.database_uri,
            config_service.nosql_config.notion_sessions.database,
            config_service.nosql_config.notion_sessions.collection,
        )
        mongo_clients.append(notion_sessions_client)
        async_mongo_clients.append(async_notion_sessions_client)

    async_whatsapp_devices_client = AsyncMongoDBClient(
        config_service.nosql_config.whatsapp_devices.database_uri,
        config_service.nosql_config.whatsapp_devices.database,
        config_service.nosql_config.whatsapp_devices.collection,
    )
    async_jobs_client = AsyncMongoDBClient(
        config_service.nosql_config.jobs.database_uri,
        config_service.nosql_config.jobs.database,
        config_service.nosql_config.jobs.collection,
    )
    async_mongo_clients.extend([async_whatsapp_devices_client, async_jobs_client])

    profiles_client.run_migrations(migrations_client.get_collection(), execute_migrations())

    storage_cfg = config_service.storage_config
    if storage_cfg and storage_cfg.backend == "local":
        store_service = LocalStoreService(
            base_path=storage_cfg.local_path,
            base_url=storage_cfg.local_base_url,
        )
        logger.info("Storage: local — %s", storage_cfg.local_path)
    else:
        s3_session = get_s3_session()
        store_service = S3StoreService(session=s3_session, config=config_service)
        logger.info("Storage: S3")

    datasources = Datasources.create_datasources(
        no_sql_conversations_client=async_conversations_client,
        no_sql_profiles_client=async_profiles_client,
        no_sql_faqs_client=faqs_client,
        no_sql_calendar_sessions_client=async_calendar_sessions_client,
        no_sql_drive_sessions_client=async_drive_sessions_client,
        no_sql_whatsapp_devices_client=async_whatsapp_devices_client,
        no_sql_jobs_client=async_jobs_client,
        no_sql_gmail_sessions_client=async_gmail_sessions_client,
        no_sql_notion_sessions_client=async_notion_sessions_client,
    )
    repositories = Repositories.create_repositories(datasources)
    skill_manager = SkillManager()
    integrations = create_integrations(
        config_service,
        calendar_repository=repositories.calendar,
        drive_repository=repositories.drive,
        gmail_repository=repositories.gmail,
        notion_repository=repositories.notion,
    )
    integrations.openai.set_skill_manager(skill_manager)
    integrations.openai.set_store_service(store_service)

    platform_services = PlatformServices.create_services(
        integrations=integrations,
        store_service=store_service,
        config_service=config_service,
        skill_manager=skill_manager,
    )
    context_factory = new_factory(
        datasources,
        integrations,
        store_service,
        config_service,
        platform_services,
    )
    usecases = create_usecases(context_factory)
    integrations.openai.set_job_usecases(usecases.jobs)

    scheduler = None
    if repositories.job is not None:
        from src.core.platform.managers.scheduler_manager import SchedulerManager

        scheduler = SchedulerManager(
            job_repository=repositories.job,
            context_factory=context_factory,
        )

    if config_service.single_user_config:
        user_id = config_service.single_user_config.user_id
    else:
        user_id = "default-user"

    neonize_integration = NeonizeIntegration(
        sessions_dir="./data/whatsapp",
        stt_integration=integrations.stt,
        whatsapp_device_repository=repositories.whatsapp_device,
        profile_repository=repositories.profile,
    )

    runtime = AppRuntime(
        cli_config=cli_config,
        config_service=config_service,
        usecases=usecases,
        repositories=repositories,
        scheduler=scheduler,
        user_id=user_id,
        neonize_integration=neonize_integration,
        openai_integration=integrations.openai,
        profiles_client=profiles_client,
        mongo_clients=mongo_clients,
        async_mongo_clients=async_mongo_clients,
    )
    return runtime


async def _close_browser_sessions() -> None:
    from src.core.platform.ai.tools.models import _browser_state

    context = _browser_state.get("context")
    browser = _browser_state.get("browser")
    pw = _browser_state.get("playwright")

    if context:
        try:
            await context.close()
        except Exception:
            logger.debug("Failed to close browser context", exc_info=True)
    if browser:
        try:
            await browser.close()
        except Exception:
            logger.debug("Failed to close browser", exc_info=True)
    if pw:
        try:
            await pw.stop()
        except Exception:
            logger.debug("Failed to stop playwright", exc_info=True)

    _browser_state["context"] = None
    _browser_state["browser"] = None
    _browser_state["page"] = None
    _browser_state["playwright"] = None
    _browser_state["connected"] = False
    logger.info("Browser sessions closed")


async def _restore_neonize_sessions(app: FastAPI) -> None:
    from src.adapters.web.controllers.whatsapp.device_controllers import _handle_incoming_message

    repositories = app.state.repositories
    if repositories.whatsapp_device is None:
        logger.info("WhatsApp device repository not available — skipping session restore")
        return

    try:
        connected_devices = await repositories.whatsapp_device.find_by_status("authenticated")
        for device in connected_devices:
            try:
                await app.state.neonize_integration.connect(device.id, _handle_incoming_message)
                logger.info(
                    "Restored neonize session for device %s (%s)",
                    device.id,
                    device.device_name,
                )
            except Exception as exc:
                logger.warning("Failed to restore session for device %s: %s", device.id, exc)
    except Exception as exc:
        logger.warning("Could not restore neonize sessions: %s", exc)


def _configure_cors(app: FastAPI) -> None:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
    allow_all = raw_origins == "*"
    allow_origins = ["*"] if allow_all else [origin.strip() for origin in raw_origins.split(",")]
    allow_origin_regex = (
        None
        if allow_all
        else r"(file://.*|null|app://.*|http://localhost(:\d+)?|https://localhost(:\d+)?)"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


def create_app() -> FastAPI:
    runtime = _build_runtime()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await app.state.repositories.profile.ensure_indexes()
            if app.state.repositories.calendar is not None:
                await app.state.repositories.calendar.ensure_indexes()
            if app.state.repositories.drive is not None:
                await app.state.repositories.drive.ensure_indexes()
            if app.state.repositories.gmail is not None:
                await app.state.repositories.gmail.ensure_indexes()
            if app.state.repositories.notion is not None:
                await app.state.repositories.notion.ensure_indexes()
            if app.state.repositories.job is not None:
                await app.state.repositories.job.ensure_indexes()
            if app.state.repositories.whatsapp_device is not None:
                await app.state.repositories.whatsapp_device.ensure_indexes()
        except Exception:
            logger.debug("Failed to ensure async indexes", exc_info=True)

        if app.state.scheduler is not None:
            await app.state.scheduler.start()
            logger.info("Scheduler started")

        if app.state.config_service.single_user_config:
            await StartupService(
                usecases=app.state.usecases,
                config_service=app.state.config_service,
                profile_repository=app.state.repositories.profile,
                openai_integration=app.state.openai_integration,
            ).initialize(
                user_id=app.state.user_id,
                cli_config=app.state.cli_config,
            )

        await _restore_neonize_sessions(app)

        try:
            yield
        finally:
            await _close_browser_sessions()
            for client in app.state.async_mongo_clients:
                try:
                    await client.disconnect()
                except Exception:
                    logger.debug("Failed to disconnect async Mongo client", exc_info=True)
            for client in app.state.mongo_clients:
                try:
                    client.disconnect()
                except Exception:
                    logger.debug("Failed to disconnect Mongo client", exc_info=True)

    app = FastAPI(
        title="Gillie IA",
        description="Service API for the Assistant",
        version="1.0.0",
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    _configure_cors(app)

    app.state.cli_config = runtime.cli_config
    app.state.config_service = runtime.config_service
    app.state.usecases = runtime.usecases
    app.state.repositories = runtime.repositories
    app.state.scheduler = runtime.scheduler
    app.state.neonize_integration = runtime.neonize_integration
    app.state.openai_integration = runtime.openai_integration
    app.state.profile_client = runtime.profiles_client
    app.state.mongo_clients = runtime.mongo_clients
    app.state.async_mongo_clients = runtime.async_mongo_clients
    app.state.user_id = runtime.user_id

    RoutesManager(
        app,
        runtime.usecases,
        runtime.config_service,
        neonize_integration=runtime.neonize_integration,
        scheduler=runtime.scheduler,
    ).include_routes()

    app.add_middleware(SingleUserMiddleware)

    @app.get("/", include_in_schema=False)
    async def redirect_to_docs():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
