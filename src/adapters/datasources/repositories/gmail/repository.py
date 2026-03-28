from typing import Optional

from src.core.domain.gmail import GmailSession, GmailCredentials
from src.adapters.datasources.datasources import Datasources
from .repository_interface import RepositoryInterface
from .find_session import find_active_session
from .upsert_session import upsert_session, deactivate_session
from .credentials import save_credentials, find_credentials


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.sessions_client = datasources.no_sql_gmail_sessions_client
        self.sessions_client.create_index("user_id")

    def upsert_session(self, session: GmailSession) -> str:
        return upsert_session(self.sessions_client, session)

    def find_active_session(self, user_id: str) -> Optional[GmailSession]:
        return find_active_session(self.sessions_client, user_id)

    def deactivate_session(self, user_id: str) -> None:
        deactivate_session(self.sessions_client, user_id)

    def save_credentials(self, creds: GmailCredentials) -> None:
        save_credentials(self.sessions_client, creds)

    def find_credentials(self) -> Optional[GmailCredentials]:
        return find_credentials(self.sessions_client)
