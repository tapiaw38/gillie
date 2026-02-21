import asyncio
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from src.core.platform.config.service import ConfigurationService


class STTIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self._executor = ThreadPoolExecutor(max_workers=2)

        self.default_settings = {
            "language": "es-ES",
        }

    async def audio_to_text(
        self,
        audio_path: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        stt_settings = {**self.default_settings, **(settings or {})}

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor, self._transcribe_audio, audio_path, stt_settings
        )

        return result

    def _transcribe_audio(self, audio_path: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            wav_path = self._convert_to_wav(audio_path)

            with sr.AudioFile(wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)

            if wav_path != audio_path and os.path.exists(wav_path):
                os.unlink(wav_path)

            text = recognizer.recognize_google(
                audio_data,
                language=settings.get("language", "es-ES"),
                show_all=False,
            )

            return {
                "text": text.strip(),
                "language": settings.get("language", "es-ES"),
                "confidence": 0.8,
                "segments": [],
                "method": "google",
                "success": True,
            }

        except ImportError:
            print("⚠️ SpeechRecognition not available - install with: pip install SpeechRecognition")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition: {e}")
        except Exception as e:
            print(f"Google STT failed: {e}")

        return {
            "text": "",
            "language": settings.get("language", "es-ES"),
            "confidence": 0.0,
            "segments": [],
            "method": "none",
            "success": False,
            "error": "Speech recognition failed",
        }

    def _convert_to_wav(self, audio_path: str) -> str:
        if audio_path.lower().endswith(".wav"):
            return audio_path

        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(audio_path)
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()
            audio.export(temp_wav.name, format="wav")
            return temp_wav.name

        except Exception as e:
            print(f"Error converting audio to WAV: {e}")
            return audio_path

    async def audio_bytes_to_text(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            return await self.audio_to_text(temp_path, settings)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def get_supported_languages(self) -> list:
        return [
            "es-ES",
            "es-MX",
            "es-AR",
            "es-CO",
            "en-US",
            "en-GB",
            "fr-FR",
            "de-DE",
            "it-IT",
            "pt-BR",
            "pt-PT",
        ]

    def update_settings(self, settings: Dict[str, Any]) -> None:
        self.default_settings.update(settings)

    def get_settings(self) -> Dict[str, Any]:
        return self.default_settings.copy()

    def __del__(self):
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
