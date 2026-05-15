"""
Ollama adapter for LangChain.

Centralizes all Ollama-specific logic:
- URL detection
- PromptProfile resolution (local_small vs default)
- LLM construction (ChatOllama)
- Tool routing (reduce 50+ tools to a relevant subset)
- Tool name aliases (gemma4 hallucinates google:search instead of web_search)
- Tool args normalization (queries list → query string)
"""

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


@dataclass
class PromptProfile:
    """Runtime profile that controls resource budgets for a single request."""
    name: str
    max_history_messages: int   # max conversation turns kept in context
    max_tool_rounds: int        # max agentic tool-call loops
    max_context_chars: int      # char budget for history (0 = no extra limit)
    short_answers: bool         # inject "be concise" instruction in system prompt
    max_workspace_files: int    # cap on workspace map entries (0 = no map)


LOCAL_PROFILE = PromptProfile(
    name="local_small",
    max_history_messages=6,
    max_tool_rounds=3,
    max_context_chars=8000,
    short_answers=True,
    max_workspace_files=60,
)

DEFAULT_PROFILE = PromptProfile(
    name="default",
    max_history_messages=20,
    max_tool_rounds=30,
    max_context_chars=24000,
    short_answers=False,
    max_workspace_files=180,
)


def is_ollama_url(base_url: str) -> bool:
    return bool(base_url and ("localhost:11434" in base_url or "127.0.0.1:11434" in base_url))


def is_local_provider(base_url: str, model: str = "", provider_name: str = "") -> bool:
    """Detect providers that are actually hosted on the local machine."""
    provider = (provider_name or "").lower()
    if "ollama" in provider:
        return True

    if is_ollama_url(base_url):
        return True

    if not base_url:
        return False

    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def resolve_profile(base_url: str, model: str = "", provider_name: str = "") -> PromptProfile:
    """Return LOCAL_PROFILE for local providers, DEFAULT_PROFILE otherwise."""
    if is_local_provider(base_url, model, provider_name):
        return LOCAL_PROFILE
    return DEFAULT_PROFILE


def build_ollama_llm(model: str):
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=model,
        temperature=0.7,
        num_predict=8000,
        timeout=300.0,
    )


TOOL_GROUPS: dict[str, list[str]] = {
    "web":       ["web_search", "fetch_url"],
    "files":     ["read_file", "write_file", "edit_file", "list_directory", "find_files", "grep_files"],
    "shell":     ["run_shell"],
    "git":       ["git_status", "git_diff", "git_log", "git_commit"],
    "code":      ["check_code", "repo_map"],
    "documents": [
        "analyze_pdf", "extract_text_from_pdf", "analyze_excel", "write_excel",
        "read_docx", "write_docx", "modify_excel", "modify_docx",
        "insert_image_docx", "insert_image_excel", "search_documents",
    ],
    "media":     ["search_images", "describe_image", "take_screenshot", "send_file", "send_screenshot"],
    "browser":   [
        "browser_connect", "browser_navigate", "browser_act", "browser_extract",
        "browser_get_content", "browser_click", "browser_type", "browser_screenshot",
        "browser_close", "browser_switch_tab", "browser_evaluate", "browser_enable_remote_debug",
    ],
    "calendar":  ["calendar_list_events", "calendar_create_event", "calendar_update_event", "calendar_delete_event"],
    "memory":    ["organize_memory", "save_memory", "search_memory", "save_solution"],
    "database":  [],  # matched dynamically by prefix query_* / execute_sql_*
    "clickup":   ["clickup_get_tasks", "clickup_create_task", "clickup_update_task", "clickup_add_comment", "clickup_get_workspaces"],
    "jira":      ["jira_search_issues", "jira_create_issue", "jira_update_issue", "jira_transition_issue", "jira_add_comment", "jira_get_projects"],
    "teams":     ["teams_send_message"],
}

_WEB_ALWAYS = {"web_search", "fetch_url"}

_ROUTING_SYSTEM = (
    "You are a tool router. Given the user's message, respond with ONLY a JSON array "
    "of the tool categories needed from this list: "
    "web, files, shell, git, code, documents, media, browser, calendar, memory, database, "
    "clickup, jira, teams. "
    "Examples: [\"web\"] or [\"files\", \"shell\"] or [\"jira\"] or []. No explanation, no markdown."
)


async def route_tools(llm, user_message: str, all_tools: list) -> list:
    """
    Run a fast routing call to select only the relevant tool subset for Ollama.
    Reduces 50+ tools to a small focused set to avoid context overflow.
    """
    try:
        response = await llm.ainvoke([
            SystemMessage(content=_ROUTING_SYSTEM),
            HumanMessage(content=user_message),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        categories: list[str] = json.loads(raw)
    except Exception as e:
        logger.warning(f"Tool routing failed ({e}), falling back to web+shell")
        categories = ["web", "shell"]

    allowed: set[str] = set(_WEB_ALWAYS)
    for cat in categories:
        allowed.update(TOOL_GROUPS.get(cat, []))
        if cat == "database":
            allowed.update(t.name for t in all_tools if t.name.startswith(("query_", "execute_sql_")))

    filtered = [t for t in all_tools if t.name in allowed]
    logger.info(f"Tool routing: categories={categories} → {len(filtered)}/{len(all_tools)} tools")
    return filtered if filtered else all_tools[:8]


TOOL_ALIASES: dict[str, str] = {
    "google:search":  "web_search",
    "google_search":  "web_search",
    "search":         "web_search",
    "internet_search": "web_search",
    "duckduckgo":     "web_search",
    "add_memory":     "save_memory",
}


def resolve_tool_name(name: str) -> str:
    """Return the canonical tool name, resolving any known alias."""
    return TOOL_ALIASES.get(name, name)

def normalize_tool_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Fix args that local models send in the wrong format.
    Example: gemma4 sends {'queries': [...]} but web_search expects {'query': '...'}.
    """
    if tool_name == "web_search" and "queries" in args and "query" not in args:
        queries = args.pop("queries")
        args["query"] = queries[0] if isinstance(queries, list) and queries else str(queries)
    return args
