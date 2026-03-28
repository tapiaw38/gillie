"""
Voice Transcription Service

This service handles voice-to-text transcription operations,
following the Single Responsibility Principle by focusing
solely on audio transcription concerns.

Responsibilities:
- Transcribe audio content to text
- Handle different audio formats
- Manage transcription errors gracefully
"""

import logging
from typing import Optional, Dict, Any
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class VoiceTranscriptionService:
    """
    Service for converting voice content to text using Speech-to-Text integration.

    This service encapsulates all voice transcription logic, making it
    reusable and testable independently of use cases.
    """

    def __init__(self, stt_integration):
        """
        Initialize the voice transcription service.

        Args:
            stt_integration: Speech-to-Text integration instance
        """
        self.stt_integration = stt_integration

    async def transcribe_audio_file(
        self,
        audio_file: UploadFile,
        language: str = "en-US",
        model: str = "base"
    ) -> Optional[str]:
        """
        Transcribes an audio file to text.

        Args:
            audio_file: The uploaded audio file to transcribe
            language: Language code for transcription (default: Spanish)
            model: STT model to use (default: base)

        Returns:
            Transcribed text or None if transcription fails
        """
        try:
            logger.info(f"Starting audio transcription for file: {audio_file.filename}")

            # Read the audio file content
            audio_content = await audio_file.read()

            # Extract audio format from filename
            audio_format = self._extract_audio_format(audio_file.filename)

            # Perform transcription
            transcription_result = await self._perform_transcription(
                audio_bytes=audio_content,
                audio_format=audio_format,
                language=language,
                model=model
            )

            return transcription_result

        except Exception as e:
            logger.error(f"Error during audio transcription: {e}")
            return None

    async def _perform_transcription(
        self,
        audio_bytes: bytes,
        audio_format: str,
        language: str,
        model: str
    ) -> Optional[str]:
        """
        Performs the actual transcription using the STT integration.

        Args:
            audio_bytes: Raw audio data
            audio_format: Audio file format (wav, mp3, etc.)
            language: Language code for transcription
            model: STT model to use

        Returns:
            Transcribed text or None if transcription fails
        """
        try:
            settings = {
                "language": language,
                "model": model,
            }

            stt_result = await self.stt_integration.audio_bytes_to_text(
                audio_bytes=audio_bytes,
                audio_format=audio_format,
                settings=settings
            )

            if stt_result.get("success", False) and stt_result.get("text", "").strip():
                transcribed_text = stt_result["text"].strip()
                logger.info(
                    f"Transcription successful: '{transcribed_text[:100]}...'"
                )
                return transcribed_text
            else:
                error_msg = stt_result.get("error", "Unknown error")
                logger.warning(f"Transcription failed: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"Error in transcription process: {e}")
            return None

    def _extract_audio_format(self, filename: Optional[str]) -> str:
        """
        Extracts audio format from filename.

        Args:
            filename: Name of the audio file

        Returns:
            Audio format extension (default: wav)
        """
        if not filename:
            return "wav"

        parts = filename.split(".")
        if len(parts) > 1:
            return parts[-1].lower()

        return "wav"

    def enhance_message_with_transcription(
        self,
        original_message: str,
        transcription: Optional[str]
    ) -> str:
        """
        Enhances a message with voice transcription context.

        Args:
            original_message: The original text message
            transcription: The voice transcription to add as context

        Returns:
            Enhanced message with voice context
        """
        if not transcription:
            return original_message

        return f"{original_message}\n\n[Contexto de voz]: {transcription}"
