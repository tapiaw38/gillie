"""
Add Message Use Case

This use case orchestrates the process of adding a message to a conversation,
following SOLID principles and hexagonal architecture.

Responsibilities:
- Orchestrate the message addition workflow
- Coordinate between different services
- Manage conversation state and validation
- Handle repository operations

The heavy lifting is delegated to specialized services:
- VoiceTranscriptionService: Voice-to-text conversion
- AIResponseService: AI response generation
- ImageProcessingService: Image search and processing
- TextToSpeechService: Text-to-speech conversion
- MessageHistoryService: Message history management
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.schemas import MessageInput, MessageListOutput
from src.core.domain import Message, SenderEnum
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import (
    ConversationGetNotFoundError,
    ConversationMessageValidationError
)
from src.core.platform.errors.mappings.common import ForbiddenError

logger = logging.getLogger(__name__)


class AddMessageUseCase:
    """
    Use case for adding messages to conversations.

    This class follows the Single Responsibility Principle by focusing
    on orchestration while delegating specific concerns to services.
    """

    def __init__(self, context_factory: Factory):
        """
        Initialize the add message use case.

        Args:
            context_factory: Factory for creating context instances
        """
        self.context_factory = context_factory()

    async def execute(
        self,
        conversation_id: str,
        message: MessageInput,
        sender: SenderEnum,
        user_id: str,
        has_image_processor: Optional[str] = None,
        has_text_to_voice: Optional[str] = None,
        auth_token: Optional[str] = None,
        client_workspace: str = "",
    ) -> list[Message]:
        """
        Executes the add message workflow.

        Workflow:
        1. Process voice content if provided (transcription)
        2. Create and validate user message
        3. Retrieve and validate conversation
        4. Generate AI response
        5. Process images if enabled
        6. Generate audio if enabled
        7. Save messages to conversation
        8. Return updated messages

        Args:
            conversation_id: ID of the conversation
            message: Input message data
            sender: Message sender (user/assistant)
            user_id: ID of the user
            has_image_processor: Flag to enable image processing
            has_text_to_voice: Flag to enable text-to-speech

        Returns:
            List of messages in the conversation

        Raises:
            ApplicationError: If conversation not found, unauthorized, or validation error
        """
        enhanced_content = await self._process_voice_content(message)

        if message.voice_content and not enhanced_content.strip():
            logger.warning("Voice content provided but transcription returned no text — skipping")
            conversation = self._get_and_validate_conversation(conversation_id, user_id)
            return MessageListOutput.from_output(conversation.messages)

        user_message = self._create_user_message(enhanced_content, sender)

        conversation = self._get_and_validate_conversation(
            conversation_id, user_id
        )

        await self._compact_if_needed(conversation, conversation_id)

        self._add_message_to_conversation(conversation, user_message)

        default_message, ai_response_text = await self._generate_ai_response(
            user_message=user_message,
            conversation=conversation,
            message_context=message.context,
            auth_token=auth_token,
            client_workspace=client_workspace,
        )

        if default_message:
            pre_message = self._create_assistant_message(content=default_message)
            self._add_message_to_conversation(conversation, pre_message)

        formatted_images = await self._process_images_if_enabled(
            has_image_processor=has_image_processor,
            user_message=user_message,
            conversation=conversation,
            message_context=message.context
        )

        audio_url = await self._generate_audio_if_enabled(
            has_text_to_voice=has_text_to_voice,
            text=ai_response_text,
            user_id=user_id,
            conversation_id=conversation_id
        )

        assistant_message = self._create_assistant_message(
            content=ai_response_text,
            audio_url=audio_url
        )

        if formatted_images:
            assistant_message.content = f"{ai_response_text}\n\n{formatted_images}"

        self._add_message_to_conversation(conversation, assistant_message)

        self._save_messages(conversation_id, conversation.messages)

        return MessageListOutput.from_output(conversation.messages)

    async def _process_voice_content(self, message: MessageInput) -> str:
        """
        Processes voice content and enhances message text.

        Args:
            message: Input message with optional voice content

        Returns:
            Enhanced content with voice transcription if available
        """
        if not message.voice_content:
            return message.content

        if not self.context_factory.platform_managers:
            logger.warning("Platform managers not available, skipping voice processing")
            return message.content

        try:
            logger.info("Processing voice content...")

            _stt_lang = "en-US"
            try:
                _profile = self.context_factory.repositories.profile.find_by_user_id(
                    self.context_factory.user_id
                ) if hasattr(self.context_factory, "user_id") else None
                if _profile and getattr(_profile, "response_language", None) == "es":
                    _stt_lang = "es-ES"
            except Exception:
                pass
            transcription = await self.context_factory.platform_managers.voice_transcription.transcribe_audio_file(
                audio_file=message.voice_content,
                language=_stt_lang,
            )

            if transcription:
                enhanced_content = self.context_factory.platform_managers.voice_transcription.enhance_message_with_transcription(
                    original_message=message.content,
                    transcription=transcription
                )
                logger.info(f"Voice transcription successful: '{transcription[:100]}...'")
                return enhanced_content
            else:
                logger.warning("Voice transcription failed, using original content")
                return message.content

        except Exception as e:
            logger.error(f"Error processing voice content: {e}")
            return message.content

    def _create_user_message(self, content: str, sender: SenderEnum) -> Message:
        """
        Creates a user message domain object.

        Args:
            content: Message content
            sender: Message sender

        Returns:
            Message domain object
        """
        return Message(
            content=content,
            sender=sender,
            created_at=datetime.now(timezone.utc),
        )

    def _create_assistant_message(
        self,
        content: str,
        audio_url: Optional[str] = None
    ) -> Message:
        """
        Creates an assistant message domain object.

        Args:
            content: Message content
            audio_url: Optional audio URL

        Returns:
            Message domain object
        """
        return Message(
            content=content,
            audio_url=audio_url,
            sender="assistant",
            created_at=datetime.now(timezone.utc),
        )

    def _get_and_validate_conversation(self, conversation_id: str, user_id: str):
        """
        Retrieves and validates a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user

        Returns:
            Conversation domain object

        Raises:
            ApplicationError: If conversation not found or user unauthorized
        """
        conversation = self.context_factory.repositories.conversation.find_by_id(
            conversation_id
        )

        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            raise NewApplicationError(ConversationGetNotFoundError)

        if user_id != conversation.profile.user_id:
            logger.error(
                f"User {user_id} not authorized for conversation {conversation_id}"
            )
            raise NewApplicationError(ForbiddenError)

        full_profile = self.context_factory.repositories.profile.find_by_id(
            conversation.profile.id
        )
        if full_profile:
            conversation.profile = full_profile
            logger.info(f"Loaded full profile with integrations for profile_id: {full_profile.id}")
        else:
            logger.warning(f"Could not load full profile for profile_id: {conversation.profile.id}")

        if not hasattr(conversation, "messages") or conversation.messages is None:
            conversation.messages = []

        return conversation

    def _add_message_to_conversation(self, conversation, message: Message) -> None:
        """
        Adds a message to the conversation with validation.

        Args:
            conversation: Conversation domain object
            message: Message to add

        Raises:
            ApplicationError: If message with same ID already exists
        """
        if any(msg.id == message.id for msg in conversation.messages):
            logger.error(f"Duplicate message ID: {message.id}")
            raise NewApplicationError(ConversationMessageValidationError)

        conversation.messages.append(message)

    async def _generate_ai_response(
        self,
        user_message: Message,
        conversation,
        message_context: Optional[str],
        auth_token: Optional[str] = None,
        client_workspace: str = "",
    ) -> Tuple[Optional[str], str]:
        """
        Generates AI response using the AI response service.

        Args:
            user_message: User's message
            conversation: Conversation object
            message_context: Optional message context

        Returns:
            Tuple of (default_message, ai_response_text)
        """
        if not self.context_factory.platform_managers:
            logger.warning("Platform services not available, using fallback")
            response = await self._generate_ai_response_fallback(
                user_message, conversation, message_context, client_workspace=client_workspace
            )
            return (None, response)

        try:
            enhanced_context = self._inject_skill_context(message_context, user_message.content)

            chat_history = self.context_factory.platform_managers.message_history.build_chat_history(
                messages=conversation.messages,
                max_messages=20
            )

            conversation_history = self.context_factory.platform_managers.message_history.convert_messages_to_string(
                conversation.messages[-20:]
            )

            return await self.context_factory.platform_managers.ai_response.generate_response(
                user_message=user_message.content,
                profile=conversation.profile,
                message_context=enhanced_context,
                conversation_history=conversation_history,
                chat_history=chat_history,
                auth_token=auth_token,
                client_workspace=client_workspace,
            )

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return (None, self._get_fallback_error_message(conversation.profile))

    async def execute_stream(
        self,
        conversation_id: str,
        content: str,
        user_id: str,
        client_workspace: str = "",
        plan_mode: bool = False,
        has_pty: bool = False,
    ):
        """
        Streaming variant for CLI use. Validates the conversation, saves the user
        message, streams AI response tokens, then persists the assistant message.

        Yields:
            str: AI response text tokens as they arrive.
            dict {"type": "shell_output", "line": str}: real-time stdout lines from
                run_shell tool invocations, emitted in real time as the process runs.
            dict {"type": "audio", "url": str}: audio URL when TTS is enabled.
        """
        conversation = self._get_and_validate_conversation(conversation_id, user_id)

        compaction_event = await self._compact_if_needed(conversation, conversation_id)
        if compaction_event:
            yield compaction_event

        user_message = self._create_user_message(content, SenderEnum.user)
        self._add_message_to_conversation(conversation, user_message)

        enhanced_context = self._inject_skill_context(None, content)
        conversation_history = (
            self.context_factory.platform_managers.message_history
            .convert_messages_to_string(conversation.messages[-20:])
            if self.context_factory.platform_managers
            else ""
        )

        # Queue for real-time shell stdout lines. LangChainService puts raw lines in,
        # drains them while _handle_tool_calls runs, and yields shell_output dicts
        # upstream — we simply forward whatever the generator yields here.
        shell_output_queue: asyncio.Queue = asyncio.Queue()

        full_text = ""
        async for token in self.context_factory.integrations.openai.ask_stream(
            question=content,
            context=enhanced_context,
            previous_messages=conversation_history,
            profile=conversation.profile,
            conversation_id=conversation_id,
            shell_output_queue=shell_output_queue,
            client_workspace=client_workspace,
            plan_mode=plan_mode,
            has_pty=has_pty,
        ):
            # dict tokens (shell_output, etc.) are forwarded as-is; only str
            # tokens contribute to the persisted assistant message text.
            yield token
            if isinstance(token, str):
                full_text += token

        # Generate audio if TTS is enabled for this profile
        audio_url = await self._generate_audio_if_enabled(
            has_text_to_voice=None,
            text=full_text,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if audio_url:
            yield {"type": "audio", "url": audio_url}

        assistant_message = self._create_assistant_message(content=full_text, audio_url=audio_url)
        self._add_message_to_conversation(conversation, assistant_message)
        self._save_messages(conversation_id, conversation.messages)

    def _inject_skill_context(self, message_context: Optional[str], user_query: str = "") -> str:
        """
        Inject skill context (general.skill.md + faqs.skill.md) into message context.
        When a user_query is provided, also searches memory for relevant snippets and
        appends them so the LLM gets targeted knowledge for the current question.

        Args:
            message_context: Original message context
            user_query: User's message text used to search memory for relevant snippets

        Returns:
            Enhanced context with skill knowledge prepended (or original if unavailable)
        """
        if not self.context_factory.platform_managers:
            return message_context

        if not self.context_factory.platform_managers.skill_manager:
            return message_context

        try:
            skill_manager = self.context_factory.platform_managers.skill_manager
            skill_context = skill_manager.get_base_context()

            if not skill_context:
                return message_context

            enhanced_context = f"{skill_context}\n\n{message_context}" if message_context else skill_context

            if user_query:
                search_results = skill_manager.search_memory(user_query)
                no_results_msg = "No se encontraron resultados relevantes en la memoria"
                if search_results and no_results_msg not in search_results:
                    enhanced_context = f"{enhanced_context}\n\n=== RELEVANT CONTEXT FOR THIS QUERY ===\n{search_results}"
                    logger.info("Skill search results injected for query")

            logger.info("Skill context injected into message context")
            return enhanced_context

        except Exception as e:
            logger.warning(f"Error getting skill context, continuing without it: {e}")
            return message_context

    async def _generate_ai_response_fallback(
        self,
        user_message: Message,
        conversation,
        message_context: Optional[str],
        client_workspace: str = "",
    ) -> str:
        """
        Fallback method for generating AI response without platform services.

        Args:
            user_message: User's message
            conversation: Conversation object
            message_context: Optional message context
            client_workspace: Optional client workspace path

        Returns:
            Generated AI response text
        """
        try:
            enhanced_context = self._inject_skill_context(message_context)

            conversation_history = " - ".join([
                f"{msg.sender}: {msg.content}"
                for msg in conversation.messages
            ])

            response = await self.context_factory.integrations.openai.ask(
                user_message.content,
                enhanced_context,
                conversation_history,
                conversation.profile,
                client_workspace=client_workspace,
            )

            return response

        except Exception as e:
            logger.error(f"Error in fallback AI response: {e}")
            return self._get_fallback_error_message(conversation.profile)

    async def _process_images_if_enabled(
        self,
        has_image_processor: Optional[str],
        user_message: Message,
        conversation,
        message_context: Optional[str]
    ) -> Optional[str]:
        """
        Processes images if image processor is enabled.

        Args:
            has_image_processor: Flag to enable image processing
            user_message: User's message
            conversation: Conversation object
            message_context: Optional message context

        Returns:
            Formatted images string or None
        """
        if has_image_processor != "activate":
            return None

        if not self.context_factory.platform_managers:
            logger.warning("Platform services not available, skipping image processing")
            return None

        try:
            logger.info("Image processing activated")

            conversation_history = self.context_factory.platform_managers.message_history.convert_messages_to_string(
                conversation.messages[-20:]
            )

            formatted_images = await self.context_factory.platform_managers.image_processing.search_and_format_images(
                user_message=user_message.content,
                profile=conversation.profile,
                message_context=message_context,
                conversation_history=conversation_history
            )

            return formatted_images

        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return None

    async def _generate_audio_if_enabled(
        self,
        has_text_to_voice: Optional[str],
        text: str,
        user_id: str,
        conversation_id: str
    ) -> Optional[str]:
        """
        Generates audio if text-to-voice is enabled.

        Args:
            has_text_to_voice: Flag to enable text-to-speech
            text: Text to convert to speech
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            Audio URL or None
        """
        tts_active = has_text_to_voice == "activate"

        if not tts_active:
            try:
                profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
                if profile and profile.tts_enabled:
                    tts_active = True
            except Exception:
                pass

        if not tts_active:
            return None

        if not self.context_factory.platform_managers:
            logger.warning("Platform services not available, skipping audio generation")
            return None

        try:
            logger.info("Generating audio response...")

            _tts_lang = "en"
            try:
                _tts_profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
                if _tts_profile and getattr(_tts_profile, "response_language", None):
                    _tts_lang = _tts_profile.response_language
            except Exception:
                pass
            audio_url = await self.context_factory.platform_managers.text_to_speech.generate_and_store_audio(
                text=text,
                user_id=user_id,
                conversation_id=conversation_id,
                language=_tts_lang,
            )

            return audio_url

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None

    async def compact_now(self, conversation_id: str, user_id: str) -> dict:
        """Force-compact the conversation immediately, regardless of message count."""
        conversation = self._get_and_validate_conversation(conversation_id, user_id)

        keep_recent = int(os.environ.get("COMPACTION_KEEP_RECENT", "20"))
        messages_to_summarize = conversation.messages[:-keep_recent] if len(conversation.messages) > keep_recent else conversation.messages
        non_summary = [m for m in messages_to_summarize if m.sender != SenderEnum.summary]

        if not non_summary:
            return {"compacted": False, "reason": "No hay mensajes para compactar"}

        summary_text = await self._generate_summary(messages_to_summarize)
        if not summary_text:
            return {"compacted": False, "reason": "No se pudo generar el resumen"}

        summary_message = Message(
            content=f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}",
            sender=SenderEnum.summary,
            created_at=datetime.now(timezone.utc),
        )
        recent_messages = conversation.messages[-keep_recent:] if len(conversation.messages) > keep_recent else []
        conversation.messages = [summary_message] + recent_messages
        self._save_messages(conversation_id, conversation.messages)

        logger.info(f"Manual compaction: {len(messages_to_summarize)} messages → 1 summary")
        return {"compacted": True, "summarized": len(messages_to_summarize)}

    async def _compact_if_needed(
        self,
        conversation,
        conversation_id: str,
    ) -> Optional[dict]:
        """
        Compacts the conversation when it exceeds the configured threshold.

        The method mutates ``conversation.messages`` in-place and persists the
        updated list to the database.  It returns a compaction SSE event dict
        when compaction was performed, or ``None`` when it was not needed.

        The compaction algorithm:
        1. Keep the most recent ``keep_recent`` messages untouched.
        2. From the older messages, filter out any that are already summaries
           (to avoid re-summarising summaries).
        3. Call OpenAI for a concise summary of those older messages.
        4. Replace the older messages with a single summary ``Message``.
        5. Persist the compacted message list before returning.

        Args:
            conversation: The ``Conversation`` domain object (mutated in-place).
            conversation_id: Identifier used for the database update.

        Returns:
            A compaction SSE event dict if compaction occurred, else ``None``.
        """
        threshold = int(os.environ.get("COMPACTION_THRESHOLD", "40"))
        keep_recent = int(os.environ.get("COMPACTION_KEEP_RECENT", "20"))

        if len(conversation.messages) <= threshold:
            return None

        messages_to_summarize = conversation.messages[:-keep_recent]
        recent_messages = conversation.messages[-keep_recent:]

        non_summary = [
            m for m in messages_to_summarize
            if m.sender != SenderEnum.summary
        ]
        if not non_summary:
            # All older messages are already summaries — nothing to compact.
            return None

        summary_text = await self._generate_summary(messages_to_summarize)
        if not summary_text:
            # Summarisation failed; continue without compacting so the normal
            # flow is never broken.
            return None

        summary_message = Message(
            content=f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}",
            sender=SenderEnum.summary,
            created_at=datetime.now(timezone.utc),
        )

        conversation.messages = [summary_message] + recent_messages

        self._save_messages(conversation_id, conversation.messages)

        logger.info(
            f"Conversation {conversation_id} compacted: "
            f"{len(messages_to_summarize)} messages condensed into 1 summary"
        )

        return {
            "type": "compaction",
            "message": "Conversación compactada para optimizar el contexto",
        }

    async def _generate_summary(self, messages: list) -> str:
        """
        Generates a concise summary of ``messages`` using OpenAI.

        Only ``user`` and ``assistant`` messages contribute to the summary
        input; existing ``summary`` messages are presented as-is under their
        own label so their context is preserved without duplication.

        Args:
            messages: The messages to summarise.

        Returns:
            The generated summary text, or an empty string on failure.
        """
        _SUMMARIZABLE = {SenderEnum.user, SenderEnum.assistant, SenderEnum.summary}

        history_lines = []
        for m in messages:
            if m.sender not in _SUMMARIZABLE or not m.content:
                continue
            label = m.sender.value.upper()
            snippet = m.content[:500]
            history_lines.append(f"{label}: {snippet}")

        if not history_lines:
            return ""

        history_text = "\n".join(history_lines)

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
        user_prompt = (
            "Summarize this conversation:\n\n"
            f"{history_text}"
        )

        try:
            summary = await self.context_factory.integrations.openai.simple_completion(
                system=system_prompt,
                user=user_prompt,
            )
            return summary
        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {e}")
            return ""

    def _save_messages(self, conversation_id: str, messages: list[Message]) -> None:
        """
        Persists messages to the database.

        Args:
            conversation_id: ID of the conversation
            messages: List of messages to save
        """
        self.context_factory.repositories.conversation.update_messages_by_id(
            conversation_id,
            messages,
        )

    def _get_fallback_error_message(self, profile) -> str:
        """
        Returns a friendly fallback error message.

        Args:
            profile: User profile

        Returns:
            Friendly error message
        """
        assistant_name = getattr(profile, "assistant_name", "Asistente")
        return (
            f"¡Hola! Soy {assistant_name} 😊 Disculpa, estoy teniendo algunos "
            f"problemas técnicos en este momento. ¿Podrías intentarlo de nuevo "
            f"en unos minutos?"
        )
