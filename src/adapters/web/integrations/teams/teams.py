import logging
from typing import Any, Dict, List, Optional

import jwt
import requests
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
_BOT_SCOPE = "https://api.botframework.com/.default"
_OPENID_CONFIG_URL = "https://login.botframework.com/v1/.well-known/openidconfiguration"
_EXPECTED_ISSUER = "https://api.botframework.com"


class TeamsIntegration:
    """
    Adapter for Microsoft Teams via the Bot Framework REST API.

    Authentication uses OAuth2 client credentials (app_id + app_password)
    issued from an Azure Bot Registration. All methods are synchronous;
    wrap in asyncio.to_thread for async contexts.

    Config required in Integration.config:
        app_id       - Azure Bot App ID (Application ID)
        app_password - Azure Bot App Password (Client Secret)
    """

    def __init__(self, app_id: str, app_password: str):
        self.app_id = app_id
        self.app_password = app_password
        self._cached_token: Optional[str] = None
        self._openid_config: Optional[Dict[str, Any]] = None
        self._jwks_client: Optional[PyJWKClient] = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_token(self) -> str:
        """Obtain a Bot Framework access token using client credentials."""
        resp = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.app_id,
                "client_secret": self.app_password,
                "scope": _BOT_SCOPE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("Teams: empty access_token in response")
        self._cached_token = token
        return token

    def _auth_headers(self) -> Dict[str, str]:
        token = self._cached_token or self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify_credentials(self) -> bool:
        """
        Verify that app_id + app_password are valid by requesting a token.
        Returns True on success, raises on failure.
        """
        self._get_token()
        return True

    def _get_openid_config(self) -> Dict[str, Any]:
        if self._openid_config is None:
            response = requests.get(_OPENID_CONFIG_URL, timeout=15)
            response.raise_for_status()
            self._openid_config = response.json()
        return self._openid_config

    def _get_jwks_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            config = self._get_openid_config()
            jwks_uri = config.get("jwks_uri")
            if not jwks_uri:
                raise RuntimeError("Teams: OpenID configuration missing jwks_uri")
            self._jwks_client = PyJWKClient(jwks_uri)
        return self._jwks_client

    def validate_incoming_activity(
        self,
        authorization_header: str,
        service_url: str,
        channel_id: str = "msteams",
    ) -> Dict[str, Any]:
        """
        Validate an incoming Bot Framework JWT for a Teams activity.
        Returns the decoded claims on success.
        """
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise ValueError("Teams: missing Bearer token")

        token = authorization_header.split(" ", 1)[1].strip()
        signing_key = self._get_jwks_client().get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.app_id,
            issuer=_EXPECTED_ISSUER,
            options={"require": ["exp", "iat", "nbf", "iss", "aud"]},
        )

        claim_service_url = claims.get("serviceurl") or claims.get("serviceUrl")
        if claim_service_url and service_url and claim_service_url.rstrip("/") != service_url.rstrip("/"):
            raise ValueError("Teams: serviceUrl claim mismatch")

        # If endorsements are present, ensure msteams is included.
        endorsements = claims.get("endorsements") or []
        if endorsements and channel_id not in endorsements:
            raise ValueError("Teams: missing msteams endorsement")

        return claims

    # ── Receive ───────────────────────────────────────────────────────────────

    def receive_message(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse an incoming Bot Framework Activity and extract messages.

        Returns a list of message dicts with keys:
            service_url, conversation_id, activity_id, user_id, text, channel_id
        """
        activity_type = payload.get("type", "")
        if activity_type != "message":
            return []

        text = payload.get("text", "").strip()
        if not text:
            return []

        conversation = payload.get("conversation", {})
        from_field = payload.get("from", {})

        return [
            {
                "service_url": payload.get("serviceUrl", ""),
                "conversation_id": conversation.get("id", ""),
                "activity_id": payload.get("id", ""),
                "user_id": from_field.get("id", ""),
                "user_name": from_field.get("name", ""),
                "bot_id": payload.get("recipient", {}).get("id", ""),
                "text": text,
                "channel_id": payload.get("channelId", ""),
                "tenant_id": (
                    payload.get("channelData", {}).get("tenant", {}).get("id")
                    or payload.get("conversation", {}).get("tenantId", "")
                ),
            }
        ]

    # ── Send ──────────────────────────────────────────────────────────────────

    def send_message(
        self,
        service_url: str,
        conversation_id: str,
        text: str,
        reply_to_activity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a text message to a Teams conversation.

        If reply_to_activity_id is provided, posts as a reply to that activity.
        Otherwise creates a new activity in the conversation.
        """
        service_url = service_url.rstrip("/")
        if reply_to_activity_id:
            url = f"{service_url}/v3/conversations/{conversation_id}/activities/{reply_to_activity_id}"
        else:
            url = f"{service_url}/v3/conversations/{conversation_id}/activities"

        body = {"type": "message", "text": text}

        try:
            headers = self._auth_headers()
        except Exception:
            # Token expired — refresh once
            self._cached_token = None
            headers = self._auth_headers()

        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def send_webhook_message(self, webhook_url: str, text: str) -> bool:
        """
        Post a plain-text message via a Teams Incoming Webhook URL.
        This does NOT require app_id/app_password — the URL itself is the credential.
        Returns True on success.
        """
        payload = {"text": text}
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
