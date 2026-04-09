from fastapi import APIRouter, status, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from src.core.platform.config.service import (
    get_config_service,
    get_available_providers,
)
from src.core.use_cases.use_cases import Usecases

_usecases_instance = None

def set_usecases(usecases: Usecases):
    global _usecases_instance
    _usecases_instance = usecases

def get_usecases() -> Usecases:
    if _usecases_instance is None:
        raise Exception("Usecases not initialized")
    return _usecases_instance

router = APIRouter(prefix="/system", tags=["system"])

_openai_integration = None


def set_openai_integration(integration) -> None:
    global _openai_integration
    _openai_integration = integration


class ProviderInput(BaseModel):
    provider: str
    api_key: Optional[str] = None


class CustomProviderInput(BaseModel):
    name: str
    base_url: str
    model: str
    auth_type: str = "api_key"
    api_key: Optional[str] = ""


@router.post("/provider", status_code=status.HTTP_200_OK)
async def set_provider(
    body: ProviderInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    providers = get_available_providers()
    if body.provider not in providers:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    preset = providers[body.provider]
    config = get_config_service()

    # Resolve API key: request body → stored keys → current config
    api_key = body.api_key or preset.get("api_key") or config.openai_config.api_key

    # Persist active provider and key in profile
    user_id = request.state.user.get("user_id", "")
    if user_id:
        usecases.profile.update_provider_usecase.execute(
            user_id=user_id,
            active_provider=body.provider,
            api_key=api_key,
        )

    # Update in-memory config
    config.openai_config.base_url = preset["base_url"]
    config.openai_config.model = preset["model"]
    config.openai_config.auth_type = preset["auth_type"]
    config.openai_config.api_key = api_key

    # Hot-reload LLM
    if _openai_integration is not None:
        _openai_integration.reload_provider(
            base_url=preset["base_url"],
            model=preset["model"],
            api_key=api_key,
            auth_type=preset["auth_type"],
        )

    return {"data": {"provider": body.provider, "model": preset["model"]}}


@router.post("/provider/custom", status_code=status.HTTP_201_CREATED)
async def add_provider(
    body: CustomProviderInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    if not body.name or not body.base_url or not body.model:
        raise HTTPException(status_code=400, detail="name, base_url and model are required")

    user_id = request.state.user.get("user_id", "")
    if user_id:
        usecases.profile.update_provider_usecase.save_custom(
            user_id=user_id,
            name=body.name,
            base_url=body.base_url,
            model=body.model,
            auth_type=body.auth_type,
            api_key=body.api_key or "",
        )

    return {"data": {"name": body.name, "model": body.model}}
