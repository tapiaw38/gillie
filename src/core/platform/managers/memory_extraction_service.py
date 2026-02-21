"""
Memory Extraction Service

Uses the LLM to summarize conversations and consolidate knowledge
into general.skill.md.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "Eres un asistente experto en resumir conversaciones de soporte al cliente. "
    "Resume la siguiente conversación en 2-3 párrafos breves en markdown, "
    "destacando: temas tratados, preguntas frecuentes detectadas y aprendizajes clave. "
    "Responde solo con el resumen en markdown, sin encabezados adicionales.\n\n"
    "CONVERSACIÓN:\n{messages}"
)

CONSOLIDATE_PROMPT = (
    "Eres un asistente de memoria. Tu tarea es consolidar conocimiento.\n\n"
    "CONOCIMIENTO ACTUAL (general.skill.md):\n{existing}\n\n"
    "NUEVOS RESÚMENES DE CONVERSACIONES:\n{new_summaries}\n\n"
    "Genera un nuevo contenido para general.skill.md que integre el conocimiento "
    "existente con los nuevos aprendizajes. Elimina redundancias. "
    "Usa markdown con secciones claras (## Preferencias, ## Aprendizajes recientes, etc.). "
    "Responde solo con el contenido markdown actualizado."
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
