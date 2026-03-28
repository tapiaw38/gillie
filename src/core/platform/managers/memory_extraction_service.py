"""
Memory Extraction Service

Uses the LLM to summarize conversations and consolidate knowledge
into general.skill.md.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "You are an expert assistant at summarizing customer support conversations. "
    "Summarize the following conversation in 2-3 brief markdown paragraphs, "
    "highlighting: topics discussed, frequently asked questions detected, and key learnings. "
    "Reply only with the markdown summary, without additional headings.\n\n"
    "CONVERSATION:\n{messages}"
)

CONSOLIDATE_PROMPT = (
    "You are a memory assistant. Your task is to consolidate knowledge.\n\n"
    "CURRENT KNOWLEDGE (general.skill.md):\n{existing}\n\n"
    "NEW CONVERSATION SUMMARIES:\n{new_summaries}\n\n"
    "Generate new content for general.skill.md that integrates the existing knowledge "
    "with the new learnings. Remove redundancies. "
    "Use markdown with clear sections (## Preferences, ## Recent Learnings, etc.). "
    "Reply only with the updated markdown content."
)


class MemoryExtractionService:
    async def summarize_conversation(self, conversation, openai_client) -> str:
        """
        Summarize a conversation using the LLM.

        Args:
            conversation: Conversation domain object
            openai_client: OpenAI integration instance

        Returns:
            Markdown summary string
        """
        messages = conversation.messages or []
        if not messages:
            return ""

        messages_text = "\n".join(
            f"{msg.sender.upper()}: {msg.content}"
            for msg in messages
            if msg.content
        )

        prompt = SUMMARIZE_PROMPT.format(messages=messages_text)
        try:
            response = await openai_client.ask(prompt, None, None, None)
            return response or ""
        except Exception as e:
            logger.error(f"Error summarizing conversation {conversation.id}: {e}")
            return ""

    async def update_general_memory(
        self,
        new_summaries: List[str],
        skill_manager,
        openai_client,
    ) -> None:
        """
        Consolidate new conversation summaries into general.skill.md.

        Args:
            new_summaries: List of markdown summary strings
            skill_manager: SkillManager instance
            openai_client: OpenAI integration instance
        """
        if not new_summaries:
            return

        existing = skill_manager.get_general_memory()
        new_text = "\n\n---\n\n".join(new_summaries)

        prompt = CONSOLIDATE_PROMPT.format(
            existing=existing or "(vacío)",
            new_summaries=new_text,
        )

        try:
            updated = await openai_client.ask(prompt, None, None, None)
            if updated:
                skill_manager.update_general_memory(updated)
                logger.info("general.skill.md updated with new memory")
        except Exception as e:
            logger.error(f"Error consolidating memory: {e}")
