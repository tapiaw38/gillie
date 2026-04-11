from fastapi import APIRouter, status, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from src.core.platform.config.service import (
    get_config_service,
    get_available_providers,
)
from src.core.platform.errors.application_error import ApplicationError
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

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
    user_id = request.state.user.get("user_id", "")
    try:
        profile = usecases.profile.find_by_user_id_usecase.execute(user_id=user_id) if user_id else None
    except ApplicationError:
        profile = None
    profile_data = profile.data if profile else None
    profile_keys = (profile_data.provider_keys if profile_data else None) or {}
    profile_custom = (profile_data.custom_providers if profile_data else None) or {}

    providers = get_available_providers(provider_keys=profile_keys, custom_providers=profile_custom)
    if body.provider not in providers:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    preset = providers[body.provider]
    config = get_config_service()

    api_key = body.api_key or preset.get("api_key", "")

    if user_id:
        usecases.profile.update_provider_usecase.execute(
            user_id=user_id,
            active_provider=body.provider,
            api_key=api_key,
        )

    config.openai_config.base_url = preset["base_url"]
    config.openai_config.model = preset["model"]
    config.openai_config.auth_type = preset["auth_type"]
    config.openai_config.api_key = api_key

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
