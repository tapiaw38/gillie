"""
Ollama adapter for LangChain.

Centralizes all Ollama-specific logic:
- URL detection
- LLM construction (ChatOllama)
- Tool routing (reduce 50+ tools to a relevant subset)
- Tool name aliases (gemma4 hallucinates google:search instead of web_search)
- Tool args normalization (queries list → query string)
"""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def is_ollama_url(base_url: str) -> bool:
    return bool(base_url and ("localhost:11434" in base_url or "127.0.0.1:11434" in base_url))


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
    "memory":    ["organize_memory", "add_memory"],
    "database":  [],  # matched dynamically by prefix query_* / execute_sql_*
}

_WEB_ALWAYS = {"web_search", "fetch_url"}

_ROUTING_SYSTEM = (
    "You are a tool router. Given the user's message, respond with ONLY a JSON array "
    "of the tool categories needed from this list: "
    "web, files, shell, git, code, documents, media, browser, calendar, memory, database. "
    "Examples: [\"web\"] or [\"files\", \"shell\"] or []. No explanation, no markdown."
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
