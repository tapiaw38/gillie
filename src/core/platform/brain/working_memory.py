import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WorkingMemoryAssembler:
    """Assembles enriched context for the LLM by retrieving relevant memories.

    Injects two blocks when available:
    - === SOUL KNOWLEDGE ===   long-term facts from the soul store (Qdrant)
    - === EPISODIC MEMORIES === recent relevant experiences

    Plugs into _inject_skill_context in AddMessageUseCase.
    """

    def __init__(self, episodic_vector_service, episodic_repo, attention_system, soul_vector_service=None):
        self.vector_service = episodic_vector_service
        self.repo = episodic_repo
        self.attention = attention_system
        self.soul_vector_service = soul_vector_service

    async def assemble(
        self,
        user_id: str,
        query: str,
        skill_context: Optional[str],
    ) -> Optional[str]:
        """Return skill_context enriched with soul knowledge and episodic memories.

        If no memories are found or an error occurs, returns skill_context unchanged.
        """
        extra_blocks: list[str] = []

        try:
            # ── Soul knowledge (long-term, from soul store) ────────────────────
            if self.soul_vector_service is not None:
                soul_results = self.soul_vector_service.search_relevant(user_id, query, k=5)
                if soul_results:
                    soul_block = "=== SOUL KNOWLEDGE ===\n"
                    for category, statement, _ in soul_results:
                        soul_block += f"- [{category}] {statement}\n"
                    soul_block += "======================"
                    extra_blocks.append(soul_block)
        except Exception as exc:
            logger.warning("Soul knowledge retrieval failed for user %s: %s", user_id, exc)

        try:
            # ── Episodic memories (recent experiences) ─────────────────────────
            candidates = self.vector_service.search_relevant(user_id, query, k=10)
            if candidates:
                memory_ids = [mid for mid, _ in candidates]
                score_map = {mid: score for mid, score in candidates}

                full_memories = await self.repo.find_by_ids(memory_ids)
                if full_memories:
                    ranked = self.attention.select_memories(
                        [(mem, score_map.get(mem.id, 0.0)) for mem in full_memories],
                        max_memories=5,
                    )
                    if ranked:
                        for mem in ranked:
                            asyncio.create_task(self.repo.update_access(mem.id))

                        episodic_block = "=== EPISODIC MEMORIES ===\n"
                        for mem in ranked:
                            date_str = mem.created_at.strftime("%Y-%m-%d")
                            emotion_tag = f" [{mem.emotion}]" if mem.emotion else ""
                            episodic_block += (
                                f"- [{date_str}]{emotion_tag} (importance: {mem.importance}) {mem.content}\n"
                            )
                        episodic_block += "========================="
                        extra_blocks.append(episodic_block)
        except Exception as exc:
            logger.warning("WorkingMemoryAssembler failed for user %s: %s", user_id, exc)

        if not extra_blocks:
            return skill_context

        combined = "\n\n".join(extra_blocks)
        if skill_context:
            return f"{skill_context}\n\n{combined}"
        return combined
