import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from src.core.domain.brain import EpisodicMemory

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = (
    "You are a memory extraction system. Given a user-assistant exchange, "
    "identify 0-3 facts, preferences, decisions, or learnings worth remembering for future conversations.\n\n"
    "Rules:\n"
    "- Skip trivial exchanges (greetings, simple acknowledgments, one-word answers).\n"
    "- Focus on: user preferences, goals, decisions made, problems solved, important facts mentioned.\n"
    "- Assign importance 1-10 (10 = critical for future interactions, 1 = barely relevant).\n"
    "- Assign an emotion if clearly expressed: curiosity, frustration, satisfaction, excitement, concern.\n"
    "- Generate 2-4 short keyword tags.\n"
    "- type must be one of: episode, fact, preference, goal\n\n"
    "Respond ONLY with a valid JSON array (can be empty []). Example:\n"
    '[\n'
    '  {\n'
    '    "type": "preference",\n'
    '    "content": "The user prefers concise responses without filler text.",\n'
    '    "importance": 8,\n'
    '    "emotion": null,\n'
    '    "tags": ["style", "communication"]\n'
    '  }\n'
    ']'
)


class EpisodicMemoryWriter:
    """Extracts episodic memories from a conversation exchange using the LLM.

    All work is fire-and-forget — failures are logged but never propagated.
    """

    def __init__(self, episodic_repo, episodic_vector_service, openai_integration):
        self.repo = episodic_repo
        self.vector_service = episodic_vector_service
        self.openai = openai_integration

    async def extract_and_store(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Extract episodic memories from the exchange and persist them.

        Should be called with asyncio.create_task() to avoid blocking responses.
        """
        try:
            if not self._is_worth_extracting(user_message, assistant_response):
                logger.debug("Skipped memory extraction for trivial exchange (user=%s)", user_id)
                return

            memories = await self._extract(user_message, assistant_response)
            for memory_data in memories:
                memory = EpisodicMemory(
                    **{"_id": str(uuid4())},
                    user_id=user_id,
                    type=memory_data.get("type", "episode"),
                    content=memory_data.get("content", ""),
                    importance=max(1, min(10, int(memory_data.get("importance", 5)))),
                    emotion=memory_data.get("emotion") or None,
                    tags=memory_data.get("tags", []),
                    source_conversation_id=conversation_id,
                    created_at=datetime.now(timezone.utc),
                )
                if not memory.content.strip():
                    continue

                if self.vector_service.is_duplicate(user_id, memory.content):
                    logger.debug(
                        "Skipped duplicate episodic memory for user %s: %s",
                        user_id, memory.content[:60],
                    )
                    continue

                memory_id = await self.repo.create(memory)
                memory.id = memory_id
                self.vector_service.store_episode(user_id, memory)

            if memories:
                logger.debug("Stored %d episodic memories for user %s", len(memories), user_id)
        except Exception as exc:
            logger.warning("Episodic memory extraction failed for user %s: %s", user_id, exc)

    @staticmethod
    def _is_worth_extracting(user_message: str, assistant_response: str) -> bool:
        """Return False for exchanges too short to contain memorable information."""
        combined = f"{user_message} {assistant_response}"
        word_count = len(combined.split())
        return word_count >= 20

    async def _extract(self, user_message: str, assistant_response: str) -> List[dict]:
        """Call LLM to extract memory objects. Returns parsed list or []."""
        prompt = (
            f"USER: {user_message[:800]}\n\n"
            f"ASSISTANT: {assistant_response[:800]}"
        )
        try:
            raw = await self.openai.simple_completion(
                system=_EXTRACTION_SYSTEM,
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
            logger.debug("Memory extraction LLM call failed: %s", exc)
            return []
