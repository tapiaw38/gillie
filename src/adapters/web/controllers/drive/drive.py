from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, status
from fastapi.responses import Response
from typing import Optional
import logging

from src.schemas.drive import (
    DriveAuthorizationOutput,
    DriveStatusOutput,
    DriveFileOutput,
    DriveFileListOutput,
    DriveUploadOutput,
    DriveCreateFolderInput,
    DriveFolderOutput,
    DriveMoveFileInput,
    DriveMoveFileOutput,
    DriveCredentialsInput,
)
from src.core.use_cases.use_cases import Usecases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drive", tags=["drive"])

_usecases_instance = None


def set_usecases(usecases: Usecases):
    global _usecases_instance
    _usecases_instance = usecases


def get_usecases() -> Usecases:
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


@router.post("/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def save_credentials(
    body: DriveCredentialsInput,
    usecases: Usecases = Depends(get_usecases),
):
    """Save Google Drive OAuth app credentials to MongoDB."""
    redirect_uri = body.redirect_uri or "http://localhost:8000/api/v1/drive/oauth/callback"
    usecases.drive.set_credentials_usecase.execute(body.client_id, body.client_secret, redirect_uri)


@router.get("/authorize", response_model=DriveAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get Google Drive OAuth authorization URL."""
    user_id = request.state.user.get("user_id")
    auth_url = usecases.drive.get_authorization_url_usecase.execute(user_id)
    return DriveAuthorizationOutput(authorization_url=auth_url, user_id=user_id)


@router.get("/oauth/callback", status_code=status.HTTP_200_OK)
async def oauth_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """Handle Google Drive OAuth2 callback. `state` carries the user_id."""
    user_id = state or request.state.user.get("user_id")
    result = usecases.drive.handle_oauth_callback_usecase.execute(user_id=user_id, code=code)
    return {"message": "Google Drive connected successfully", **result}


@router.get("/status", response_model=DriveStatusOutput, status_code=status.HTTP_200_OK)
async def check_drive_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Check if the user has an active Google Drive session."""
    user_id = request.state.user.get("user_id")
    is_active = usecases.drive.check_session_status_usecase.execute(user_id)
    return DriveStatusOutput(is_active=is_active, user_id=user_id)


@router.get("/files", response_model=DriveFileListOutput, status_code=status.HTTP_200_OK)
async def list_files(
    request: Request,
    folder_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """List all files and folders in Google Drive."""
    user_id = request.state.user.get("user_id")
    files = usecases.drive.list_files_usecase.execute(user_id, folder_id)
    return DriveFileListOutput(
        files=[DriveFileOutput(**f) for f in files],
        total=len(files),
    )


@router.get("/files/{file_id}", response_model=DriveFileOutput, status_code=status.HTTP_200_OK)
async def get_file_metadata(
    file_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get metadata for a specific file in Google Drive."""
    from src.core.platform.errors import NewApplicationError
    from src.core.platform.errors.mappings.drive import DriveOperationError
    from src.core.use_cases.drive._helpers import get_drive_service

    user_id = request.state.user.get("user_id")
    # Access context via any use case that holds it
    ctx = usecases.drive.list_files_usecase.context_factory
    service = get_drive_service(ctx, user_id)
    meta = ctx.integrations.google_drive.get_file_metadata(service, file_id)
    return DriveFileOutput(**meta)


@router.get("/files/{file_id}/download", status_code=status.HTTP_200_OK)
async def download_file(
    file_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Download a file from Google Drive."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.download_file_usecase.execute(user_id, file_id)
    file_name = result["file_name"]
    mime_type = result["mime_type"] or "application/octet-stream"
    return Response(
        content=result["content"],
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/files/upload", response_model=DriveUploadOutput, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(default=None),
    usecases: Usecases = Depends(get_usecases),
):
    """Upload a file to Google Drive."""
    user_id = request.state.user.get("user_id")
    file_bytes = await file.read()
    result = usecases.drive.upload_file_usecase.execute(
        user_id=user_id,
        file_bytes=file_bytes,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        folder_id=folder_id,
    )
    return DriveUploadOutput(**result)


@router.post("/folders", response_model=DriveFolderOutput, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: DriveCreateFolderInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Create a new folder in Google Drive."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.create_folder_usecase.execute(
        user_id=user_id,
        name=body.name,
        parent_id=body.parent_id,
    )
    return DriveFolderOutput(**result)


@router.patch("/files/{file_id}/move", response_model=DriveMoveFileOutput, status_code=status.HTTP_200_OK)
async def move_file(
    file_id: str,
    body: DriveMoveFileInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Move a file to a different folder in Google Drive."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.move_file_usecase.execute(
        user_id=user_id,
        file_id=file_id,
        new_folder_id=body.new_folder_id,
    )
    return DriveMoveFileOutput(**result)
