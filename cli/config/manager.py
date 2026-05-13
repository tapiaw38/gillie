import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from cli.config.schema import (
    AssistantConfig,
    ProfileConfig,
    ServerConfig,
    ServicesConfig,
    MongoDBConfig,
    OpenAIServiceConfig,
    LangChainServiceConfig,
    QdrantServiceConfig,
    BrainServiceConfig,
    EmbeddingsServiceConfig,
    StorageServiceConfig,
    S3ServiceConfig,
    TTSServiceConfig,
    STTServiceConfig,
    WhatsAppServiceConfig,
    MercadoLibreServiceConfig,
    LangSmithServiceConfig,
    LLMExtendedServiceConfig,
    LoggingConfig,
    TunnelConfig,
    ExposeConfig,
)

CONFIG_DIR = Path.home() / ".gillie"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _config_has_required_identity(data: dict) -> bool:
    """Return True when config.json includes the fields needed to load AssistantConfig."""
    return "user_id" in data and "profile" in data



def get_config_path() -> Path:
    """Return the technical config path (env override or default)."""
    env_path = os.environ.get("GILLIE_CONFIG")
    if env_path:
        return Path(env_path)
    return CONFIG_FILE


def config_exists() -> bool:
    """Return True if config.json exists and contains the minimum required identity fields."""
    path = get_config_path()
    if not path.exists():
        return False

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    return _config_has_required_identity(data)



def _build_services(services_data: dict) -> ServicesConfig:
    return ServicesConfig(
        mongodb=MongoDBConfig(**services_data.get("mongodb", {})),
        openai=OpenAIServiceConfig(**services_data.get("openai", {})),
        langchain=LangChainServiceConfig(**services_data.get("langchain", {})),
        qdrant=QdrantServiceConfig(**services_data.get("qdrant", {})),
        brain=BrainServiceConfig(**services_data.get("brain", {})),
        embeddings=EmbeddingsServiceConfig(**services_data.get("embeddings", {})),
        storage=StorageServiceConfig(**services_data.get("storage", {})),
        s3=S3ServiceConfig(**services_data.get("s3", {})),
        tts=TTSServiceConfig(**services_data.get("tts", {})),
        stt=STTServiceConfig(**services_data.get("stt", {})),
        whatsapp=WhatsAppServiceConfig(**services_data.get("whatsapp", {})),
        mercadolibre=MercadoLibreServiceConfig(**services_data.get("mercadolibre", {})),
        langsmith=LangSmithServiceConfig(**services_data.get("langsmith", {})),
        llm=LLMExtendedServiceConfig(**services_data.get("llm", {})),
        provider_keys=services_data.get("provider_keys", {}),
    )



def _parse_profile(data: dict) -> ProfileConfig:
    known_fields = {f.name for f in ProfileConfig.__dataclass_fields__.values()}
    profile_data = {k: v for k, v in data.items() if k in known_fields}
    return ProfileConfig(**profile_data)


def _persist_single_file_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)



def load_config() -> AssistantConfig:
    """
    Load the full in-memory config from config.json.
    """
    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `gillie init` first."
        )
    with open(path, "r") as f:
        data = json.load(f)

    if not _config_has_required_identity(data):
        raise FileNotFoundError(
            "Config does not contain user_id/profile. Run `gillie init --force` to recreate configuration."
        )
    user_id = data["user_id"]
    profile = _parse_profile(data["profile"])

    return AssistantConfig(
        user_id=user_id,
        profile=profile,
        server=ServerConfig(**data.get("server", {})),
        services=_build_services(data.get("services", {})),
        logging=LoggingConfig(**data.get("logging", {})),
        tunnel=TunnelConfig(**data.get("tunnel", {})),
        expose=ExposeConfig(**data.get("expose", {})),
        workspace=data.get("workspace", ""),
    )


def save_config(config: AssistantConfig) -> None:
    """
    Persist the full config into a single config.json file.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    services_dict = asdict(config.services)
    services_dict["provider_keys"] = config.services.provider_keys
    payload = {
        "user_id": config.user_id,
        "profile": asdict(config.profile),
        "server": asdict(config.server),
        "services": services_dict,
        "logging": asdict(config.logging),
        "tunnel": asdict(config.tunnel),
        "expose": asdict(config.expose),
        "workspace": config.workspace,
    }
    _persist_single_file_config(path, payload)



def get_user_id() -> Optional[str]:
    """Return the configured user_id, or None if not initialised."""
    if not config_exists():
        return None
    return load_config().user_id
