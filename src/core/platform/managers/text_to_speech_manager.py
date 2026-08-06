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

import asyncio
import logging
import io
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

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
        self._phrase_cache: Dict[tuple, str] = {}

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
        logger.info("Starting text-to-speech generation...")

        settings = {**self._get_default_settings(), **(settings or {})}
        settings["language"] = language

        for attempt in (1, 2):
            try:
                audio_data = await self._generate_audio(text, settings)
                if audio_data is None:
                    return None
                if not audio_data:
                    raise RuntimeError("TTS returned empty audio data")

                audio_url = await self._upload_audio_to_storage(
                    audio_data=audio_data,
                    user_id=user_id,
                    conversation_id=conversation_id
                )

                logger.info(f"Audio generated and uploaded successfully: {audio_url}")
                return audio_url

            except Exception as e:
                logger.error(f"Text-to-speech attempt {attempt}/2 failed: {e}")
                if attempt == 2:
                    logger.error(f"Dropping speech segment after 2 attempts: {text[:60]!r}")
                    return None
                await asyncio.sleep(0.5)

        return None

    async def generate_and_store_cached_audio(
        self,
        text: str,
        user_id: str,
        conversation_id: str,
        settings: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> Optional[str]:
        """
        Same as generate_and_store_audio, but reuses the stored file for a
        phrase already synthesized with the same voice.

        Meant for the handful of fixed phrases the assistant repeats, where
        paying the synthesis latency every time would defeat their purpose.

        Returns:
            URL of the stored audio file or None if generation fails
        """
        settings = settings or {}
        key = (text, language, settings.get("voice"), settings.get("engine"), settings.get("pitch", 0))
        cached = self._phrase_cache.get(key)
        if cached:
            return cached

        url = await self.generate_and_store_audio(
            text=text,
            user_id=user_id,
            conversation_id=conversation_id,
            settings=settings or None,
            language=language,
        )
        if url:
            self._phrase_cache[key] = url
        return url

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
            Audio data, or None when the segment holds nothing speakable.

        Raises:
            Exception: on a real synthesis failure, so the caller can retry it.
        """
        try:
            return await self.tts_integration.text_to_speech_stream(
                text=text,
                settings=settings
            )
        except ValueError as e:
            logger.info(f"Skipping segment without speakable text: {e}")
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

            filename = self._generate_audio_filename(
                conversation_id, self._audio_extension(audio_data)
            )

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

    @staticmethod
    def _audio_extension(audio_data: bytes) -> str:
        """
        Resolves the container extension from the audio bytes themselves.

        Args:
            audio_data: Raw audio data

        Returns:
            ".wav" for RIFF/PCM payloads, ".mp3" otherwise
        """
        return ".wav" if audio_data[:4] == b"RIFF" else ".mp3"

    def _generate_audio_filename(
        self, conversation_id: str, extension: str = ".wav"
    ) -> str:
        """
        Generates a unique filename for the audio file.

        A reply is spoken one sentence per segment and the segments are
        generated concurrently, so several land inside the same second. A
        second-resolution name made them share a storage key, and the survivor
        was played once per colliding segment — the same sentence heard twice.

        Args:
            conversation_id: ID of the conversation
            extension: Container extension for the stored file

        Returns:
            Generated filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"tts_audio_{conversation_id}_{timestamp}_{uuid4().hex[:8]}{extension}"

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
