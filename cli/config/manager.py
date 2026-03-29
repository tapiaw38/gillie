import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from cli.config.schema import (
    AssistantConfig,
    SoulConfig,
    ProfileConfig,
    ServerConfig,
    ServicesConfig,
    MongoDBConfig,
    OpenAIServiceConfig,
    LangChainServiceConfig,
    QdrantServiceConfig,
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
SOUL_FILE = CONFIG_DIR / "soul.json"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ── Path helpers ─────────────────────────────────────────────────────────────

def get_config_path() -> Path:
    """Return the technical config path (env override or default)."""
    env_path = os.environ.get("GILLIE_CONFIG")
    if env_path:
        return Path(env_path)
    return CONFIG_FILE


def get_soul_path() -> Path:
    """Return the soul config path (always ~/.gillie/soul.json)."""
    return SOUL_FILE


# ── Existence checks ─────────────────────────────────────────────────────────

def soul_exists() -> bool:
    """Return True if soul.json has been created."""
    return get_soul_path().exists()


def config_exists() -> bool:
    """Return True if both soul.json and config.json exist."""
    return soul_exists() and get_config_path().exists()


# ── Serialization helpers ─────────────────────────────────────────────────────

def _build_services(services_data: dict) -> ServicesConfig:
    return ServicesConfig(
        mongodb=MongoDBConfig(**services_data.get("mongodb", {})),
        openai=OpenAIServiceConfig(**services_data.get("openai", {})),
        langchain=LangChainServiceConfig(**services_data.get("langchain", {})),
        qdrant=QdrantServiceConfig(**services_data.get("qdrant", {})),
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


# ── Soul I/O ─────────────────────────────────────────────────────────────────

def load_soul() -> SoulConfig:
    """Load soul.json (user_id + profile)."""
    path = get_soul_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Soul not found at {path}. Run `gillie init` first."
        )
    with open(path, "r") as f:
        data = json.load(f)
    known_fields = {f.name for f in ProfileConfig.__dataclass_fields__.values()}
    profile_data = {k: v for k, v in data["profile"].items() if k in known_fields}
    return SoulConfig(
        user_id=data["user_id"],
        profile=ProfileConfig(**profile_data),
    )


def save_soul(soul: SoulConfig) -> None:
    """Save soul.json."""
    path = get_soul_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(asdict(soul), f, indent=2)


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_config() -> AssistantConfig:
    """
    Load the full in-memory config by merging soul.json + config.json.
    """
    soul = load_soul()

    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `gillie init` first."
        )
    with open(path, "r") as f:
        data = json.load(f)

    return AssistantConfig(
        user_id=soul.user_id,
        profile=soul.profile,
        server=ServerConfig(**data.get("server", {})),
        services=_build_services(data.get("services", {})),
        logging=LoggingConfig(**data.get("logging", {})),
        tunnel=TunnelConfig(**data.get("tunnel", {})),
        expose=ExposeConfig(**data.get("expose", {})),
        workspace=data.get("workspace", ""),
    )


def save_config(config: AssistantConfig) -> None:
    """
    Persist the full config by splitting it into:
      - soul.json  (user_id + profile)
      - config.json (server + services + logging)
    """
    save_soul(SoulConfig(user_id=config.user_id, profile=config.profile))

    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    services_dict = asdict(config.services)
    services_dict["provider_keys"] = config.services.provider_keys
    technical = {
        "server": asdict(config.server),
        "services": services_dict,
        "logging": asdict(config.logging),
        "tunnel": asdict(config.tunnel),
        "expose": asdict(config.expose),
        "workspace": config.workspace,
    }
    with open(path, "w") as f:
        json.dump(technical, f, indent=2)


# ── Shortcuts ─────────────────────────────────────────────────────────────────

def get_user_id() -> Optional[str]:
    """Return the configured user_id, or None if not initialised."""
    if not soul_exists():
        return None
    return load_soul().user_id
