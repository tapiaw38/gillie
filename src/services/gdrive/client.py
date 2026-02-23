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
    Uses its own OAuth2 scopes (drive.readonly), completely separate from Calendar.
    Requires: google-api-python-client, google-auth, google-auth-oauthlib
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

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
        List files in Drive (or a specific folder).
        Returns only supported MIME types.
        """
        supported = list(DRIVE_MIME_TYPES.keys())
        mime_filter = " or ".join(f"mimeType='{m}'" for m in supported)
        query = f"({mime_filter}) and trashed=false"

        if folder_id:
            query += f" and '{folder_id}' in parents"

        fields = "files(id,name,mimeType,md5Checksum,size,modifiedTime,webViewLink)"
        results = (
            service.files()
            .list(q=query, pageSize=page_size, fields=fields)
            .execute()
        )
        files = results.get("files", [])
        logger.info(f"Listed {len(files)} files from Google Drive")
        return files

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
