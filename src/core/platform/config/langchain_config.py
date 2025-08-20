from dataclasses import dataclass
from typing import Optional, List
from src.core.platform.config.service import ConfigurationService

@dataclass
class LangChainConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_pages: int = 50
    enable_vectors: bool = True
    vector_store_type: str = "chroma"
    embedding_model: str = "text-embedding-ada-002"
    similarity_search_k: int = 5
    enable_fallback: bool = True
    log_level: str = "INFO"

class LangChainConfigService:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self.langchain_config = self._load_langchain_config()

    def _load_langchain_config(self) -> LangChainConfig:
        return LangChainConfig(
            chunk_size=self.config_service.get_env("LANGCHAIN_CHUNK_SIZE", 1000, int),
            chunk_overlap=self.config_service.get_env("LANGCHAIN_CHUNK_OVERLAP", 200, int),
            max_pages=self.config_service.get_env("LANGCHAIN_MAX_PAGES", 50, int),
            enable_vectors=self.config_service.get_env("LANGCHAIN_ENABLE_VECTORS", True, bool),
            vector_store_type=self.config_service.get_env("LANGCHAIN_VECTOR_STORE", "chroma", str),
            embedding_model=self.config_service.get_env("LANGCHAIN_EMBEDDING_MODEL", "text-embedding-ada-002", str),
            similarity_search_k=self.config_service.get_env("LANGCHAIN_SIMILARITY_K", 5, int),
            enable_fallback=self.config_service.get_env("LANGCHAIN_ENABLE_FALLBACK", True, bool),
            log_level=self.config_service.get_env("LANGCHAIN_LOG_LEVEL", "INFO", str)
        )

    def get_config(self) -> LangChainConfig:
        return self.langchain_config

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.langchain_config, key):
                setattr(self.langchain_config, key, value)
