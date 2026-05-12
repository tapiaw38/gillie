from typing import Optional

from src.core.domain.gmail import GmailSession, GmailCredentials
from src.adapters.datasources.datasources import Datasources
from pymongo.errors import PyMongoError
from datetime import datetime

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailSessionQueryError
from .repository_interface import RepositoryInterface

_CREDENTIALS_DOC_ID = "__app_credentials__"


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.sessions_client = datasources.no_sql_gmail_sessions_client
 
    async def ensure_indexes(self) -> None:
        await self.sessions_client.create_index("user_id")

    async def upsert_session(self, session: GmailSession) -> str:
        try:
            doc = session.dict(by_alias=True, exclude_none=True)
            doc.pop("_id", None)
            doc["updated_at"] = datetime.now()
            result = await self.sessions_client.replace_one({"user_id": session.user_id}, doc, upsert=True)
            if result.upserted_id:
                return str(result.upserted_id)
            existing = await self.sessions_client.find_one({"user_id": session.user_id})
            return str(existing["_id"])
        except PyMongoError as exc:
            raise NewApplicationError(GmailSessionQueryError, exc)

    async def find_active_session(self, user_id: str) -> Optional[GmailSession]:
        try:
            doc = await self.sessions_client.find_one({"user_id": user_id, "is_active": True})
            if doc:
                doc["_id"] = str(doc["_id"])
                return GmailSession(**doc)
            return None
        except PyMongoError as exc:
            raise NewApplicationError(GmailSessionQueryError, exc)

    async def deactivate_session(self, user_id: str) -> None:
        try:
            await self.sessions_client.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": False, "updated_at": datetime.now()}},
            )
        except PyMongoError as exc:
            raise NewApplicationError(GmailSessionQueryError, exc)

    async def save_credentials(self, creds: GmailCredentials) -> None:
        try:
            doc = {
                "user_id": _CREDENTIALS_DOC_ID,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "redirect_uri": creds.redirect_uri,
            }
            await self.sessions_client.replace_one({"user_id": _CREDENTIALS_DOC_ID}, doc, upsert=True)
        except PyMongoError as exc:
            raise NewApplicationError(GmailSessionQueryError, exc)

    async def find_credentials(self) -> Optional[GmailCredentials]:
        try:
            doc = await self.sessions_client.find_one({"user_id": _CREDENTIALS_DOC_ID})
            if not doc:
                return None
            return GmailCredentials(
                client_id=doc["client_id"],
                client_secret=doc["client_secret"],
                redirect_uri=doc.get("redirect_uri", "http://localhost:8000/api/v1/gmail/oauth/callback"),
            )
        except PyMongoError as exc:
            raise NewApplicationError(GmailSessionQueryError, exc)
