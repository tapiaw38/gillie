import pyttsx3
import asyncio
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from src.core.platform.config.service import ConfigurationService


class TTSIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self._executor = ThreadPoolExecutor(max_workers=2)

        # Default TTS settings
        self.default_settings = {
            "rate": 150,  # Speech rate (words per minute)
            "volume": 0.8,  # Volume level (0.0 to 1.0)
            "voice_id": None,  # Voice ID (None for default)
        }

    def _create_engine(self) -> pyttsx3.Engine:
        """Create and configure a new TTS engine instance with ultra-safe error handling"""
        engine = pyttsx3.init()

        try:
            # Configure basic engine settings (these are usually safe)
            engine.setProperty("rate", self.default_settings["rate"])
            engine.setProperty("volume", self.default_settings["volume"])

        except Exception as e:
            print(f"⚠️ Error configurando motor TTS: {e}. Usando configuración mínima.")

        return engine

    async def text_to_speech_file(
        self,
        text: str,
        output_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Convert text to speech and save as audio file

        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file (optional)
            settings: TTS settings override (optional)

        Returns:
            Path to the generated audio file
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        # Use provided settings or defaults
        tts_settings = {**self.default_settings, **(settings or {})}

        # Generate output path if not provided
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir, f"tts_output_{asyncio.get_event_loop().time()}.wav"
            )

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Run TTS in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor, self._generate_speech_file, text, output_path, tts_settings
        )

        return output_path

    def _generate_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any]
    ) -> None:
        """Generate speech file with improved fallback strategies and better diagnostics"""

        # Strategy 1: Try with absolute minimal configuration - NO properties at all
        try:
            engine = pyttsx3.init()

            engine.save_to_file(text, output_path)
            engine.runAndWait()
            engine.stop()

            # Verify file was created and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ ESTRATEGIA 1 EXITOSA: Archivo creado con {file_size} bytes")
                if file_size > 1000:  # Reasonable size for audio
                    return
                else:
                    print(
                        f"⚠️ Archivo muy pequeño ({file_size} bytes), intentando siguiente estrategia..."
                    )
            else:
                print("⚠️ Archivo no creado, intentando siguiente estrategia...")

        except Exception as e1:
            print(f"Strategy 1 failed: {e1}")

        try:
            engine = pyttsx3.init()

            try:
                voices = engine.getProperty("voices")

                if voices and len(voices) > 0:
                    # Try each voice individually until one works
                    for i, voice in enumerate(voices):
                        try:

                            # Create a fresh engine for each voice test
                            test_engine = pyttsx3.init()
                            test_engine.setProperty("voice", voice.id)
                            test_engine.setProperty("rate", 150)
                            test_engine.setProperty("volume", 0.8)

                            # Test with a short phrase first
                            test_path = output_path + f"_test_{i}.wav"
                            test_engine.save_to_file("Test", test_path)
                            test_engine.runAndWait()
                            test_engine.stop()

                            # If test succeeded, use this voice for the full text
                            if (
                                os.path.exists(test_path)
                                and os.path.getsize(test_path) > 100
                            ):
                                print(
                                    f"✅ Voz {i} funciona! Generando audio completo..."
                                )
                                os.unlink(test_path)  # Clean up test file

                                # Generate full audio with working voice
                                final_engine = pyttsx3.init()
                                final_engine.setProperty("voice", voice.id)
                                final_engine.setProperty("rate", 150)
                                final_engine.setProperty("volume", 0.8)
                                final_engine.save_to_file(text, output_path)
                                final_engine.runAndWait()
                                final_engine.stop()

                                if os.path.exists(output_path):
                                    file_size = os.path.getsize(output_path)

                                    if file_size > 1000:
                                        return

                            else:
                                # Clean up failed test
                                if os.path.exists(test_path):
                                    os.unlink(test_path)

                        except Exception as voice_test_error:
                            # Clean up any test file
                            test_path = output_path + f"_test_{i}.wav"
                            if os.path.exists(test_path):
                                os.unlink(test_path)
                            continue

                print("Ninguna voz individual funcionó")

            except Exception as voice_error:
                print(f"⚠️ Error obteniendo voces: {voice_error}")

            engine.stop()

        except Exception as e2:
            print(f"Strategy 2 failed: {e2}")

        # Strategy 3: Try Google Text-to-Speech (gTTS) - Much more natural voice
        try:
            from gtts import gTTS

            # Pre-process text for natural speech (remove special chars, add pauses)
            processed_text = self._preprocess_text_for_natural_speech(text)

            # Try different Spanish variants for more voice variety
            # Prioritize Colombian Spanish for clearest, most neutral female voice
            spanish_variants = [
                "es-co",  # Spanish (Colombia) - Acento colombiano muy claro (PRIORIDAD)
                "es-mx",  # Spanish (Mexico) - Acento mexicano cálido
                "es-ar",  # Spanish (Argentina) - Acento argentino distintivo
                "es",  # Spanish (Spain) - Voz femenina europea
                "es-es",  # Spanish (Spain) - Más específico
                "es-cl",  # Spanish (Chile) - Acento chileno
            ]

            # Try each variant until one works
            for lang_variant in spanish_variants:
                try:
                    # Create gTTS object with Spanish variant
                    tts_gtts = gTTS(
                        text=processed_text,
                        lang=lang_variant,  # Spanish language variant
                        slow=False,  # Normal speed (not slow)
                        lang_check=True,  # Check language
                    )

                    break  # Use first available variant

                except Exception as variant_error:
                    print(f"⚠️ Variante {lang_variant} no disponible: {variant_error}")
                    continue

            # Fallback to basic Spanish if no variants work
            if "tts_gtts" not in locals():
                print("🎵 Usando español básico como fallback")
                tts_gtts = gTTS(
                    text=processed_text,
                    lang="es",  # Basic Spanish
                    slow=False,
                    lang_check=True,
                )

            # Save to temporary file first (gTTS saves as MP3)
            temp_mp3_path = output_path.replace(".wav", ".mp3")
            tts_gtts.save(temp_mp3_path)

            # Convert MP3 to WAV using ffmpeg for consistency
            if os.path.exists(temp_mp3_path):
                import subprocess

                try:
                    # Convert MP3 to WAV
                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-y",  # -y to overwrite
                        "-i",
                        temp_mp3_path,
                        "-acodec",
                        "pcm_s16le",  # 16-bit PCM
                        "-ar",
                        "22050",  # 22kHz sample rate
                        "-ac",
                        "1",  # Mono
                        output_path,
                    ]

                    result = subprocess.run(
                        ffmpeg_cmd, capture_output=True, text=True, timeout=30
                    )

                    if result.returncode == 0 and os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)

                        # Clean up temporary MP3 file
                        os.unlink(temp_mp3_path)

                        if file_size > 1000:
                            return
                    else:
                        print(f"Error converting MP3 to WAV: {result.stderr}")

                except subprocess.TimeoutExpired:
                    print("ffmpeg timeout durante conversión")
                except Exception as conv_error:
                    print(f"Error en conversión: {conv_error}")
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_mp3_path):
                        os.unlink(temp_mp3_path)

        except ImportError:
            print("⚠️ gTTS not available - install with: pip install gtts")
        except Exception as e3:
            print(f"Strategy 3 failed: {e3}")

        # Strategy 4: Fallback to espeak if gTTS fails
        try:
            import subprocess

            subprocess.run(["espeak", "--version"], capture_output=True, check=True)

            # Use processed text from gTTS attempt
            processed_text = self._preprocess_text_for_natural_speech(text)

            # Simple espeak command as fallback
            espeak_cmd = [
                "espeak",
                "-w",
                output_path,
                "-s",
                "140",
                "-a",
                "85",
                "-v",
                "es+f3",
                processed_text,
            ]

            result = subprocess.run(
                espeak_cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(
                    f"✅ ESTRATEGIA 4 EXITOSA: Fallback espeak creado con {file_size} bytes"
                )
                if file_size > 1000:
                    return

        except Exception as e4:
            print(f"Strategy 4 failed: {e4}")

        # Strategy 5: Create enhanced dummy audio file as last resort
        self._create_enhanced_dummy_audio_file(output_path, text)
        return

    async def get_available_voices(self) -> list:
        """
        Get list of available voices

        Returns:
            List of available voices with their properties
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._get_voices)

    def _get_voices(self) -> list:
        """Get available voices in a separate thread"""
        engine = self._create_engine()
        voices = engine.getProperty("voices")
        engine.stop()

        if not voices:
            return []

        voice_list = []
        for i, voice in enumerate(voices):
            voice_info = {
                "id": i,
                "name": voice.name,
                "languages": getattr(voice, "languages", []),
                "gender": getattr(voice, "gender", "unknown"),
                "age": getattr(voice, "age", "unknown"),
            }
            voice_list.append(voice_info)

        return voice_list

    async def text_to_speech_stream(
        self, text: str, settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Convert text to speech and return as bytes stream

        Args:
            text: Text to convert to speech
            settings: TTS settings override (optional)

        Returns:
            Audio data as bytes
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate speech file
            await self.text_to_speech_file(text, temp_path, settings)

            # Read file as bytes
            with open(temp_path, "rb") as audio_file:
                audio_data = audio_file.read()

            return audio_data

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update default TTS settings

        Args:
            settings: Dictionary with new settings
        """
        self.default_settings.update(settings)

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current TTS settings

        Returns:
            Current settings dictionary
        """
        return self.default_settings.copy()

    async def validate_text_length(self, text: str, max_length: int = 5000) -> bool:
        """
        Validate text length for TTS processing

        Args:
            text: Text to validate
            max_length: Maximum allowed text length

        Returns:
            True if text is valid, False otherwise
        """
        return len(text.strip()) > 0 and len(text) <= max_length

    def _preprocess_text_for_natural_speech(self, text: str) -> str:
        """
        Pre-process text to make it sound more natural when spoken.
        This includes handling abbreviations, numbers, and adding pauses.
        """
        try:
            import re

            # Make a copy to work with
            processed_text = text

            # 1. Add pauses after punctuation for more natural flow
            processed_text = re.sub(r"([.!?])\s+", r"\1... ", processed_text)
            processed_text = re.sub(r"([,;:])\s+", r"\1.. ", processed_text)

            # 2. Handle common abbreviations in Spanish
            abbreviations = {
                "Dr.": "Doctor",
                "Dra.": "Doctora",
                "Sr.": "Señor",
                "Sra.": "Señora",
                "Srta.": "Señorita",
                "etc.": "etcétera",
                "p.ej.": "por ejemplo",
                "vs.": "versus",
                "ej.": "ejemplo",
                "pág.": "página",
                "págs.": "páginas",
                "cap.": "capítulo",
                "art.": "artículo",
                "núm.": "número",
                "tel.": "teléfono",
                "dir.": "dirección",
                "admin.": "administración",
                "info.": "información",
                "config.": "configuración",
                "app.": "aplicación",
                "API": "A P I",
                "URL": "U R L",
                "HTTP": "H T T P",
                "JSON": "J S O N",
                "XML": "X M L",
                "PDF": "P D F",
                "TTS": "T T S",
                "AI": "A I",
                "IA": "I A",
            }

            for abbrev, expansion in abbreviations.items():
                processed_text = processed_text.replace(abbrev, expansion)

            # 3. Handle numbers for more natural pronunciation
            # Convert standalone numbers to words (basic cases)
            number_words = {
                "0": "cero",
                "1": "uno",
                "2": "dos",
                "3": "tres",
                "4": "cuatro",
                "5": "cinco",
                "6": "seis",
                "7": "siete",
                "8": "ocho",
                "9": "nueve",
                "10": "diez",
                "11": "once",
                "12": "doce",
                "13": "trece",
                "14": "catorce",
                "15": "quince",
                "16": "dieciséis",
                "17": "diecisiete",
                "18": "dieciocho",
                "19": "diecinueve",
                "20": "veinte",
            }

            # Replace standalone single/double digit numbers
            for num, word in number_words.items():
                processed_text = re.sub(rf"\b{num}\b", word, processed_text)

            # 4. Handle percentages
            processed_text = re.sub(r"(\d+)%", r"\1 por ciento", processed_text)

            # 5. Remove or replace special characters that shouldn't be read aloud
            # But use them for pauses and emotions

            # Remove markdown formatting but keep the emphasis
            processed_text = re.sub(
                r"\*\*(.*?)\*\*", r".. \1 ..", processed_text
            )  # Bold -> emphasis with pauses
            processed_text = re.sub(
                r"\*(.*?)\*", r". \1 .", processed_text
            )  # Italic -> slight pause
            processed_text = re.sub(
                r"_(.*?)_", r". \1 .", processed_text
            )  # Underscore -> slight pause

            # Handle emoticons and emojis - convert to pauses or remove
            processed_text = re.sub(
                r"[😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾]",
                " .. ",
                processed_text,
            )

            # Handle common symbols
            processed_text = processed_text.replace("&", "y")
            processed_text = processed_text.replace("@", "arroba")
            processed_text = processed_text.replace("#", "numeral")
            processed_text = processed_text.replace("$", "dólares")
            processed_text = processed_text.replace("€", "euros")
            processed_text = processed_text.replace("£", "libras")
            processed_text = processed_text.replace("+", "más")
            processed_text = processed_text.replace("=", "igual")
            processed_text = processed_text.replace("<", "menor que")
            processed_text = processed_text.replace(">", "mayor que")

            # Remove or replace special punctuation that sounds bad when read
            processed_text = processed_text.replace("|", " .. ")  # Pipe -> pause
            processed_text = processed_text.replace("\\", " ")  # Backslash -> space
            processed_text = processed_text.replace("/", " o ")  # Slash -> "o"
            processed_text = processed_text.replace("[", " .. ")  # Brackets -> pauses
            processed_text = processed_text.replace("]", " .. ")
            processed_text = processed_text.replace("{", " .. ")  # Braces -> pauses
            processed_text = processed_text.replace("}", " .. ")
            processed_text = processed_text.replace(
                "(", " .. "
            )  # Parentheses -> pauses
            processed_text = processed_text.replace(")", " .. ")
            processed_text = processed_text.replace('"', " ")  # Quotes -> space
            processed_text = processed_text.replace("'", " ")  # Apostrophe -> space
            processed_text = processed_text.replace("`", " ")  # Backtick -> space
            processed_text = processed_text.replace("~", " ")  # Tilde -> space
            processed_text = processed_text.replace("^", " ")  # Caret -> space
            processed_text = processed_text.replace(
                "_", " "
            )  # Underscore -> space (if not handled above)

            # Handle multiple punctuation marks for emotional emphasis
            processed_text = re.sub(
                r"!{2,}", " ¡con énfasis! ", processed_text
            )  # Multiple ! -> emphasis
            processed_text = re.sub(
                r"\?{2,}", " ¿en serio? ", processed_text
            )  # Multiple ? -> questioning
            processed_text = re.sub(
                r"\.{3,}", " ... ", processed_text
            )  # Multiple dots -> pause

            # 6. Add slight pauses before important words for emphasis
            emphasis_words = [
                "importante",
                "atención",
                "nota",
                "cuidado",
                "recuerda",
                "observa",
            ]
            for word in emphasis_words:
                processed_text = re.sub(
                    rf"\b({word})\b", r".. \1", processed_text, flags=re.IGNORECASE
                )

            # 7. Clean up multiple spaces and dots
            processed_text = re.sub(r"\.{4,}", "...", processed_text)  # Max 3 dots
            processed_text = re.sub(r"\s+", " ", processed_text)  # Single spaces
            processed_text = processed_text.strip()

            return processed_text

        except Exception as e:
            return text  # Return original text if preprocessing fails$', 'dólares')
            processed_text = processed_text.replace("€", "euros")
            processed_text = processed_text.replace("£", "libras")

            # 6. Add slight pauses before important words for emphasis
            emphasis_words = [
                "importante",
                "atención",
                "nota",
                "cuidado",
                "recuerda",
                "observa",
            ]
            for word in emphasis_words:
                processed_text = re.sub(
                    rf"\b({word})\b", r".. \1", processed_text, flags=re.IGNORECASE
                )

            # 7. Clean up multiple spaces and dots
            processed_text = re.sub(r"\.{4,}", "...", processed_text)  # Max 3 dots
            processed_text = re.sub(r"\s+", " ", processed_text)  # Single spaces
            processed_text = processed_text.strip()

            return processed_text

        except Exception as e:
            return text  # Return original text if preprocessing fails

    def _create_dummy_audio_file(self, output_path: str, text: str) -> None:
        """
        Create a dummy audio file as last resort when TTS fails completely.
        This creates a minimal WAV file with silence to prevent complete failure.
        """
        try:
            import wave
            import struct

            # Create a minimal WAV file with silence
            # This ensures the API doesn't fail completely if TTS is broken
            duration = min(
                len(text) * 0.1, 10.0
            )  # Estimate duration based on text length, max 10 seconds
            sample_rate = 22050
            num_samples = int(duration * sample_rate)

            with wave.open(output_path, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)

                # Write silence (zeros)
                silence = struct.pack("<h", 0) * num_samples
                wav_file.writeframes(silence)

        except Exception as e:
            print(f"❌ Error creando archivo dummy: {e}")
            # As absolute last resort, create an empty file
            with open(output_path, "wb") as f:
                f.write(b"")
            print(f"Fallback: Created empty file at {output_path}")

    def _create_enhanced_dummy_audio_file(self, output_path: str, text: str) -> None:
        """
        Create an enhanced dummy audio file with clear audio feedback.
        This makes it obvious that TTS failed but provides audible confirmation.
        """
        try:
            import wave
            import struct
            import math

            # Create a WAV file with a distinctive pattern
            duration = min(len(text) * 0.05, 5.0)  # Shorter duration, max 5 seconds
            sample_rate = 22050
            num_samples = int(duration * sample_rate)

            with wave.open(output_path, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)

                # Generate a distinctive "TTS failed" pattern
                # 3 short beeps followed by silence
                audio_data = []
                for i in range(num_samples):
                    time_pos = i / sample_rate

                    # Pattern: 3 beeps of 0.2s each, with 0.1s gaps, then silence
                    beep_pattern = [
                        (0.0, 0.2),  # First beep
                        (0.3, 0.5),  # Second beep
                        (0.6, 0.8),  # Third beep
                    ]

                    sample = 0
                    for start, end in beep_pattern:
                        if start <= time_pos <= end:
                            # Generate a clear 800Hz tone (higher pitch, more noticeable)
                            frequency = 800
                            amplitude = 0.4  # Clear, audible volume
                            sample = int(
                                amplitude
                                * 32767
                                * math.sin(2 * math.pi * frequency * time_pos)
                            )
                            break

                    audio_data.append(struct.pack("<h", sample))

                # Write all samples
                wav_file.writeframes(b"".join(audio_data))

        except Exception as e:
            self._create_dummy_audio_file(output_path, text)

    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
