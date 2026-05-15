import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.clickup.com/api/v2"


class ClickUpIntegration:
    """
    Adapter for the ClickUp REST API v2.

    Authentication uses a personal API token passed in the Authorization header.
    All methods are synchronous; wrap in asyncio.to_thread for async contexts.
    """

    def __init__(self, api_token: str):
        self.api_token = api_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{_BASE_URL}{path}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: Dict) -> Dict:
        url = f"{_BASE_URL}{path}"
        resp = requests.post(url, headers=self._headers(), json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, body: Dict) -> Dict:
        url = f"{_BASE_URL}{path}"
        resp = requests.put(url, headers=self._headers(), json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> Dict:
        url = f"{_BASE_URL}{path}"
        resp = requests.delete(url, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def get_teams(self) -> List[Dict]:
        """Return all workspaces (teams) the token has access to."""
        data = self._get("/team")
        return data.get("teams", [])

    def get_spaces(self, team_id: str) -> List[Dict]:
        """Return all spaces within a workspace."""
        data = self._get(f"/team/{team_id}/space")
        return data.get("spaces", [])

    def get_lists(self, folder_id: str) -> List[Dict]:
        """Return all lists within a folder."""
        data = self._get(f"/folder/{folder_id}/list")
        return data.get("lists", [])

    def get_folderless_lists(self, space_id: str) -> List[Dict]:
        """Return lists that are directly inside a space (no folder)."""
        data = self._get(f"/space/{space_id}/list")
        return data.get("lists", [])

    def get_tasks(
        self,
        list_id: str,
        *,
        page: int = 0,
        archived: bool = False,
        include_closed: bool = False,
        assignees: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        due_date_gt: Optional[int] = None,
        due_date_lt: Optional[int] = None,
    ) -> List[Dict]:
        """Return tasks in a list. Supports pagination and basic filters."""
        params: Dict[str, Any] = {
            "page": page,
            "archived": str(archived).lower(),
            "include_closed": str(include_closed).lower(),
        }
        if assignees:
            params["assignees[]"] = assignees
        if statuses:
            params["statuses[]"] = statuses
        if due_date_gt is not None:
            params["due_date_gt"] = due_date_gt
        if due_date_lt is not None:
            params["due_date_lt"] = due_date_lt

        data = self._get(f"/list/{list_id}/task", params=params)
        return data.get("tasks", [])

    def get_task(self, task_id: str) -> Dict:
        """Return a single task by ID."""
        return self._get(f"/task/{task_id}")

    def create_task(
        self,
        list_id: str,
        name: str,
        *,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[int] = None,
        assignees: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """Create a task in the given list. Returns the created task dict."""
        body: Dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if priority is not None:
            body["priority"] = priority
        if due_date is not None:
            body["due_date"] = due_date
        if assignees is not None:
            body["assignees"] = assignees
        if tags is not None:
            body["tags"] = tags

        return self._post(f"/list/{list_id}/task", body)

    def update_task(
        self,
        task_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[int] = None,
    ) -> Dict:
        """Update fields of an existing task."""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if priority is not None:
            body["priority"] = priority
        if due_date is not None:
            body["due_date"] = due_date

        return self._put(f"/task/{task_id}", body)

    def delete_task(self, task_id: str) -> Dict:
        """Delete a task by ID."""
        return self._delete(f"/task/{task_id}")

    def get_task_comments(self, task_id: str) -> List[Dict]:
        """Return all comments on a task."""
        data = self._get(f"/task/{task_id}/comment")
        return data.get("comments", [])

    def add_task_comment(self, task_id: str, comment_text: str) -> Dict:
        """Post a plain-text comment on a task."""
        return self._post(f"/task/{task_id}/comment", {"comment_text": comment_text})
