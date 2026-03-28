from typing import Optional
from src.core.domain.drive import DriveCredentials
from .repository_interface import RepositoryInterface
from .credentials import save_credentials, find_credentials


class Repository(RepositoryInterface):
    def __init__(self, datasources):
        self.sessions_client = datasources.no_sql_drive_sessions_client
        self.sessions_client.create_index("user_id")

    def save_credentials(self, creds: DriveCredentials) -> None:
        save_credentials(self.sessions_client, creds)

    def find_credentials(self) -> Optional[DriveCredentials]:
        return find_credentials(self.sessions_client)
