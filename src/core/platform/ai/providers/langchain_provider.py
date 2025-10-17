"""
LangChain Provider Implementation

This module wraps the existing LangChainService to conform to the BaseLLMProvider interface.
"""

import logging
from typing import Dict, Any, AsyncIterator

from .base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderConfigurationError,
    ProviderAPIError,
)

logger = logging.getLogger(__name__)


class LangChainProvider(BaseLLMProvider):
    """
    LangChain Provider implementation.

    This wraps the existing LangChainService to provide a standardized interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LangChain provider.

        Args:
            config: Configuration dictionary including langchain_service instance
        """
        super().__init__(config)

        # LangChainService should be passed in config
        self.langchain_service = config.get("langchain_service")
        if not self.langchain_service:
            raise ProviderConfigurationError("langchain_service not provided in config")

        logger.info("LangChain provider initialized")

    def _validate_config(self) -> None:
        """Validate LangChain configuration"""
        if "langchain_service" not in self.config:
            raise ProviderConfigurationError("langchain_service required in config")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using LangChain.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        try:
            # Extract metadata
            profile = request.metadata.get("profile") if request.metadata else None
            conversation_id = request.metadata.get("conversation_id") if request.metadata else None
            context = request.metadata.get("context") if request.metadata else None
            previous_messages = request.messages or []

            if not profile:
                raise ProviderAPIError("Profile required in request metadata for LangChain")

            # Call LangChain service
            content = await self.langchain_service.generate_response(
                question=request.prompt,
                context=context,
                previous_messages=previous_messages,
                profile=profile,
                conversation_id=conversation_id or profile.user_id,
                use_tools=bool(request.tools),
            )

            # Get stats
            stats = self.langchain_service.get_stats()

            return LLMResponse(
                content=content,
                model=stats.get("model", "unknown"),
                metadata={"langchain_stats": stats},
            )

        except Exception as e:
            logger.error(f"Error in LangChain provider: {e}")
            raise ProviderAPIError(f"LangChain error: {str(e)}")

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate streaming response (not implemented for LangChain yet).

        Args:
            request: LLM request

        Yields:
            Response chunks
        """
        # LangChain streaming not implemented yet
        response = await self.generate_response(request)
        yield response.content

    def count_tokens(self, text: str) -> int:
        """
        Count tokens (delegate to underlying LLM).

        Args:
            text: Text to count

        Returns:
            Token count
        """
        # Rough estimate
        return len(text) // 4

    async def health_check(self) -> bool:
        """
        Check LangChain service health.

        Returns:
            True if healthy
        """
        try:
            stats = self.langchain_service.get_stats()
            is_healthy = not stats.get("circuit_open", False)
            logger.info(f"LangChain health check: {is_healthy}")
            return is_healthy
        except Exception as e:
            logger.error(f"LangChain health check failed: {e}")
            return False
