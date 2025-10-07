from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi import UploadFile


class STTInput(BaseModel):
    audio_file: UploadFile = Field(..., description="Audio file to transcribe")
    settings: Optional[Dict[str, Any]] = Field(
        None, description="STT settings override"
    )


class STTSettingsInput(BaseModel):
    language: Optional[str] = Field(
        None, description="Language code (e.g., 'es-ES', 'en-US')"
    )
    model: Optional[str] = Field(
        None, description="Model size for Whisper (tiny, base, small, medium, large)"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Temperature for transcription"
    )
    word_timestamps: Optional[bool] = Field(
        None, description="Include word-level timestamps"
    )


class STTResultData(BaseModel):
    text: str
    language: str
    confidence: float
    method: str
    success: bool
    segments: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class STTOutput(BaseModel):
    data: STTResultData

    @staticmethod
    def from_output(result: Dict[str, Any]):
        return STTOutput(
            data=STTResultData(
                text=result.get("text", ""),
                language=result.get("language", ""),
                confidence=result.get("confidence", 0.0),
                method=result.get("method", ""),
                success=result.get("success", False),
                segments=result.get("segments"),
                error=result.get("error"),
            )
        )


class STTLanguageData(BaseModel):
    code: str
    name: str


class STTLanguagesOutput(BaseModel):
    data: List[STTLanguageData]

    @staticmethod
    def from_output(languages: List[str]):
        language_names = {
            "es-ES": "Spanish (Spain)",
            "es-MX": "Spanish (Mexico)",
            "es-AR": "Spanish (Argentina)",
            "es-CO": "Spanish (Colombia)",
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "fr-FR": "French",
            "de-DE": "German",
            "it-IT": "Italian",
            "pt-BR": "Portuguese (Brazil)",
            "pt-PT": "Portuguese (Portugal)",
        }

        return STTLanguagesOutput(
            data=[
                STTLanguageData(
                    code=lang,
                    name=language_names.get(lang, lang)
                )
                for lang in languages
            ]
        )


class STTValidationData(BaseModel):
    valid: bool
    size: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    channels: Optional[int] = None
    frame_rate: Optional[int] = None
    error: Optional[str] = None
    supported_formats: Optional[List[str]] = None
    note: Optional[str] = None


class STTValidationOutput(BaseModel):
    data: STTValidationData

    @staticmethod
    def from_output(validation: Dict[str, Any]):
        return STTValidationOutput(
            data=STTValidationData(
                valid=validation.get("valid", False),
                size=validation.get("size"),
                duration=validation.get("duration"),
                format=validation.get("format"),
                channels=validation.get("channels"),
                frame_rate=validation.get("frame_rate"),
                error=validation.get("error"),
                supported_formats=validation.get("supported_formats"),
                note=validation.get("note"),
            )
        )
