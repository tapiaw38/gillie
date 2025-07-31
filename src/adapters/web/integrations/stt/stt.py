import asyncio
import tempfile
import os
from typing import Optional, Dict, Any, Union
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from src.core.platform.config.service import ConfigurationService


class STTIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Default STT settings
        self.default_settings = {
            "language": "es-ES",  # Spanish (Spain) by default
            "model": "base",  # Whisper model size
            "temperature": 0.0,  # Temperature for transcription
            "word_timestamps": False,  # Include word-level timestamps
        }

    async def audio_to_text(
        self,
        audio_path: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert audio file to text using speech recognition

        Args:
            audio_path: Path to the audio file
            settings: STT settings override (optional)

        Returns:
            Dictionary with transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Use provided settings or defaults
        stt_settings = {**self.default_settings, **(settings or {})}

        # Run STT in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor, self._transcribe_audio, audio_path, stt_settings
        )

        return result

    def _transcribe_audio(
        self, audio_path: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transcribe audio file with multiple fallback strategies"""

        # Strategy 1: Try OpenAI Whisper (most accurate)
        try:
            import whisper

            # Load model based on settings
            model_name = settings.get("model", "base")
            model = whisper.load_model(model_name)

            # Transcribe audio
            result = model.transcribe(
                audio_path,
                language=settings.get("language", "es").split("-")[0],  # Extract language code
                temperature=settings.get("temperature", 0.0),
                word_timestamps=settings.get("word_timestamps", False),
            )

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "es"),
                "confidence": 1.0,  # Whisper doesn't provide confidence scores
                "segments": result.get("segments", []),
                "method": "whisper",
                "success": True,
            }

        except ImportError:
            print("⚠️ Whisper not available - install with: pip install openai-whisper")
        except Exception as e:
            print(f"Strategy 1 (Whisper) failed: {e}")

        # Strategy 2: Try Google Speech Recognition
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            # Convert audio to WAV if needed
            wav_path = self._convert_to_wav(audio_path)

            with sr.AudioFile(wav_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)

            # Try Google Speech Recognition
            text = recognizer.recognize_google(
                audio_data,
                language=settings.get("language", "es-ES"),
                show_all=False,
            )

            # Clean up temporary WAV file if created
            if wav_path != audio_path and os.path.exists(wav_path):
                os.unlink(wav_path)

            return {
                "text": text.strip(),
                "language": settings.get("language", "es-ES"),
                "confidence": 0.8,  # Estimated confidence
                "segments": [],
                "method": "google",
                "success": True,
            }

        except ImportError:
            print("⚠️ SpeechRecognition not available - install with: pip install SpeechRecognition")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service: {e}")
        except Exception as e:
            print(f"Strategy 2 (Google) failed: {e}")

        # Strategy 3: Try Vosk (offline recognition)
        try:
            import vosk
            import json
            import wave

            # Download Spanish model if not exists
            model_path = self._ensure_vosk_model("es")
            if not model_path:
                raise Exception("Could not download Vosk Spanish model")

            model = vosk.Model(model_path)
            recognizer = vosk.KaldiRecognizer(model, 16000)

            # Convert audio to proper format for Vosk
            wav_path = self._convert_to_wav_16khz(audio_path)

            with wave.open(wav_path, "rb") as wf:
                results = []
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        if result.get("text"):
                            results.append(result["text"])

                # Get final result
                final_result = json.loads(recognizer.FinalResult())
                if final_result.get("text"):
                    results.append(final_result["text"])

            # Clean up temporary WAV file if created
            if wav_path != audio_path and os.path.exists(wav_path):
                os.unlink(wav_path)

            full_text = " ".join(results).strip()
            if full_text:
                return {
                    "text": full_text,
                    "language": "es",
                    "confidence": 0.7,  # Estimated confidence
                    "segments": [],
                    "method": "vosk",
                    "success": True,
                }

        except ImportError:
            print("⚠️ Vosk not available - install with: pip install vosk")
        except Exception as e:
            print(f"Strategy 3 (Vosk) failed: {e}")

        # Strategy 4: Try pocketsphinx (basic offline recognition)
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            wav_path = self._convert_to_wav(audio_path)

            with sr.AudioFile(wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)

            # Try pocketsphinx
            text = recognizer.recognize_sphinx(
                audio_data,
                language="es-ES",
            )

            # Clean up temporary WAV file if created
            if wav_path != audio_path and os.path.exists(wav_path):
                os.unlink(wav_path)

            return {
                "text": text.strip(),
                "language": "es-ES",
                "confidence": 0.6,  # Lower confidence for pocketsphinx
                "segments": [],
                "method": "pocketsphinx",
                "success": True,
            }

        except ImportError:
            print("⚠️ PocketSphinx not available")
        except sr.UnknownValueError:
            print("PocketSphinx could not understand audio")
        except Exception as e:
            print(f"Strategy 4 (PocketSphinx) failed: {e}")

        # All strategies failed
        return {
            "text": "",
            "language": settings.get("language", "es-ES"),
            "confidence": 0.0,
            "segments": [],
            "method": "none",
            "success": False,
            "error": "All speech recognition methods failed",
        }

    def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format if needed"""
        if audio_path.lower().endswith('.wav'):
            return audio_path

        try:
            from pydub import AudioSegment

            # Load audio file
            audio = AudioSegment.from_file(audio_path)

            # Create temporary WAV file
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()

            # Export as WAV
            audio.export(temp_wav.name, format="wav")
            return temp_wav.name

        except ImportError:
            print("⚠️ pydub not available - install with: pip install pydub")
            return audio_path
        except Exception as e:
            print(f"Error converting audio to WAV: {e}")
            return audio_path

    def _convert_to_wav_16khz(self, audio_path: str) -> str:
        """Convert audio file to 16kHz WAV format for Vosk"""
        try:
            from pydub import AudioSegment

            # Load audio file
            audio = AudioSegment.from_file(audio_path)

            # Convert to 16kHz mono
            audio = audio.set_frame_rate(16000).set_channels(1)

            # Create temporary WAV file
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()

            # Export as WAV
            audio.export(temp_wav.name, format="wav")
            return temp_wav.name

        except ImportError:
            print("⚠️ pydub not available for audio conversion")
            return audio_path
        except Exception as e:
            print(f"Error converting audio to 16kHz WAV: {e}")
            return audio_path

    def _ensure_vosk_model(self, language: str) -> Optional[str]:
        """Ensure Vosk model is available for the specified language"""
        try:
            import vosk
            import urllib.request
            import zipfile
            import os

            # Model URLs for different languages
            models = {
                "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
                "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            }

            if language not in models:
                return None

            # Create models directory
            models_dir = os.path.expanduser("~/.vosk/models")
            os.makedirs(models_dir, exist_ok=True)

            model_name = f"vosk-model-small-{language}"
            model_path = os.path.join(models_dir, model_name)

            # Check if model already exists
            if os.path.exists(model_path):
                return model_path

            # Download and extract model
            model_url = models[language]
            zip_path = os.path.join(models_dir, f"{model_name}.zip")

            print(f"Downloading Vosk model for {language}...")
            urllib.request.urlretrieve(model_url, zip_path)

            # Extract model
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(models_dir)

            # Remove zip file
            os.unlink(zip_path)

            # Find extracted model directory
            for item in os.listdir(models_dir):
                item_path = os.path.join(models_dir, item)
                if os.path.isdir(item_path) and item.startswith("vosk-model"):
                    # Rename to expected name
                    if item != model_name:
                        os.rename(item_path, model_path)
                    return model_path

            return None

        except Exception as e:
            print(f"Error ensuring Vosk model: {e}")
            return None

    async def audio_bytes_to_text(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert audio bytes to text

        Args:
            audio_bytes: Audio data as bytes
            audio_format: Audio format (wav, mp3, etc.)
            settings: STT settings override (optional)

        Returns:
            Dictionary with transcription results
        """
        # Create temporary file from bytes
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            # Transcribe temporary file
            result = await self.audio_to_text(temp_path, settings)
            return result

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def get_supported_languages(self) -> list:
        """
        Get list of supported languages for speech recognition

        Returns:
            List of supported language codes
        """
        return [
            "es-ES",  # Spanish (Spain)
            "es-MX",  # Spanish (Mexico)
            "es-AR",  # Spanish (Argentina)
            "es-CO",  # Spanish (Colombia)
            "en-US",  # English (US)
            "en-GB",  # English (UK)
            "fr-FR",  # French
            "de-DE",  # German
            "it-IT",  # Italian
            "pt-BR",  # Portuguese (Brazil)
            "pt-PT",  # Portuguese (Portugal)
        ]

    async def validate_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Validate audio file for STT processing

        Args:
            audio_path: Path to audio file

        Returns:
            Validation results
        """
        if not os.path.exists(audio_path):
            return {
                "valid": False,
                "error": "File does not exist",
            }

        try:
            # Check file size (max 25MB)
            file_size = os.path.getsize(audio_path)
            if file_size > 25 * 1024 * 1024:
                return {
                    "valid": False,
                    "error": "File too large (max 25MB)",
                    "size": file_size,
                }

            # Check file extension
            valid_extensions = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac']
            file_ext = Path(audio_path).suffix.lower()
            if file_ext not in valid_extensions:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {file_ext}",
                    "supported_formats": valid_extensions,
                }

            # Try to get audio info
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path)
                duration = len(audio) / 1000.0  # Duration in seconds

                # Check duration (max 10 minutes)
                if duration > 600:
                    return {
                        "valid": False,
                        "error": "Audio too long (max 10 minutes)",
                        "duration": duration,
                    }

                return {
                    "valid": True,
                    "size": file_size,
                    "duration": duration,
                    "format": file_ext,
                    "channels": audio.channels,
                    "frame_rate": audio.frame_rate,
                }

            except ImportError:
                # If pydub not available, just check basic file properties
                return {
                    "valid": True,
                    "size": file_size,
                    "format": file_ext,
                    "note": "Limited validation (pydub not available)",
                }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
            }

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update default STT settings

        Args:
            settings: Dictionary with new settings
        """
        self.default_settings.update(settings)

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current STT settings

        Returns:
            Current settings dictionary
        """
        return self.default_settings.copy()

    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)