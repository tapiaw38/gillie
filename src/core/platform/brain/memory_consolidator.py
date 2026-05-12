"""
MemoryConsolidator

Promotes high-importance episodic memories (importance >= 7) to the soul store,
molding the assistant's long-term knowledge over time.

Usage:
    await consolidator.consolidate(user_id, openai_integration)
"""

import json
import logging
from typing import List, Optional

from src.core.domain.brain import EpisodicMemory

logger = logging.getLogger(__name__)

_CONSOLIDATION_SYSTEM = (
    "You are a knowledge distillation system. Given a list of episodic memories from a user, "
    "synthesize them into clear, concise knowledge statements that an assistant should remember "
    "as permanent facts about the user.\n\n"
    "Rules:\n"
    "- Each output statement should be 1-2 sentences maximum.\n"
    "- Group related memories into single statements when possible.\n"
    "- Focus on: user preferences, recurring goals, important facts, behavioral patterns.\n"
    "- Write in third person: 'The user prefers...', 'The user works on...'.\n"
    "- Skip trivial or transient information.\n"
    "- Assign a short category label (e.g. 'Preferencias', 'Proyecto', 'Hábitos', 'Metas').\n\n"
    "Respond ONLY with a valid JSON array. Example:\n"
    '[\n'
    '  {"category": "Preferencias", "statement": "The user prefers concise responses without filler text."},\n'
    '  {"category": "Proyecto", "statement": "The user is building an AI assistant named Gillie."}\n'
    ']'
)


class MemoryConsolidator:
    """Promotes high-importance episodic memories into the soul store (soul molding).

    Synthesized knowledge statements are stored in the `soul_{user_id}` Qdrant
    collection and retrieved on-demand per conversation.

    After promotion, removes the source memories from MongoDB and Qdrant — they are
    no longer needed as episodic entries because the knowledge now lives in the soul store.
    """

    def __init__(
        self,
        episodic_repo,
        openai_integration,
        episodic_vector_service=None,
        soul_vector_service=None,
    ):
        self.repo = episodic_repo
        self.openai = openai_integration
        self.vector_service = episodic_vector_service
        self.soul_vector_service = soul_vector_service

    async def prune_stale(
        self,
        user_id: str,
        max_importance_30d: int = 3,
        max_importance_90d: int = 5,
    ) -> int:
        """Delete stale low-value memories. Returns count deleted."""
        pruned: list[str] = []

        try:
            tier1 = await self.repo.find_stale(user_id, max_importance=max_importance_30d, older_than_days=30)
            tier2 = await self.repo.find_stale(user_id, max_importance=max_importance_90d, older_than_days=90, require_zero_access=True)

            seen: set[str] = set()
            for m in tier1 + tier2:
                if m.id and m.id not in seen:
                    seen.add(m.id)
                    pruned.append(m.id)
        except Exception as exc:
            logger.warning("Prune stale query failed for user %s: %s", user_id, exc)
            return 0

        if not pruned:
            return 0

        deleted = await self.repo.delete_many_by_ids(pruned)
        if self.vector_service:
            self.vector_service.delete_episodes(user_id, pruned)

        logger.info("Pruned %d stale memories for user %s", deleted, user_id)
        return deleted

    async def consolidate(
        self,
        user_id: str,
        min_importance: int = 7,
        auto_prune: bool = True,
    ) -> dict:
        """
        Load unconsolidated memories, synthesize knowledge statements via LLM,
        write them to the soul store, and optionally prune stale memories.

        Returns a dict: {"written": int, "pruned": int}
        """
        if self.soul_vector_service is None:
            raise RuntimeError("Soul store is not configured")

        memories = await self.repo.find_unconsolidated(user_id, min_importance)
        written = 0

        if memories:
            logger.info("Consolidating %d memories for user %s", len(memories), user_id)
            statements = await self._synthesize(memories)

            for item in statements:
                category = item.get("category", "General")
                statement = item.get("statement", "").strip()
                if not statement:
                    continue
                stored = self.soul_vector_service.store_statement(user_id, statement, category)
                if stored:
                    written += 1

            if written > 0:
                promoted_ids = [m.id for m in memories if m.id]
                await self.repo.delete_many_by_ids(promoted_ids)
                if self.vector_service:
                    self.vector_service.delete_episodes(user_id, promoted_ids)
                logger.info(
                    "Consolidated %d statements from %d memories for user %s",
                    written, len(memories), user_id,
                )
            else:
                logger.warning(
                    "Synthesis returned no statements for user %s — source memories preserved",
                    user_id,
                )
        else:
            logger.info("No unconsolidated memories for user %s (min_importance=%d)", user_id, min_importance)

        pruned = 0
        if auto_prune:
            pruned = await self.prune_stale(user_id)

        return {"written": written, "pruned": pruned}

    async def _synthesize(self, memories: List[EpisodicMemory]) -> List[dict]:
        """Call LLM to synthesize memories into knowledge statements."""
        memory_list = [
            {"type": m.type, "content": m.content, "importance": m.importance, "tags": m.tags}
            for m in memories
        ]
        prompt = f"Memories to consolidate:\n{json.dumps(memory_list, ensure_ascii=False, indent=2)}"

        try:
            raw = await self.openai.simple_completion(
                system=_CONSOLIDATION_SYSTEM,
                user=prompt,
            )
            if not raw:
                return []

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return []
            return parsed
        except Exception as exc:
            logger.warning("Memory consolidation LLM call failed: %s", exc)
            return []
