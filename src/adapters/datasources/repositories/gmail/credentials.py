from typing import Optional

from pymongo.errors import PyMongoError

from src.core.domain.gmail import GmailCredentials
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailSessionQueryError

_CREDENTIALS_DOC_ID = "__app_credentials__"


def save_credentials(client, creds: GmailCredentials) -> None:
    try:
        doc = {
            "user_id": _CREDENTIALS_DOC_ID,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "redirect_uri": creds.redirect_uri,
        }
        client.replace_one({"user_id": _CREDENTIALS_DOC_ID}, doc, upsert=True)
    except PyMongoError as e:
        raise NewApplicationError(GmailSessionQueryError, e)


def find_credentials(client) -> Optional[GmailCredentials]:
    try:
        doc = client.find_one({"user_id": _CREDENTIALS_DOC_ID})
        if not doc:
            return None
        return GmailCredentials(
            client_id=doc["client_id"],
            client_secret=doc["client_secret"],
            redirect_uri=doc.get("redirect_uri", "http://localhost:8000/api/v1/gmail/oauth/callback"),
        )
    except PyMongoError as e:
        raise NewApplicationError(GmailSessionQueryError, e)
