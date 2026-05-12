"""
Memory Extraction Service

Uses the LLM to summarize conversations so they can be stored on the
conversation record without mutating long-term memory stores.
"""

import logging

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "You are an expert assistant at summarizing customer support conversations. "
    "Summarize the following conversation in 2-3 brief markdown paragraphs, "
    "highlighting: topics discussed, frequently asked questions detected, and key learnings. "
    "Reply only with the markdown summary, without additional headings.\n\n"
    "CONVERSATION:\n{messages}"
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
