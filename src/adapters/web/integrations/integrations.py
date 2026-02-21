import logging
from src.adapters.web.integrations.openapi.openapi import OpenAIIntegration
from src.adapters.web.integrations.tts.tts import TTSIntegration
from src.adapters.web.integrations.stt.stt import STTIntegration
from src.adapters.web.integrations.mercadolibre.mercadolibre import MercadoLibreIntegration
from src.adapters.web.integrations.google_calendar.google_calendar import GoogleCalendarIntegration
from src.adapters.web.integrations.mcp.mcp_client import MCPClient
from src.core.platform.config.service import ConfigurationService

logger = logging.getLogger(__name__)


class Integrations:
    _instance = None

    def __init__(
        self,
        config_service: ConfigurationService,
        calendar_repository=None,
    ):
        if Integrations._instance is not None:
            raise Exception("This class is a singleton! Use `Integrations.get_instance()` to access it.")

        self.openai = OpenAIIntegration(config_service)
        self.tts = TTSIntegration(config_service)
        self.stt = STTIntegration(config_service)
        self.mercadolibre = None  # initialized per-user with credentials

        # Google Calendar — real in-process adapter
        self.google_calendar = None
        gc_cfg = config_service.google_calendar_config
        if gc_cfg and gc_cfg.enabled and gc_cfg.client_id and calendar_repository is not None:
            from src.services.calendar.client import GoogleCalendarClient
            gc_client = GoogleCalendarClient(
                client_id=gc_cfg.client_id,
                client_secret=gc_cfg.client_secret,
                redirect_uri=gc_cfg.redirect_uri,
            )
            self.google_calendar = GoogleCalendarIntegration(gc_client, calendar_repository)
            logger.info("Google Calendar integration initialized")
        else:
            logger.info("Google Calendar integration disabled (not configured or no repository)")

        # MCP — in-process DatetimeTools
        self.mcp = MCPClient()
        logger.info("MCPClient (in-process) initialized")

        Integrations._instance = self

    def initialize_mercadolibre(self, access_token: str, user_id: str):
        """Initialize MercadoLibre integration with user credentials."""
        self.mercadolibre = MercadoLibreIntegration(access_token, user_id)
        return self.mercadolibre

    def initialize_faq_service(self, faq_repository):
        """Initialize FAQ repository for LangChain tools."""
        self.openai.set_faq_repository(faq_repository)

    @classmethod
    def get_instance(cls) -> "Integrations":
        if cls._instance is None:
            raise Exception("Integrations has not been initialized. Call `create_integrations` first.")
        return cls._instance


def create_integrations(
    cfg: ConfigurationService,
    calendar_repository=None,
) -> Integrations:
    if Integrations._instance is None:
        return Integrations(cfg, calendar_repository=calendar_repository)
    return Integrations.get_instance()
