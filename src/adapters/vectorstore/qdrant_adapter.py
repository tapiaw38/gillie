"""
Qdrant Vector Store Adapter

This adapter implements the port for vector storage using Qdrant,
following the Hexagonal Architecture pattern (Ports & Adapters).

This allows the core business logic to remain independent of the
specific vector database implementation.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models

from src.core.platform.config.service import ConfigurationService

logger = logging.getLogger(__name__)


class QdrantVectorStoreAdapter:
    """
    Adapter for Qdrant vector database.

    This adapter provides a clean interface between the application's core logic
    and the Qdrant vector database, implementing the Adapter pattern.
    """

    def __init__(self, config_service: ConfigurationService, embeddings=None):
        """
        Initialize Qdrant adapter with configuration.

        Args:
            config_service: Configuration service instance
            embeddings: Embedding model instance (HuggingFace, OpenAI, etc.)
        """
        self.config_service = config_service
        self.embeddings = embeddings

        # Get Qdrant configuration from config service
        qdrant_config = config_service.qdrant_config
        qdrant_host = qdrant_config.host
        qdrant_port = qdrant_config.port
        qdrant_grpc_port = qdrant_config.grpc_port
        use_grpc = qdrant_config.use_grpc

        # Initialize Qdrant client
        try:
            self.client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                grpc_port=qdrant_grpc_port,
                prefer_grpc=use_grpc,
                timeout=30
            )
            logger.info(f"Qdrant client initialized: {qdrant_host}:{qdrant_port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create a new collection in Qdrant if it doesn't exist.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of the vectors (default: 384 for all-MiniLM-L6-v2)
            distance: Distance metric to use (COSINE, EUCLID, DOT)

        Returns:
            True if collection was created or already exists, False otherwise
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name in collection_names:
                logger.info(f"Collection '{collection_name}' already exists")
                return True

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")
            return True

        except Exception as e:
            logger.error(f"Error creating collection '{collection_name}': {e}")
            return False

    def get_vectorstore(
        self,
        collection_name: str,
        create_if_missing: bool = True,
        vector_size: int = 384
    ) -> Optional[Qdrant]:
        """
        Get a LangChain Qdrant vectorstore instance.

        Args:
            collection_name: Name of the collection
            create_if_missing: Create collection if it doesn't exist
            vector_size: Vector dimension (for creation)

        Returns:
            Qdrant vectorstore instance or None if error
        """
        try:
            if create_if_missing:
                self.create_collection(collection_name, vector_size)

            if self.embeddings is None:
                logger.error("No embeddings model provided")
                return None

            vectorstore = Qdrant(
                client=self.client,
                collection_name=collection_name,
                embeddings=self.embeddings
            )

            logger.debug(f"Retrieved vectorstore for collection '{collection_name}'")
            return vectorstore

        except Exception as e:
            logger.error(f"Error getting vectorstore for '{collection_name}': {e}")
            return None

    def add_documents(
        self,
        collection_name: str,
        documents: List[Document],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add documents to a collection.

        Args:
            collection_name: Name of the collection
            documents: List of LangChain Document objects
            metadata: Optional list of metadata dicts for each document

        Returns:
            True if successful, False otherwise
        """
        try:
            vectorstore = self.get_vectorstore(collection_name)
            if vectorstore is None:
                return False

            # Add metadata to documents if provided
            if metadata:
                for i, doc in enumerate(documents):
                    if i < len(metadata):
                        doc.metadata.update(metadata[i])

            vectorstore.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to '{collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Error adding documents to '{collection_name}': {e}")
            return False

    def search_similar(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        score_threshold: Optional[float] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[tuple]:
        """
        Search for similar documents using semantic search.

        Args:
            collection_name: Name of the collection
            query: Query string
            k: Number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            filter_dict: Optional metadata filter

        Returns:
            List of (Document, score) tuples
        """
        try:
            vectorstore = self.get_vectorstore(collection_name, create_if_missing=False)
            if vectorstore is None:
                return []

            # Build filter if provided
            qdrant_filter = None
            if filter_dict:
                qdrant_filter = self._build_filter(filter_dict)

            # Perform similarity search
            if score_threshold is not None:
                results = vectorstore.similarity_search_with_score(
                    query,
                    k=k,
                    filter=qdrant_filter
                )
                # Filter by score threshold
                results = [(doc, score) for doc, score in results if score >= score_threshold]
            else:
                results = vectorstore.similarity_search_with_score(
                    query,
                    k=k,
                    filter=qdrant_filter
                )

            logger.debug(f"Found {len(results)} similar documents in '{collection_name}'")
            return results

        except Exception as e:
            logger.error(f"Error searching in '{collection_name}': {e}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from Qdrant.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection '{collection_name}': {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection info or None if error
        """
        try:
            collection_info = self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status.value,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value
                }
            }

        except Exception as e:
            logger.error(f"Error getting info for collection '{collection_name}': {e}")
            return None

    def list_collections(self) -> List[str]:
        """
        List all collections in Qdrant.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            logger.debug(f"Found {len(collection_names)} collections")
            return collection_names

        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def _build_filter(self, filter_dict: Dict[str, Any]) -> models.Filter:
        """
        Build Qdrant filter from dictionary.

        Args:
            filter_dict: Dictionary with filter conditions

        Returns:
            Qdrant Filter object
        """
        conditions = []

        for key, value in filter_dict.items():
            conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                )
            )

        return models.Filter(must=conditions)

    def delete_by_metadata(
        self,
        collection_name: str,
        metadata_filter: Dict[str, Any]
    ) -> bool:
        """
        Delete documents by metadata filter.

        Args:
            collection_name: Name of the collection
            metadata_filter: Dictionary with metadata conditions

        Returns:
            True if successful, False otherwise
        """
        try:
            qdrant_filter = self._build_filter(metadata_filter)

            self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=qdrant_filter
                )
            )

            logger.info(f"Deleted documents from '{collection_name}' matching filter: {metadata_filter}")
            return True

        except Exception as e:
            logger.error(f"Error deleting documents from '{collection_name}': {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and responding.

        Returns:
            True if healthy, False otherwise
        """
        try:
            collections = self.client.get_collections()
            logger.debug(f"Qdrant health check passed. Found {len(collections.collections)} collections")
            return True

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
