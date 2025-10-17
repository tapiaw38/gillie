"""
AI Platform Module

Centralized AI infrastructure for the application with:
- Multiple LLM provider support (OpenAI, LangChain, Anthropic)
- Advanced conversation management
- Memory and context handling
- Document processing and RAG
- Observability and metrics
- Circuit breaker pattern
- Embeddings service
- Prompt management

Architecture:
- providers/: LLM provider implementations (Strategy Pattern)
- services/: High-level AI services (conversation, circuit breaker)
- processors/: Document processors (PDF, Excel, RAG)
- config/: Centralized configuration
- memory/: Conversation memory management
- tools/: LangChain tools and functions
- prompts/: Prompt templates and management
- embeddings/: Embedding generation service
- observability/: Metrics and tracing (LangSmith)
- utils/: Utilities (token counting, retry logic, validators)
"""

# Legacy export (for backward compatibility)
from .langchain_service import LangChainService

# Providers
from .providers import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
)

# Config - Now centralized in ConfigurationService
# Legacy imports removed - use ConfigurationService instead

# Services
from .services import (
    ConversationService,
    CircuitBreakerService,
    CircuitBreakerConfig,
)

# Memory
from .memory.manager import ConversationMemoryManager

# Tools
from .tools.models import create_langchain_tools

# Prompts
from .prompts import (
    build_conversation_prompt,
    build_rag_prompt,
    build_function_calling_system_prompt,
)

# Embeddings
from .embeddings import (
    EmbeddingService,
    create_embedding_service_from_config,
)

# Observability
from .observability import (
    get_langsmith_service,
    get_metrics_collector,
)

# Utils
from .utils import (
    TokenCounter,
    count_tokens,
    RetryHandler,
    with_retry,
    ResponseValidator,
)

__all__ = [
    # Legacy
    "LangChainService",
    # Providers
    "BaseLLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ProviderError",
    # Config - Removed: Use ConfigurationService instead
    # Services
    "ConversationService",
    "CircuitBreakerService",
    "CircuitBreakerConfig",
    # Memory
    "ConversationMemoryManager",
    # Tools
    "create_langchain_tools",
    # Prompts
    "build_conversation_prompt",
    "build_rag_prompt",
    "build_function_calling_system_prompt",
    # Embeddings
    "EmbeddingService",
    "create_embedding_service_from_config",
    # Observability
    "get_langsmith_service",
    "get_metrics_collector",
    # Utils
    "TokenCounter",
    "count_tokens",
    "RetryHandler",
    "with_retry",
    "ResponseValidator",
]
