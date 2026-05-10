from fastapi import APIRouter, status, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Any, Optional
import logging
from starlette.concurrency import run_in_threadpool
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger(__name__)


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
    result = await run_in_threadpool(
        usecases.profile.update_provider_usecase.execute,
        user_id,
        body.provider,
        body.api_key or "",
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
        await run_in_threadpool(
            usecases.profile.update_provider_usecase.save_custom,
            user_id,
            body.name,
            body.base_url,
            body.model,
            body.auth_type,
            body.api_key or "",
        )

    return {"data": {"name": body.name, "model": body.model}}


class CompleteInput(BaseModel):
    prefix: str
    context: Any = ""


class InlineAssistInput(BaseModel):
    command: str
    context: Any = ""
    exit_code: Optional[int] = None


@router.post("/complete", status_code=status.HTTP_200_OK)
async def shell_complete(
    body: CompleteInput,
    usecases: Usecases = Depends(get_usecases),
):
    logger.info(
        "[system.complete] prefix=%r context_type=%s",
        body.prefix,
        type(body.context).__name__,
    )
    suggestion = await usecases.system.shell_complete_usecase.execute(
        prefix=body.prefix,
        terminal_context=body.context,
    )
    return {"suggestion": suggestion}


@router.post("/inline-assist", status_code=status.HTTP_200_OK)
async def shell_inline_assist(
    body: InlineAssistInput,
    usecases: Usecases = Depends(get_usecases),
):
    logger.info(
        "[system.inline_assist] command=%r exit_code=%r context_type=%s",
        body.command,
        body.exit_code,
        type(body.context).__name__,
    )
    result = await usecases.system.shell_inline_assist_usecase.execute(
        command=body.command,
        terminal_context=body.context,
        exit_code=body.exit_code,
    )
    return result
