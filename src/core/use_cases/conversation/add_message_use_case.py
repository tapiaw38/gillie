import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.schemas import MessageInput, MessageListOutput
from src.core.domain import Message, SenderEnum
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import (
    ConversationGetNotFoundError,
    ConversationMessageValidationError,
)
from src.core.platform.errors.mappings.common import ForbiddenError
from src.core.use_cases.conversation.compact_use_case import CompactConversationUseCase

logger = logging.getLogger(__name__)

_LANG_MAP = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-BR"}


class AddMessageUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

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
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)

        enhanced_content = await self._process_voice_content(message, profile, context)

        if message.voice_content and not enhanced_content.strip():
            logger.warning("Voice content provided but transcription returned no text — skipping")
            conversation = await self._get_and_validate_conversation(conversation_id, user_id, context)
            return MessageListOutput.from_output(conversation.messages)

        user_message = self._create_user_message(enhanced_content, sender)
        conversation = await self._get_and_validate_conversation(conversation_id, user_id, context)

        compact_uc = CompactConversationUseCase(self.context_factory)
        await compact_uc.compact_if_needed(conversation, conversation_id, context)

        self._add_message_to_conversation(conversation, user_message)

        default_message, ai_response_text = await self._generate_ai_response(
            user_message=user_message,
            conversation=conversation,
            message_context=message.context,
            auth_token=auth_token,
            client_workspace=client_workspace,
            context=context,
        )

        if default_message:
            self._add_message_to_conversation(conversation, self._create_assistant_message(default_message))

        formatted_images = await self._process_images_if_enabled(
            has_image_processor=has_image_processor,
            user_message=user_message,
            conversation=conversation,
            message_context=message.context,
            context=context,
        )

        audio_url = await self._generate_audio_if_enabled(
            has_text_to_voice=has_text_to_voice,
            text=ai_response_text,
            profile=profile,
            user_id=user_id,
            conversation_id=conversation_id,
            context=context,
        )

        assistant_message = self._create_assistant_message(content=ai_response_text, audio_url=audio_url)
        if formatted_images:
            assistant_message.content = f"{ai_response_text}\n\n{formatted_images}"

        self._add_message_to_conversation(conversation, assistant_message)
        await context.repositories.conversation.update_messages_by_id(conversation_id, conversation.messages)

        return MessageListOutput.from_output(conversation.messages)

    async def execute_stream(
        self,
        conversation_id: str,
        content: str,
        user_id: str,
        client_workspace: str = "",
        plan_mode: bool = False,
    ):
        """Streaming variant for CLI. Yields str tokens, shell_output dicts, and audio dicts."""
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)
        conversation = await self._get_and_validate_conversation(conversation_id, user_id, context)

        compact_uc = CompactConversationUseCase(self.context_factory)
        compaction_event = await compact_uc.compact_if_needed(conversation, conversation_id, context)
        if compaction_event:
            yield compaction_event

        user_message = self._create_user_message(content, SenderEnum.user)
        self._add_message_to_conversation(conversation, user_message)

        enhanced_context = self._inject_skill_context(None, content, context)
        conversation_history = (
            context.platform_managers.message_history.convert_messages_to_string(conversation.messages[-20:])
            if context.platform_managers
            else ""
        )

        shell_output_queue: asyncio.Queue = asyncio.Queue()

        full_text = ""
        async for token in context.integrations.openai.ask_stream(
            question=content,
            context=enhanced_context,
            previous_messages=conversation_history,
            profile=conversation.profile,
            conversation_id=conversation_id,
            shell_output_queue=shell_output_queue,
            client_workspace=client_workspace,
            plan_mode=plan_mode,
        ):
            yield token
            if isinstance(token, str):
                full_text += token

        audio_url = await self._generate_audio_if_enabled(
            has_text_to_voice=None,
            text=full_text,
            profile=profile,
            user_id=user_id,
            conversation_id=conversation_id,
            context=context,
        )

        if audio_url:
            yield {"type": "audio", "url": audio_url}

        assistant_message = self._create_assistant_message(content=full_text, audio_url=audio_url)
        self._add_message_to_conversation(conversation, assistant_message)
        await context.repositories.conversation.update_messages_by_id(conversation_id, conversation.messages)

    async def _get_and_validate_conversation(self, conversation_id: str, user_id: str, context):
        conversation = await context.repositories.conversation.find_by_id(conversation_id)
        if not conversation:
            raise NewApplicationError(ConversationGetNotFoundError)
        if user_id != conversation.profile.user_id:
            raise NewApplicationError(ForbiddenError)

        full_profile = await context.repositories.profile.find_by_id(conversation.profile.id)
        if full_profile:
            conversation.profile = full_profile

        if not hasattr(conversation, "messages") or conversation.messages is None:
            conversation.messages = []
        return conversation

    def _create_user_message(self, content: str, sender: SenderEnum) -> Message:
        return Message(content=content, sender=sender, created_at=datetime.now(timezone.utc))

    def _create_assistant_message(self, content: str, audio_url: Optional[str] = None) -> Message:
        return Message(content=content, audio_url=audio_url, sender="assistant", created_at=datetime.now(timezone.utc))

    def _add_message_to_conversation(self, conversation, message: Message) -> None:
        if any(msg.id == message.id for msg in conversation.messages):
            raise NewApplicationError(ConversationMessageValidationError)
        conversation.messages.append(message)

    async def _process_voice_content(self, message: MessageInput, profile, context) -> str:
        if not message.voice_content:
            return message.content
        if not context.platform_managers:
            return message.content
        try:
            lang = getattr(profile, "response_language", "en") or "en"
            stt_lang = _LANG_MAP.get(lang, "en-US")
            transcription = await context.platform_managers.voice_transcription.transcribe_audio_file(
                audio_file=message.voice_content,
                language=stt_lang,
            )
            if transcription:
                return context.platform_managers.voice_transcription.enhance_message_with_transcription(
                    original_message=message.content,
                    transcription=transcription,
                )
        except Exception as e:
            logger.error(f"Error processing voice content: {e}")
        return message.content

    async def _generate_ai_response(
        self,
        user_message: Message,
        conversation,
        message_context: Optional[str],
        auth_token: Optional[str],
        client_workspace: str,
        context,
    ) -> Tuple[Optional[str], str]:
        if not context.platform_managers:
            return (None, await self._generate_ai_response_fallback(
                user_message, conversation, message_context, client_workspace, context
            ))
        try:
            enhanced_context = self._inject_skill_context(message_context, user_message.content, context)
            chat_history = context.platform_managers.message_history.build_chat_history(
                messages=conversation.messages, max_messages=20
            )
            conversation_history = context.platform_managers.message_history.convert_messages_to_string(
                conversation.messages[-20:]
            )
            return await context.platform_managers.ai_response.generate_response(
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

    async def _generate_ai_response_fallback(
        self, user_message: Message, conversation, message_context: Optional[str],
        client_workspace: str, context,
    ) -> str:
        try:
            enhanced_context = self._inject_skill_context(message_context, context=context)
            conversation_history = " - ".join(
                f"{msg.sender}: {msg.content}" for msg in conversation.messages
            )
            return await context.integrations.openai.ask(
                user_message.content, enhanced_context, conversation_history,
                conversation.profile, client_workspace=client_workspace,
            )
        except Exception as e:
            logger.error(f"Error in fallback AI response: {e}")
            return self._get_fallback_error_message(conversation.profile)

    def _inject_skill_context(self, message_context: Optional[str], user_query: str = "", context=None) -> str:
        if not context or not context.platform_managers:
            return message_context
        skill_manager = getattr(context.platform_managers, "skill_manager", None)
        if not skill_manager:
            return message_context
        try:
            skill_context = skill_manager.get_base_context()
            if not skill_context:
                return message_context
            enhanced = f"{skill_context}\n\n{message_context}" if message_context else skill_context
            if user_query:
                results = skill_manager.search_memory(user_query)
                if results and "No se encontraron resultados" not in results:
                    enhanced = f"{enhanced}\n\n=== RELEVANT CONTEXT FOR THIS QUERY ===\n{results}"
            return enhanced
        except Exception as e:
            logger.warning(f"Error getting skill context: {e}")
            return message_context

    async def _process_images_if_enabled(
        self, has_image_processor: Optional[str], user_message: Message,
        conversation, message_context: Optional[str], context,
    ) -> Optional[str]:
        if has_image_processor != "activate" or not context.platform_managers:
            return None
        try:
            conversation_history = context.platform_managers.message_history.convert_messages_to_string(
                conversation.messages[-20:]
            )
            return await context.platform_managers.image_processing.search_and_format_images(
                user_message=user_message.content,
                profile=conversation.profile,
                message_context=message_context,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return None

    async def _generate_audio_if_enabled(
        self, has_text_to_voice: Optional[str], text: str,
        profile, user_id: str, conversation_id: str, context,
    ) -> Optional[str]:
        tts_active = has_text_to_voice == "activate" or (
            profile and getattr(profile, "tts_enabled", False)
        )
        if not tts_active or not context.platform_managers:
            return None
        try:
            lang = getattr(profile, "response_language", "en") or "en"
            return await context.platform_managers.text_to_speech.generate_and_store_audio(
                text=text, user_id=user_id, conversation_id=conversation_id, language=lang,
            )
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None

    def _get_fallback_error_message(self, profile) -> str:
        name = getattr(profile, "assistant_name", "Asistente")
        return (
            f"¡Hola! Soy {name} 😊 Disculpa, estoy teniendo algunos "
            f"problemas técnicos en este momento. ¿Podrías intentarlo de nuevo en unos minutos?"
        )
