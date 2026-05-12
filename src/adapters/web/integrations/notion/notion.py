from typing import Any, Dict, Optional, Tuple

import httpx

from src.adapters.services.notion.client import NotionClient


class NotionIntegration:
    def __init__(self, repository=None, fallback_client: Optional[NotionClient] = None):
        self.repository = repository
        self._fallback_client = fallback_client

    async def _get_client(self) -> NotionClient:
        if self.repository is not None:
            creds = await self.repository.find_credentials()
            if creds:
                return NotionClient(
                    client_id=creds.client_id,
                    client_secret=creds.client_secret,
                    redirect_uri=creds.redirect_uri,
                )
        if self._fallback_client:
            return self._fallback_client
        raise RuntimeError(
            "Notion credentials not configured. "
            "Use POST /api/v1/notion/credentials to save client_id and client_secret."
        )

    async def get_authorization_url(self, user_id: str) -> str:
        return (await self._get_client()).get_authorization_url(state=user_id)

    async def handle_oauth_callback(self, code: str) -> Dict[str, Any]:
        return await (await self._get_client()).exchange_code(code)

    async def revoke_token(self, config: Dict[str, Any]) -> None:
        token = config.get("access_token")
        if token:
            await (await self._get_client()).revoke_token(token)

    async def check_session_status(
        self,
        config: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any], Optional[Dict[str, Any]]]:
        payload, updated = await self.search_pages(config, query="", page_size=1)
        return True, payload, updated

    async def search_pages(
        self,
        config: Dict[str, Any],
        query: str = "",
        page_size: int = 20,
        start_cursor: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        client = await self._get_client()
        return await self._execute_with_refresh(
            client,
            config,
            lambda access_token: client.search(
                access_token,
                query=query,
                page_size=page_size,
                start_cursor=start_cursor,
            ),
        )

    async def get_page(
        self,
        config: Dict[str, Any],
        page_id: str,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        client = await self._get_client()
        return await self._execute_with_refresh(
            client,
            config,
            lambda access_token: client.retrieve_page(access_token, page_id),
        )

    async def get_page_content(
        self,
        config: Dict[str, Any],
        page_id: str,
        max_depth: int = 4,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        client = await self._get_client()

        async def _fetch(access_token: str) -> Dict[str, Any]:
            return {
                "results": await self._fetch_block_tree(
                    client,
                    access_token,
                    page_id,
                    max_depth=max_depth,
                )
            }

        return await self._execute_with_refresh(client, config, _fetch)

    async def _fetch_block_tree(
        self,
        client: NotionClient,
        access_token: str,
        block_id: str,
        *,
        max_depth: int,
        depth: int = 0,
    ) -> list[Dict[str, Any]]:
        blocks: list[Dict[str, Any]] = []
        cursor = None
        while True:
            payload = await client.retrieve_block_children(
                access_token,
                block_id,
                start_cursor=cursor,
            )
            for block in payload.get("results", []):
                normalized = self._normalize_block(block)
                if depth < max_depth and block.get("has_children"):
                    normalized["children"] = await self._fetch_block_tree(
                        client,
                        access_token,
                        block["id"],
                        max_depth=max_depth,
                        depth=depth + 1,
                    )
                blocks.append(normalized)
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
        return blocks

    async def _execute_with_refresh(
        self,
        client: NotionClient,
        config: Dict[str, Any],
        operation,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        access_token = config.get("access_token")
        if not access_token:
            raise RuntimeError("Notion integration is not connected for this user.")
        try:
            return await operation(access_token), None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 401 or not config.get("refresh_token"):
                raise

        refreshed = await client.refresh_access_token(config["refresh_token"])
        updated = dict(config)
        updated.update(
            {
                "access_token": refreshed["access_token"],
                "refresh_token": refreshed.get("refresh_token", config.get("refresh_token")),
                "workspace_id": refreshed.get("workspace_id", config.get("workspace_id")),
                "workspace_name": refreshed.get("workspace_name", config.get("workspace_name")),
                "workspace_icon": refreshed.get("workspace_icon", config.get("workspace_icon")),
                "bot_id": refreshed.get("bot_id", config.get("bot_id")),
                "owner": refreshed.get("owner", config.get("owner")),
                "is_connected": True,
            }
        )
        return await operation(updated["access_token"]), updated

    def _normalize_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        block_type = block.get("type", "unsupported")
        content = block.get(block_type, {})
        plain_text = ""
        rich_text = content.get("rich_text") or content.get("title") or []
        if rich_text:
            plain_text = "".join(part.get("plain_text", "") for part in rich_text)
        elif block_type == "child_page":
            plain_text = content.get("title", "")

        return {
            "id": block.get("id"),
            "type": block_type,
            "has_children": block.get("has_children", False),
            "plain_text": plain_text,
            "content": content,
        }
