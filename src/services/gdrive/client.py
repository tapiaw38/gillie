import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DRIVE_MIME_TYPES = {
    "application/vnd.google-apps.document":       "gdoc",
    "application/vnd.google-apps.spreadsheet":    "gsheet",
    "application/vnd.google-apps.presentation":   "gslides",
    "application/pdf":                            "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":   "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":         "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-excel":                   "xls",
    "text/plain":                                  "txt",
    "text/csv":                                    "csv",
}

EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document":     "application/pdf",
    "application/vnd.google-apps.spreadsheet":  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation": "application/pdf",
}

EXPORT_EXT_MAP = {
    "application/vnd.google-apps.document":     ".pdf",
    "application/vnd.google-apps.spreadsheet":  ".xlsx",
    "application/vnd.google-apps.presentation": ".pdf",
    "application/pdf":                          ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":       ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/csv":   ".csv",
}


class GoogleDriveClient:
    """
    Wrapper for the Google Drive API v3.
    Uses full drive scope to support read/write operations.
    Requires: google-api-python-client, google-auth, google-auth-oauthlib
    """

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Return the Google OAuth2 authorization URL (Drive scope only)."""
        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        return auth_url

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        flow = self._build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry,
            "scopes": list(creds.scopes or self.SCOPES),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        creds.refresh(Request())
        return {"access_token": creds.token, "expiry": creds.expiry}

    def build_service(self, access_token: str, refresh_token: str, expiry: datetime):
        """Build an authenticated Google Drive service object."""
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def list_files(
        self,
        service,
        folder_id: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List all files and folders in Drive (or a specific folder).
        Does not filter by MIME type — returns everything including folders.
        """
        query = "trashed=false"

        if folder_id:
            query += f" and '{folder_id}' in parents"

        fields = "files(id,name,mimeType,size,modifiedTime,webViewLink,parents)"
        results = (
            service.files()
            .list(q=query, pageSize=page_size, fields=fields)
            .execute()
        )
        files = results.get("files", [])
        logger.info(f"Listed {len(files)} files from Google Drive")
        return files

    def upload_file(
        self,
        service,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive. Optionally place it inside a folder."""
        import io
        from googleapiclient.http import MediaIoBaseUpload

        metadata: Dict[str, Any] = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]

        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
        result = (
            service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name,mimeType,webViewLink,parents",
            )
            .execute()
        )
        logger.info(f"Uploaded file '{file_name}' to Google Drive: {result.get('id')}")
        return result

    def create_folder(
        self,
        service,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a folder in Google Drive. Optionally nest it under a parent folder."""
        metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        result = (
            service.files()
            .create(body=metadata, fields="id,name,mimeType,parents")
            .execute()
        )
        logger.info(f"Created Drive folder '{name}': {result.get('id')}")
        return result

    def move_file(
        self,
        service,
        file_id: str,
        new_folder_id: str,
    ) -> Dict[str, Any]:
        """Move a file to a different folder by updating its parents."""
        current = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(current.get("parents", []))

        result = (
            service.files()
            .update(
                fileId=file_id,
                addParents=new_folder_id,
                removeParents=previous_parents,
                fields="id,name,mimeType,parents",
            )
            .execute()
        )
        logger.info(f"Moved Drive file {file_id} to folder {new_folder_id}")
        return result

    def get_file_metadata(self, service, file_id: str) -> Dict[str, Any]:
        """Get metadata for a single file."""
        fields = "id,name,mimeType,md5Checksum,size,modifiedTime,webViewLink"
        return service.files().get(fileId=file_id, fields=fields).execute()

    def download_or_export(self, service, file_id: str, mime_type: str) -> bytes:
        """
        Download a file or export a Google Workspace file to a processable format.
        Returns raw bytes.
        """
        from googleapiclient.http import MediaIoBaseDownload
        import io

        export_mime = EXPORT_MIME_MAP.get(mime_type)

        if export_mime:
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            logger.info(f"Exporting Drive file {file_id} ({mime_type}) → {export_mime}")
        else:
            request = service.files().get_media(fileId=file_id)
            logger.info(f"Downloading Drive file {file_id} ({mime_type})")

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    @staticmethod
    def get_file_extension(mime_type: str) -> str:
        """Return the file extension for a given MIME type (after export if needed)."""
        return EXPORT_EXT_MAP.get(mime_type, ".bin")

    @staticmethod
    def is_supported(mime_type: str) -> bool:
        return mime_type in DRIVE_MIME_TYPES

    def _build_flow(self):
        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )
