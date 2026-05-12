import base64
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx


class NotionClient:
    API_BASE = "https://api.notion.com/v1"
    AUTHORIZE_URL = f"{API_BASE}/oauth/authorize"
    TOKEN_URL = f"{API_BASE}/oauth/token"
    REVOKE_URL = f"{API_BASE}/oauth/revoke"
    NOTION_VERSION = "2026-03-11"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        params = {
            "owner": "user",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.TOKEN_URL,
                headers=self._basic_headers(),
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.TOKEN_URL,
                headers=self._basic_headers(),
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def revoke_token(self, token: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.REVOKE_URL,
                headers=self._basic_headers(),
                json={"token": token},
            )
            response.raise_for_status()

    async def search(
        self,
        access_token: str,
        query: str = "",
        page_size: int = 20,
        start_cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "page_size": page_size,
            "filter": {"property": "object", "value": "page"},
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        }
        if query:
            body["query"] = query
        if start_cursor:
            body["start_cursor"] = start_cursor
        return await self._bearer_request("POST", "/search", access_token, json=body)

    async def retrieve_page(self, access_token: str, page_id: str) -> Dict[str, Any]:
        return await self._bearer_request("GET", f"/pages/{page_id}", access_token)

    async def retrieve_block_children(
        self,
        access_token: str,
        block_id: str,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page_size": page_size}
        if start_cursor:
            params["start_cursor"] = start_cursor
        return await self._bearer_request(
            "GET",
            f"/blocks/{block_id}/children",
            access_token,
            params=params,
        )

    async def _bearer_request(
        self,
        method: str,
        path: str,
        access_token: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method,
                f"{self.API_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": self.NOTION_VERSION,
                    "Content-Type": "application/json",
                },
                json=json,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def _basic_headers(self) -> Dict[str, str]:
        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("utf-8")
        return {
            "Authorization": f"Basic {basic}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }
