"""
Conversation Service

High-level service for managing AI conversations with enhanced capabilities.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .providers.base import BaseLLMProvider, LLMRequest
from .memory.manager import ConversationMemoryManager
from .circuit_breaker import CircuitBreakerService, CircuitBreakerConfig

logger = logging.getLogger(__name__)


@dataclass
class ConversationConfig:
    """Configuration for conversation service"""
    max_history_messages: int = 20
    enable_circuit_breaker: bool = True
    enable_memory: bool = True
    default_temperature: float = 0.7
    default_max_tokens: int = 2000


class ConversationService:
    """
    High-level service for AI conversations.

    Features:
    - Multiple LLM provider support
    - Conversation memory management
    - Circuit breaker protection
    - Context management
    """

    def __init__(
        self,
        provider: BaseLLMProvider,
        config: Optional[ConversationConfig] = None,
        memory_manager: Optional[ConversationMemoryManager] = None,
        circuit_breaker: Optional[CircuitBreakerService] = None,
    ):
        """
        Initialize conversation service.

        Args:
            provider: LLM provider instance
            config: Service configuration
            memory_manager: Optional memory manager
            circuit_breaker: Optional circuit breaker
        """
        self.provider = provider
        self.config = config or ConversationConfig()

        # Initialize memory manager
        if self.config.enable_memory:
            self.memory_manager = memory_manager or ConversationMemoryManager(
                max_messages=self.config.max_history_messages
            )
        else:
            self.memory_manager = None

        if self.config.enable_circuit_breaker:
            self.circuit_breaker = circuit_breaker or CircuitBreakerService(
                CircuitBreakerConfig()
            )
        else:
            self.circuit_breaker = None

        logger.info(
            f"ConversationService initialized with provider: {provider.__class__.__name__}"
        )

    async def generate_response(
        self,
        user_message: str,
        conversation_id: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        previous_messages: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate AI response for a conversation.

        Args:
            user_message: User's message
            conversation_id: Unique conversation identifier
            system_prompt: Optional system prompt
            context: Optional additional context
            previous_messages: Optional conversation history
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            tools: Optional tools for function calling
            metadata: Optional metadata for the request

        Returns:
            Generated response text

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            ProviderError: If LLM provider fails
        """
        try:
            enhanced_system_prompt = self._build_system_prompt(
                system_prompt, context
            )

            messages = []
            if previous_messages:
                if self.memory_manager:
                    langchain_messages = self.memory_manager.messages_to_langchain(
                        previous_messages
                    )
                    langchain_messages = self.memory_manager.optimize_message_history(
                        langchain_messages
                    )
                    messages = [
                        {"role": msg.__class__.__name__.replace("Message", "").lower(),
                         "content": msg.content}
                        for msg in langchain_messages
                    ]
                else:
                    messages = previous_messages

            llm_request = LLMRequest(
                prompt=user_message,
                system_prompt=enhanced_system_prompt,
                messages=messages,
                temperature=temperature or self.config.default_temperature,
                max_tokens=max_tokens or self.config.default_max_tokens,
                tools=tools,
                metadata=metadata or {},
            )

            if self.circuit_breaker:
                response = await self.circuit_breaker.call(
                    self.provider.generate_response,
                    llm_request,
                    fallback=self._get_fallback_response,
                )
            else:
                response = await self.provider.generate_response(llm_request)

            logger.info(
                f"Response generated successfully for conversation {conversation_id}"
            )
            return response.content

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    async def generate_streaming_response(
        self,
        user_message: str,
        conversation_id: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Generate streaming AI response.

        Args:
            user_message: User's message
            conversation_id: Conversation ID
            system_prompt: Optional system prompt
            context: Optional context
            temperature: Optional temperature
            max_tokens: Optional max tokens

        Yields:
            Response chunks
        """
        try:
            enhanced_system_prompt = self._build_system_prompt(
                system_prompt, context
            )

            llm_request = LLMRequest(
                prompt=user_message,
                system_prompt=enhanced_system_prompt,
                temperature=temperature or self.config.default_temperature,
                max_tokens=max_tokens or self.config.default_max_tokens,
                stream=True,
            )

            async for chunk in self.provider.generate_streaming_response(llm_request):
                yield chunk

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            raise

    def _build_system_prompt(
        self,
        system_prompt: Optional[str],
        context: Optional[str]
    ) -> str:
        """
        Build enhanced system prompt with context.

        Args:
            system_prompt: Base system prompt
            context: Additional context

        Returns:
            Enhanced system prompt
        """
        parts = []

        if system_prompt:
            parts.append(system_prompt)

        if context:
            parts.append(f"\nAdditional Context:\n{context}")

        return "\n".join(parts) if parts else ""

    async def _get_fallback_response(self, *args, **kwargs) -> str:
        """Fallback response when circuit breaker is open"""
        return (
            "I apologize, but I'm experiencing technical difficulties at the moment. "
            "Please try again in a few moments."
        )

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            "provider": self.provider.__class__.__name__,
            "config": {
                "max_history": self.config.max_history_messages,
                "circuit_breaker_enabled": self.config.enable_circuit_breaker,
                "memory_enabled": self.config.enable_memory,
            },
        }

        if self.circuit_breaker:
            stats["circuit_breaker"] = self.circuit_breaker.get_state()

        return stats
