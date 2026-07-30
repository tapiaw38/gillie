"""
Text-to-Speech Service

This service handles text-to-speech conversion and audio storage,
following the Single Responsibility Principle by focusing
solely on TTS and audio management concerns.

Responsibilities:
- Convert text to speech audio
- Upload audio to storage service
- Manage TTS voice selection and settings
"""

import logging
import io
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """
    Service for converting text to speech and managing audio storage.

    This service encapsulates all TTS-related operations, making it
    reusable and testable independently of use cases.
    """

    def __init__(self, tts_integration, store_service):
        """
        Initialize the text-to-speech service.

        Args:
            tts_integration: Text-to-Speech integration instance
            store_service: Storage service for uploading audio files
        """
        self.tts_integration = tts_integration
        self.store_service = store_service

    async def generate_and_store_audio(
        self,
        text: str,
        user_id: str,
        conversation_id: str,
        settings: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> Optional[str]:
        """
        Generates audio from text and stores it in S3.

        Args:
            text: The text to convert to speech
            user_id: ID of the user
            conversation_id: ID of the conversation
            settings: Optional TTS settings (rate, volume, voice_id)
            language: Language code for TTS (en or es)

        Returns:
            URL of the stored audio file or None if generation fails
        """
        try:
            logger.info("Starting text-to-speech generation...")

            settings = {**self._get_default_settings(), **(settings or {})}
            settings["language"] = language

            audio_data = await self._generate_audio(text, settings)

            if not audio_data:
                logger.error("Failed to generate audio data")
                return None

            audio_url = await self._upload_audio_to_storage(
                audio_data=audio_data,
                user_id=user_id,
                conversation_id=conversation_id
            )

            logger.info(f"Audio generated and uploaded successfully: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Error in text-to-speech process: {e}")
            return None

    async def _generate_audio(
        self,
        text: str,
        settings: Dict[str, Any]
    ) -> Optional[bytes]:
        """
        Generates audio data from text using TTS integration.

        Args:
            text: The text to convert to speech
            settings: TTS settings

        Returns:
            Audio data as bytes or None if generation fails
        """
        try:
            audio_data = await self.tts_integration.text_to_speech_stream(
                text=text,
                settings=settings
            )
            return audio_data

        except Exception as e:
            logger.error(f"Error generating audio with TTS integration: {e}")
            return None

    async def _upload_audio_to_storage(
        self,
        audio_data: bytes,
        user_id: str,
        conversation_id: str
    ) -> str:
        """
        Uploads audio data to storage service and returns the public URL.

        Args:
            audio_data: Raw audio data
            user_id: ID of the user
            conversation_id: ID of the conversation

        Returns:
            Public URL of the uploaded audio file

        Raises:
            Exception: If upload fails
        """
        try:
            audio_file = io.BytesIO(audio_data)

            filename = self._generate_audio_filename(conversation_id)

            s3_key = self.store_service.put_object(
                file=audio_file,
                user_file=user_id,
                filename=filename,
                size=len(audio_data),
                object_id=conversation_id,
            )

            audio_url = self.store_service.generate_url(s3_key)

            return audio_url

        except Exception as e:
            logger.error(f"Error uploading audio to storage: {e}")
            raise Exception(f"Failed to upload audio: {e}")

    def _generate_audio_filename(self, conversation_id: str) -> str:
        """
        Generates a unique filename for the audio file.

        Args:
            conversation_id: ID of the conversation

        Returns:
            Generated filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"tts_audio_{conversation_id}_{timestamp}.wav"

    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Returns default TTS settings.

        Returns:
            Dictionary with default TTS settings
        """
        return {
            "rate": 150,  # Moderate speech rate
            "volume": 0.8,  # High volume
        }

    async def get_spanish_female_voice_id(self) -> Optional[int]:
        """
        Searches for a female Spanish voice among available voices.

        Returns:
            Voice ID or None if a suitable voice is not found
        """
        try:
            voices = await self.tts_integration.get_available_voices()
            logger.info(f"Available voices found: {len(voices)}")

            if not voices:
                logger.warning("No available voices found")
                return None

            for i, voice in enumerate(voices):
                logger.info(
                    f"Voice {i}: {voice.get('name', 'No name')} - "
                    f"Gender: {voice.get('gender', 'Unknown')} - "
                    f"Languages: {voice.get('languages', [])}"
                )

            spanish_female_voice = self._find_spanish_female_voice(voices)
            if spanish_female_voice:
                return spanish_female_voice

            female_voice = self._find_female_voice(voices)
            if female_voice:
                return female_voice

            logger.warning(
                "No voice matching criteria found, will use system default"
            )
            return None

        except Exception as e:
            logger.error(f"Error while fetching voices: {e}")
            return None

    def _find_spanish_female_voice(self, voices: list) -> Optional[int]:
        """
        Finds a Spanish female voice from the available voices.

        Args:
            voices: List of available voice dictionaries

        Returns:
            Voice ID or None if not found
        """
        spanish_indicators = [
            "spanish", "español", "es_", "es-",
            "helena", "sabina", "monica", "paloma", "carmen"
        ]
        female_indicators = ["female", "mujer", "femenina", "woman"]

        for voice in voices:
            voice_name = voice.get("name", "").lower()
            languages = voice.get("languages", [])
            gender = voice.get("gender", "").lower()

            is_spanish = any(
                indicator in voice_name for indicator in spanish_indicators
            ) or any("es" in str(lang).lower() for lang in languages if lang)

            is_female = gender in ["female", "mujer"] or any(
                indicator in voice_name for indicator in female_indicators
            )

            if is_spanish and is_female:
                logger.info(
                    f"Spanish female voice found: {voice['name']} (ID: {voice['id']})"
                )
                return voice["id"]

        return None

    def _find_female_voice(self, voices: list) -> Optional[int]:
        """
        Finds any female voice from the available voices.

        Args:
            voices: List of available voice dictionaries

        Returns:
            Voice ID or None if not found
        """
        for voice in voices:
            gender = voice.get("gender", "").lower()
            if gender in ["female", "mujer"]:
                logger.info(
                    f"Female voice found: {voice['name']} (ID: {voice['id']})"
                )
                return voice["id"]

        return None
