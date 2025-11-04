"""
Platform Services Container

This module provides a container for all platform services,
implementing the Dependency Inversion Principle by centralizing
service instantiation and management.

This follows the Factory pattern and allows easy service injection
into use cases.
"""

from src.core.platform.services.voice_transcription_service import VoiceTranscriptionService
from src.core.platform.services.text_to_speech_service import TextToSpeechService
from src.core.platform.services.image_processing_service import ImageProcessingService
from src.core.platform.services.ai_response_service import AIResponseService
from src.core.platform.services.message_history_service import MessageHistoryService
from src.core.platform.managers.faq_context_manager import FAQContextManager


class PlatformServices:
    """
    Container for all platform services.

    This class provides centralized access to all platform services,
    making dependency injection cleaner and more maintainable.
    """

    def __init__(
        self,
        voice_transcription: VoiceTranscriptionService,
        text_to_speech: TextToSpeechService,
        image_processing: ImageProcessingService,
        ai_response: AIResponseService,
        message_history: MessageHistoryService,
        faq_context: FAQContextManager = None
    ):
        """
        Initialize platform services container.

        Args:
            voice_transcription: Voice transcription service
            text_to_speech: Text-to-speech service
            image_processing: Image processing service
            ai_response: AI response service
            message_history: Message history service
            faq_context: FAQ context manager (optional)
        """
        self.voice_transcription = voice_transcription
        self.text_to_speech = text_to_speech
        self.image_processing = image_processing
        self.ai_response = ai_response
        self.message_history = message_history
        self.faq_context = faq_context

    @staticmethod
    def create_services(integrations, store_service, config_service, faq_repository=None) -> "PlatformServices":
        """
        Factory method to create all platform services.

        This static method instantiates all services with their dependencies,
        following the Factory pattern for centralized object creation.

        Args:
            integrations: Integrations instance (OpenAI, TTS, STT)
            store_service: Storage service instance
            config_service: Configuration service instance
            faq_repository: Optional FAQ repository for FAQ context injection

        Returns:
            PlatformServices instance with all services initialized
        """
        voice_transcription = VoiceTranscriptionService(
            stt_integration=integrations.stt
        )

        text_to_speech = TextToSpeechService(
            tts_integration=integrations.tts,
            store_service=store_service
        )

        image_processing = ImageProcessingService(
            openai_integration=integrations.openai
        )

        faq_context_manager = None
        if faq_repository:
            faq_context_manager = FAQContextManager(faq_repository=faq_repository)

        mcp_client = getattr(integrations, 'mcp', None)

        ai_response = AIResponseService(
            openai_integration=integrations.openai,
            config_service=config_service,
            faq_context_manager=faq_context_manager,
            mcp_client=mcp_client
        )

        message_history = MessageHistoryService()

        return PlatformServices(
            voice_transcription=voice_transcription,
            text_to_speech=text_to_speech,
            image_processing=image_processing,
            ai_response=ai_response,
            message_history=message_history,
            faq_context=faq_context_manager
        )
