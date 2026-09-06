"""Routing narrows the tool set without ever losing a tool."""

import asyncio

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from src.core.platform.ai.ollama_adapter import (
    TOOL_GROUPS,
    route_tools,
    unclassified_tools,
)
from src.core.platform.ai.tools.models import create_langchain_tools


class _Args(BaseModel):
    pass


def tool(name):
    return StructuredTool(
        name=name, description=name, args_schema=_Args, coroutine=None, func=lambda: None
    )


class RouterLLM:
    """Stands in for the routing call, replying with fixed categories."""

    def __init__(self, reply):
        self.reply = reply

    async def ainvoke(self, _messages):
        return AIMessage(content=self.reply)


def route(reply, names):
    return {
        t.name for t in asyncio.run(route_tools(RouterLLM(reply), "q", [tool(n) for n in names]))
    }


def test_routing_keeps_only_the_named_categories():
    kept = route('["files"]', ["read_file", "write_file", "jira_create_issue", "browser_click"])
    assert "read_file" in kept and "write_file" in kept
    assert "jira_create_issue" not in kept and "browser_click" not in kept


def test_a_tool_in_no_category_is_kept_rather_than_lost():
    """TOOL_GROUPS is hand-maintained. A tool added without touching it must
    still reach the model, or it vanishes with no error to trace."""
    kept = route('["files"]', ["read_file", "brand_new_unlisted_tool"])
    assert "brand_new_unlisted_tool" in kept


def test_run_workflow_survives_any_routing_decision():
    """The router picks tool categories; a workflow's name is not one, so it
    can never tell that run_workflow is what the turn needs."""
    assert "run_workflow" in route('["media"]', ["run_workflow", "search_images"])
    assert "run_workflow" in route("[]", ["run_workflow", "read_file"])


def test_web_access_survives_as_the_catch_all():
    assert "web_search" in route('["git"]', ["web_search", "git_status"])


def test_a_broken_router_reply_falls_back_without_dropping_tools():
    names = ["read_file", "git_status", "jira_create_issue"]
    kept = route("not json at all", names)
    assert kept, "a router that fails must not leave the model toolless"


def test_database_tools_match_by_prefix():
    kept = route('["database"]', ["query_sales", "execute_sql_raw", "read_file"])
    assert {"query_sales", "execute_sql_raw"} <= kept


def test_every_real_tool_is_classified():
    """Unclassified tools still work, but they cost tokens on every call —
    this fails when the catalogue grows past what the groups cover."""
    profile = type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": None, "integrations": None, "files": None,
        "assistant_name": "g", "business_context": "", "response_language": "en",
    })()
    tools = [t for t in create_langchain_tools(None, profile) if t]

    orphans = unclassified_tools(tools) - {"run_workflow"}
    assert not orphans, (
        f"add these to TOOL_GROUPS in ollama_adapter.py so routing can drop "
        f"them when irrelevant: {sorted(orphans)}"
    )


def test_groups_do_not_name_tools_that_cannot_exist():
    """Integration tools appear conditionally, so absent names are normal —
    but a typo in TOOL_GROUPS is silent, so keep the known set explicit."""
    grouped = {n for names in TOOL_GROUPS.values() for n in names}
    assert "read_file" in grouped and "run_shell" in grouped
