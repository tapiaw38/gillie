from fastapi import APIRouter, Depends, Request, status
from typing import Optional
import logging

from src.schemas.drive import (
    DriveAuthorizationOutput,
    DriveStatusOutput,
    DriveFileOutput,
    DriveFileListOutput,
    DriveIngestOutput,
    DriveSyncOutput,
    DriveSearchInput,
    DriveSearchOutput,
    DriveSearchResultItem,
    DriveIndexStatusOutput,
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
    """List available files in Google Drive (with index status)."""
    user_id = request.state.user.get("user_id")
    files = usecases.drive.list_files_usecase.execute(user_id, folder_id)
    return DriveFileListOutput(
        files=[DriveFileOutput(**f) for f in files],
        total=len(files),
    )


@router.post("/ingest/{file_id}", response_model=DriveIngestOutput, status_code=status.HTTP_200_OK)
async def ingest_file(
    file_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Download and index a specific Drive file into Qdrant."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.ingest_file_usecase.execute(user_id, file_id)
    return DriveIngestOutput(**result)


@router.post("/sync", response_model=DriveSyncOutput, status_code=status.HTTP_200_OK)
async def sync_drive(
    request: Request,
    folder_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """Sync all Drive files to Qdrant. Skips unchanged files (md5 match)."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.sync_drive_usecase.execute(user_id, folder_id)
    return DriveSyncOutput(**result)


@router.post("/search", response_model=DriveSearchOutput, status_code=status.HTTP_200_OK)
async def search_drive(
    body: DriveSearchInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Semantic search over indexed Drive documents using Qdrant."""
    user_id = request.state.user.get("user_id")
    results = usecases.drive.search_drive_usecase.execute(
        user_id=user_id,
        query=body.query,
        k=body.k,
        file_id=body.file_id,
    )
    return DriveSearchOutput(
        query=body.query,
        results=[DriveSearchResultItem(**r) for r in results],
        total=len(results),
    )


@router.get("/index/status", response_model=DriveIndexStatusOutput, status_code=status.HTTP_200_OK)
async def get_index_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get a summary of what's indexed in Qdrant for this user."""
    user_id = request.state.user.get("user_id")
    result = usecases.drive.get_index_status_usecase.execute(user_id)
    return DriveIndexStatusOutput(**result)


@router.delete("/index/{file_id}", status_code=status.HTTP_200_OK)
async def remove_file_index(
    file_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Remove a file's vectors from Qdrant and its index entry from MongoDB."""
    user_id = request.state.user.get("user_id")
    usecases.drive.remove_file_index_usecase.execute(user_id, file_id)
    return {"message": "File index removed", "file_id": file_id}
