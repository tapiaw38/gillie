import os
import logging
from datetime import datetime, timezone

from src.core.domain import Message, SenderEnum
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationGetNotFoundError
from src.core.platform.errors.mappings.common import ForbiddenError

logger = logging.getLogger(__name__)


class CompactConversationUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, conversation_id: str, user_id: str) -> dict:
        """Force-compact a conversation immediately, regardless of message count."""
        context = self.context_factory()
        conversation = self._get_and_validate(conversation_id, user_id, context)

        keep_recent = int(os.environ.get("COMPACTION_KEEP_RECENT", "20"))
        messages_to_summarize = (
            conversation.messages[:-keep_recent]
            if len(conversation.messages) > keep_recent
            else conversation.messages
        )
        non_summary = [m for m in messages_to_summarize if m.sender != SenderEnum.summary]

        if not non_summary:
            return {"compacted": False, "reason": "No hay mensajes para compactar"}

        summary_text = await self._generate_summary(messages_to_summarize, context)
        if not summary_text:
            return {"compacted": False, "reason": "No se pudo generar el resumen"}

        summary_message = Message(
            content=f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}",
            sender=SenderEnum.summary,
            created_at=datetime.now(timezone.utc),
        )
        recent = conversation.messages[-keep_recent:] if len(conversation.messages) > keep_recent else []
        conversation.messages = [summary_message] + recent
        context.repositories.conversation.update_messages_by_id(conversation_id, conversation.messages)

        logger.info(f"Manual compaction: {len(messages_to_summarize)} messages → 1 summary")
        return {"compacted": True, "summarized": len(messages_to_summarize)}

    async def compact_if_needed(self, conversation, conversation_id: str, context) -> dict | None:
        """Compact when message count exceeds threshold. Returns SSE event dict or None."""
        threshold = int(os.environ.get("COMPACTION_THRESHOLD", "40"))
        keep_recent = int(os.environ.get("COMPACTION_KEEP_RECENT", "20"))

        if len(conversation.messages) <= threshold:
            return None

        messages_to_summarize = conversation.messages[:-keep_recent]
        recent_messages = conversation.messages[-keep_recent:]

        non_summary = [m for m in messages_to_summarize if m.sender != SenderEnum.summary]
        if not non_summary:
            return None

        summary_text = await self._generate_summary(messages_to_summarize, context)
        if not summary_text:
            return None

        summary_message = Message(
            content=f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}",
            sender=SenderEnum.summary,
            created_at=datetime.now(timezone.utc),
        )
        conversation.messages = [summary_message] + recent_messages
        context.repositories.conversation.update_messages_by_id(conversation_id, conversation.messages)

        logger.info(
            f"Conversation {conversation_id} compacted: "
            f"{len(messages_to_summarize)} messages condensed into 1 summary"
        )
        return {"type": "compaction", "message": "Conversación compactada para optimizar el contexto"}

    async def _generate_summary(self, messages: list, context) -> str:
        """Summarize messages using OpenAI. Returns empty string on failure."""
        _SUMMARIZABLE = {SenderEnum.user, SenderEnum.assistant, SenderEnum.summary}

        history_lines = []
        for m in messages:
            if m.sender not in _SUMMARIZABLE or not m.content:
                continue
            label = m.sender.value.upper()
            history_lines.append(f"{label}: {m.content[:500]}")

        if not history_lines:
            return ""

        system_prompt = (
            "You are an assistant that summarizes conversations. Summarize the following "
            "conversation concisely but completely, preserving:\n"
            "- Important decisions made\n"
            "- Problems solved and their solutions\n"
            "- Project or task context in progress\n"
            "- Mentioned preferences or settings\n"
            "- Modified files or code\n\n"
            "Reply ONLY with the summary in concise bullet points. No introduction or closing."
        )
        try:
            return await context.integrations.openai.simple_completion(
                system=system_prompt,
                user=f"Summarize this conversation:\n\n{chr(10).join(history_lines)}",
            )
        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {e}")
            return ""

    def _get_and_validate(self, conversation_id: str, user_id: str, context):
        conversation = context.repositories.conversation.find_by_id(conversation_id)
        if not conversation:
            raise NewApplicationError(ConversationGetNotFoundError)
        if user_id != conversation.profile.user_id:
            raise NewApplicationError(ForbiddenError)
        if not hasattr(conversation, "messages") or conversation.messages is None:
            conversation.messages = []
        return conversation
