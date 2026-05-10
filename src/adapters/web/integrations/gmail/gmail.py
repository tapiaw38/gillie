import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from src.core.domain.gmail import GmailSession, GmailCredentials
from src.adapters.services.gmail.client import GoogleGmailClient

logger = logging.getLogger(__name__)


class GmailIntegration:
    def __init__(self, repository, fallback_client: Optional[GoogleGmailClient] = None):
        self.repository = repository
        self._fallback_client = fallback_client
        self._pending_verifiers: Dict[str, str] = {}

    async def _get_client(self) -> GoogleGmailClient:
        creds = await self.repository.find_credentials()
        if creds:
            return GoogleGmailClient(
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                redirect_uri=creds.redirect_uri,
            )
        if self._fallback_client:
            return self._fallback_client
        raise RuntimeError(
            "Gmail credentials not configured. "
            "Use POST /api/v1/gmail/credentials to save client_id and client_secret."
        )

    async def get_authorization_url(self, user_id: str) -> str:
        auth_url, code_verifier = (await self._get_client()).get_authorization_url(state=user_id)
        if code_verifier:
            self._pending_verifiers[user_id] = code_verifier
        return auth_url

    async def handle_oauth_callback(self, user_id: str, code: str) -> GmailSession:
        code_verifier = self._pending_verifiers.pop(user_id, None)
        client = await self._get_client()
        tokens = client.exchange_code(code, code_verifier=code_verifier)
        session = GmailSession(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expiry=tokens["expiry"],
            scopes=tokens["scopes"],
            is_active=True,
        )
        try:
            service = client.build_service(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                expiry=session.token_expiry,
            )
            email = client.get_user_email(service)
            session.email = email
            logger.info(f"Gmail authorized for user_id={user_id}, email={email}")
        except Exception as e:
            logger.warning(f"Could not get Gmail user email for user_id={user_id}: {e}")
        await self.repository.upsert_session(session)
        return session

    async def check_session_status(self, user_id: str) -> bool:
        session = await self.repository.find_active_session(user_id)
        if not session:
            return False
        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > now

    async def _get_service(self, user_id: str):
        session = await self.repository.find_active_session(user_id)
        if not session:
            raise RuntimeError(f"No active Gmail session for user_id={user_id}")
        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        client = await self._get_client()
        if expiry <= now:
            refreshed = client.refresh_access_token(session.refresh_token)
            session.access_token = refreshed["access_token"]
            session.token_expiry = refreshed["expiry"]
            await self.repository.upsert_session(session)
        return client.build_service(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expiry=session.token_expiry,
        )

    async def list_emails(
        self,
        user_id: str,
        query: str = "",
        max_results: int = 20,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        service = await self._get_service(user_id)
        client = await self._get_client()
        message_refs = client.list_messages(service, query=query, max_results=max_results, label_ids=label_ids)
        result = []
        for ref in message_refs:
            try:
                msg = client.get_message(service, ref["id"])
                result.append(GoogleGmailClient.parse_message(msg))
            except Exception as e:
                logger.warning(f"Could not fetch Gmail message {ref['id']}: {e}")
        return result

    async def get_email(self, user_id: str, message_id: str) -> Dict[str, Any]:
        service = await self._get_service(user_id)
        client = await self._get_client()
        msg = client.get_message(service, message_id)
        return GoogleGmailClient.parse_message(msg)

    async def send_email(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        service = await self._get_service(user_id)
        sent = (await self._get_client()).send_message(
            service,
            to=to,
            subject=subject,
            body=body,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
        )
        return {"id": sent.get("id", ""), "thread_id": sent.get("threadId", ""), "status": "sent"}

    async def reply_email(
        self,
        user_id: str,
        message_id: str,
        body: str,
        body_html: Optional[str] = None,
    ) -> Dict[str, Any]:
        service = await self._get_service(user_id)
        client = await self._get_client()
        original = client.get_message(service, message_id, format="metadata")
        parsed = GoogleGmailClient.parse_message(original)
        thread_id = parsed["thread_id"]
        to = parsed["from"]
        subject = parsed["subject"]
        sent = client.reply_message(
            service,
            thread_id=thread_id,
            message_id=message_id,
            to=to,
            subject=subject,
            body=body,
            body_html=body_html,
        )
        return {"id": sent.get("id", ""), "thread_id": sent.get("threadId", ""), "status": "sent"}

    async def delete_email(self, user_id: str, message_id: str) -> None:
        service = await self._get_service(user_id)
        (await self._get_client()).delete_message(service, message_id)

    async def mark_as_read(self, user_id: str, message_id: str) -> None:
        service = await self._get_service(user_id)
        (await self._get_client()).mark_as_read(service, message_id)

    async def mark_as_unread(self, user_id: str, message_id: str) -> None:
        service = await self._get_service(user_id)
        (await self._get_client()).mark_as_unread(service, message_id)
