from fastapi import APIRouter, status, Depends, Request, UploadFile, File
from src.schemas import (
    ProfileInput,
    ProfileStatusInput,
    ApiKeyInput,
    FileInput,
    IntegrationInput,
)
from typing import List
from src.core.use_cases.use_cases import Usecases


router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)

_usecases_instance = None

def set_usecases(usecases: Usecases):
    """Set the usecases instance (called during app initialization)"""
    global _usecases_instance
    _usecases_instance = usecases

def get_usecases() -> Usecases:
    """Get the usecases instance for dependency injection"""
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile: ProfileInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    profile = usecases.profile.create_usecase.execute(profile, user_id)
    return profile


@router.get("/", status_code=status.HTTP_200_OK)
async def find_profile_by_user_id(
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    profile = usecases.profile.find_by_user_id_usecase.execute(user_id)
    return profile

@router.patch("/", status_code=status.HTTP_200_OK)
async def update_profile(
    profile: ProfileInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    profile = usecases.profile.update_usecase.execute(user_id, profile)
    return profile


@router.post("/status", status_code=status.HTTP_200_OK)
async def change_status(
    status_input: ProfileStatusInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    profile = usecases.profile.change_status_usecase.execute(user_id, status_input.is_active)
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
    api_key_id = await usecases.profile.delete_api_key_usecase.execute(user_id, api_key_id)
    return api_key_id


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
    file_id = await usecases.profile.delete_file_by_id_usecase.execute(user_id, file_id)
    return file_id

@router.post("/integrations", status_code=status.HTTP_201_CREATED)
async def add_integration(
    integration: IntegrationInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    integration = await usecases.profile.add_integration_usecase.execute(user_id, integration)
    return integration

@router.get("/options", status_code=status.HTTP_200_OK)
async def list_options(
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    list_options = usecases.profile.list_options_usecase.execute()
    return list_options