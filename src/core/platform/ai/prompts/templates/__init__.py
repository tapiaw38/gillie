"""
Prompt Templates Module
"""

from .conversation import (
    build_conversation_prompt,
    CONVERSATION_BASE_TEMPLATE,
    ROLE_CONTEXT_SELLER,
    ROLE_CONTEXT_TUTOR,
    ROLE_CONTEXT_ASSISTANT,
)

from .rag import (
    build_rag_prompt,
    build_rag_system_prompt,
    RAG_SYSTEM_TEMPLATE,
)

from .function_calling import (
    build_function_calling_system_prompt,
    FUNCTION_CALLING_SYSTEM,
)

__all__ = [
    "build_conversation_prompt",
    "CONVERSATION_BASE_TEMPLATE",
    "ROLE_CONTEXT_SELLER",
    "ROLE_CONTEXT_TUTOR",
    "ROLE_CONTEXT_ASSISTANT",
    "build_rag_prompt",
    "build_rag_system_prompt",
    "RAG_SYSTEM_TEMPLATE",
    "build_function_calling_system_prompt",
    "FUNCTION_CALLING_SYSTEM",
]
