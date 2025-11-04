import os
from dotenv import load_dotenv
from enum import Enum
from dataclasses import dataclass
from typing import Optional


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

@dataclass
class ServerConfig:
    mode: ModeServer
    port: str
    host: str
    jwt_secret: str
    encryption_algorithm: str

@dataclass
class OpenAIConfig:
    api_key: str
    base_url: str
    model: str
    role: str


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
class CalendarConfig:
    api_url: str


@dataclass
class MCPConfig:
    server_url: str
    timeout: int
    enabled: bool


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
    enable_fallback: bool
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
    # OpenAI specific
    openai_model: str
    openai_dimension: int
    # HuggingFace specific
    hf_model: str
    hf_dimension: int


@dataclass
class LLMExtendedConfig:
    provider: str  # openai, anthropic
    # OpenAI extended
    openai_temperature: float
    openai_max_tokens: int
    openai_timeout: float
    openai_max_retries: int
    # Anthropic
    anthropic_api_key: Optional[str]
    anthropic_model: str
    anthropic_temperature: float
    anthropic_max_tokens: int
    anthropic_timeout: float
    anthropic_max_retries: int


@dataclass
class LoggingConfig:
    environment: str  # development, production, testing, docker
    log_level: str
    scope: str  # prod, test, (empty for local)


@dataclass
class ConfigurationService:
    server_config: ServerConfig
    nosql_config: NoSQLConfig
    openai_config: OpenAIConfig
    aws_config: AWSConfig
    whatsapp_config: WhatsAppConfig
    calendar_config: CalendarConfig
    mcp_config: MCPConfig
    qdrant_config: QdrantConfig
    langchain_config: LangChainConfig
    langsmith_config: LangSmithConfig
    embeddings_config: EmbeddingsConfig
    llm_extended_config: LLMExtendedConfig
    logging_config: LoggingConfig

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
            database=get_env("DB_NAME", "assistant-ia-db"),
            collection=get_env("DB_COLLECTION_MIGRATIONS", "migrations"),
        ),
        conversations=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "assistant-ia-db"),
            collection=get_env("DB_COLLECTION_CONVERSATIONS", "conversations"),
        ),
        profiles=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "assistant-ia-db"),
            collection=get_env("DB_COLLECTION_PROFILES", "profiles"),
        ),
        faqs=NoSQLCollectionConfig(
            database_uri=database_uri,
            database=get_env("DB_NAME", "assistant-ia-db"),
            collection=get_env("DB_COLLECTION_FAQS", "faqs"),
        ),
    )

    openai_config = OpenAIConfig(
        api_key=get_env("OPENAI_API_KEY", ""),
        base_url=get_env("OPENAI_BASE_URL", "https://api.deepseek.com"),
        model=get_env("OPENAI_MODEL", "deepseek-chat"),
        role=get_env("OPENAI_ROLE", "user"),
    )

    aws_config = AWSConfig(
        access_key_id=get_env("AWS_ACCESS_KEY_ID", ""),
        secret_access_key=get_env("AWS_SECRET_ACCESS_KEY", ""),
        region=get_env("AWS_REGION", "us-east-1"),
        bucket_name=get_env("AWS_BUCKET_NAME", "assistant-ia-bucket"),
    )
    
    whatsapp_config = WhatsAppConfig(
        verify_token=get_env("WHATSAPP_VERIFY_TOKEN", "assistant_ia_whatsapp_verification_token"),
    )

    calendar_config = CalendarConfig(
        api_url=get_env("CALENDAR_API_URL", "http://calendar-api-be:8084"),
    )

    mcp_config = MCPConfig(
        server_url=get_env("MCP_SERVER_URL", "http://mcp-context-server:8085"),
        timeout=int(get_env("MCP_TIMEOUT", "30")),
        enabled=get_env("MCP_ENABLED", "true").lower() == "true",
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
        enable_fallback=get_env("LANGCHAIN_ENABLE_FALLBACK", "true").lower() == "true",
        log_level=get_env("LANGCHAIN_LOG_LEVEL", "INFO"),
    )

    langsmith_config = LangSmithConfig(
        api_key=get_env("LANGSMITH_API_KEY", None),
        project=get_env("LANGSMITH_PROJECT", "assistant-ia-api"),
        endpoint=get_env("LANGSMITH_ENDPOINT", None),
        tracing_enabled=get_env("LANGSMITH_TRACING_ENABLED", "false").lower() == "true",
    )

    embeddings_config = EmbeddingsConfig(
        provider=get_env("EMBEDDING_PROVIDER", "huggingface"),
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

    return ConfigurationService(
        server_config=server_config,
        nosql_config=nosql_config,
        openai_config=openai_config,
        aws_config=aws_config,
        whatsapp_config=whatsapp_config,
        calendar_config=calendar_config,
        mcp_config=mcp_config,
        qdrant_config=qdrant_config,
        langchain_config=langchain_config,
        langsmith_config=langsmith_config,
        embeddings_config=embeddings_config,
        llm_extended_config=llm_extended_config,
        logging_config=logging_config,
    )


def init_config() -> None:
    config_service = read_config()
    init_config_service(config_service)