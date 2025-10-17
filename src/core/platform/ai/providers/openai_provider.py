"""
OpenAI Provider Implementation

This module implements the OpenAI LLM provider following the BaseLLMProvider interface.
"""

import logging
from typing import Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI, APIError, APITimeoutError

from .base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderConfigurationError,
    ProviderAPIError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM Provider implementation.

    Supports GPT-4, GPT-3.5, and other OpenAI models.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAI provider.

        Args:
            config: Configuration dictionary with api_key, model, etc.
        """
        super().__init__(config)

        self.client = AsyncOpenAI(
            api_key=self.config["api_key"],
            base_url=self.config.get("base_url"),
            timeout=self.config.get("timeout", 45.0),
            max_retries=self.config.get("max_retries", 3),
        )

        logger.info(f"OpenAI provider initialized with model: {self.config['model']}")

    def _validate_config(self) -> None:
        """Validate OpenAI configuration"""
        required_keys = ["api_key", "model"]
        for key in required_keys:
            if key not in self.config:
                raise ProviderConfigurationError(f"Missing required config key: {key}")

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from OpenAI.

        Args:
            request: LLM request

        Returns:
            LLM response

        Raises:
            ProviderAPIError: If API call fails
            ProviderTimeoutError: If request times out
        """
        try:
            # Build messages
            messages = self._build_messages(request)

            # Prepare request parameters
            request_params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            # Add tools if provided
            if request.tools:
                request_params["tools"] = request.tools
                request_params["tool_choice"] = "auto"

            # Make API call
            logger.debug(f"Calling OpenAI API with model: {self.config['model']}")
            response = await self.client.chat.completions.create(**request_params)

            # Extract response
            message = response.choices[0].message
            content = message.content or ""

            # Handle tool calls if present
            metadata = {}
            if hasattr(message, 'tool_calls') and message.tool_calls:
                metadata["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in message.tool_calls
                ]

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
                metadata=metadata,
            )

        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise ProviderTimeoutError(f"Request timed out: {str(e)}")
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ProviderAPIError(f"API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise ProviderAPIError(f"Unexpected error: {str(e)}")

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from OpenAI.

        Args:
            request: LLM request

        Yields:
            Response chunks as they arrive
        """
        try:
            messages = self._build_messages(request)

            request_params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
            }

            stream = await self.client.chat.completions.create(**request_params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            raise ProviderAPIError(f"Streaming error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken (approximate).

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """
        try:
            import tiktoken

            # Get encoding for model
            model = self.config["model"]
            if "gpt-4" in model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            else:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            logger.warning("tiktoken not installed, using rough token estimate")
            return len(text) // 4
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return len(text) // 4

    async def health_check(self) -> bool:
        """
        Check OpenAI API health.

        Returns:
            True if healthy
        """
        try:
            # Simple test request
            test_request = LLMRequest(
                prompt="test",
                max_tokens=5,
            )
            await self.generate_response(test_request)
            logger.info("OpenAI health check passed")
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

    def _build_messages(self, request: LLMRequest) -> list:
        """
        Build messages array for OpenAI API.

        Args:
            request: LLM request

        Returns:
            Messages array
        """
        messages = []

        # Add system prompt if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt,
            })

        # Add existing messages if provided
        if request.messages:
            messages.extend(request.messages)
        else:
            # Add user prompt
            messages.append({
                "role": "user",
                "content": request.prompt,
            })

        return messages
