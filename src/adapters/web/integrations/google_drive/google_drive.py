import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from src.services.gdrive.client import GoogleDriveClient

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "google_drive"
INTEGRATION_TYPE = "oauth"


class GoogleDriveIntegration:
    """
    Stateless adapter for Google Drive.
    OAuth tokens are stored in Profile.integrations (per-user).
    App credentials (client_id/secret) are stored in MongoDB drive_sessions collection.
    """

    def __init__(
        self,
        repository=None,
        fallback_client: Optional[GoogleDriveClient] = None,
    ):
        self.repository = repository
        self.fallback_client = fallback_client
        self._pending_verifiers: Dict[str, str] = {}  # user_id -> code_verifier (PKCE)

    def _get_client(self) -> GoogleDriveClient:
        """Load credentials from DB or fall back to env-var client."""
        if self.repository:
            creds = self.repository.find_credentials()
            if creds:
                return GoogleDriveClient(
                    client_id=creds.client_id,
                    client_secret=creds.client_secret,
                    redirect_uri=creds.redirect_uri,
                )
        if self.fallback_client:
            return self.fallback_client
        raise RuntimeError(
            "No Google Drive credentials configured. "
            "Save credentials first via POST /api/v1/drive/credentials."
        )

    def get_authorization_url(self, user_id: str) -> str:
        """Return the Google OAuth2 authorization URL (Drive scope)."""
        auth_url, code_verifier = self._get_client().get_authorization_url(state=user_id)
        if code_verifier:
            self._pending_verifiers[user_id] = code_verifier
        return auth_url

    def handle_oauth_callback(self, user_id: str, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens, using stored PKCE verifier if available."""
        code_verifier = self._pending_verifiers.pop(user_id, None)
        tokens = self._get_client().exchange_code(code, code_verifier=code_verifier)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_expiry": tokens["expiry"].isoformat() if tokens["expiry"] else None,
            "scopes": tokens["scopes"],
        }

    def refresh_if_needed(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check token expiry. If expired, refresh and return updated config dict."""
        expiry_raw = config.get("token_expiry")
        if not expiry_raw:
            return config

        if isinstance(expiry_raw, str):
            try:
                expiry = datetime.fromisoformat(expiry_raw)
            except ValueError:
                return config
        else:
            expiry = expiry_raw

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if expiry > now:
            return config  # still valid

        refreshed = self._get_client().refresh_access_token(config["refresh_token"])
        updated = dict(config)
        updated["access_token"] = refreshed["access_token"]
        updated["token_expiry"] = refreshed["expiry"].isoformat() if refreshed["expiry"] else None
        logger.info("Drive access token refreshed")
        return updated

    def build_service(self, config: Dict[str, Any]):
        """Build an authenticated Google Drive service from a config dict."""
        expiry_raw = config.get("token_expiry")
        if isinstance(expiry_raw, str):
            try:
                expiry = datetime.fromisoformat(expiry_raw)
            except ValueError:
                expiry = None
        else:
            expiry = expiry_raw

        return self._get_client().build_service(
            access_token=config["access_token"],
            refresh_token=config["refresh_token"],
            expiry=expiry,
        )

    def list_files(
        self,
        service,
        folder_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all files and folders in Drive, optionally filtered by folder."""
        return self._get_client().list_files(service, folder_id=folder_id)

    def get_file_metadata(self, service, file_id: str) -> Dict[str, Any]:
        """Get metadata for a single file."""
        return self._get_client().get_file_metadata(service, file_id)

    def download_file(self, service, file_id: str, mime_type: str) -> bytes:
        """Download or export a file, returning raw bytes."""
        return self._get_client().download_or_export(service, file_id, mime_type)

    def upload_file(
        self,
        service,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive."""
        return self._get_client().upload_file(service, file_bytes, file_name, mime_type, folder_id)

    def create_folder(
        self,
        service,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a folder in Google Drive."""
        return self._get_client().create_folder(service, name, parent_id)

    def move_file(
        self,
        service,
        file_id: str,
        new_folder_id: str,
    ) -> Dict[str, Any]:
        """Move a file to a different folder in Google Drive."""
        return self._get_client().move_file(service, file_id, new_folder_id)
