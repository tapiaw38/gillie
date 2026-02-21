from pydantic import BaseModel
from typing import List
from datetime import datetime
from src.core.domain import ApiKey


class ApiKeyInput(BaseModel):
    description: str


class ApiKeyOutputData(BaseModel):
    id: str
    value: str
    description: str
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
