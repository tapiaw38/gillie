from pydantic import BaseModel
from typing import Optional, List, Dict, Any


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
    md5Checksum: Optional[str] = None
    modifiedTime: Optional[str] = None
    webViewLink: Optional[str] = None
    index_status: str = "not_indexed"
    chunks_count: int = 0


class DriveFileListOutput(BaseModel):
    files: List[DriveFileOutput]
    total: int


class DriveIngestOutput(BaseModel):
    file_id: str
    file_name: str
    status: str
    chunks: int = 0
    collection: Optional[str] = None
    reason: Optional[str] = None


class DriveSyncOutput(BaseModel):
    total: int
    indexed: int
    skipped: int
    failed: int


class DriveSearchInput(BaseModel):
    query: str
    k: int = 5
    file_id: Optional[str] = None


class DriveSearchResultItem(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any]


class DriveSearchOutput(BaseModel):
    query: str
    results: List[DriveSearchResultItem]
    total: int


class DriveIndexStatusOutput(BaseModel):
    user_id: str
    collection: str
    total_files: int
    indexed: int
    failed: int
    total_chunks: int
