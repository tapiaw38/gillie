from typing import Optional

from pymongo.errors import PyMongoError

from src.core.domain.notion import NotionCredentials
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError

from .repository_interface import RepositoryInterface

_CREDENTIALS_DOC_ID = "__app_credentials__"


class Repository(RepositoryInterface):
    def __init__(self, datasources):
        self.sessions_client = datasources.no_sql_notion_sessions_client

    async def ensure_indexes(self) -> None:
        await self.sessions_client.create_index("user_id")

    async def save_credentials(self, creds: NotionCredentials) -> None:
        try:
            doc = {
                "user_id": _CREDENTIALS_DOC_ID,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "redirect_uri": creds.redirect_uri,
            }
            await self.sessions_client.replace_one(
                {"user_id": _CREDENTIALS_DOC_ID},
                doc,
                upsert=True,
            )
        except PyMongoError as exc:
            raise NewApplicationError(ValidationError, exc)

    async def find_credentials(self) -> Optional[NotionCredentials]:
        try:
            doc = await self.sessions_client.find_one({"user_id": _CREDENTIALS_DOC_ID})
            if not doc:
                return None
            return NotionCredentials(
                client_id=doc["client_id"],
                client_secret=doc["client_secret"],
                redirect_uri=doc.get(
                    "redirect_uri",
                    "http://localhost:8000/api/v1/notion/oauth/callback",
                ),
            )
        except PyMongoError as exc:
            raise NewApplicationError(ValidationError, exc)
