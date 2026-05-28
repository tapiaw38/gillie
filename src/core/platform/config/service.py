import os
from pathlib import Path
from dotenv import load_dotenv
from enum import Enum
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from cli.config.schema import AssistantConfig


class ModeServer(str, Enum):
    RELEASE = "release"
    DEBUG = "debug"


@dataclass
class NoSQLCollectionConfig:
    database_uri: str
    database: str
    collection: str

@dataclass
class NoSQLConfig:
    migrations: Optional[NoSQLCollectionConfig] = None
    conversations: Optional[NoSQLCollectionConfig] = None
    profiles: Optional[NoSQLCollectionConfig] = None
    faqs: Optional[NoSQLCollectionConfig] = None
    calendar_sessions: Optional[NoSQLCollectionConfig] = None
    drive_sessions: Optional[NoSQLCollectionConfig] = None
    whatsapp_devices: Optional[NoSQLCollectionConfig] = None
    jobs: Optional[NoSQLCollectionConfig] = None
    gmail_sessions: Optional[NoSQLCollectionConfig] = None
    notion_sessions: Optional[NoSQLCollectionConfig] = None
    episodic_memories: Optional[NoSQLCollectionConfig] = None

@dataclass
class ServerConfig:
    mode: ModeServer
    port: str
    host: str
    jwt_secret: str
    encryption_algorithm: str

_PROVIDER_PRESETS: dict = {
    "deepseek":   {"base_url": "https://api.deepseek.com",                               "model": "deepseek-chat",                "auth_type": "api_key"},
    "kimi-k2":    {"base_url": "https://api.moonshot.ai/v1",                            "model": "kimi-k2-0905-preview",         "auth_type": "api_key"},
    "anthropic":  {"base_url": "https://api.anthropic.com/v1",                           "model": "claude-sonnet-4-6",            "auth_type": "api_key"},
    "openai":     {"base_url": "https://api.openai.com/v1",                              "model": "gpt-4o",                       "auth_type": "api_key"},
    "kimi":       {"base_url": "https://api.moonshot.ai/v1",                            "model": "kimi-k2-turbo-preview",        "auth_type": "api_key"},
    "gemini":     {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/","model": "gemini-2.0-flash",             "auth_type": "api_key"},
    "grok":       {"base_url": "https://api.x.ai/v1",                                 "model": "grok-4-fast",                 "auth_type": "api_key"},
    "minimax":    {"base_url": "https://api.minimax.io/v1",                            "model": "MiniMax-M2.7",                 "auth_type": "api_key"},
}


@dataclass
class OpenAIConfig:
    api_key: str
    base_url: str
    model: str
    role: str
    auth_type: str = "api_key"  # "api_key" | "bearer" | "none"


@dataclass
class AWSConfig:
    access_key_id: str
    secret_access_key: str
    region: str
    bucket_name: str


@dataclass
class WhatsAppConfig:
    verify_token: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    grpc_port: int
    use_grpc: bool
    api_key: Optional[str] = None


@dataclass
class LangChainConfig:
    service_enabled: bool
    max_concurrent_requests: int
    memory_max_messages: int
    chunk_size: int
    chunk_overlap: int
    max_pages: int
    enable_vectors: bool
    vector_store: str
    similarity_k: int
    log_level: str


@dataclass
class LangSmithConfig:
    api_key: Optional[str]
    project: str
    endpoint: Optional[str]
    tracing_enabled: bool


@dataclass
class EmbeddingsConfig:
    provider: str  # openai, huggingface, sentence_transformers
    batch_size: int
    device: str  # cpu, cuda, mps
    openai_model: str
    openai_dimension: int
    hf_model: str
    hf_dimension: int


@dataclass
class LLMExtendedConfig:
    provider: str  # openai, anthropic
    openai_temperature: float
    openai_max_tokens: int
    openai_timeout: float
    openai_max_retries: int
    anthropic_api_key: Optional[str]
    anthropic_model: str
    anthropic_temperature: float
    anthropic_max_tokens: int
    anthropic_timeout: float
    anthropic_max_retries: int


@dataclass
class LoggingConfig:
    environment: str
    log_level: str
    scope: str


@dataclass
class GoogleCalendarConfig:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/calendar/oauth/callback"


@dataclass
class GoogleDriveConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/drive/oauth/callback"


@dataclass
class GoogleGmailConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/gmail/oauth/callback"


@dataclass
class NotionConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/notion/oauth/callback"


@dataclass
class StorageConfig:
    backend: str = "local"  # "s3" | "local"
    local_path: str = ""
    local_base_url: str = "http://localhost:8000/api/storage"


@dataclass
class VisionConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@dataclass
class ImageGenerationConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@dataclass
class VideoGenerationConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@dataclass
class SingleUserConfig:
    """Configuration for single-user mode (set by CLI init)."""
    user_id: str
    tts_enabled: bool = False
    stt_enabled: bool = False
    whatsapp_enabled: bool = False


@dataclass
class ConfigurationService:
    server_config: ServerConfig
    nosql_config: NoSQLConfig
    openai_config: OpenAIConfig
    aws_config: AWSConfig
    whatsapp_config: WhatsAppConfig
    qdrant_config: QdrantConfig
    langchain_config: LangChainConfig
    langsmith_config: LangSmithConfig
    embeddings_config: EmbeddingsConfig
    llm_extended_config: LLMExtendedConfig
    logging_config: LoggingConfig
    single_user_config: Optional[SingleUserConfig] = None
    google_calendar_config: Optional[GoogleCalendarConfig] = None
    google_drive_config: Optional[GoogleDriveConfig] = None
    google_gmail_config: Optional[GoogleGmailConfig] = None
    notion_config: Optional[NotionConfig] = None
    storage_config: Optional[StorageConfig] = None
    vision_config: Optional[VisionConfig] = None
    image_generation_config: Optional[ImageGenerationConfig] = None
    video_generation_config: Optional[VideoGenerationConfig] = None


_config_service: Optional[ConfigurationService] = None

def init_config_service(config: ConfigurationService):
    global _config_service
    if _config_service is None:
        _config_service = config

def get_config_service() -> ConfigurationService:
    if _config_service is None:
        raise ValueError("ConfigurationService has not been initialized.")
    return _config_service

def get_env(key: str, fallback: str) -> str:
    return os.getenv(key, fallback)


def read_config() -> ConfigurationService:
    load_dotenv()

    # Allow OAuth2 over HTTP in local development
    if os.getenv("OAUTHLIB_INSECURE_TRANSPORT") == "1":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    database_uri = get_env("DATABASE_URI", "mongodb://localhost:27017")
    server_config = ServerConfig(
        mode=ModeServer(get_env("APP_MODE", "release")),
        port=get_env("APP_PORT", "8000"),
        host=get_env("APP_HOST", "localhost"),
        jwt_secret=get_env("APP_JWT_SECRET", "secret"),
        encryption_algorithm=get_env("APP_ENCRYPTION_ALGORITHM", "HS256"),
    )

    nosql_config = NoSQLConfig(
        migrations=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_MIGRATIONS", "migrations"),
        ),
        conversations=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_CONVERSATIONS", "conversations"),
        ),
        profiles=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_PROFILES", "profiles"),
        ),
        faqs=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_FAQS", "faqs"),
        ),
        calendar_sessions=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_CALENDAR_SESSIONS", "calendar_sessions"),
        ),
        drive_sessions=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_DRIVE_SESSIONS", "drive_sessions"),
        ),
        whatsapp_devices=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_WHATSAPP_DEVICES", "whatsapp_devices"),
        ),
        jobs=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_JOBS", "jobs"),
        ),
        gmail_sessions=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_GMAIL_SESSIONS", "gmail_sessions"),
        ),
        notion_sessions=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_NOTION_SESSIONS", "notion_sessions"),
        ),
        episodic_memories=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "gillie-db"),
            collection=get_env("DB_COLLECTION_EPISODIC_MEMORIES", "episodic_memories"),
        ) if get_env("BRAIN_ENABLED", "false").lower() == "true" else None,
    )

    provider = get_env("AI_PROVIDER", "")
    preset = _PROVIDER_PRESETS.get(provider, {})

    openai_config = OpenAIConfig(
        api_key=get_env("AI_AUTH_TOKEN", get_env("OPENAI_API_KEY", "")),
        base_url=get_env("OPENAI_BASE_URL", preset.get("base_url", "https://api.deepseek.com")),
        model=get_env("OPENAI_MODEL", preset.get("model", "deepseek-chat")),
        role=get_env("OPENAI_ROLE", "user"),
        auth_type=get_env("AI_AUTH_TYPE", preset.get("auth_type", "api_key")),
    )

    aws_config = AWSConfig(
        access_key_id=get_env("AWS_ACCESS_KEY_ID", ""),
        secret_access_key=get_env("AWS_SECRET_ACCESS_KEY", ""),
        region=get_env("AWS_REGION", "us-east-1"),
        bucket_name=get_env("AWS_BUCKET_NAME", "gillie-bucket"),
    )

    whatsapp_config = WhatsAppConfig(
        verify_token=get_env("WHATSAPP_VERIFY_TOKEN", "gillie_whatsapp_verification_token"),
    )

    qdrant_config = QdrantConfig(
        host=get_env("QDRANT_HOST", "localhost"),
        port=int(get_env("QDRANT_PORT", "6333")),
        grpc_port=int(get_env("QDRANT_GRPC_PORT", "6334")),
        use_grpc=get_env("QDRANT_USE_GRPC", "false").lower() == "true",
        api_key=get_env("QDRANT_API_KEY", None),
    )

    langchain_config = LangChainConfig(
        service_enabled=get_env("LANGCHAIN_SERVICE_ENABLED", "false").lower() == "true",
        max_concurrent_requests=int(get_env("LANGCHAIN_MAX_CONCURRENT_REQUESTS", "3")),
        memory_max_messages=int(get_env("LANGCHAIN_MEMORY_MAX_MESSAGES", "20")),
        chunk_size=int(get_env("LANGCHAIN_CHUNK_SIZE", "1000")),
        chunk_overlap=int(get_env("LANGCHAIN_CHUNK_OVERLAP", "200")),
        max_pages=int(get_env("LANGCHAIN_MAX_PAGES", "50")),
        enable_vectors=get_env("LANGCHAIN_ENABLE_VECTORS", "true").lower() == "true",
        vector_store=get_env("LANGCHAIN_VECTOR_STORE", "qdrant"),
        similarity_k=int(get_env("LANGCHAIN_SIMILARITY_K", "5")),
        log_level=get_env("LANGCHAIN_LOG_LEVEL", "INFO"),
    )

    langsmith_config = LangSmithConfig(
        api_key=get_env("LANGSMITH_API_KEY", None),
        project=get_env("LANGSMITH_PROJECT", "gillie-api"),
        endpoint=get_env("LANGSMITH_ENDPOINT", None),
        tracing_enabled=get_env("LANGSMITH_TRACING_ENABLED", "false").lower() == "true",
    )

    embeddings_config = EmbeddingsConfig(
        provider=get_env("EMBEDDING_PROVIDER", "openai"),
        batch_size=int(get_env("EMBEDDING_BATCH_SIZE", "32")),
        device=get_env("EMBEDDING_DEVICE", "cpu"),
        openai_model=get_env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_dimension=int(get_env("OPENAI_EMBEDDING_DIMENSION", "1536")),
        hf_model=get_env("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        hf_dimension=int(get_env("HF_EMBEDDING_DIMENSION", "384")),
    )

    llm_extended_config = LLMExtendedConfig(
        provider=get_env("LLM_PROVIDER", "openai"),
        openai_temperature=float(get_env("OPENAI_TEMPERATURE", "0.7")),
        openai_max_tokens=int(get_env("OPENAI_MAX_TOKENS", "2000")),
        openai_timeout=float(get_env("OPENAI_TIMEOUT", "45.0")),
        openai_max_retries=int(get_env("OPENAI_MAX_RETRIES", "3")),
        anthropic_api_key=get_env("ANTHROPIC_API_KEY", None),
        anthropic_model=get_env("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        anthropic_temperature=float(get_env("ANTHROPIC_TEMPERATURE", "0.7")),
        anthropic_max_tokens=int(get_env("ANTHROPIC_MAX_TOKENS", "4096")),
        anthropic_timeout=float(get_env("ANTHROPIC_TIMEOUT", "45.0")),
        anthropic_max_retries=int(get_env("ANTHROPIC_MAX_RETRIES", "3")),
    )

    logging_config = LoggingConfig(
        environment=get_env("ENVIRONMENT", "development"),
        log_level=get_env("LOG_LEVEL", "INFO"),
        scope=get_env("SCOPE", ""),
    )

    storage_config = StorageConfig(
        backend=get_env("STORAGE_BACKEND", "local"),
        local_path=get_env("STORAGE_LOCAL_PATH", str(Path.home() / ".local" / "share" / "gillie" / "storage")),
        local_base_url=get_env("STORAGE_LOCAL_BASE_URL", "http://localhost:8000/api/storage"),
    )

    # Single-user config from env (optional, set by CLI)
    single_user_id = get_env("SINGLE_USER_ID", "")
    single_user_config = None
    if single_user_id:
        single_user_config = SingleUserConfig(
            user_id=single_user_id,
            tts_enabled=get_env("TTS_ENABLED", "false").lower() == "true",
            stt_enabled=get_env("STT_ENABLED", "false").lower() == "true",
            whatsapp_enabled=get_env("WHATSAPP_ENABLED", "false").lower() == "true",
        )

    google_calendar_config = GoogleCalendarConfig(
        enabled=get_env("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true",
        client_id=get_env("GOOGLE_CALENDAR_CLIENT_ID", ""),
        client_secret=get_env("GOOGLE_CALENDAR_CLIENT_SECRET", ""),
        redirect_uri=get_env("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8000/api/v1/calendar/oauth/callback"),
    )

    google_drive_config = GoogleDriveConfig(
        client_id=get_env("GOOGLE_DRIVE_CLIENT_ID", ""),
        client_secret=get_env("GOOGLE_DRIVE_CLIENT_SECRET", ""),
        redirect_uri=get_env("GOOGLE_DRIVE_REDIRECT_URI", "http://localhost:8000/api/v1/drive/oauth/callback"),
    )

    vision_config = VisionConfig(
        api_key=get_env("VISION_API_KEY", ""),
        base_url=get_env("VISION_BASE_URL", ""),
        model=get_env("VISION_MODEL", ""),
    )

    image_generation_config = ImageGenerationConfig(
        api_key=get_env("IMAGE_GENERATION_API_KEY", ""),
        base_url=get_env("IMAGE_GENERATION_BASE_URL", ""),
        model=get_env("IMAGE_GENERATION_MODEL", ""),
    )

    video_generation_config = VideoGenerationConfig(
        api_key=get_env("VIDEO_GENERATION_API_KEY", ""),
        base_url=get_env("VIDEO_GENERATION_BASE_URL", ""),
        model=get_env("VIDEO_GENERATION_MODEL", ""),
    )

    google_gmail_config = GoogleGmailConfig(
        client_id=get_env("GOOGLE_GMAIL_CLIENT_ID", ""),
        client_secret=get_env("GOOGLE_GMAIL_CLIENT_SECRET", ""),
        redirect_uri=get_env("GOOGLE_GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/gmail/oauth/callback"),
    )

    notion_config = NotionConfig(
        client_id=get_env("NOTION_CLIENT_ID", ""),
        client_secret=get_env("NOTION_CLIENT_SECRET", ""),
        redirect_uri=get_env("NOTION_REDIRECT_URI", "http://localhost:8000/api/v1/notion/oauth/callback"),
    )

    return ConfigurationService(
        server_config=server_config,
        nosql_config=nosql_config,
        openai_config=openai_config,
        aws_config=aws_config,
        whatsapp_config=whatsapp_config,
        qdrant_config=qdrant_config,
        langchain_config=langchain_config,
        langsmith_config=langsmith_config,
        embeddings_config=embeddings_config,
        llm_extended_config=llm_extended_config,
        logging_config=logging_config,
        single_user_config=single_user_config,
        google_calendar_config=google_calendar_config,
        google_drive_config=google_drive_config,
        google_gmail_config=google_gmail_config,
        notion_config=notion_config,
        storage_config=storage_config,
        vision_config=vision_config,
        image_generation_config=image_generation_config,
        video_generation_config=video_generation_config,
    )


def get_available_providers(
    provider_keys: Optional[Dict[str, str]] = None,
    custom_providers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return the full provider map: built-in presets merged with profile data.
    Each entry has base_url, model, auth_type, api_key (may be empty), is_builtin.
    """
    keys = provider_keys or {}
    customs = custom_providers or {}

    merged: Dict[str, Any] = {}
    for name, preset in _PROVIDER_PRESETS.items():
        merged[name] = {**preset, "api_key": keys.get(name, ""), "is_builtin": True}
    for name, entry in customs.items():
        if name not in merged:
            merged[name] = {**entry, "api_key": keys.get(name, entry.get("api_key", "")), "is_builtin": False}
    return merged


def get_active_provider_name(active_provider: Optional[str] = None) -> str:
    """Return stored active provider name, or detect from current config."""
    if active_provider:
        return active_provider
    try:
        config = get_config_service()
        current_base = config.openai_config.base_url
        current_model = config.openai_config.model
        for name, preset in _PROVIDER_PRESETS.items():
            if preset["base_url"] == current_base and preset["model"] == current_model:
                return name
        return "custom"
    except Exception:
        return "custom"



def init_config() -> None:
    config_service = read_config()
    init_config_service(config_service)


def init_config_from_json(config_data: "AssistantConfig") -> None:
    """Initialize ConfigurationService from CLI config.json (single-user mode)."""
    s = config_data.services
    db_uri = s.mongodb.uri
    db_name = s.mongodb.database

    nosql_config = NoSQLConfig(
        migrations=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="migrations",
        ),
        conversations=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="conversations",
        ),
        profiles=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="profiles",
        ),
        faqs=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="faqs",
        ),
        calendar_sessions=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="calendar_sessions",
        ),
        drive_sessions=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="drive_sessions",
        ),
        whatsapp_devices=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="whatsapp_devices",
        ),
        jobs=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="jobs",
        ),
        gmail_sessions=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="gmail_sessions",
        ),
        notion_sessions=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="notion_sessions",
        ),
        episodic_memories=NoSQLCollectionConfig(
            database_uri=db_uri,
            database=db_name,
            collection="episodic_memories",
        ) if getattr(s, "brain", None) and s.brain.enabled else None,
    )

    config = ConfigurationService(
        server_config=ServerConfig(
            mode=ModeServer(config_data.server.mode),
            port=str(config_data.server.port),
            host=config_data.server.host,
            jwt_secret="single-user-no-auth",
            encryption_algorithm="HS256",
        ),
        nosql_config=nosql_config,
        openai_config=OpenAIConfig(
            api_key=s.openai.api_key,
            base_url=s.openai.base_url,
            model=s.openai.model,
            role=s.openai.role,
            auth_type=s.openai.auth_type,
        ),
        aws_config=AWSConfig(
            access_key_id=s.s3.access_key_id if s.s3.enabled else "",
            secret_access_key=s.s3.secret_access_key if s.s3.enabled else "",
            region=s.s3.region,
            bucket_name=s.s3.bucket_name if s.s3.enabled else "",
        ),
        whatsapp_config=WhatsAppConfig(
            verify_token=s.whatsapp.verify_token if s.whatsapp.enabled else "",
        ),
        qdrant_config=QdrantConfig(
            host=s.qdrant.host,
            port=s.qdrant.port,
            grpc_port=s.qdrant.grpc_port,
            use_grpc=s.qdrant.use_grpc,
            api_key=s.qdrant.api_key,
        ),
        langchain_config=LangChainConfig(
            service_enabled=s.langchain.enabled,
            max_concurrent_requests=s.langchain.max_concurrent_requests,
            memory_max_messages=s.langchain.memory_max_messages,
            chunk_size=s.langchain.chunk_size,
            chunk_overlap=s.langchain.chunk_overlap,
            max_pages=s.langchain.max_pages,
            enable_vectors=s.langchain.enable_vectors,
            vector_store=s.langchain.vector_store,
            similarity_k=s.langchain.similarity_k,
            log_level="INFO",
        ),
        langsmith_config=LangSmithConfig(
            api_key=s.langsmith.api_key if s.langsmith.enabled else None,
            project=s.langsmith.project,
            endpoint=s.langsmith.endpoint if s.langsmith.enabled else None,
            tracing_enabled=s.langsmith.enabled,
        ),
        embeddings_config=EmbeddingsConfig(
            provider=s.embeddings.provider,
            batch_size=s.embeddings.batch_size,
            device=s.embeddings.device,
            openai_model=s.embeddings.openai_model,
            openai_dimension=s.embeddings.openai_dimension,
            hf_model=s.embeddings.hf_model,
            hf_dimension=s.embeddings.hf_dimension,
        ),
        llm_extended_config=LLMExtendedConfig(
            provider=s.llm.provider,
            openai_temperature=s.openai.temperature,
            openai_max_tokens=s.openai.max_tokens,
            openai_timeout=s.openai.timeout,
            openai_max_retries=s.openai.max_retries,
            anthropic_api_key=s.llm.anthropic_api_key,
            anthropic_model=s.llm.anthropic_model,
            anthropic_temperature=s.llm.anthropic_temperature,
            anthropic_max_tokens=s.llm.anthropic_max_tokens,
            anthropic_timeout=s.llm.anthropic_timeout,
            anthropic_max_retries=s.llm.anthropic_max_retries,
        ),
        logging_config=LoggingConfig(
            environment=config_data.logging.environment,
            log_level=config_data.logging.log_level,
            scope="",
        ),
        single_user_config=SingleUserConfig(
            user_id=config_data.user_id,
            tts_enabled=s.tts.enabled,
            stt_enabled=s.stt.enabled,
            whatsapp_enabled=s.whatsapp.enabled,
        ),
        google_calendar_config=GoogleCalendarConfig(
            enabled=s.google_calendar.enabled if hasattr(s, "google_calendar") else False,
            client_id=s.google_calendar.client_id if hasattr(s, "google_calendar") else "",
            client_secret=s.google_calendar.client_secret if hasattr(s, "google_calendar") else "",
            redirect_uri=s.google_calendar.redirect_uri if hasattr(s, "google_calendar") else "http://localhost:8000/api/v1/calendar/oauth/callback",
        ),
        google_drive_config=GoogleDriveConfig(
            client_id=s.google_drive.client_id if hasattr(s, "google_drive") else "",
            client_secret=s.google_drive.client_secret if hasattr(s, "google_drive") else "",
            redirect_uri=s.google_drive.redirect_uri if hasattr(s, "google_drive") else "http://localhost:8000/api/v1/drive/oauth/callback",
        ),
        google_gmail_config=GoogleGmailConfig(
            client_id=s.google_gmail.client_id if hasattr(s, "google_gmail") else "",
            client_secret=s.google_gmail.client_secret if hasattr(s, "google_gmail") else "",
            redirect_uri=s.google_gmail.redirect_uri if hasattr(s, "google_gmail") else "http://localhost:8000/api/v1/gmail/oauth/callback",
        ),
        notion_config=NotionConfig(
            client_id=s.notion.client_id if hasattr(s, "notion") else "",
            client_secret=s.notion.client_secret if hasattr(s, "notion") else "",
            redirect_uri=s.notion.redirect_uri if hasattr(s, "notion") else "http://localhost:8000/api/v1/notion/oauth/callback",
        ),
        storage_config=StorageConfig(
            backend=s.storage.backend if hasattr(s, "storage") else "local",
            local_path=s.storage.local_path if hasattr(s, "storage") else str(Path.home() / ".local" / "share" / "gillie" / "storage"),
            local_base_url=s.storage.local_base_url if hasattr(s, "storage") else "http://localhost:8000/api/storage",
        ),
        vision_config=VisionConfig(
            api_key=s.vision.api_key if hasattr(s, "vision") else "",
            base_url=s.vision.base_url if hasattr(s, "vision") else "",
            model=s.vision.model if hasattr(s, "vision") else "",
        ),
        image_generation_config=ImageGenerationConfig(
            api_key=s.image_generation.api_key if hasattr(s, "image_generation") else "",
            base_url=s.image_generation.base_url if hasattr(s, "image_generation") else "",
            model=s.image_generation.model if hasattr(s, "image_generation") else "",
        ),
        video_generation_config=VideoGenerationConfig(
            api_key=s.video_generation.api_key if hasattr(s, "video_generation") else "",
            base_url=s.video_generation.base_url if hasattr(s, "video_generation") else "",
            model=s.video_generation.model if hasattr(s, "video_generation") else "",
        ),
    )

    init_config_service(config)
