"""
SoulVectorService

Manages the soul store: a Qdrant collection (`soul_{user_id}`) containing
long-term knowledge statements synthesized from episodic memories.

Unlike general.skill.md (always-in-context), soul knowledge is retrieved
on-demand by semantic similarity — only the K most relevant statements
for each conversation are injected, keeping context window usage bounded.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class SoulVectorService:
    """Manages consolidated knowledge vectors in Qdrant (soul store).

    Each user gets their own collection: soul_{user_id}.
    Statements are stored with dedup (threshold=0.92) to avoid near-identical entries.
    """

    _DEDUP_THRESHOLD = 0.92

    def __init__(self, qdrant_adapter, embedding_service):
        self.qdrant = qdrant_adapter
        self.embedding_service = embedding_service
        self._ready_collections: set[str] = set()

    def _collection(self, user_id: str) -> str:
        return f"soul_{user_id}"

    def _ensure_collection(self, user_id: str) -> None:
        collection = self._collection(user_id)
        if collection in self._ready_collections:
            return
        vector_size = self.embedding_service.get_dimension()
        self.qdrant.create_collection(collection, vector_size=vector_size)
        self.qdrant.ensure_payload_index(collection, "metadata.soul_id")
        self._ready_collections.add(collection)

    def store_statement(self, user_id: str, statement: str, category: str = "General") -> bool:
        """Store a knowledge statement in the soul store.

        Skips storage if a semantically similar statement already exists.
        Returns True if stored, False if skipped (duplicate) or on error.
        """
        if self.is_duplicate(user_id, statement):
            logger.debug("Soul store: skipped duplicate statement for user %s", user_id)
            return False
        try:
            self._ensure_collection(user_id)
            soul_id = uuid.uuid4().hex[:8]
            doc = Document(
                page_content=statement,
                metadata={
                    "soul_id": soul_id,
                    "category": category,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            self.qdrant.add_documents(self._collection(user_id), [doc])
            logger.info("Soul store: stored statement [%s] for user %s", category, user_id)
            return True
        except Exception as exc:
            logger.warning("Soul store: failed to store statement for user %s: %s", user_id, exc)
            return False

    def is_duplicate(self, user_id: str, statement: str) -> bool:
        """Return True if a semantically similar statement exists (score >= threshold)."""
        try:
            results = self.qdrant.search_similar(
                collection_name=self._collection(user_id),
                query=statement,
                k=1,
                score_threshold=self._DEDUP_THRESHOLD,
            )
            return len(results) > 0
        except Exception:
            return False

    def search_relevant(
        self,
        user_id: str,
        query: str,
        k: int = 5,
        score_threshold: float = 0.30,
    ) -> List[Tuple[str, str, float]]:
        """Retrieve the K most relevant soul knowledge statements for a query.

        Returns list of (category, statement, score) tuples ordered by score desc.
        """
        try:
            results = self.qdrant.search_similar(
                collection_name=self._collection(user_id),
                query=query,
                k=k,
                score_threshold=score_threshold,
            )
            return [
                (doc.metadata.get("category", "General"), doc.page_content, score)
                for doc, score in results
            ]
        except Exception as exc:
            logger.warning("Soul store: search failed for user %s: %s", user_id, exc)
            return []
