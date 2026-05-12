import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WorkingMemoryAssembler:
    """Assembles enriched context for the LLM by retrieving relevant episodic memories.

    Plugs into _inject_skill_context in AddMessageUseCase.
    """

    def __init__(self, episodic_vector_service, episodic_repo, attention_system):
        self.vector_service = episodic_vector_service
        self.repo = episodic_repo
        self.attention = attention_system

    async def assemble(
        self,
        user_id: str,
        query: str,
        skill_context: Optional[str],
    ) -> Optional[str]:
        """Return skill_context enriched with relevant episodic memories.

        If no memories are found or an error occurs, returns skill_context unchanged.
        """
        try:
            candidates = self.vector_service.search_relevant(user_id, query, k=10)
            if not candidates:
                return skill_context

            memory_ids = [mid for mid, _ in candidates]
            score_map = {mid: score for mid, score in candidates}

            full_memories = await self.repo.find_by_ids(memory_ids)
            if not full_memories:
                return skill_context

            ranked = self.attention.select_memories(
                [(mem, score_map.get(mem.id, 0.0)) for mem in full_memories],
                max_memories=5,
            )
            if not ranked:
                return skill_context

            # Fire-and-forget access count updates
            for mem in ranked:
                asyncio.create_task(self.repo.update_access(mem.id))

            block = "=== EPISODIC MEMORIES ===\n"
            for mem in ranked:
                date_str = mem.created_at.strftime("%Y-%m-%d")
                emotion_tag = f" [{mem.emotion}]" if mem.emotion else ""
                block += f"- [{date_str}]{emotion_tag} (importance: {mem.importance}) {mem.content}\n"
            block += "========================="

            if skill_context:
                return f"{skill_context}\n\n{block}"
            return block

        except Exception as exc:
            logger.warning("WorkingMemoryAssembler failed for user %s: %s", user_id, exc)
            return skill_context
