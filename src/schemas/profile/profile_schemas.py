from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.core.domain import Profile
from .api_key_schemas import ApiKeyOutput, ApiKeyOutputData
from ..file.file_schemas import FileOutput, FileOutputData
from ..integration.integration_schemas import IntegrationOutput, IntegrationOutputData


class ProfileInput(BaseModel):
    assistant_name: Optional[str] = None
    business_name: Optional[str] = None
    functions: Optional[str] = None
    tool_prompts: Optional[str] = None
    disabled_tools: Optional[List[str]] = None
    tts_enabled: Optional[bool] = None


class ProfileStatusInput(BaseModel):
    is_active: bool


class ProfileOutputData(BaseModel):
    id: str
    user_id: str
    assistant_name: str
    business_name: Optional[str] = None
    functions: Optional[str] = None
    tool_prompts: Optional[str] = None
    disabled_tools: Optional[List[str]] = None
    is_active: bool
    tts_enabled: Optional[bool] = False
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
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
                tool_prompts=profile.tool_prompts,
                disabled_tools=profile.disabled_tools,
                is_active=profile.is_active,
                tts_enabled=profile.tts_enabled or False,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
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
