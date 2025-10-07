from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TTSInput(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=5000, description="Text to convert to speech"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="TTS settings override"
    )


class TTSSettingsInput(BaseModel):
    rate: Optional[int] = Field(
        None, ge=50, le=400, description="Speech rate (words per minute)"
    )
    volume: Optional[float] = Field(None, ge=0.0, le=1.0, description="Volume level")
    voice_id: Optional[int] = Field(None, ge=0, description="Voice ID")


class TTSVoiceData(BaseModel):
    id: int
    name: str
    languages: List[str]
    gender: str
    age: str


class TTSVoicesOutput(BaseModel):
    data: List[TTSVoiceData]

    @staticmethod
    def from_output(voices: List[Dict[str, Any]]):
        return TTSVoicesOutput(
            data=[
                TTSVoiceData(
                    id=voice["id"],
                    name=voice["name"],
                    languages=voice["languages"],
                    gender=voice["gender"],
                    age=voice["age"],
                )
                for voice in voices
            ]
        )


class TTSSettingsOutput(BaseModel):
    data: Dict[str, Any]

    @staticmethod
    def from_output(settings: Dict[str, Any]):
        return TTSSettingsOutput(data=settings)


class TTSFileOutput(BaseModel):
    data: Dict[str, str]

    @staticmethod
    def from_output(file_path: str):
        return TTSFileOutput(
            data={
                "file_path": file_path,
                "message": "Audio file generated successfully",
            }
        )
