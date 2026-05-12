import math
from datetime import datetime, timezone
from typing import List, Tuple

from src.core.domain.brain import EpisodicMemory


class AttentionSystem:
    """Scores and ranks episodic memories using multiple signals.

    Composite score formula:
        score = 0.50 * semantic
              + 0.25 * recency
              + 0.20 * (importance / 10)
              + 0.05 * log_access
    """

    def score_memory(self, memory: EpisodicMemory, semantic_score: float) -> float:
        recency = self._recency(memory.created_at)
        importance = memory.importance / 10.0
        log_access = math.log1p(memory.access_count) / 10.0  # soft cap at ~10 accesses

        return (
            0.50 * semantic_score
            + 0.25 * recency
            + 0.20 * importance
            + 0.05 * log_access
        )

    def select_memories(
        self,
        candidates: List[Tuple[EpisodicMemory, float]],
        max_memories: int = 5,
        min_score: float = 0.30,
    ) -> List[EpisodicMemory]:
        scored = [
            (memory, self.score_memory(memory, semantic_score))
            for memory, semantic_score in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored if s >= min_score][:max_memories]

    @staticmethod
    def _recency(created_at: datetime) -> float:
        """Exponential decay: score=1.0 at creation, ~0.5 after 7 days, ~0.1 after 30 days."""
        now = datetime.now(timezone.utc)
        days = max(0.0, (now - created_at).total_seconds() / 86400)
        return math.exp(-0.1 * days)
