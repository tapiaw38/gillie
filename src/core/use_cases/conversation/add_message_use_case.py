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

import logging
from datetime import datetime, timezone
from typing import Optional

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
        # Step 1: Process voice content if provided
        enhanced_content = await self._process_voice_content(message)

        # Step 2: Create user message
        user_message = self._create_user_message(enhanced_content, sender)

        # Step 3: Retrieve and validate conversation
        conversation = self._get_and_validate_conversation(
            conversation_id, user_id
        )

        # Step 4: Add user message to conversation
        self._add_message_to_conversation(conversation, user_message)

        # Step 5: Generate AI response
        ai_response_text = await self._generate_ai_response(
            user_message=user_message,
            conversation=conversation,
            message_context=message.context,
            auth_token=auth_token
        )

        # Step 6: Process images if enabled
        formatted_images = await self._process_images_if_enabled(
            has_image_processor=has_image_processor,
            user_message=user_message,
            conversation=conversation,
            message_context=message.context
        )

        # Step 7: Generate audio if enabled
        audio_url = await self._generate_audio_if_enabled(
            has_text_to_voice=has_text_to_voice,
            text=ai_response_text,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Step 8: Create assistant response message
        assistant_message = self._create_assistant_message(
            content=ai_response_text,
            audio_url=audio_url
        )

        # Step 9: Append images to assistant message if available
        if formatted_images:
            assistant_message.content = f"{ai_response_text}\n\n{formatted_images}"

        # Step 10: Add assistant message to conversation
        self._add_message_to_conversation(conversation, assistant_message)

        # Step 11: Persist messages to database
        self._save_messages(conversation_id, conversation.messages)

        # Step 12: Return messages
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

            transcription = await self.context_factory.platform_managers.voice_transcription.transcribe_audio_file(
                audio_file=message.voice_content
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
        auth_token: Optional[str] = None
    ) -> str:
        """
        Generates AI response using the AI response service.

        Args:
            user_message: User's message
            conversation: Conversation object
            message_context: Optional message context

        Returns:
            Generated AI response text
        """
        if not self.context_factory.platform_managers:
            logger.warning("Platform services not available, using fallback")
            return await self._generate_ai_response_fallback(
                user_message, conversation, message_context
            )

        try:
            # Inject skill context BEFORE any AI processing (highest priority)
            enhanced_context = self._inject_skill_context(message_context)

            # Build chat history for function execution
            chat_history = self.context_factory.platform_managers.message_history.build_chat_history(
                messages=conversation.messages,
                max_messages=40
            )

            # Convert messages to string for conversation context (last 40 to avoid processing entire history)
            conversation_history = self.context_factory.platform_managers.message_history.convert_messages_to_string(
                conversation.messages[-40:]
            )

            # Generate response using AI response service
            response = await self.context_factory.platform_managers.ai_response.generate_response(
                user_message=user_message.content,
                profile=conversation.profile,
                message_context=enhanced_context,
                conversation_history=conversation_history,
                chat_history=chat_history,
                auth_token=auth_token
            )

            return response

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_error_message(conversation.profile)

    def _inject_skill_context(self, message_context: Optional[str]) -> str:
        """
        Inject skill context (general.skill.md + faqs.skill.md) into message context.

        Args:
            message_context: Original message context

        Returns:
            Enhanced context with skill knowledge prepended (or original if unavailable)
        """
        if not self.context_factory.platform_managers:
            return message_context

        if not self.context_factory.platform_managers.skill_manager:
            return message_context

        try:
            skill_context = self.context_factory.platform_managers.skill_manager.get_base_context()

            if not skill_context:
                return message_context

            enhanced_context = f"{skill_context}\n\n{message_context}" if message_context else skill_context
            logger.info("Skill context injected into message context")
            return enhanced_context

        except Exception as e:
            logger.warning(f"Error getting skill context, continuing without it: {e}")
            return message_context

    async def _generate_ai_response_fallback(
        self,
        user_message: Message,
        conversation,
        message_context: Optional[str]
    ) -> str:
        """
        Fallback method for generating AI response without platform services.

        Args:
            user_message: User's message
            conversation: Conversation object
            message_context: Optional message context

        Returns:
            Generated AI response text
        """
        try:
            # Inject skill context even in fallback mode
            enhanced_context = self._inject_skill_context(message_context)

            # Manual conversion of messages to string
            conversation_history = " - ".join([
                f"{msg.sender}: {msg.content}"
                for msg in conversation.messages
            ])

            response = await self.context_factory.integrations.openai.ask(
                user_message.content,
                enhanced_context,
                conversation_history,
                conversation.profile
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
                conversation.messages[-40:]
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
        if has_text_to_voice != "activate":
            return None

        if not self.context_factory.platform_managers:
            logger.warning("Platform services not available, skipping audio generation")
            return None

        try:
            logger.info("Generating audio response...")

            audio_url = await self.context_factory.platform_managers.text_to_speech.generate_and_store_audio(
                text=text,
                user_id=user_id,
                conversation_id=conversation_id
            )

            return audio_url

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None

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
