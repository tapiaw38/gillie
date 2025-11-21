from typing import Dict, Any
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError
from src.core.platform.logging import get_logger


class TranscribeAudioUseCase:
    """
    Transcribe audio files to text using STT (Speech-to-Text) service.

    This use case handles audio transcription for WhatsApp voice messages
    and other audio inputs, using Google Speech Recognition as the primary method.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        audio_bytes: bytes,
        audio_format: str = "ogg",
        language: str = "es-ES"
    ) -> Dict[str, Any]:
        """
        Execute the use case to transcribe audio to text.
        """
        logger = get_logger(__name__)
        context = self.context_factory()

        try:
            logger.info(f"Transcribing audio: format={audio_format}, language={language}, size={len(audio_bytes)} bytes")

            stt_integration = context.integrations.stt

            if not stt_integration:
                raise NewApplicationError(
                    ValidationError,
                    Exception("STT integration is not configured")
                )

            settings = {
                "language": language,
                "model": "base"  # For Whisper fallback
            }

            result = await stt_integration.audio_bytes_to_text(
                audio_bytes=audio_bytes,
                audio_format=audio_format,
                settings=settings
            )

            if not result.get("success", False):
                error_msg = result.get("error", "Unknown transcription error")
                logger.error(f"Transcription failed: {error_msg}")
                raise NewApplicationError(
                    ValidationError,
                    Exception(f"Transcription failed: {error_msg}")
                )

            logger.info(
                f"Transcription successful - Method: {result['method']}, "
                f"Text: '{result['text'][:100]}...'"
            )

            return {
                "transcription": result["text"],
                "language": result["language"],
                "confidence": result["confidence"],
                "method": result["method"],
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)

            if isinstance(e, type(NewApplicationError)):
                raise

            raise NewApplicationError(ValidationError, e)
