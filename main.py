import os
import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.routes.routes_manager import RoutesManager
from src.adapters.web.integrations.integrations import create_integrations
from src.core.platform.config.service import (
    init_config,
    init_config_from_json,
    get_config_service,
)
from src.core.platform.nosql.client import MongoDBClient
from src.adapters.datasources.datasources import Datasources
from src.core.platform.appcontext.appcontext import new_factory
from src.core.use_cases.use_cases import create_usecases
from src.core.platform.nosql.migrations import execute_migrations
from src.core.platform.objectstorange.s3_session import get_s3_session
from src.adapters.storeservice.s3_storeservice import S3StoreService
from src.adapters.storeservice.local_storeservice import LocalStoreService
from src.core.platform.managers.platform_manager import PlatformServices
from src.core.platform.managers.skill_manager import SkillManager
from src.core.platform.errors.exception_handler import register_exception_handlers
from src.adapters.web.middlewares.authorization import SingleUserMiddleware
from src.adapters.web.integrations.neonize.neonize_integration import NeonizeIntegration

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gillie IA",
    description="Service API for the Assistant",
    version="1.0.0"
)

register_exception_handlers(app)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_allow_all = _raw_origins == "*"
_allow_origins = ["*"] if _allow_all else [o.strip() for o in _raw_origins.split(",")]
_allow_origin_regex = None if _allow_all else r"(file://.*|null|app://.*|http://localhost(:\d+)?|https://localhost(:\d+)?)"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


_cli_config = None

try:
    from cli.config.manager import config_exists, load_config
    if config_exists():
        _cli_config = load_config()
        init_config_from_json(_cli_config)
        logger.info(f"Loaded config from CLI config.json (user_id={_cli_config.user_id})")
    else:
        init_config()
        logger.info("Loaded config from .env (no CLI config found)")
except ImportError:
    init_config()
    logger.info("CLI module not available, loaded config from .env")

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

calendar_sessions_client = None
if config_service.nosql_config.calendar_sessions:
    calendar_sessions_client = MongoDBClient(
        config_service.nosql_config.calendar_sessions.database_uri,
        config_service.nosql_config.calendar_sessions.database,
        config_service.nosql_config.calendar_sessions.collection,
    )

drive_sessions_client = None
if config_service.nosql_config.drive_sessions:
    drive_sessions_client = MongoDBClient(
        config_service.nosql_config.drive_sessions.database_uri,
        config_service.nosql_config.drive_sessions.database,
        config_service.nosql_config.drive_sessions.collection,
    )

gmail_sessions_client = None
if config_service.nosql_config.gmail_sessions:
    gmail_sessions_client = MongoDBClient(
        config_service.nosql_config.gmail_sessions.database_uri,
        config_service.nosql_config.gmail_sessions.database,
        config_service.nosql_config.gmail_sessions.collection,
    )

profiles_client.run_migrations(migrations_client.get_collection(), execute_migrations())

_storage_cfg = config_service.storage_config
if _storage_cfg and _storage_cfg.backend == "local":
    store_service = LocalStoreService(
        base_path=_storage_cfg.local_path,
        base_url=_storage_cfg.local_base_url,
    )
    logger.info(f"Storage: local — {_storage_cfg.local_path}")
else:
    s3_session = get_s3_session()
    store_service = S3StoreService(session=s3_session, config=config_service)
    logger.info("Storage: S3")

datasources = Datasources.create_datasources(
    no_sql_conversations_client=conversations_client,
    no_sql_profiles_client=profiles_client,
    no_sql_faqs_client=faqs_client,
    no_sql_calendar_sessions_client=calendar_sessions_client,
    no_sql_drive_sessions_client=drive_sessions_client,
    no_sql_whatsapp_devices_client=whatsapp_devices_client,
    no_sql_jobs_client=jobs_client,
    no_sql_gmail_sessions_client=gmail_sessions_client,
)

from src.adapters.datasources.repositories.repositories import Repositories
repositories = Repositories.create_repositories(datasources)

skill_manager = SkillManager()

integrations = create_integrations(
    config_service,
    calendar_repository=repositories.calendar,
    drive_repository=repositories.drive,
    gmail_repository=repositories.gmail,
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
    platform_services
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
    from src.adapters.bootstrap.startup_service import StartupService
    StartupService(
        usecases=usecases,
        config_service=config_service,
        profile_repository=repositories.profile,
        openai_integration=integrations.openai,
    ).initialize(user_id=user_id, cli_config=_cli_config)
else:
    user_id = "default-user"

neonize_integration = NeonizeIntegration(
    sessions_dir="./data/whatsapp",
    stt_integration=integrations.stt,
    whatsapp_device_repository=repositories.whatsapp_device,
    profile_repository=repositories.profile,
)


routes_manager = RoutesManager(app, usecases, config_service, neonize_integration=neonize_integration, scheduler=scheduler, openai_integration=integrations.openai)
routes_manager.include_routes()

app.add_middleware(SingleUserMiddleware, user_id=user_id, profile_client=profiles_client)


@app.on_event("startup")
async def start_scheduler():
    if scheduler is not None:
        await scheduler.start()
        logger.info("Scheduler started")


@app.on_event("shutdown")
async def close_browser_sessions():
    from src.core.platform.ai.tools.models import _browser_state
    context = _browser_state.get("context")
    browser = _browser_state.get("browser")
    pw = _browser_state.get("playwright")
    if context:
        try:
            await context.close()
        except Exception:
            pass
    if browser:
        try:
            await browser.close()
        except Exception:
            pass
    if pw:
        try:
            await pw.stop()
        except Exception:
            pass
    _browser_state["context"] = None
    _browser_state["browser"] = None
    _browser_state["page"] = None
    _browser_state["playwright"] = None
    _browser_state["connected"] = False
    logger.info("Browser sessions closed")


@app.on_event("startup")
async def restore_neonize_sessions():
    """On startup, reconnect all devices that were previously authenticated."""
    from src.adapters.web.controllers.whatsapp.device_controllers import _handle_incoming_message

    if repositories.whatsapp_device is None:
        logger.info("WhatsApp device repository not available — skipping session restore")
        return

    try:
        connected_devices = repositories.whatsapp_device.find_by_status("authenticated")
        for device in connected_devices:
            try:
                await neonize_integration.connect(device.id, _handle_incoming_message)
                logger.info(f"Restored neonize session for device {device.id} ({device.device_name})")
            except Exception as e:
                logger.warning(f"Failed to restore session for device {device.id}: {e}")
    except Exception as e:
        logger.warning(f"Could not restore neonize sessions: {e}")
