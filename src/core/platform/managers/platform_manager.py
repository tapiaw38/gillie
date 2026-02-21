"""
Platform Services Container

This module provides a container for all platform services,
implementing the Dependency Inversion Principle by centralizing
service instantiation and management.
"""

from src.core.platform.services.voice_transcription_service import VoiceTranscriptionService
from src.core.platform.services.text_to_speech_service import TextToSpeechService
from src.core.platform.services.image_processing_service import ImageProcessingService
from src.core.platform.services.ai_response_service import AIResponseService
from src.core.platform.services.message_history_service import MessageHistoryService
from src.core.platform.managers.skill_manager import SkillManager


class PlatformServices:
    def __init__(
        self,
        voice_transcription: VoiceTranscriptionService,
        text_to_speech: TextToSpeechService,
        image_processing: ImageProcessingService,
        ai_response: AIResponseService,
        message_history: MessageHistoryService,
        skill_manager: SkillManager = None,
    ):
        self.voice_transcription = voice_transcription
        self.text_to_speech = text_to_speech
        self.image_processing = image_processing
        self.ai_response = ai_response
        self.message_history = message_history
        self.skill_manager = skill_manager

    @staticmethod
    def create_services(integrations, store_service, config_service, skill_manager: SkillManager = None) -> "PlatformServices":
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

        mcp_client = getattr(integrations, 'mcp', None)

        ai_response = AIResponseService(
            openai_integration=integrations.openai,
            config_service=config_service,
            mcp_client=mcp_client
        )

        message_history = MessageHistoryService()

        return PlatformServices(
            voice_transcription=voice_transcription,
            text_to_speech=text_to_speech,
            image_processing=image_processing,
            ai_response=ai_response,
            message_history=message_history,
            skill_manager=skill_manager,
        )
