from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


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
