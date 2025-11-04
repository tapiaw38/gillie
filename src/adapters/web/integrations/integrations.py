from src.adapters.web.integrations.openapi.openapi import OpenAIIntegration
from src.adapters.web.integrations.tts.tts import TTSIntegration
from src.adapters.web.integrations.stt.stt import STTIntegration
from src.adapters.web.integrations.mercadolibre.mercadolibre import MercadoLibreIntegration
from src.adapters.web.integrations.google_calendar.google_calendar import GoogleCalendarIntegration
from src.adapters.web.integrations.mcp.mcp_client import MCPClient
from src.core.platform.config.service import ConfigurationService
import logging

logger = logging.getLogger(__name__)


class Integrations:
    _instance = None

    def __init__(self, config_service: ConfigurationService):
        if Integrations._instance is not None:
            raise Exception("This class is a singleton! Use `Integrations.get_instance()` to access it.")
        self.openai = OpenAIIntegration(config_service)
        self.tts = TTSIntegration(config_service)
        self.stt = STTIntegration(config_service)
        self.mercadolibre = None  # Will be initialized when needed with user credentials
        self.google_calendar = GoogleCalendarIntegration(config_service.calendar_config.api_url)

        self.mcp = None
        if config_service.mcp_config.enabled:
            try:
                self.mcp = MCPClient(
                    base_url=config_service.mcp_config.server_url,
                    timeout=config_service.mcp_config.timeout
                )
                logger.info("MCP Client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MCP Client: {str(e)}")
                self.mcp = None
        else:
            logger.info("MCP Client is disabled in configuration")

        Integrations._instance = self

    def initialize_mercadolibre(self, access_token: str, user_id: str):
        """Initialize MercadoLibre integration with user credentials"""
        self.mercadolibre = MercadoLibreIntegration(access_token, user_id)
        return self.mercadolibre

    def initialize_faq_service(self, faq_repository):
        """Initialize FAQ repository for LangChain tools"""
        self.openai.set_faq_repository(faq_repository)

    @classmethod
    def get_instance(cls) -> "Integrations":
        if cls._instance is None:
            raise Exception("Integrations has not been initialized. Call `create_integrations` first.")
        return cls._instance


def create_integrations(cfg: ConfigurationService) -> Integrations:
    if Integrations._instance is None:
        return Integrations(cfg)
    return Integrations.get_instance()