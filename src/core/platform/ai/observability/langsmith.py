"""
LangSmith Observability Integration

Centralized LangSmith configuration and utilities.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LangSmithConfig:
    """Configuration for LangSmith tracing"""
    api_key: str
    project: str = "assistant-ia-api"
    endpoint: Optional[str] = None
    enabled: bool = True


class LangSmithService:
    """
    Service for LangSmith observability and tracing.
    """

    def __init__(self, config: Optional[LangSmithConfig] = None):
        """
        Initialize LangSmith service.

        Args:
            config: LangSmith configuration
        """
        self.config = config or self._load_config_from_env()
        self.is_configured = False

        if self.config and self.config.enabled and self.config.api_key:
            self._setup_langsmith()

    def _load_config_from_env(self) -> Optional[LangSmithConfig]:
        """Load configuration from ConfigurationService"""
        try:
            from src.core.platform.config.service import get_config_service
            config_service = get_config_service()
            langsmith_config = config_service.langsmith_config

            if not langsmith_config.api_key or not langsmith_config.tracing_enabled:
                logger.info("LangSmith not configured or disabled")
                return None

            return LangSmithConfig(
                api_key=langsmith_config.api_key,
                project=langsmith_config.project,
                endpoint=langsmith_config.endpoint,
                enabled=langsmith_config.tracing_enabled,
            )
        except Exception as e:
            logger.warning(f"Could not load LangSmith config from ConfigurationService: {e}")
            return None

    def _setup_langsmith(self) -> None:
        """Configure LangSmith environment variables"""
        try:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.config.api_key
            os.environ["LANGCHAIN_PROJECT"] = self.config.project

            if self.config.endpoint:
                os.environ["LANGCHAIN_ENDPOINT"] = self.config.endpoint

            self.is_configured = True
            logger.info(f"LangSmith tracing enabled: project={self.config.project}")

        except Exception as e:
            logger.error(f"Failed to setup LangSmith: {e}")
            self.is_configured = False

    def disable_tracing(self) -> None:
        """Disable LangSmith tracing"""
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        self.is_configured = False
        logger.info("LangSmith tracing disabled")

    def enable_tracing(self) -> None:
        """Enable LangSmith tracing"""
        if self.config and self.config.api_key:
            self._setup_langsmith()
        else:
            logger.warning("Cannot enable tracing: LangSmith not configured")

    def get_status(self) -> Dict[str, Any]:
        """Get LangSmith service status"""
        return {
            "configured": self.is_configured,
            "enabled": self.config.enabled if self.config else False,
            "project": self.config.project if self.config else None,
        }


# Global instance
_langsmith_service: Optional[LangSmithService] = None


def get_langsmith_service() -> LangSmithService:
    """
    Get or create global LangSmith service instance.

    Returns:
        LangSmith service instance
    """
    global _langsmith_service
    if _langsmith_service is None:
        _langsmith_service = LangSmithService()
    return _langsmith_service


def setup_langsmith(config: Optional[LangSmithConfig] = None) -> LangSmithService:
    """
    Setup LangSmith with custom configuration.

    Args:
        config: Optional custom configuration

    Returns:
        LangSmith service instance
    """
    global _langsmith_service
    _langsmith_service = LangSmithService(config)
    return _langsmith_service
