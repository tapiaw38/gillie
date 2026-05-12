import logging
from typing import List, Tuple

from langchain_core.documents import Document

from src.core.domain.brain import EpisodicMemory

logger = logging.getLogger(__name__)


class EpisodicVectorService:
    """Manages episodic memory vectors in Qdrant.

    Each user gets their own collection: episodic_{user_id}.
    The vector dimension is determined by the configured embeddings model.
    """

    def __init__(self, qdrant_adapter, embedding_service):
        self.qdrant = qdrant_adapter
        self.embedding_service = embedding_service
        self._ready_collections: set[str] = set()

    def _collection(self, user_id: str) -> str:
        return f"episodic_{user_id}"

    def _ensure_collection(self, user_id: str) -> None:
        collection = self._collection(user_id)
        if collection in self._ready_collections:
            return
        vector_size = self.embedding_service.get_dimension()
        self.qdrant.create_collection(collection, vector_size=vector_size)
        self.qdrant.ensure_payload_index(collection, "metadata.memory_id")
        self._ready_collections.add(collection)

    def store_episode(self, user_id: str, memory: EpisodicMemory) -> bool:
        """Store an episodic memory vector. Returns True on success."""
        try:
            self._ensure_collection(user_id)
            doc = Document(
                page_content=memory.content,
                metadata={
                    "memory_id": memory.id,
                    "importance": memory.importance,
                    "emotion": memory.emotion or "",
                    "tags": ",".join(memory.tags),
                    "type": memory.type,
                    "created_at": memory.created_at.isoformat(),
                },
            )
            return self.qdrant.add_documents(self._collection(user_id), [doc])
        except Exception as exc:
            logger.warning("Failed to store episode vector for user %s: %s", user_id, exc)
            return False

    def is_duplicate(
        self,
        user_id: str,
        content: str,
        threshold: float = 0.85,
    ) -> bool:
        """Return True if a semantically similar memory already exists (score >= threshold)."""
        try:
            results = self.qdrant.search_similar(
                collection_name=self._collection(user_id),
                query=content,
                k=1,
                score_threshold=threshold,
            )
            return len(results) > 0
        except Exception as exc:
            logger.warning("Dedup check failed for user %s: %s", user_id, exc)
            return False

    def delete_episodes(self, user_id: str, memory_ids: List[str]) -> bool:
        """Delete vectors for the given memory IDs from the user's collection."""
        if not memory_ids:
            return True
        try:
            return self.qdrant.delete_points_by_memory_ids(
                self._collection(user_id), memory_ids
            )
        except Exception as exc:
            logger.warning("Failed to delete episode vectors for user %s: %s", user_id, exc)
            return False

    def search_relevant(
        self,
        user_id: str,
        query: str,
        k: int = 10,
        score_threshold: float = 0.25,
    ) -> List[Tuple[str, float]]:
        """Search for relevant episodic memories.

        Returns list of (memory_id, score) tuples ordered by score desc.
        """
        try:
            results = self.qdrant.search_similar(
                collection_name=self._collection(user_id),
                query=query,
                k=k,
                score_threshold=score_threshold,
            )
            return [
                (doc.metadata.get("memory_id", ""), score)
                for doc, score in results
                if doc.metadata.get("memory_id")
            ]
        except Exception as exc:
            logger.warning("Failed to search episodic vectors for user %s: %s", user_id, exc)
            return []
