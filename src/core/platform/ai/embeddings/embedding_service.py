"""
Embedding Service

Centralized service for generating embeddings from text.
"""

import logging
from typing import List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Supports multiple embedding providers (OpenAI, HuggingFace, etc.)
    """

    def __init__(self, embeddings_model):
        """
        Initialize embedding service.

        Args:
            embeddings_model: LangChain embeddings model instance
        """
        self.embeddings_model = embeddings_model
        logger.info(f"EmbeddingService initialized with model: {embeddings_model.__class__.__name__}")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            embedding = await self.embeddings_model.aembed_query(text)
            logger.debug(f"Generated embedding of dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = await self.embeddings_model.aembed_documents(texts)
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        if hasattr(self.embeddings_model, 'dimension'):
            return self.embeddings_model.dimension
        elif hasattr(self.embeddings_model, 'model_name'):
            model_dimensions = {
                'text-embedding-3-small': 1536,
                'text-embedding-3-large': 3072,
                'text-embedding-ada-002': 1536,
                'all-MiniLM-L6-v2': 384,
                'all-mpnet-base-v2': 768,
            }
            model_name = self.embeddings_model.model_name
            return model_dimensions.get(model_name, 384)  # Default to 384
        else:
            return 384  # Safe default

    def get_model_info(self) -> dict:
        """
        Get information about the embedding model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_class": self.embeddings_model.__class__.__name__,
            "dimension": self.get_dimension(),
        }


def create_openai_embeddings(api_key: str, model: str = "text-embedding-3-small"):
    """
    Create OpenAI embeddings instance.

    Args:
        api_key: OpenAI API key
        model: Model name

    Returns:
        OpenAI embeddings instance
    """
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        api_key=api_key,
        model=model,
    )


def create_huggingface_embeddings(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    device: str = "cpu"
):
    """
    Create HuggingFace embeddings instance.

    Args:
        model_name: Model name from HuggingFace
        device: Device to run on (cpu, cuda, mps)

    Returns:
        HuggingFace embeddings instance
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )


def create_embedding_service_from_config(config: dict) -> EmbeddingService:
    """
    Create embedding service from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        EmbeddingService instance
    """
    provider = config.get("provider", "huggingface")

    if provider == "openai":
        embeddings = create_openai_embeddings(
            api_key=config.get("api_key"),
            model=config.get("model", "text-embedding-3-small"),
        )
    elif provider == "huggingface":
        embeddings = create_huggingface_embeddings(
            model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
            device=config.get("device", "cpu"),
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

    return EmbeddingService(embeddings)
