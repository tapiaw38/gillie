from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProfileConfig:
    assistant_name: str
    business_name: str = ""
    functions: str = ""
    response_language: str = "en"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    mode: str = "release"


@dataclass
class MongoDBConfig:
    uri: str = "mongodb://localhost:27017"
    database: str = "gillie-db"
    mode: str = "docker"  # "docker" | "external"


@dataclass
class OpenAIServiceConfig:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    role: str = "user"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 45.0
    max_retries: int = 3
    auth_type: str = "api_key"  # "api_key" | "bearer"


@dataclass
class LangChainServiceConfig:
    enabled: bool = False
    max_concurrent_requests: int = 3
    memory_max_messages: int = 20
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_pages: int = 50
    enable_vectors: bool = True
    vector_store: str = "faiss"
    similarity_k: int = 5
    enable_fallback: bool = True


@dataclass
class QdrantServiceConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    use_grpc: bool = False
    api_key: Optional[str] = None
    mode: str = "docker"  # "docker" | "external"


@dataclass
class EmbeddingsServiceConfig:
    provider: str = "huggingface"
    batch_size: int = 32
    device: str = "cpu"
    openai_model: str = "text-embedding-3-small"
    openai_dimension: int = 1536
    hf_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_dimension: int = 384


@dataclass
class S3ServiceConfig:
    enabled: bool = False
    access_key_id: str = ""
    secret_access_key: str = ""
    region: str = "us-east-1"
    bucket_name: str = ""


@dataclass
class StorageServiceConfig:
    backend: str = "local"  # "s3" | "local"
    local_path: str = ""
    local_base_url: str = "http://localhost:8000/api/storage"


@dataclass
class VisionServiceConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@dataclass
class TTSServiceConfig:
    enabled: bool = False


@dataclass
class STTServiceConfig:
    enabled: bool = False


@dataclass
class WhatsAppServiceConfig:
    enabled: bool = False
    verify_token: str = ""


@dataclass
class MercadoLibreServiceConfig:
    enabled: bool = False


@dataclass
class GoogleCalendarServiceConfig:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/calendar/oauth/callback"


@dataclass
class GoogleDriveServiceConfig:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/drive/oauth/callback"


@dataclass
class LangSmithServiceConfig:
    enabled: bool = False
    api_key: Optional[str] = None
    project: str = "gillie-api"
    endpoint: Optional[str] = None


@dataclass
class LLMExtendedServiceConfig:
    provider: str = "openai"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-opus-20240229"
    anthropic_temperature: float = 0.7
    anthropic_max_tokens: int = 4096
    anthropic_timeout: float = 45.0
    anthropic_max_retries: int = 3


@dataclass
class ServicesConfig:
    mongodb: MongoDBConfig = field(default_factory=MongoDBConfig)
    openai: OpenAIServiceConfig = field(default_factory=OpenAIServiceConfig)
    langchain: LangChainServiceConfig = field(default_factory=LangChainServiceConfig)
    qdrant: QdrantServiceConfig = field(default_factory=QdrantServiceConfig)
    embeddings: EmbeddingsServiceConfig = field(default_factory=EmbeddingsServiceConfig)
    storage: StorageServiceConfig = field(default_factory=StorageServiceConfig)
    s3: S3ServiceConfig = field(default_factory=S3ServiceConfig)
    tts: TTSServiceConfig = field(default_factory=TTSServiceConfig)
    stt: STTServiceConfig = field(default_factory=STTServiceConfig)
    whatsapp: WhatsAppServiceConfig = field(default_factory=WhatsAppServiceConfig)
    mercadolibre: MercadoLibreServiceConfig = field(default_factory=MercadoLibreServiceConfig)
    google_calendar: GoogleCalendarServiceConfig = field(default_factory=GoogleCalendarServiceConfig)
    google_drive: GoogleDriveServiceConfig = field(default_factory=GoogleDriveServiceConfig)
    langsmith: LangSmithServiceConfig = field(default_factory=LangSmithServiceConfig)
    llm: LLMExtendedServiceConfig = field(default_factory=LLMExtendedServiceConfig)
    vision: VisionServiceConfig = field(default_factory=VisionServiceConfig)


@dataclass
class TunnelConfig:
    host: str = ""
    user: str = ""
    ssh_port: int = 22
    api_port: int = 8000
    local_port: int = 8000


@dataclass
class ExposeConfig:
    domain: str = ""
    port: int = 8000
    ssl: bool = False
    email: str = ""  # used by certbot for Let's Encrypt


@dataclass
class LoggingConfig:
    environment: str = "development"
    log_level: str = "INFO"


@dataclass
class SoulConfig:
    """Identity of the assistant — stored in soul.json."""
    user_id: str
    profile: ProfileConfig


@dataclass
class AssistantConfig:
    """Full in-memory configuration (soul + technical config merged)."""
    user_id: str
    profile: ProfileConfig
    server: ServerConfig = field(default_factory=ServerConfig)
    services: ServicesConfig = field(default_factory=ServicesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tunnel: TunnelConfig = field(default_factory=TunnelConfig)
    expose: ExposeConfig = field(default_factory=ExposeConfig)
    workspace: str = ""  # Base directory for file tools. Empty = auto-detect from cwd.
