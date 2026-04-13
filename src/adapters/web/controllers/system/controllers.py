from fastapi import APIRouter, status, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

router = APIRouter(prefix="/system", tags=["system"])


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
    result = usecases.profile.update_provider_usecase.execute(
        user_id=user_id,
        provider_name=body.provider,
        api_key=body.api_key or "",
    )
    return {"data": result}


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


class CompleteInput(BaseModel):
    prefix: str


@router.post("/complete", status_code=status.HTTP_200_OK)
async def shell_complete(
    body: CompleteInput,
    usecases: Usecases = Depends(get_usecases),
):
    suggestion = await usecases.system.shell_complete_usecase.execute(body.prefix)
    return {"suggestion": suggestion}
