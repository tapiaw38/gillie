"""
Embeddings Module
"""

from .embedding_service import (
    EmbeddingService,
    create_openai_embeddings,
    create_huggingface_embeddings,
    create_embedding_service_from_config,
)

__all__ = [
    "EmbeddingService",
    "create_openai_embeddings",
    "create_huggingface_embeddings",
    "create_embedding_service_from_config",
]
