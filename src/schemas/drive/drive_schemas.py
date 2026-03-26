from pydantic import BaseModel
from typing import Optional, List


class DriveAuthorizationOutput(BaseModel):
    authorization_url: str
    user_id: str


class DriveStatusOutput(BaseModel):
    is_active: bool
    user_id: str


class DriveFileOutput(BaseModel):
    id: str
    name: str
    mimeType: str
    size: Optional[str] = None
    modifiedTime: Optional[str] = None
    webViewLink: Optional[str] = None
    parents: Optional[List[str]] = None


class DriveFileListOutput(BaseModel):
    files: List[DriveFileOutput]
    total: int


class DriveCredentialsInput(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


class DriveUploadInput(BaseModel):
    file_name: str
    mime_type: str
    folder_id: Optional[str] = None


class DriveUploadOutput(BaseModel):
    id: str
    name: str
    webViewLink: Optional[str] = None


class DriveCreateFolderInput(BaseModel):
    name: str
    parent_id: Optional[str] = None


class DriveFolderOutput(BaseModel):
    id: str
    name: str


class DriveMoveFileInput(BaseModel):
    new_folder_id: str


class DriveMoveFileOutput(BaseModel):
    id: str
    name: str
    parents: Optional[List[str]] = None
