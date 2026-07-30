from pydantic import BaseModel
from typing import List


class RoleOutputData(BaseModel):
    code: str
    name: str


class ProviderOutputData(BaseModel):
    key: str
    model: str
    base_url: str = ""
    auth_type: str = "api_key"
    api_key_set: bool = False
    is_builtin: bool = True


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


class VoiceOptionData(BaseModel):
    """A single selectable voice within a speech engine"""
    id: str
    label: str


class VoiceEngineOutputData(BaseModel):
    """A speech engine and the voices it offers"""
    key: str
    label: str
    description: str = ""
    requires_key: bool = False
    key_available: bool = True
    voices: List[VoiceOptionData] = []


class ListOptionsOutputData(BaseModel):
    """Output data structure for role list options"""
    roles: List[RoleOutputData]
    providers: List[ProviderOutputData] = []
    active_provider: str = ""
    voice_engines: List[VoiceEngineOutputData] = []


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
