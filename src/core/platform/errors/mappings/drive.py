from src.core.platform.errors.application_error import ErrorDetails

DriveSessionNotFoundError = ErrorDetails(
    internal_code="drive:session:not-found",
    status_code=404,
    message="no active Google Drive session found, please authorize first",
)

DriveOAuthError = ErrorDetails(
    internal_code="drive:oauth:error",
    status_code=502,
    message="error during Google Drive OAuth flow",
)

DriveTokenRefreshError = ErrorDetails(
    internal_code="drive:token:refresh-error",
    status_code=502,
    message="failed to refresh Google Drive access token",
)

DriveListFilesError = ErrorDetails(
    internal_code="drive:files:list-error",
    status_code=502,
    message="error listing Google Drive files",
)

DriveFileNotFoundError = ErrorDetails(
    internal_code="drive:file:not-found",
    status_code=404,
    message="file not found in Google Drive",
)

DriveFileDownloadError = ErrorDetails(
    internal_code="drive:file:download-error",
    status_code=502,
    message="error downloading file from Google Drive",
)

DriveIngestionError = ErrorDetails(
    internal_code="drive:ingest:error",
    status_code=500,
    message="error processing and indexing Drive file",
)

DriveSearchError = ErrorDetails(
    internal_code="drive:search:error",
    status_code=500,
    message="error searching indexed Drive documents",
)

DriveSyncError = ErrorDetails(
    internal_code="drive:sync:error",
    status_code=500,
    message="error syncing Google Drive files",
)

DriveIndexNotFoundError = ErrorDetails(
    internal_code="drive:index:not-found",
    status_code=404,
    message="file index entry not found",
)
