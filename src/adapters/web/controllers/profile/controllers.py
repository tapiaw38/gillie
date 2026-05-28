from fastapi import APIRouter, status, Depends, Request, UploadFile, File
from src.schemas import (
    ProfileInput,
    ApiKeyInput,
    FileInput,
    IntegrationInput,
    ContactInput,
)
from typing import List
from src.adapters.web.dependencies import get_usecases
from src.core.use_cases.use_cases import Usecases


router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)


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
