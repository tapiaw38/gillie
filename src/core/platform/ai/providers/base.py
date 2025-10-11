"""
Base Provider Interface for LLM Providers

This module defines the abstract base class for all LLM providers,
following the Strategy Pattern to allow easy switching between
different AI service providers (OpenAI, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMRequest:
    """Standardized request to any LLM provider"""
    prompt: str
    system_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False
    tools: Optional[List[Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    This interface ensures all providers implement the same methods,
    making them interchangeable throughout the application.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.

        Args:
            config: Configuration dictionary specific to the provider
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate that required configuration is present"""
        pass

    @abstractmethod
    async def generate_response(
        self,
        request: LLMRequest
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: Standardized LLM request

        Returns:
            Standardized LLM response

        Raises:
            ProviderError: If the provider encounters an error
        """
        pass

    @abstractmethod
    async def generate_streaming_response(
        self,
        request: LLMRequest
    ):
        """
        Generate a streaming response from the LLM.

        Args:
            request: Standardized LLM request

        Yields:
            Chunks of the response as they become available

        Raises:
            ProviderError: If the provider encounters an error
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and responding.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            "provider": self.__class__.__name__,
            "model": self.config.get("model", "unknown"),
            "config": self.config
        }


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid"""
    pass


class ProviderAPIError(ProviderError):
    """Raised when the provider API returns an error"""
    pass


class ProviderTimeoutError(ProviderError):
    """Raised when the provider request times out"""
    pass
