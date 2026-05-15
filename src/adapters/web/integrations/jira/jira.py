import base64
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class JiraIntegration:
    """
    Adapter for the Jira Cloud REST API v3.

    Authentication uses HTTP Basic Auth: base64(email:api_token).
    All methods are synchronous; wrap in asyncio.to_thread for async contexts.
    """

    def __init__(self, domain: str, email: str, api_token: str):
        """
        Args:
            domain:    Atlassian subdomain, e.g. "mycompany.atlassian.net"
            email:     User email associated with the API token
            api_token: Jira API token (not account password)
        """
        self.domain = domain.rstrip("/")
        self.base_url = f"https://{self.domain}/rest/api/3"
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self._auth_header = f"Basic {credentials}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: Dict) -> Dict:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self._headers(), json=body, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _put(self, path: str, body: Dict) -> Dict:
        url = f"{self.base_url}{path}"
        resp = requests.put(url, headers=self._headers(), json=body, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def _delete(self, path: str) -> None:
        url = f"{self.base_url}{path}"
        resp = requests.delete(url, headers=self._headers(), timeout=15)
        resp.raise_for_status()

    def get_projects(self, max_results: int = 50) -> List[Dict]:
        """Return all accessible Jira projects."""
        data = self._get("/project/search", params={"maxResults": max_results})
        return data.get("values", [])

    def search_issues(
        self,
        jql: str,
        *,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[List[str]] = None,
    ) -> Dict:
        """
        Search issues using JQL. Returns the raw search response which includes
        'issues', 'total', 'startAt', 'maxResults'.
        """
        body: Dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
        }
        if fields:
            body["fields"] = fields
        return self._post("/search", body)

    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict:
        """Return a single issue by key (e.g. 'PROJ-123')."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return self._get(f"/issue/{issue_key}", params=params or None)

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        *,
        description: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create a new Jira issue. Returns the created issue dict with 'id', 'key', 'self'.

        description is sent as Atlassian Document Format (ADF) plain text paragraph.
        """
        fields: Dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels

        return self._post("/issue", {"fields": fields})

    def update_issue(
        self,
        issue_key: str,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> None:
        """Update fields of an existing issue. No-ops for fields not provided."""
        fields: Dict[str, Any] = {}
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        if assignee_account_id is not None:
            fields["assignee"] = {"accountId": assignee_account_id}
        if priority is not None:
            fields["priority"] = {"name": priority}
        if labels is not None:
            fields["labels"] = labels

        self._put(f"/issue/{issue_key}", {"fields": fields})

    def delete_issue(self, issue_key: str) -> None:
        """Permanently delete an issue."""
        self._delete(f"/issue/{issue_key}")

    def get_transitions(self, issue_key: str) -> List[Dict]:
        """Return available transitions for an issue."""
        data = self._get(f"/issue/{issue_key}/transitions")
        return data.get("transitions", [])

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Move an issue to a new status via a workflow transition."""
        self._post(f"/issue/{issue_key}/transitions", {"transition": {"id": transition_id}})

    def get_comments(self, issue_key: str, max_results: int = 50) -> List[Dict]:
        """Return comments on an issue."""
        data = self._get(f"/issue/{issue_key}/comment", params={"maxResults": max_results})
        return data.get("comments", [])

    def add_comment(self, issue_key: str, body_text: str) -> Dict:
        """Post a plain-text comment on an issue using ADF format."""
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body_text}],
                    }
                ],
            }
        }
        return self._post(f"/issue/{issue_key}/comment", body)
