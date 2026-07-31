import asyncio
import io
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.schemas import MessageInput, MessageListOutput
from src.core.domain import Message, SenderEnum, MessageImageAttachment, ImageAnalysis
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.managers.speech_segmentation import split_leading_sentence
from src.core.platform.errors.mappings.conversation import (
    ConversationGetNotFoundError,
    ConversationMessageValidationError,
    ConversationMessageImageUnsupportedFormatError,
    ConversationMessageImageTooLargeError,
    ConversationMessageImageAnalysisError,
)
from src.core.platform.errors.mappings.common import ForbiddenError
from src.core.use_cases.conversation.compact_use_case import CompactConversationUseCase

logger = logging.getLogger(__name__)

_LANG_MAP = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-BR"}

_FILLER_PHRASES = {
    "en": ["Let me check.", "One moment.", "Hang on a second."],
    "es": ["A ver, dejame ver.", "Dame un segundo.", "Ahí voy, un momento."],
    "pt": ["Deixa eu ver.", "Um momento."],
    "fr": ["Laisse-moi voir.", "Un instant."],
    "de": ["Lass mich nachsehen.", "Einen Moment."],
}

_FILLER_WAIT_SECONDS = 0.2
_ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


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
        conversation = await self._get_and_validate_conversation(conversation_id, user_id, context)
        await self._show_avatar(context)
        image_attachments, image_analysis_summary = await self._process_image_content(
            message=message,
            user_id=user_id,
            context=context,
            user_message_content=enhanced_content,
            conversation=conversation,
        )

        if image_analysis_summary:
            if enhanced_content.strip():
                enhanced_content = (
                    f"{enhanced_content.strip()}\n\n"
                    f"[Attached image analysis]\n{image_analysis_summary}"
                )
            else:
                enhanced_content = f"[Attached image analysis]\n{image_analysis_summary}"

        if message.voice_content and not enhanced_content.strip():
            logger.warning("Voice content provided but transcription returned no text — skipping")
            return MessageListOutput.from_output(conversation.messages)

        user_message = self._create_user_message(
            enhanced_content,
            sender,
            image_attachments=image_attachments,
        )
        scoped_message_context = self._build_message_context(message.context, conversation)
        memory_scope_id = self._build_memory_scope_id(conversation)

        compact_uc = CompactConversationUseCase(self.context_factory)
        await compact_uc.compact_if_needed(conversation, conversation_id, context)

        self._add_message_to_conversation(conversation, user_message)

        default_message, ai_response_text = await self._generate_ai_response(
            user_message=user_message,
            conversation=conversation,
            message_context=scoped_message_context,
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
            message_context=scoped_message_context,
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

        self._schedule_memory_extraction(
            user_id=memory_scope_id,
            user_message=user_message.content,
            assistant_response=ai_response_text,
            conversation_id=conversation_id,
            context=context,
            owner_user_id=conversation.profile.user_id,
        )

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
        asyncio.create_task(self._show_avatar(context))

        compact_uc = CompactConversationUseCase(self.context_factory)
        compaction_event = await compact_uc.compact_if_needed(conversation, conversation_id, context)
        if compaction_event:
            yield compaction_event

        memory_scope_id = self._build_memory_scope_id(conversation)

        user_message = self._create_user_message(content, SenderEnum.user)
        self._add_message_to_conversation(conversation, user_message)

        scoped_message_context = self._build_message_context(None, conversation)
        enhanced_context = await self._inject_skill_context(
            scoped_message_context,
            content,
            context,
            user_id=memory_scope_id,
        )
        conversation_history = (
            context.platform_managers.message_history.convert_messages_to_string(conversation.messages[-20:])
            if context.platform_managers
            else ""
        )

        shell_output_queue: asyncio.Queue = asyncio.Queue()

        full_text = ""
        pending_speech = ""
        speech_tasks: list = []
        audio_url = None
        emitted = 0
        speech_enabled = self._tts_active(None, profile) and bool(context.platform_managers)

        def speak(fragment: str) -> None:
            speech_tasks.append(asyncio.create_task(self._generate_audio_if_enabled(
                has_text_to_voice=None, text=fragment, profile=profile,
                user_id=user_id, conversation_id=conversation_id, context=context,
            )))

        filler_spoken = False
        filler_task = None
        if speech_enabled:
            phrase = self._filler_phrase(profile)
            if phrase:
                filler_task = self._filler_task(
                    phrase, profile, user_id, conversation_id, context
                )

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
            if not isinstance(token, str):
                if (
                    speech_enabled
                    and not filler_spoken
                    and isinstance(token, dict)
                    and token.get("type") == "tool_call"
                ):
                    filler_spoken = True
                    filler_url = await self._filler_audio_url(filler_task)
                    if filler_url:
                        yield {"type": "audio", "url": filler_url, "index": -1, "final": False}
                continue
            full_text += token
            if not speech_enabled:
                continue
            pending_speech += token
            sentence, pending_speech = split_leading_sentence(pending_speech)
            if sentence:
                speak(sentence)
            while speech_tasks and speech_tasks[0].done():
                url = self._segment_url(speech_tasks.pop(0))
                if url:
                    audio_url = audio_url or url
                    yield {"type": "audio", "url": url, "index": emitted, "final": False}
                    emitted += 1

        if speech_enabled and pending_speech.strip():
            speak(pending_speech)
        if speech_enabled and not speech_tasks and not emitted and full_text.strip():
            speak(full_text)

        while speech_tasks:
            task = speech_tasks.pop(0)
            try:
                url = await task
            except Exception as e:
                logger.error(f"Error generating streamed audio segment: {e}")
                continue
            if url:
                audio_url = audio_url or url
                yield {"type": "audio", "url": url, "index": emitted, "final": not speech_tasks}
                emitted += 1

        assistant_message = self._create_assistant_message(content=full_text, audio_url=audio_url)
        self._add_message_to_conversation(conversation, assistant_message)
        await context.repositories.conversation.update_messages_by_id(conversation_id, conversation.messages)

        self._schedule_memory_extraction(
            user_id=memory_scope_id,
            user_message=content,
            assistant_response=full_text,
            conversation_id=conversation_id,
            context=context,
            owner_user_id=conversation.profile.user_id,
        )

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

    async def _show_avatar(self, context) -> None:
        mcp = getattr(context.integrations, "mcp", None)
        if mcp is not None:
            await mcp.avatar_control_window("show")

    def _create_user_message(
        self,
        content: str,
        sender: SenderEnum,
        image_attachments: Optional[list[MessageImageAttachment]] = None,
    ) -> Message:
        return Message(
            content=content,
            sender=sender,
            image_attachments=image_attachments,
            created_at=datetime.now(timezone.utc),
        )

    def _create_assistant_message(self, content: str, audio_url: Optional[str] = None) -> Message:
        return Message(content=content, audio_url=audio_url, sender="assistant", created_at=datetime.now(timezone.utc))

    def _add_message_to_conversation(self, conversation, message: Message) -> None:
        if any(msg.id == message.id for msg in conversation.messages):
            raise NewApplicationError(ConversationMessageValidationError)
        conversation.messages.append(message)

    async def transcribe(self, voice_content, user_id: str) -> Optional[str]:
        """Transcribe a recording on its own, so a caller can show the text
        before the reply is generated."""
        context = self.context_factory()
        if not context.platform_managers:
            return None
        profile = await context.repositories.profile.find_by_user_id(user_id)
        lang = (profile.response_language if profile else None) or "en"
        try:
            return await context.platform_managers.voice_transcription.transcribe_audio_file(
                audio_file=voice_content,
                language=_LANG_MAP.get(lang, "en-US"),
            )
        except Exception as e:
            logger.error(f"Error transcribing voice content: {e}")
            return None

    async def _process_voice_content(self, message: MessageInput, profile, context) -> str:
        if not message.voice_content:
            return message.content
        if not context.platform_managers:
            return message.content
        try:
            lang = profile.response_language or "en"
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

    async def _process_image_content(
        self,
        message: MessageInput,
        user_id: str,
        context,
        user_message_content: str,
        conversation,
    ) -> tuple[Optional[list[MessageImageAttachment]], Optional[str]]:
        incoming_images = []
        if message.image_content:
            incoming_images.append(message.image_content)
        if message.image_contents:
            incoming_images.extend(message.image_contents)

        if not incoming_images:
            return None, None

        attachments: list[MessageImageAttachment] = []
        summaries: list[str] = []

        analysis_prompt = self._build_generic_image_context_prompt(user_message_content, conversation)

        for image in incoming_images:
            mime_type = (image.content_type or "").lower()
            if mime_type not in _ALLOWED_IMAGE_MIME_TYPES:
                raise NewApplicationError(ConversationMessageImageUnsupportedFormatError)

            image_bytes = await image.read()
            if not image_bytes:
                raise NewApplicationError(ConversationMessageValidationError)
            if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
                raise NewApplicationError(ConversationMessageImageTooLargeError)

            ext = os.path.splitext(image.filename or "")[1] or self._mime_to_extension(mime_type)
            object_id = str(uuid.uuid4())

            try:
                storage_key = context.store_service.put_object(
                    file=io.BytesIO(image_bytes),
                    user_file=user_id,
                    filename=image.filename or f"message-image{ext}",
                    size=len(image_bytes),
                    object_id=object_id,
                )
                url = context.store_service.generate_url(storage_key)
            except Exception as exc:
                logger.error(f"Error uploading message image: {exc}")
                raise NewApplicationError(ConversationMessageImageAnalysisError, exc)

            try:
                analysis = await context.integrations.openai.analyze_uploaded_image(
                    image_bytes=image_bytes,
                    prompt=analysis_prompt,
                )
            except Exception as exc:
                logger.error(f"Error analyzing uploaded image: {exc}")
                raise NewApplicationError(ConversationMessageImageAnalysisError, exc)

            summary = (analysis or {}).get("summary", "")
            prompt = (analysis or {}).get("prompt")
            parsed = self._parse_image_analysis(summary)
            if summary:
                summaries.append(summary)

            attachments.append(
                MessageImageAttachment(
                    name=image.filename or f"message-image{ext}",
                    mime_type=mime_type,
                    size=len(image_bytes),
                    storage_key=storage_key,
                    url=url,
                    analysis=ImageAnalysis(
                        summary=summary,
                        prompt=prompt,
                        extracted_text=parsed.get("extracted_text"),
                        key_findings=parsed.get("key_findings"),
                        response_context=parsed.get("response_context"),
                    ),
                )
            )

        combined_summary = "\n\n".join(summaries) if summaries else None
        return attachments, combined_summary

    def _build_generic_image_context_prompt(self, user_message_content: str, conversation) -> str:
        contact_context = self._contact_context_string(conversation)
        return (
            "Analyze this image as conversation context. "
            "Return concise structured output with the following labels:\n"
            "TEXT_FOUND: exact visible text transcription if any.\n"
            "KEY_FINDINGS: relevant visual findings.\n"
            "RESPONSE_CONTEXT: what should be used to answer the user.\n\n"
            f"Conversation scope: {contact_context}\n"
            f"User message: {user_message_content or 'No additional user message provided.'}"
        )

    def _build_message_context(self, message_context: Optional[str], conversation) -> str:
        contact_context = self._contact_context_string(conversation)
        owner_contacts = len(getattr(conversation.profile, "contacts", None) or [])
        scoped = (
            f"Conversation scope: {contact_context}\n"
            f"Owner contacts count: {owner_contacts}\n"
            "If the user asks about contacts or memories, answer using this owner context first."
        )
        if message_context:
            return f"{scoped}\n\n{message_context}"
        return scoped

    def _contact_context_string(self, conversation) -> str:
        if getattr(conversation, "contact_id", None):
            contact_name = getattr(conversation, "contact_name", None) or "unknown-contact"
            return f"contact_id={conversation.contact_id}, contact_name={contact_name}"
        return "owner-direct-conversation"

    def _build_memory_scope_id(self, conversation) -> str:
        owner_user_id = (getattr(conversation.profile, "user_id", None) or "").strip()
        if not owner_user_id:
            return "owner__unknown"
        contact_id = (getattr(conversation, "contact_id", None) or "").strip()
        if contact_id:
            return f"{owner_user_id}__contact__{contact_id}"
        return f"{owner_user_id}__owner"

    def _parse_image_analysis(self, summary: str) -> dict[str, Optional[str]]:
        if not summary:
            return {"extracted_text": None, "key_findings": None, "response_context": None}

        parsed = {"extracted_text": None, "key_findings": None, "response_context": None}
        lines = summary.splitlines()
        for line in lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = key.strip().upper()
            text_value = value.strip() or None
            if normalized_key == "TEXT_FOUND":
                parsed["extracted_text"] = text_value
            elif normalized_key == "KEY_FINDINGS":
                parsed["key_findings"] = text_value
            elif normalized_key == "RESPONSE_CONTEXT":
                parsed["response_context"] = text_value
        return parsed

    def _mime_to_extension(self, mime_type: str) -> str:
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        return mapping.get(mime_type, ".img")

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
            memory_scope_id = self._build_memory_scope_id(conversation)
            enhanced_context = await self._inject_skill_context(
                message_context,
                user_message.content,
                context,
                user_id=memory_scope_id,
            )
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
            enhanced_context = await self._inject_skill_context(
                message_context,
                user_message.content,
                context,
                user_id=self._build_memory_scope_id(conversation),
            )
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

    async def _inject_skill_context(
        self,
        message_context: Optional[str],
        user_query: str = "",
        context=None,
        user_id: str = "",
    ) -> str:
        if not context or not context.platform_managers:
            return message_context
        skill_manager = getattr(context.platform_managers, "skill_manager", None)
        enhanced = message_context
        if skill_manager:
            try:
                skill_context = skill_manager.get_base_context()
                if skill_context:
                    enhanced = f"{skill_context}\n\n{message_context}" if message_context else skill_context
                    if user_query:
                        results = skill_manager.search_memory(user_query)
                        if results and "No se encontraron resultados" not in results:
                            enhanced = f"{enhanced}\n\n=== RELEVANT CONTEXT FOR THIS QUERY ===\n{results}"
            except Exception as e:
                logger.warning(f"Error getting skill context: {e}")

        brain = getattr(context.platform_managers, "brain", None)
        if brain and user_id and user_query:
            try:
                enhanced = await brain.working_memory.assemble(
                    user_id=user_id,
                    query=user_query,
                    skill_context=enhanced,
                )
            except Exception as e:
                logger.warning(f"Error assembling working memory: {e}")

        return enhanced

    def _schedule_memory_extraction(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        conversation_id: str,
        context,
        owner_user_id: Optional[str] = None,
    ) -> None:
        brain = getattr(context.platform_managers, "brain", None) if context.platform_managers else None
        if not brain:
            return
        asyncio.create_task(
            brain.memory_writer.extract_and_store(
                user_id=user_id,
                user_message=user_message,
                assistant_response=assistant_response,
                conversation_id=conversation_id,
                owner_user_id=owner_user_id,
                memory_scope_id=user_id,
            )
        )

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

    @staticmethod
    def _tts_active(has_text_to_voice: Optional[str], profile) -> bool:
        return has_text_to_voice == "activate" or bool(
            profile and getattr(profile, "tts_enabled", False)
        )

    @staticmethod
    def _segment_url(task) -> Optional[str]:
        try:
            return task.result()
        except Exception as e:
            logger.error(f"Error generating streamed audio segment: {e}")
            return None

    def _filler_task(
        self, phrase: str, profile, user_id: str, conversation_id: str, context,
    ):
        """Start synthesis of a fixed phrase, reusing the cached clip if any."""
        lang = (profile.response_language if profile else None) or "en"
        overrides = {
            key: value
            for key, value in (
                ("voice", getattr(profile, "tts_voice", None)),
                ("engine", getattr(profile, "tts_engine", None)),
            )
            if value
        }
        task = asyncio.create_task(
            context.platform_managers.text_to_speech.generate_and_store_cached_audio(
                text=phrase, user_id=user_id, conversation_id=conversation_id,
                language=lang, settings=overrides or None,
            )
        )
        task.add_done_callback(lambda finished: finished.exception())
        return task

    @staticmethod
    def _filler_phrase(profile) -> Optional[str]:
        lang = (profile.response_language if profile else None) or "en"
        phrases = _FILLER_PHRASES.get(lang)
        return random.choice(phrases) if phrases else None

    async def _filler_audio_url(self, task) -> Optional[str]:
        """Return the filler clip only if it is ready, never waiting on it.

        Synthesizing on the spot would add the very delay the clip exists to
        hide, so a warm-up task is started when the turn begins and this only
        collects it.
        """
        if task is None:
            return None
        done, _ = await asyncio.wait({task}, timeout=_FILLER_WAIT_SECONDS)
        if task not in done:
            return None
        try:
            return task.result()
        except Exception as e:
            logger.error(f"Error generating filler audio: {e}")
            return None

    async def _generate_audio_if_enabled(
        self, has_text_to_voice: Optional[str], text: str,
        profile, user_id: str, conversation_id: str, context,
    ) -> Optional[str]:
        if not self._tts_active(has_text_to_voice, profile) or not context.platform_managers:
            return None
        try:
            lang = profile.response_language or "en"
            overrides = {
                key: value
                for key, value in (
                    ("voice", getattr(profile, "tts_voice", None)),
                    ("engine", getattr(profile, "tts_engine", None)),
                )
                if value
            }
            return await context.platform_managers.text_to_speech.generate_and_store_audio(
                text=text, user_id=user_id, conversation_id=conversation_id, language=lang,
                settings=overrides or None,
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
