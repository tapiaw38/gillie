import logging
from src.adapters.web.integrations.openapi.openapi import OpenAIIntegration
from src.adapters.web.integrations.tts.tts import TTSIntegration
from src.adapters.web.integrations.stt.stt import STTIntegration
from src.adapters.web.integrations.mercadolibre.mercadolibre import MercadoLibreIntegration
from src.adapters.web.integrations.google_calendar.google_calendar import GoogleCalendarIntegration
from src.adapters.web.integrations.google_drive.google_drive import GoogleDriveIntegration
from src.adapters.web.integrations.mcp.mcp_client import MCPClient
from src.core.platform.config.service import ConfigurationService

logger = logging.getLogger(__name__)


class Integrations:
    _instance = None

    def __init__(
        self,
        config_service: ConfigurationService,
        calendar_repository=None,
        drive_repository=None,
        gmail_repository=None,
    ):
        if Integrations._instance is not None:
            raise Exception("This class is a singleton! Use `Integrations.get_instance()` to access it.")

        self.openai = OpenAIIntegration(config_service)
        self.tts = TTSIntegration(config_service)
        self.stt = STTIntegration(config_service)
        self.mercadolibre = None  # initialized per-user with credentials

        self.google_calendar = None
        if calendar_repository is not None:
            from src.services.calendar.client import GoogleCalendarClient
            gc_cfg = config_service.google_calendar_config
            fallback_client = None
            if gc_cfg and gc_cfg.client_id:
                fallback_client = GoogleCalendarClient(
                    client_id=gc_cfg.client_id,
                    client_secret=gc_cfg.client_secret,
                    redirect_uri=gc_cfg.redirect_uri,
                )
            self.google_calendar = GoogleCalendarIntegration(
                repository=calendar_repository,
                fallback_client=fallback_client,
            )
            logger.info("Google Calendar integration initialized (credentials loaded from DB or env)")
        else:
            logger.info("Google Calendar integration disabled (no repository)")

        # Drive integration
        gd_cfg = config_service.google_drive_config
        drive_fallback_client = None
        if gd_cfg and gd_cfg.client_id:
            from src.services.gdrive.client import GoogleDriveClient
            drive_fallback_client = GoogleDriveClient(
                client_id=gd_cfg.client_id,
                client_secret=gd_cfg.client_secret,
                redirect_uri=gd_cfg.redirect_uri,
            )
        self.google_drive = GoogleDriveIntegration(
            repository=drive_repository,
            fallback_client=drive_fallback_client,
        )
        logger.info("Google Drive integration initialized (credentials loaded from DB or env)")

        # Gmail integration
        self.gmail = None
        if gmail_repository is not None:
            from src.services.gmail.client import GoogleGmailClient
            from src.adapters.web.integrations.gmail.gmail import GmailIntegration
            gm_cfg = config_service.google_gmail_config
            fallback_client = None
            if gm_cfg and gm_cfg.client_id:
                fallback_client = GoogleGmailClient(
                    client_id=gm_cfg.client_id,
                    client_secret=gm_cfg.client_secret,
                    redirect_uri=gm_cfg.redirect_uri,
                )
            self.gmail = GmailIntegration(
                repository=gmail_repository,
                fallback_client=fallback_client,
            )
            logger.info("Gmail integration initialized")
        else:
            logger.info("Gmail integration disabled (no repository)")

        self.mcp = MCPClient()
        logger.info("MCPClient (in-process) initialized")

        Integrations._instance = self

    def make_whatsapp_client(self, access_token: str, phone_number_id: str):
        from src.adapters.web.integrations.whatsapp.whatsapp import WhatsAppIntegration
        return WhatsAppIntegration(access_token=access_token, phone_number_id=phone_number_id)

    def make_slack_client(self, bot_token: str, signing_secret: str = ""):
        from src.adapters.web.integrations.slack.slack import SlackIntegration
        return SlackIntegration(bot_token=bot_token, signing_secret=signing_secret)

    def make_telegram_client(self, bot_token: str, secret_token: str = "", store_service=None):
        from src.adapters.web.integrations.telegram.telegram import TelegramIntegration
        return TelegramIntegration(bot_token=bot_token, secret_token=secret_token, store_service=store_service)

    def make_sqldatabase_client(self, connection_string: str, allowed_table: str, table_description: str = ""):
        from src.adapters.web.integrations.sqldatabase.sqldatabase import SQLDatabaseIntegration
        return SQLDatabaseIntegration(
            connection_string=connection_string,
            allowed_table=allowed_table,
            table_description=table_description,
        )

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
    drive_repository=None,
    gmail_repository=None,
) -> Integrations:
    if Integrations._instance is None:
        return Integrations(
            cfg,
            calendar_repository=calendar_repository,
            drive_repository=drive_repository,
            gmail_repository=gmail_repository,
        )
    return Integrations.get_instance()
