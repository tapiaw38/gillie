import asyncio
import tempfile
import os
import logging
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from src.core.platform.config.service import ConfigurationService

logger = logging.getLogger(__name__)


class TTSIntegration:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self._executor = ThreadPoolExecutor(max_workers=2)

        self.default_settings = {
            "rate": 150,
            "volume": 0.8,
            "voice_id": None,
        }

    async def text_to_speech_file(
        self,
        text: str,
        output_path: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Convert text to speech and save as audio file.

        Returns:
            Path to the generated audio file
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        tts_settings = {**self.default_settings, **(settings or {})}

        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir, f"tts_output_{asyncio.get_event_loop().time()}.wav"
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor, self._generate_speech_file, text, output_path, tts_settings
        )

        return output_path

    def _generate_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any]
    ) -> None:
        """Generate speech file using gTTS (Google Text-to-Speech)."""
        logger.info("TTS (gTTS): starting")
        try:
            from gtts import gTTS

            processed_text = self._preprocess_text_for_natural_speech(text)

            tts_gtts = gTTS(text=processed_text, lang="es", slow=False)
            logger.info("TTS (gTTS): usando lang='es'")

            temp_mp3_path = output_path.replace(".wav", ".mp3")
            tts_gtts.save(temp_mp3_path)

            if os.path.exists(temp_mp3_path):
                import subprocess
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_mp3_path,
                    "-acodec", "pcm_s16le",
                    "-ar", "22050",
                    "-ac", "1",
                    output_path,
                ]
                result = subprocess.run(
                    ffmpeg_cmd, capture_output=True, text=True, timeout=30
                )

                if os.path.exists(temp_mp3_path):
                    os.unlink(temp_mp3_path)

                if result.returncode == 0 and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > 1000:
                        logger.info(
                            "TTS (gTTS): SUCCESS — %d bytes at %s",
                            file_size, output_path,
                        )
                        return
                    else:
                        logger.warning(
                            "TTS (gTTS): output too small (%d bytes)", file_size
                        )
                else:
                    logger.warning("TTS (gTTS): ffmpeg failed: %s", result.stderr[:200])

        except ImportError:
            logger.error("TTS (gTTS): not available (pip install gtts)")
        except Exception as e:
            logger.error("TTS (gTTS): FAILED — %s", e)

    async def text_to_speech_stream(
        self, text: str, settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Convert text to speech and return as bytes stream.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            await self.text_to_speech_file(text, temp_path, settings)
            with open(temp_path, "rb") as audio_file:
                return audio_file.read()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def get_available_voices(self) -> list:
        """Get list of available voices from pyttsx3 (best-effort)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._get_voices)

    def _get_voices(self) -> list:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            engine.stop()
            return [
                {
                    "id": i,
                    "name": v.name,
                    "languages": getattr(v, "languages", []),
                    "gender": getattr(v, "gender", "unknown"),
                    "age": getattr(v, "age", "unknown"),
                }
                for i, v in enumerate(voices)
            ]
        except Exception as e:
            logger.debug("get_available_voices: %s", e)
            return []

    def update_settings(self, settings: Dict[str, Any]) -> None:
        self.default_settings.update(settings)

    def get_settings(self) -> Dict[str, Any]:
        return self.default_settings.copy()

    async def validate_text_length(self, text: str, max_length: int = 5000) -> bool:
        return len(text.strip()) > 0 and len(text) <= max_length

    def _preprocess_text_for_natural_speech(self, text: str) -> str:
        """Pre-process text to make it sound more natural when spoken."""
        try:
            import re

            processed_text = text

            # 1. Add pauses after punctuation
            processed_text = re.sub(r"([.!?])\s+", r"\1... ", processed_text)
            processed_text = re.sub(r"([,;:])\s+", r"\1.. ", processed_text)

            # 2. Expand common Spanish abbreviations
            abbreviations = {
                "Dr.": "Doctor", "Dra.": "Doctora",
                "Sr.": "Señor", "Sra.": "Señora", "Srta.": "Señorita",
                "etc.": "etcétera", "p.ej.": "por ejemplo", "vs.": "versus",
                "ej.": "ejemplo", "pág.": "página", "págs.": "páginas",
                "cap.": "capítulo", "art.": "artículo", "núm.": "número",
                "tel.": "teléfono", "dir.": "dirección",
                "admin.": "administración", "info.": "información",
                "config.": "configuración", "app.": "aplicación",
                "API": "A P I", "URL": "U R L", "HTTP": "H T T P",
                "JSON": "J S O N", "XML": "X M L", "PDF": "P D F",
                "TTS": "T T S", "AI": "A I", "IA": "I A",
            }
            for abbrev, expansion in abbreviations.items():
                processed_text = processed_text.replace(abbrev, expansion)

            # 3. Convert standalone small numbers to words
            number_words = {
                "0": "cero", "1": "uno", "2": "dos", "3": "tres",
                "4": "cuatro", "5": "cinco", "6": "seis", "7": "siete",
                "8": "ocho", "9": "nueve", "10": "diez", "11": "once",
                "12": "doce", "13": "trece", "14": "catorce", "15": "quince",
                "16": "dieciséis", "17": "diecisiete", "18": "dieciocho",
                "19": "diecinueve", "20": "veinte",
            }
            for num, word in number_words.items():
                processed_text = re.sub(rf"\b{num}\b", word, processed_text)

            # 4. Percentages
            processed_text = re.sub(r"(\d+)%", r"\1 por ciento", processed_text)

            # 5. Markdown formatting → pauses
            processed_text = re.sub(r"\*\*(.*?)\*\*", r".. \1 ..", processed_text)
            processed_text = re.sub(r"\*(.*?)\*", r". \1 .", processed_text)
            processed_text = re.sub(r"_(.*?)_", r". \1 .", processed_text)

            # 6. Emoji → pause
            processed_text = re.sub(
                r"[😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜"
                r"🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡"
                r"🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲"
                r"🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️"
                r"👽👾🤖🎃😺😸😹😻😼😽🙀😿😾]",
                " .. ",
                processed_text,
            )

            # 7. Common symbols
            replacements = {
                "&": "y", "@": "arroba", "#": "numeral", "$": "dólares",
                "€": "euros", "£": "libras", "+": "más", "=": "igual",
                "<": "menor que", ">": "mayor que",
                "|": " .. ", "\\": " ", "/": " o ",
                "[": " .. ", "]": " .. ", "{": " .. ", "}": " .. ",
                "(": " .. ", ")": " .. ",
                '"': " ", "'": " ", "`": " ", "~": " ", "^": " ", "_": " ",
            }
            for char, replacement in replacements.items():
                processed_text = processed_text.replace(char, replacement)

            # 8. Emphasis patterns
            processed_text = re.sub(r"!{2,}", " ¡con énfasis! ", processed_text)
            processed_text = re.sub(r"\?{2,}", " ¿en serio? ", processed_text)
            processed_text = re.sub(r"\.{3,}", " ... ", processed_text)

            # 9. Pauses before key words
            for word in ["importante", "atención", "nota", "cuidado", "recuerda", "observa"]:
                processed_text = re.sub(
                    rf"\b({word})\b", r".. \1", processed_text, flags=re.IGNORECASE
                )

            # 10. Cleanup
            processed_text = re.sub(r"\.{4,}", "...", processed_text)
            processed_text = re.sub(r"\s+", " ", processed_text).strip()

            return processed_text

        except Exception:
            return text

    def __del__(self):
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
