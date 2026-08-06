import time

from fastapi import APIRouter, status, Depends, Request, UploadFile, File, Form, HTTPException
from pathlib import Path
from uuid import uuid4
from asyncio import to_thread
import os
import subprocess
from src.schemas import (
    ProfileInput,
    ApiKeyInput,
    FileInput,
    IntegrationInput,
    ContactInput,
    WorkflowStepTestInput,
)
from typing import List
from src.adapters.web.dependencies import get_usecases
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileFunctionStepBlockedError
from src.core.platform.functions.workflow_executor import WorkflowError, WorkflowExecutor
from src.core.use_cases.use_cases import Usecases


router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)

_AVATAR_EXTENSIONS = {"model": ".vrm", "animation": ".vrma"}


def _avatar_assets(profile):
    assets = profile.avatar_assets or []
    return {
        "model": next((asset for asset in assets if asset.get("type") == "model"), None),
        "animations": sorted(
            [asset for asset in assets if asset.get("type") == "animation"],
            key=lambda asset: asset.get("name", "").lower(),
        ),
    }


async def _save_avatar_profile(request: Request, profile, assets):
    profile.avatar_assets = assets
    await request.app.state.repositories.profile.update(profile.id, profile)
    return _avatar_assets(profile)


@router.get("/avatar/assets", status_code=status.HTTP_200_OK)
async def list_avatar_assets(request: Request):
    profile = await request.app.state.repositories.profile.find_by_user_id(
        request.state.user.get("user_id")
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"data": _avatar_assets(profile)}


@router.post("/avatar/assets", status_code=status.HTTP_200_OK)
async def upload_avatar_asset(
    request: Request,
    asset_type: str = Form(...),
    file: UploadFile = File(...),
):
    if asset_type not in _AVATAR_EXTENSIONS:
        raise HTTPException(status_code=400, detail="asset_type must be model or animation")
    filename = os.path.basename(file.filename or "")
    extension = Path(filename).suffix.lower()
    if extension != _AVATAR_EXTENSIONS[asset_type]:
        raise HTTPException(status_code=400, detail=f"Expected {_AVATAR_EXTENSIONS[asset_type]} file")

    user_id = request.state.user.get("user_id")
    profile = await request.app.state.repositories.profile.find_by_user_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    existing = profile.avatar_assets or []
    if asset_type == "model":
        old = next((asset for asset in existing if asset.get("type") == "model"), None)
        if old:
            await to_thread(request.app.state.store_service.delete_object, old["key"])
        existing = [asset for asset in existing if asset.get("type") != "model"]
    else:
        old = next(
            (asset for asset in existing if asset.get("type") == "animation" and asset.get("name") == filename),
            None,
        )
        if old:
            await to_thread(request.app.state.store_service.delete_object, old["key"])
        existing = [
            asset for asset in existing
            if not (asset.get("type") == "animation" and asset.get("name") == filename)
        ]

    key = await to_thread(
        request.app.state.store_service.put_object,
        file.file,
        f"avatar/{user_id}",
        filename,
        file.size or 0,
        str(uuid4()),
    )
    asset = {
        "type": asset_type,
        "name": "model.vrm" if asset_type == "model" else filename,
        "key": key,
        "url": request.app.state.store_service.generate_url(key),
    }
    existing.append(asset)
    return {"data": await _save_avatar_profile(request, profile, existing)}


@router.delete("/avatar/assets/{asset_type}/{name}", status_code=status.HTTP_200_OK)
async def delete_avatar_asset(asset_type: str, name: str, request: Request):
    if asset_type != "animation" or Path(name).name != name:
        raise HTTPException(status_code=400, detail="Only animation removal is supported")
    profile = await request.app.state.repositories.profile.find_by_user_id(request.state.user.get("user_id"))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    assets = profile.avatar_assets or []
    target = next((asset for asset in assets if asset.get("type") == "animation" and asset.get("name") == name), None)
    if not target:
        raise HTTPException(status_code=404, detail="Animation not found")
    await to_thread(request.app.state.store_service.delete_object, target["key"])
    return {"data": await _save_avatar_profile(request, profile, [asset for asset in assets if asset is not target])}


@router.post("/avatar/assets/rebuild", status_code=status.HTTP_200_OK)
async def rebuild_remote_avatar(request: Request):
    """Materialize remote assets on VPS, regenerate manifest, then build avatar."""
    profile = await request.app.state.repositories.profile.find_by_user_id(request.state.user.get("user_id"))
    assets = profile.avatar_assets if profile else []
    model = next((asset for asset in assets if asset.get("type") == "model"), None)
    if not model:
        raise HTTPException(status_code=400, detail="A model is required")
    avatar_dir = Path(__file__).resolve().parents[5] / "avatar"
    asset_dir = avatar_dir / "public" / "assets"
    animation_dir = asset_dir / "animations"
    animation_dir.mkdir(parents=True, exist_ok=True)
    for old_asset in animation_dir.glob("*.vrma"):
        old_asset.unlink()
    await to_thread((asset_dir / "model.vrm").write_bytes, await to_thread(request.app.state.store_service.get_object, model["key"]))
    for asset in assets:
        if asset.get("type") == "animation":
            await to_thread((animation_dir / asset["name"]).write_bytes, await to_thread(request.app.state.store_service.get_object, asset["key"]))
    for command in (("npm", "run", "assets:generate"), ("npm", "run", "build")):
        result = await to_thread(subprocess.run, command, cwd=avatar_dir, capture_output=True, text=True)
        if result.returncode:
            raise HTTPException(status_code=500, detail=result.stderr[-2000:])
    return {"data": _avatar_assets(profile)}


@router.get("/", status_code=status.HTTP_200_OK)
async def find_profile(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    profile = await usecases.profile.find_by_user_id_usecase.execute(user_id)
    return profile


@router.patch("/", status_code=status.HTTP_200_OK)
async def update_profile(
    profile: ProfileInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    profile = await usecases.profile.update_usecase.execute(user_id, profile)
    return profile


@router.post("/api-key", status_code=status.HTTP_201_CREATED)
async def add_api_key(
    api_key: ApiKeyInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    api_keys = await usecases.profile.add_api_key_usecase.execute(api_key, user_id)
    return api_keys


@router.delete("/api-key/{api_key_id}", status_code=status.HTTP_200_OK)
async def delete_api_key(
    api_key_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    result = await usecases.profile.delete_api_key_usecase.execute(user_id, api_key_id)
    return result


@router.post("/files/upload", status_code=status.HTTP_200_OK)
async def upload_files(
    files: List[UploadFile] = File(...),
    request: Request = None,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    file_inputs = [FileInput(f) for f in files]
    files = await usecases.profile.add_files_usecase.execute(user_id, file_inputs)
    return files


@router.get("/files/status", status_code=status.HTTP_200_OK)
async def get_files_vector_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    return await usecases.profile.get_files_vector_status_usecase.execute(user_id)


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    result = await usecases.profile.delete_file_by_id_usecase.execute(user_id, file_id)
    return result


@router.post("/integrations", status_code=status.HTTP_201_CREATED)
async def add_integration(
    integration: IntegrationInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    integration = await usecases.profile.add_integration_usecase.execute(user_id, integration)
    return integration


@router.delete("/integrations/{integration_id}", status_code=status.HTTP_200_OK)
async def delete_integration(
    integration_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    result = await usecases.profile.delete_integration_usecase.execute(user_id, integration_id)
    return result


@router.post("/functions/test-step", status_code=status.HTTP_200_OK)
async def test_workflow_step(
    payload: WorkflowStepTestInput,
    request: Request,
):
    """Run a single workflow step and return the raw response.

    Writing `response_mapping` means knowing the shape of the response, and
    without this the only way to find out was to save the workflow, send a
    real message and read the server logs.
    """
    executor = WorkflowExecutor()
    context = dict(payload.context or {})
    context.setdefault("user_id", request.state.user.get("user_id"))

    started = time.monotonic()
    try:
        result = await executor.execute_single_step(
            payload.step.model_dump(exclude_none=True), context
        )
    except WorkflowError as e:
        raise NewApplicationError(ProfileFunctionStepBlockedError, e)
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }

    return {
        "ok": True,
        "response": result,
        "paths": _describe_paths(result),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


def _describe_paths(node, prefix: str = "", depth: int = 0) -> List[str]:
    """Flatten a response into dot-paths so the editor can offer them for mapping."""
    if depth > 4:
        return []
    paths: List[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                paths.extend(_describe_paths(value, path, depth + 1))
            else:
                paths.append(path)
    elif isinstance(node, list) and node:
        paths.extend(_describe_paths(node[0], f"{prefix}.0" if prefix else "0", depth + 1))
    return paths[:100]


@router.get("/options", status_code=status.HTTP_200_OK)
async def list_options(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id", "")
    return await usecases.profile.list_options_usecase.execute(user_id)


@router.get("/contacts", status_code=status.HTTP_200_OK)
async def list_contacts(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return await usecases.profile.list_contacts_usecase.execute(user_id)


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
async def add_contact(
    contact: ContactInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return await usecases.profile.add_contact_usecase.execute(user_id, contact)


@router.patch("/contacts/{contact_id}", status_code=status.HTTP_200_OK)
async def update_contact(
    contact_id: str,
    contact: ContactInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return await usecases.profile.update_contact_usecase.execute(user_id, contact_id, contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_200_OK)
async def delete_contact(
    contact_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return await usecases.profile.delete_contact_usecase.execute(user_id, contact_id)
