from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from src.core.domain.model import (
    Profile,
    Conversation,
    Message,
    ApiKey,
)
from datetime import datetime
from fastapi import UploadFile


class ConversationInput(BaseModel):
    title: str


class MessageInput(BaseModel):
    content: str
    context: Optional[str]
    voice_content: Optional[UploadFile] = None


class ApiKeyInput(BaseModel):
    description: str


class ApiKeyOutputData(BaseModel):
    id: str
    value: str
    description: str
    limit: int
    is_active: bool
    created_at: datetime


class ApiKeyOutput(BaseModel):
    data: ApiKeyOutputData

    @staticmethod
    def from_output(api_key: ApiKey):
        return ApiKeyOutput(
            data=ApiKeyOutputData(
                id=api_key.id,
                value=api_key.value,
                description=api_key.description,
                limit=api_key.limit,
                is_active=api_key.is_active,
                created_at=api_key.created_at,
            )
        )


class ApiKeyListOutput(BaseModel):
    data: List[ApiKeyOutputData]

    @staticmethod
    def from_output(api_keys: list[ApiKey]):
        return ApiKeyListOutput(
            data=[ApiKeyOutput.from_output(api_key).data for api_key in api_keys]
        )


class ApiKeyDeleteOutputData(BaseModel):
    id: str


class ApiKeyDeleteOutput(BaseModel):
    data: ApiKeyDeleteOutputData

    @staticmethod
    def from_output(api_key_id: str):
        return ApiKeyDeleteOutput(
            data=ApiKeyDeleteOutputData(
                id=api_key_id,
            )
        )


class FileInput:
    def __init__(self, file: UploadFile):
        if not file:
            raise ValueError("File object cannot be None")
        if not hasattr(file, "filename"):
            raise ValueError("UploadFile object missing 'filename' attribute")

        if not hasattr(file, "file"):
            raise ValueError("UploadFile object missing 'file' attribute")

        self.filename = file.filename
        self.file = file.file
        self.file_header = getattr(file, "headers", {})

        try:
            if hasattr(file, "size") and file.size is not None:
                self.filesize = file.size
                print(f"FileInput init - size from file.size: {self.filesize}")
            elif (
                self.file
                and hasattr(self.file, "_file")
                and hasattr(self.file._file, "tell")
            ):
                current_pos = self.file._file.tell()
                self.file._file.seek(0, 2)  # Ir al final
                self.filesize = self.file._file.tell()
                self.file._file.seek(current_pos)  # Volver a la posición original
                print(f"FileInput init - size from file._file.tell(): {self.filesize}")
            else:
                self.filesize = 0
                print("FileInput init - size defaulted to 0")
        except (AttributeError, OSError, TypeError) as e:
            print(f"FileInput init - error getting size: {e}")
            self.filesize = 0

        if not self.file:
            raise ValueError(f"File content is None for file: {self.filename}")

        print(
            f"FileInput init completed - filename: {self.filename}, size: {self.filesize}"
        )

    def __repr__(self):
        return f"FileInput(filename='{self.filename}', filesize={self.filesize}, file_type={type(self.file)})"


class FileOutputData(BaseModel):
    id: str
    name: str
    url: str


class FileOutput(BaseModel):
    data: FileOutputData

    @staticmethod
    def from_output(file: FileOutputData):
        return FileOutput(
            data=FileOutputData(
                id=file.id,
                name=file.name,
                url=file.url,
            )
        )


class FileListOutput(BaseModel):
    data: List[FileOutputData]

    @staticmethod
    def from_output(files: list[FileOutputData]):
        return FileListOutput(
            data=[FileOutput.from_output(file).data for file in files]
        )


class FileDeleteOutputData(BaseModel):
    id: str


class FileDeleteOutput(BaseModel):
    data: FileDeleteOutputData

    @staticmethod
    def from_output(file_id: str):
        return FileDeleteOutput(
            data=FileDeleteOutputData(
                id=file_id,
            )
        )


class IntegrationInput(BaseModel):
    name: str
    type: str
    activated: bool
    config: dict


class IntegrationOutputData(BaseModel):
    id: str
    name: str
    type: str
    activated: bool
    config: dict
    created_at: datetime
    updated_at: Optional[datetime] = None


class IntegrationOutput(BaseModel):
    data: IntegrationOutputData

    @staticmethod
    def from_output(integration: IntegrationOutputData):
        return IntegrationOutput(
            data=IntegrationOutputData(
                id=integration.id,
                name=integration.name,
                type=integration.type,
                activated=integration.activated,
                config=integration.config,
                created_at=integration.created_at,
                updated_at=integration.updated_at if integration.updated_at else None,
            )
        )


class IntegrationListOutput(BaseModel):
    data: List[IntegrationOutputData]

    @staticmethod
    def from_output(integrations: list[IntegrationOutputData]):
        return IntegrationListOutput(
            data=[
                IntegrationOutput.from_output(integration).data
                for integration in integrations
            ]
        )


class ProfileInput(BaseModel):
    assistant_name: Optional[str] = None
    business_name: Optional[str] = None
    functions: Optional[str] = None
    business_context: Optional[str] = None
    role: Optional[str] = None


class ProfileStatusInput(BaseModel):
    is_active: bool


class ProfileOutputData(BaseModel):
    id: str
    user_id: str
    assistant_name: str
    business_name: str
    functions: str
    business_context: str
    role: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    iteration_limit: Optional[int]
    api_keys: Optional[List[ApiKeyOutputData]]
    files: Optional[List[FileOutputData]]
    integrations: Optional[List[IntegrationOutputData]]


class ProfileOutput(BaseModel):
    data: ProfileOutputData

    @staticmethod
    def from_output(profile: Profile):
        return ProfileOutput(
            data=ProfileOutputData(
                id=profile.id,
                user_id=profile.user_id,
                assistant_name=profile.assistant_name,
                business_name=profile.business_name,
                functions=profile.functions,
                business_context=profile.business_context,
                is_active=profile.is_active,
                role=profile.role,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
                iteration_limit=profile.iteration_limit,
                api_keys=(
                    [
                        ApiKeyOutput.from_output(api_key).data
                        for api_key in profile.api_keys
                    ]
                    if profile.api_keys
                    else None
                ),
                files=(
                    [FileOutput.from_output(file).data for file in profile.files]
                    if profile.files
                    else None
                ),
                integrations=(
                    [
                        IntegrationOutput.from_output(integration).data
                        for integration in profile.integrations
                    ]
                    if profile.integrations
                    else None
                ),
            )
        )


class ConversationOutputData(BaseModel):
    id: Optional[str]
    title: str
    created_at: datetime
    client_id: str
    profile: Profile
    messages: Optional[List[Message]]


class ConversationOutput(BaseModel):
    data: ConversationOutputData

    @staticmethod
    def from_output(conversation: Conversation):
        return ConversationOutput(
            data=ConversationOutputData(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                client_id=conversation.client_id,
                profile=conversation.profile,
                messages=conversation.messages,
            )
        )


class ConversationListOutput(BaseModel):
    data: List[ConversationOutputData]

    @staticmethod
    def from_output(conversations: list[Conversation]):
        return ConversationListOutput(
            data=[
                ConversationOutput.from_output(conversation).data
                for conversation in conversations
            ]
        )


class MessageOutputData(BaseModel):
    id: str
    content: str
    audio_url: Optional[str] = None
    sender: str
    created_at: datetime


class MessageOutput(BaseModel):
    data: MessageOutputData

    @staticmethod
    def from_output(message: Message):
        return MessageOutput(
            data=MessageOutputData(
                id=message.id,
                content=message.content,
                audio_url=message.audio_url,
                sender=message.sender,
                created_at=message.created_at,
            )
        )


class MessageListOutput(BaseModel):
    data: List[MessageOutputData]

    @staticmethod
    def from_output(messages: list[Message]):
        return MessageListOutput(
            data=[MessageOutput.from_output(message).data for message in messages]
        )


# TTS Schemas
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


# STT Schemas
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


class RoleOutputData(BaseModel):
    code: str
    name: str


class RoleOutput(BaseModel):
    data: RoleOutputData
    @staticmethod
    def from_output(role):
        return RoleOutput(
            data=RoleOutputData(
                code=role.code,
                name=role.name,
            )
        )


class ListOptionsOutputData(BaseModel):
    """Output data structure for role list options"""
    roles: List[RoleOutputData]


class ListOptionsOutput(BaseModel):
    """Main output structure for role list options"""
    data: ListOptionsOutputData
    @staticmethod
    def from_output(roles: List):
        role_data = []
        for role in roles:
            role_data.append(
                RoleOutputData(
                    code=role.code,
                    name=role.name,
                )
            )

        return ListOptionsOutput(data=ListOptionsOutputData(roles=role_data))