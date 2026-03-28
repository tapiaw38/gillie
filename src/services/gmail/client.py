import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GoogleGmailClient:
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> tuple:
        """Return (authorization_url, code_verifier)."""
        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
        )
        return auth_url, getattr(flow, "code_verifier", None)

    def exchange_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        flow = self._build_flow()
        fetch_kwargs: Dict[str, Any] = {"code": code}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier
        flow.fetch_token(**fetch_kwargs)
        creds = flow.credentials
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry,
            "scopes": list(creds.scopes or self.SCOPES),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        creds.refresh(Request())
        return {"access_token": creds.token, "expiry": creds.expiry}

    def build_service(self, access_token: str, refresh_token: str, expiry: datetime):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def get_user_email(self, service) -> str:
        """Get the authenticated user's email address."""
        try:
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress", "")
        except Exception as e:
            logger.warning(f"Could not get user email: {e}")
            return ""

    def list_messages(
        self,
        service,
        query: str = "",
        max_results: int = 20,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List messages matching a query. Returns list of {id, threadId}."""
        kwargs: Dict[str, Any] = {"userId": "me", "maxResults": min(max_results, 500)}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids
        result = service.users().messages().list(**kwargs).execute()
        return result.get("messages", [])

    def get_message(self, service, message_id: str, format: str = "full") -> Dict[str, Any]:
        """Get a full message by ID."""
        return service.users().messages().get(userId="me", id=message_id, format=format).execute()

    def send_message(
        self,
        service,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email. Returns the sent message."""
        if body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg = MIMEText(body, "plain")
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"Gmail message sent: {sent.get('id')}")
        return sent

    def reply_message(
        self,
        service,
        thread_id: str,
        message_id: str,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reply to an existing thread."""
        if body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg = MIMEText(body, "plain")
        msg["To"] = to
        msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id},
        ).execute()
        logger.info(f"Gmail reply sent: {sent.get('id')}")
        return sent

    def delete_message(self, service, message_id: str) -> None:
        """Trash a message (move to Trash)."""
        service.users().messages().trash(userId="me", id=message_id).execute()
        logger.info(f"Gmail message trashed: {message_id}")

    def mark_as_read(self, service, message_id: str) -> None:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

    def mark_as_unread(self, service, message_id: str) -> None:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["UNREAD"]},
        ).execute()

    def _build_flow(self):
        from google_auth_oauthlib.flow import Flow
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        return Flow.from_client_config(client_config, scopes=self.SCOPES, redirect_uri=self.redirect_uri)

    @staticmethod
    def parse_message(msg: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Gmail message dict into a clean structure."""
        payload = msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        body_plain = ""
        body_html = ""

        def extract_body(part: Dict[str, Any]) -> None:
            nonlocal body_plain, body_html
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data", "")
            if data:
                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                if mime == "text/plain" and not body_plain:
                    body_plain = decoded
                elif mime == "text/html" and not body_html:
                    body_html = decoded
            for sub in part.get("parts", []):
                extract_body(sub)

        extract_body(payload)
        return {
            "id": msg.get("id", ""),
            "thread_id": msg.get("threadId", ""),
            "label_ids": msg.get("labelIds", []),
            "snippet": msg.get("snippet", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "body": body_plain or body_html,
            "body_html": body_html,
            "is_read": "UNREAD" not in msg.get("labelIds", []),
        }
