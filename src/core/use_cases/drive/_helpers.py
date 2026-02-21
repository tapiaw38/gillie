from datetime import datetime, timezone

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveSessionNotFoundError

INTEGRATION_NAME = "google_drive"


def get_drive_service(context, user_id: str):
    """Get an authenticated Google Drive service from stored profile tokens.

    Refreshes the access token if expired and saves updated tokens back.
    Raises DriveSessionNotFoundError if no active Drive integration found.
    """
    profile = context.repositories.profile.find_by_user_id(user_id)
    if not profile:
        raise NewApplicationError(DriveSessionNotFoundError)

    drive_integration = next(
        (i for i in (profile.integrations or []) if i.name == INTEGRATION_NAME),
        None,
    )
    if not drive_integration or not drive_integration.activated:
        raise NewApplicationError(DriveSessionNotFoundError)

    config = drive_integration.config
    updated_config = context.integrations.google_drive.refresh_if_needed(config)

    if updated_config is not config:
        now = datetime.now(timezone.utc)
        updated_integrations = [
            i.copy(update={"config": updated_config, "updated_at": now})
            if i.name == INTEGRATION_NAME else i
            for i in profile.integrations
        ]
        context.repositories.profile.update_integrations(user_id, updated_integrations)

    return context.integrations.google_drive.build_service(updated_config)
