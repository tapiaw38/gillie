import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from src.services.gdrive.client import GoogleDriveClient
from src.services.gdrive.ingestion import DriveIngestionService

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "google_drive"
INTEGRATION_TYPE = "oauth"


class GoogleDriveIntegration:
    """
    Stateless adapter for Google Drive.
    Does NOT store OAuth tokens internally — tokens are managed by the caller
    (stored in Profile.integrations via the profile repository).
    """

    def __init__(self, client: GoogleDriveClient, ingestion: DriveIngestionService):
        self.client = client
        self.ingestion = ingestion

    # ── OAuth helpers (no state stored here) ──────────────────────────────────

    def get_authorization_url(self, user_id: str) -> str:
        """Return the Google OAuth2 authorization URL (Drive scope)."""
        return self.client.get_authorization_url(state=user_id)

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        Returns a dict ready to be saved in Profile.integrations[].config.
        """
        tokens = self.client.exchange_code(code)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_expiry": tokens["expiry"].isoformat() if tokens["expiry"] else None,
            "scopes": tokens["scopes"],
        }

    def refresh_if_needed(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check token expiry. If expired, refresh and return updated config dict.
        If still valid, return config unchanged.
        """
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

        # Need refresh
        refreshed = self.client.refresh_access_token(config["refresh_token"])
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

        return self.client.build_service(
            access_token=config["access_token"],
            refresh_token=config["refresh_token"],
            expiry=expiry,
        )

    # ── Files ─────────────────────────────────────────────────────────────────

    def list_files(
        self,
        service,
        user_id: str,
        folder_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List Drive files enriched with Qdrant index status."""
        files = self.client.list_files(service, folder_id=folder_id)
        for f in files:
            meta = self.ingestion.get_file_index_meta(user_id, f["id"])
            f["index_status"] = meta.get("index_status", "not_indexed") if meta else "not_indexed"
            f["chunks_count"] = meta.get("chunks_count", 0) if meta else 0
        return files

    def ingest_file(
        self,
        service,
        user_id: str,
        file_id: str,
    ) -> Dict[str, Any]:
        """Download and index a single Drive file into Qdrant."""
        meta = self.client.get_file_metadata(service, file_id)
        mime_type = meta.get("mimeType", "")
        file_name = meta.get("name", file_id)

        if not GoogleDriveClient.is_supported(mime_type):
            return {"status": "skipped", "reason": f"unsupported mime type: {mime_type}",
                    "file_id": file_id, "file_name": file_name, "chunks": 0}

        # Dedup via Qdrant: skip if md5 hasn't changed
        drive_md5 = meta.get("md5Checksum")
        existing_meta = self.ingestion.get_file_index_meta(user_id, file_id)
        if existing_meta and existing_meta.get("md5_checksum") == drive_md5 and drive_md5:
            logger.info(f"Skipping '{file_name}' — already indexed (same md5)")
            return {
                "status": "skipped",
                "reason": "already up to date",
                "file_id": file_id,
                "file_name": file_name,
                "chunks": existing_meta.get("chunks_count", 0),
            }

        # Remove old vectors if re-indexing
        if existing_meta:
            self.ingestion.delete_file_vectors(file_id, user_id)

        # Download / export
        file_bytes = self.client.download_or_export(service, file_id, mime_type)
        ext = GoogleDriveClient.get_file_extension(mime_type)

        result = self.ingestion.ingest(
            file_bytes=file_bytes,
            original_mime=mime_type,
            file_extension=ext,
            metadata={
                "file_id": file_id,
                "file_name": file_name,
                "mime_type": mime_type,
                "md5_checksum": drive_md5 or "",
                "web_view_link": meta.get("webViewLink", ""),
                "chunks_count": 0,         # will be updated after ingest
                "index_status": "indexed",
            },
            user_id=user_id,
        )

        return {"file_id": file_id, "file_name": file_name, **result}

    def sync(
        self,
        service,
        user_id: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sync all supported Drive files. Returns a summary."""
        files = self.client.list_files(service, folder_id=folder_id)
        results = {"total": len(files), "indexed": 0, "skipped": 0, "failed": 0}

        for f in files:
            try:
                r = self.ingest_file(service, user_id, f["id"])
                if r["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["indexed"] += 1
            except Exception as e:
                logger.error(f"Sync failed for '{f.get('name')}': {e}")
                results["failed"] += 1

        return results

    def search(
        self,
        user_id: str,
        query: str,
        k: int = 5,
        file_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.ingestion.search(query=query, user_id=user_id, k=k, file_id=file_id)

    def remove_file_index(self, user_id: str, file_id: str) -> None:
        self.ingestion.delete_file_vectors(file_id, user_id)

    def get_index_status(self, user_id: str) -> Dict[str, Any]:
        return self.ingestion.get_index_status(user_id)
