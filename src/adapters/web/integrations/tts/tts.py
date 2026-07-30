import asyncio
import re
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
            "language": "en",
        }

        self._gtts_lang_map = {
            "en": "en",
            "es": "es",
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

    def _tts_config(self):
        return getattr(self.config_service, "tts_config", None)

    def _generate_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any]
    ) -> None:
        """Generate speech with the configured engine, falling back to gTTS."""
        config = self._tts_config()
        engine = self._resolve_engine(config, settings.get("engine"))

        if engine == "openai":
            try:
                self._generate_openai_speech_file(text, output_path, settings, config)
                return
            except Exception as e:
                logger.warning("TTS (OpenAI): failed, falling back to gTTS — %s", e)
        elif engine == "edge":
            try:
                self._generate_edge_speech_file(text, output_path, settings, config)
                return
            except Exception as e:
                logger.warning("TTS (edge): failed, falling back to gTTS — %s", e)

        self._generate_gtts_speech_file(text, output_path, settings)

    @staticmethod
    def _resolve_engine(config, requested: Optional[str] = None) -> str:
        if config is None:
            return "gtts"
        engine = (requested or getattr(config, "engine", "") or "").strip().lower()
        if engine == "openai" and not config.api_key:
            logger.warning("TTS: openai engine requested without an API key, using gTTS")
            return "gtts"
        if engine:
            return engine
        return "openai" if config.api_key else "gtts"

    def _generate_edge_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any], config
    ) -> None:
        import asyncio

        import edge_tts

        voice = settings.get("voice") or config.voice or self._default_edge_voice(
            settings.get("language", "en")
        )
        logger.info("TTS (edge): voice='%s'", voice)

        processed_text = self._preprocess_text_for_natural_speech(
            text, language=settings.get("language", "en")
        )
        temp_source_path = output_path + ".edge.mp3"

        async def synthesize() -> None:
            await edge_tts.Communicate(processed_text, voice).save(temp_source_path)

        asyncio.run(synthesize())

        try:
            self._transcode_to_pcm(temp_source_path, output_path)
        finally:
            if os.path.exists(temp_source_path):
                os.unlink(temp_source_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 1000:
            raise RuntimeError("edge TTS produced no usable audio")
        logger.info(
            "TTS (edge): SUCCESS — %d bytes at %s",
            os.path.getsize(output_path), output_path,
        )

    @staticmethod
    def _default_edge_voice(language: str) -> str:
        return {"es": "es-AR-ElenaNeural"}.get(language, "en-US-AvaNeural")

    def _generate_openai_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any], config
    ) -> None:
        import requests

        voice = settings.get("voice") or config.voice or "nova"
        model = config.model or "gpt-4o-mini-tts"
        base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        logger.info("TTS (OpenAI): model='%s' voice='%s'", model, voice)

        response = requests.post(
            f"{base_url}/audio/speech",
            headers={"Authorization": f"Bearer {config.api_key}"},
            json={
                "model": model,
                "voice": voice,
                "input": self._preprocess_text_for_natural_speech(
                    text, language=settings.get("language", "en")
                ),
                "response_format": "wav",
            },
            timeout=60,
        )
        response.raise_for_status()

        temp_source_path = output_path + ".openai.wav"
        with open(temp_source_path, "wb") as audio_file:
            audio_file.write(response.content)

        try:
            self._transcode_to_pcm(temp_source_path, output_path)
        finally:
            if os.path.exists(temp_source_path):
                os.unlink(temp_source_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 1000:
            raise RuntimeError("OpenAI TTS produced no usable audio")
        logger.info(
            "TTS (OpenAI): SUCCESS — %d bytes at %s",
            os.path.getsize(output_path), output_path,
        )

    def _transcode_to_pcm(self, source_path: str, output_path: str) -> None:
        import subprocess

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", source_path,
                "-acodec", "pcm_s16le",
                "-ar", "22050",
                "-ac", "1",
                output_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[:200]}")

    def _generate_gtts_speech_file(
        self, text: str, output_path: str, settings: Dict[str, Any]
    ) -> None:
        """Generate speech file using gTTS (Google Text-to-Speech)."""
        logger.info("TTS (gTTS): starting")
        try:
            from gtts import gTTS

            processed_text = self._preprocess_text_for_natural_speech(text, language=settings.get("language", "en"))

            lang_code = self._gtts_lang_map.get(settings.get("language", "en"), "en")
            tts_gtts = gTTS(text=processed_text, lang=lang_code, slow=False)
            logger.info("TTS (gTTS): using lang='%s'", lang_code)

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

    _EMOJI_AND_SYMBOLS = re.compile(
        "["
        "\U0001F000-\U0001FAFF"
        "\U00002190-\U000021FF"
        "\U00002300-\U000023FF"
        "\U00002460-\U000024FF"
        "\U00002500-\U00002BFF"
        "\U0000FE00-\U0000FE0F"
        "\U0001F1E6-\U0001F1FF"
        "\U000E0000-\U000E007F"
        "\U0000200D"
        "\U000020E3"
        "]+"
    )

    def _strip_unspeakable(self, text: str, language: str = "en") -> str:
        """Remove everything a voice should never read out: emoji, code, URLs."""
        spanish = language == "es"
        code_word = "un bloque de código" if spanish else "a code block"
        link_word = "un enlace" if spanish else "a link"
        path_word = "una ruta" if spanish else "a path"

        cleaned = re.sub(r"```[\s\S]*?```", f" {code_word} ", text)
        cleaned = re.sub(r"`[^`\n]+`", " ", cleaned)
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleaned)
        cleaned = re.sub(r"<[^>\s]+@[^>\s]+>|\b[\w.+-]+@[\w-]+\.[\w.]+\b", f" {link_word} ", cleaned)
        cleaned = re.sub(r"\b(?:https?://|www\.)\S+", f" {link_word} ", cleaned)
        cleaned = re.sub(r"(?<![\w.])(?:~|\.{1,2})?/[\w./-]{2,}", f" {path_word} ", cleaned)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = self._EMOJI_AND_SYMBOLS.sub(" ", cleaned)
        return re.sub(r"[ \t]{2,}", " ", cleaned).strip()

    def _preprocess_text_for_natural_speech(self, text: str, language: str = "en") -> str:
        """Pre-process text to make it sound more natural when spoken."""
        try:
            import re

            processed_text = self._strip_unspeakable(text, language)

            processed_text = re.sub(r"([.!?])\s+", r"\1... ", processed_text)
            processed_text = re.sub(r"([,;:])\s+", r"\1.. ", processed_text)

            if language == "es":
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
            else:
                abbreviations = {
                    "Dr.": "Doctor", "Mrs.": "Missus", "Mr.": "Mister", "Ms.": "Miss",
                    "etc.": "etcetera", "e.g.": "for example", "i.e.": "that is",
                    "vs.": "versus", "approx.": "approximately",
                    "API": "A P I", "URL": "U R L", "HTTP": "H T T P",
                    "JSON": "J S O N", "XML": "X M L", "PDF": "P D F",
                    "TTS": "T T S", "STT": "S T T", "AI": "A I",
                }
            for abbrev, expansion in abbreviations.items():
                processed_text = processed_text.replace(abbrev, expansion)

            if language == "es":
                number_words = {
                    "0": "cero", "1": "uno", "2": "dos", "3": "tres",
                    "4": "cuatro", "5": "cinco", "6": "seis", "7": "siete",
                    "8": "ocho", "9": "nueve", "10": "diez", "11": "once",
                    "12": "doce", "13": "trece", "14": "catorce", "15": "quince",
                }
                for num, word in number_words.items():
                    processed_text = re.sub(rf"\b{num}\b", word, processed_text)
                processed_text = re.sub(r"(\d+)%", r"\1 por ciento", processed_text)
            else:
                processed_text = re.sub(r"(\d+)%", r"\1 percent", processed_text)

            processed_text = re.sub(r"\*\*(.*?)\*\*", r".. \1 ..", processed_text)
            processed_text = re.sub(r"\*(.*?)\*", r". \1 .", processed_text)
            processed_text = re.sub(r"_(.*?)_", r". \1 .", processed_text)

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

            processed_text = re.sub(r"!{2,}", " ¡con énfasis! ", processed_text)
            processed_text = re.sub(r"\?{2,}", " ¿en serio? ", processed_text)
            processed_text = re.sub(r"\.{3,}", " ... ", processed_text)

            for word in ["importante", "atención", "nota", "cuidado", "recuerda", "observa"]:
                processed_text = re.sub(
                    rf"\b({word})\b", r".. \1", processed_text, flags=re.IGNORECASE
                )

            processed_text = re.sub(r"\.{4,}", "...", processed_text)
            processed_text = re.sub(r"\s+", " ", processed_text).strip()

            return processed_text

        except Exception:
            return text

    def __del__(self):
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
