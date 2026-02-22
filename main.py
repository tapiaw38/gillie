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
from src.adapters.storeservice.storeservice import StoreServiceImpl
from src.core.platform.services.platform_services import PlatformServices
from src.core.platform.managers.skill_manager import SkillManager
from src.core.platform.errors.exception_handler import register_exception_handlers
from src.adapters.web.middlewares.authorization import SingleUserMiddleware
from src.adapters.web.integrations.neonize.neonize_integration import NeonizeIntegration

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Assistant IA API",
    description="API for the Assistant IA",
    version="1.0.0"
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


# ─── Configuration ────────────────────────────────────────────────────────────
# Priority: CLI config.json > .env
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

# ─── Database ─────────────────────────────────────────────────────────────────
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

calendar_sessions_client = None
calendar_events_client = None
gc_cfg = config_service.google_calendar_config
if gc_cfg and gc_cfg.enabled and config_service.nosql_config.calendar_sessions:
    calendar_sessions_client = MongoDBClient(
        config_service.nosql_config.calendar_sessions.database_uri,
        config_service.nosql_config.calendar_sessions.database,
        config_service.nosql_config.calendar_sessions.collection,
    )
    calendar_events_client = MongoDBClient(
        config_service.nosql_config.calendar_events.database_uri,
        config_service.nosql_config.calendar_events.database,
        config_service.nosql_config.calendar_events.collection,
    )

profiles_client.run_migrations(migrations_client.get_collection(), execute_migrations())

# ─── Storage ──────────────────────────────────────────────────────────────────
s3_session = get_s3_session()
store_service = StoreServiceImpl(
    session=s3_session,
    config=config_service
)

# ─── Repositories ─────────────────────────────────────────────────────────────
datasources = Datasources.create_datasources(
    no_sql_conversations_client=conversations_client,
    no_sql_profiles_client=profiles_client,
    no_sql_faqs_client=faqs_client,
    no_sql_calendar_sessions_client=calendar_sessions_client,
    no_sql_calendar_events_client=calendar_events_client,
    no_sql_whatsapp_devices_client=whatsapp_devices_client,
)

from src.adapters.datasources.repositories.repositories import Repositories
repositories = Repositories.create_repositories(datasources)

# ─── Integrations & Services ──────────────────────────────────────────────────
integrations = create_integrations(config_service, calendar_repository=repositories.calendar)

platform_services = PlatformServices.create_services(
    integrations=integrations,
    store_service=store_service,
    config_service=config_service,
    skill_manager=SkillManager(),
)

context_factory = new_factory(
    datasources,
    integrations,
    store_service,
    config_service,
    platform_services
)
usecases = create_usecases(context_factory)

# ─── Auto-create profile for single-user mode ────────────────────────────────
if config_service.single_user_config:
    user_id = config_service.single_user_config.user_id
    try:
        existing_profile = repositories.profile.find_by_user_id(user_id)
        if not existing_profile and _cli_config:
            from src.schemas import ProfileInput
            profile_input = ProfileInput(
                assistant_name=_cli_config.profile.assistant_name,
                business_name=_cli_config.profile.business_name,
                business_context=_cli_config.profile.business_context,
                functions=_cli_config.profile.functions,
                role=_cli_config.profile.role,
            )
            usecases.profile.create_usecase.execute(profile_input, user_id)
            logger.info(f"Auto-created profile for user_id={user_id}")
        elif existing_profile:
            logger.info(f"Profile already exists for user_id={user_id}")
    except Exception as e:
        logger.warning(f"Could not auto-create profile: {e}")
else:
    user_id = "default-user"

# ─── Neonize (WhatsApp device integration) ────────────────────────────────────
neonize_integration = NeonizeIntegration(sessions_dir="./data/whatsapp", stt_integration=integrations.stt)


# ─── Routes & Middleware ──────────────────────────────────────────────────────
routes_manager = RoutesManager(app, usecases, config_service, neonize_integration=neonize_integration)
routes_manager.include_routes()

app.add_middleware(SingleUserMiddleware, user_id=user_id)


# ─── Startup: restore previously connected devices ────────────────────────────
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
