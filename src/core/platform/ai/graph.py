"""
The agent loop, as a LangGraph state graph.

Replaces the hand-rolled "invoke → run tools → invoke again" loop that used to
live in ``LangChainService``. The graph is what both the blocking and the
streaming entry points run, so tool handling exists in exactly one place.

Two properties of the graph shape matter:

* **One tool call per node run.** ``call_tool`` executes a single pending call
  and loops back to itself. A node that pauses for approval is re-run from the
  top when it resumes, so batching calls into one node would re-execute the
  side effects of the calls that already succeeded.
* **Approval happens before the side effect.** A tool asks via ``interrupt()``,
  which suspends the whole run and checkpoints it. Everything the tool did
  before that point (reading the file, diffing it) is pure, so replaying it on
  resume costs nothing and changes nothing.
"""

import asyncio
import json
import logging
import re
import time
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolMessage,
    message_chunk_to_message,
)
from langgraph.config import get_stream_writer
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from .agent_contracts import RunBudget, can_retry, needs_central_approval, observation, redact, risk_for

logger = logging.getLogger(__name__)

# What a tool declares about its own result, through the StructuredTool `tags`
# field. The loop reacts to these instead of to tool names, so a new tool opts
# in where it is defined rather than by being added to a list in here — this
# module has no business knowing that .docx exists.
#
# FILE_URL: the result carries a link meant for the user. Models routinely run
#   such a tool and then summarize without pasting the link, so it is
#   re-attached to the final answer.
# LOCAL_FILE: the result names a file in the user's workspace, which the CLI
#   lists at the end of a turn so they can see what was touched.
# NEEDS_APPROVAL: this tool applies its change the moment it runs, with no
#   confirmation step of its own. Some tools only need it under part of their
#   configuration, which a name-based list in agent_contracts cannot express —
#   the tool knows, so the tool declares it.
TAG_FILE_URL = "file_url"
TAG_LOCAL_FILE = "local_file"
TAG_NEEDS_APPROVAL = "needs_approval"

_FILE_URL_RE = re.compile(
    r"https?://[^\s\)\]\"\'<>]+"
    r"\.(?:jpg|jpeg|png|gif|webp|bmp|svg"
    r"|pdf|doc|docx|xls|xlsx|csv|txt|ppt|pptx"
    r"|zip|tar|gz|json|xml|mp4|mp3|ogg|wav)"
    r"(?:\?[^\s\)\]\"\'<>]*)?",
    re.IGNORECASE,
)


def declares(tool, tag: str) -> bool:
    """Whether a tool opted into the given result behaviour."""
    return tag in (getattr(tool, "tags", None) or ())


class AgentState(TypedDict):
    """Everything the loop carries between steps."""

    messages: Annotated[list[AnyMessage], add_messages]
    file_urls: dict[str, str]


def pending_tool_calls(messages: list[AnyMessage]) -> list[dict]:
    """Tool calls requested by the last AI turn that have no result yet."""
    last_ai_index = None
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], AIMessage):
            last_ai_index = index
            break
    if last_ai_index is None:
        return []

    last_ai = messages[last_ai_index]
    tool_calls = getattr(last_ai, "tool_calls", None) or []
    if not tool_calls:
        return []

    answered = {
        message.tool_call_id
        for message in messages[last_ai_index + 1:]
        if isinstance(message, ToolMessage)
    }
    return [call for call in tool_calls if call.get("id") not in answered]


def emit_event(event: dict) -> None:
    """Push a UI event onto the graph's custom stream, if one is listening.

    Outside a streaming run there is no writer, and the event is dropped —
    the blocking entry point has nowhere to show it anyway.
    """
    try:
        writer = get_stream_writer()
    except Exception:
        return
    if writer is not None:
        writer(event)


def key_arg(tool_name: str, args: dict) -> str:
    """Pick the one argument worth showing on the CLI's tool progress line."""
    import os

    for key in ("file_name", "path", "query", "url", "name", "command"):
        value = args.get(key)
        if value and isinstance(value, str):
            return os.path.basename(value.rstrip("/")) or value
    for value in args.values():
        if value and isinstance(value, str):
            return value[:60]
    return ""


def result_payload(result: str) -> Any:
    """What the tool actually returned, unwrapped from its observation.

    Every result now travels inside the ToolObservation envelope
    (``{"ok", "data", ...}``), so anything reading the tool's own fields has
    to look one level down. Plain results from before the envelope, and
    non-JSON results, are returned untouched.
    """
    try:
        parsed = json.loads(result)
    except Exception:
        return None
    if isinstance(parsed, dict) and "ok" in parsed and "data" in parsed:
        return parsed["data"]
    return parsed


def approval_target(args: dict) -> str:
    """What is about to happen, shown verbatim in the approval prompt.

    Deliberately not ``key_arg``: that shortens a path to its basename to keep
    the CLI's progress line narrow, which renders "rm -rf /tmp/x" as "x". Some-
    one deciding whether to allow a command has to see the command.
    """
    for key in ("command", "url", "path", "file_name", "name", "query"):
        value = args.get(key)
        if value and isinstance(value, str):
            return value[:500]
    return ""


def brief_result(tool_name: str, result: str) -> str:
    """One-line summary of a tool result, for the CLI's progress line."""
    data = result_payload(result)

    if tool_name == "read_docx":
        count = len(data.get("paragraphs", [])) if isinstance(data, dict) else 0
        return f"{count} paragraphs read" if count else "read"
    if tool_name in ("analyze_excel", "read_excel"):
        count = len(data.get("sheets", [])) if isinstance(data, dict) else 0
        return f"{count} sheet(s) analyzed" if count else "analyzed"
    if tool_name in ("modify_docx", "modify_excel", "write_docx", "write_excel"):
        import os

        saved = data.get("saved_to", "") if isinstance(data, dict) else ""
        return f"saved → {os.path.basename(saved)}" if saved else "saved"
    if tool_name == "list_directory":
        lines = result.count("\n")
        return f"{lines} entries" if lines else "listed"
    if tool_name == "find_files":
        files = data.get("files", []) if isinstance(data, dict) else []
        return f"{len(files)} file(s) found"
    if tool_name in ("search_documents", "search_content"):
        results = data.get("results", []) if isinstance(data, dict) else []
        return f"{len(results)} result(s)"
    if tool_name == "run_command":
        return "command executed"
    if "error" in result[:50].lower():
        return "error"
    return "ok"


async def _run_tool(tool, args: dict) -> Any:
    """Run a tool through its Runnable interface.

    Calling ``tool.coroutine`` directly drops LangGraph's runnable context.
    That context is required by ``interrupt()`` and ``get_stream_writer()``,
    so approval-capable tools must run through ``ainvoke``.
    """
    import inspect

    if hasattr(tool, "ainvoke"):
        return await tool.ainvoke(args)
    if getattr(tool, "coroutine", None):
        return await tool.coroutine(**args)
    if getattr(tool, "afunc", None):
        return await tool.afunc(**args)
    func = getattr(tool, "func", None)
    if func is None:
        return f"Tool {tool.name} has no executable method"
    if inspect.iscoroutinefunction(func):
        return await func(**args)
    return func(**args)


def _validate_args(tool, args: dict) -> tuple[dict, Optional[str]]:
    """Coerce args through the tool's schema.

    On failure the model gets told exactly which fields are missing and that it
    must retry, which recovers far more often than surfacing a raw Pydantic
    error.
    """
    schema = getattr(tool, "args_schema", None)
    if not schema:
        return args, None
    try:
        return schema(**args).model_dump(), None
    except Exception:
        missing = [
            name
            for name, field in schema.model_fields.items()
            if field.is_required() and name not in args
        ]
        missing_str = ", ".join(missing) if missing else "unknown"
        logger.warning(f"Tool {tool.name} args validation failed — missing: {missing_str}")
        return args, (
            f"Tool call validation failed for '{tool.name}': missing required fields: "
            f"{missing_str}. You MUST retry this tool call immediately with ALL required "
            f"arguments included in a single call. Do not respond to the user until the "
            f"tool succeeds."
        )


def build_agent_graph(llm_with_tools, tools: list, checkpointer=None, budget: RunBudget | None = None,
                      approvals_enabled: bool = False, tool_timeout: float = 90.0):
    """Compile the agent loop for one request.

    ``tools`` close over the caller's profile, workspace and callbacks, so a
    graph belongs to a single request. The caller supplies a request-scoped
    checkpointer because approval state is only valid while its SSE stream is
    alive.
    """
    from src.core.platform.ai.ollama_adapter import (
        normalize_tool_args as _normalize_tool_args,
        resolve_tool_name as _resolve_tool_name,
    )

    tools_by_name = {tool.name: tool for tool in tools or []}
    budget = budget or RunBudget()

    async def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        try:
            merged = None
            async for chunk in llm_with_tools.astream(messages):
                merged = chunk if merged is None else merged + chunk
            response = (
                message_chunk_to_message(merged)
                if merged is not None
                else AIMessage(content="")
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response = AIMessage(
                content=(
                    "Lo siento, ocurrió un error al procesar los resultados. "
                    "Por favor, intenta de nuevo."
                )
            )

        for call in getattr(response, "tool_calls", None) or []:
            name = call.get("name", "tool")
            emit_event({
                "type": "tool_call",
                "name": name,
                "arg": key_arg(name, call.get("args", {})),
                "risk": risk_for(name),
            })
        return {"messages": [response]}

    async def call_tool(state: AgentState) -> dict:
        """Execute exactly one pending tool call. See the module docstring."""
        pending = pending_tool_calls(state["messages"])
        if not pending:
            return {}

        call = pending[0]
        tool_name = _resolve_tool_name(call.get("name", "unknown"))
        if tool_name != call.get("name"):
            logger.info(f"Tool alias: {call.get('name')} → {tool_name}")
        args = _normalize_tool_args(tool_name, call.get("args", {}) or {})
        call_id = call.get("id", "unknown")
        # Keyed by call_id so an approval replay of this node is admitted
        # again rather than mistaken for the model repeating itself.
        blocked = budget.admit(tool_name, args, call_id)
        started = time.monotonic()

        tool = tools_by_name.get(tool_name)
        if blocked:
            result: Any = {"ok": False, "error": blocked, "retryable": False}
        elif tool is None:
            result = {"ok": False, "error": f"Tool {tool_name} not found", "retryable": False}
        else:
            args, validation_error = _validate_args(tool, args)
            if validation_error:
                result = validation_error
            elif approvals_enabled and (
                needs_central_approval(tool_name)
                or declares(tool, TAG_NEEDS_APPROVAL)
            ):
                from src.core.platform.ai.tools.approval_manager import rejection_message, request_approval
                approved, feedback = request_approval(
                    tool_name, approval_target(args),
                    json.dumps(redact(args), ensure_ascii=False, indent=2)[:2000],
                )
                result = None if approved else {"ok": False, "error": rejection_message(tool_name, feedback)}
            else:
                result = None
            if result is None:
                logger.info(f"Executing tool: {tool_name} with args: {args}")
                try:
                    result = await asyncio.wait_for(_run_tool(tool, args), timeout=tool_timeout)
                except GraphBubbleUp:
                    raise
                except asyncio.TimeoutError as e:
                    result = observation(None, error=e).as_json()
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    if can_retry(tool_name):
                        try:
                            result = await asyncio.wait_for(_run_tool(tool, args), timeout=tool_timeout)
                        except GraphBubbleUp:
                            raise
                        except Exception as retry_error:
                            result = observation(None, error=retry_error).as_json()
                    else:
                        result = observation(None, error=e).as_json()

        normalized = observation(result)
        result_str = normalized.as_json()
        logger.info(f"Tool {tool_name} result: {result_str[:200]}...")

        emit_event({
            "type": "tool_result",
            "name": tool_name,
            "summary": brief_result(tool_name, result_str),
            "ok": normalized.ok,
            "retryable": normalized.retryable,
        })
        # The audit trail belongs in the server log, not on the wire: no client
        # renders it, and shipping tool arguments to the browser widens their
        # exposure for nothing.
        logger.info(
            "agent_trace",
            extra={
                "tool": tool_name,
                "risk": risk_for(tool_name),
                # Not "args": logging reserves that name on LogRecord.
                "tool_args": redact(args),
                "ok": normalized.ok,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        if normalized.citations:
            emit_event({"type": "citations", "items": normalized.citations})

        if declares(tool, TAG_LOCAL_FILE):
            path = _touched_path(result_str, args)
            if path:
                emit_event({"type": "local_file_used", "path": path, "tool": tool_name})

        update: dict = {"messages": [ToolMessage(content=result_str, tool_call_id=call_id)]}
        if declares(tool, TAG_FILE_URL):
            urls = _FILE_URL_RE.findall(result_str)
            file_urls = dict(state.get("file_urls") or {})
            if urls:
                file_urls[tool_name] = urls[-1]
            else:
                file_urls.pop(tool_name, None)
            update["file_urls"] = file_urls

        return update

    def after_model(state: AgentState) -> str:
        return "tools" if pending_tool_calls(state["messages"]) else END

    def after_tool(state: AgentState) -> str:
        return "tools" if pending_tool_calls(state["messages"]) else "model"

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tool)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", after_model, {"tools": "tools", END: END})
    graph.add_conditional_edges("tools", after_tool, {"tools": "tools", "model": "model"})

    return graph.compile(checkpointer=checkpointer)


def _touched_path(result_str: str, args: dict) -> str:
    """Best-effort path of the file a document tool just read or wrote."""
    data = result_payload(result_str)
    if isinstance(data, dict):
        saved = data.get("saved_to") or data.get("path")
        if saved:
            return str(saved)
    return str(args.get("file_name") or args.get("path") or "")


def missing_file_urls(state: dict, text: str) -> list[str]:
    """Links a file tool produced that the model left out of its answer.

    Models routinely run send_file, then describe the result in prose without
    pasting the URL, which leaves the user with nothing to click.
    """
    return [
        url
        for url in (state.get("file_urls") or {}).values()
        if url and url not in text
    ]


def final_text(state: dict, extract_text) -> str:
    """The answer to show the user, with any file links the model dropped.

    ``extract_text`` normalizes provider-specific content shapes (Anthropic
    returns a list of blocks rather than a string).
    """
    messages = state.get("messages") or []
    content = ""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
            content = extract_text(message.content or "")
            break

    if not content:
        logger.warning("Agent loop ended without a final text response")
        content = "(Las herramientas se ejecutaron correctamente. Tarea completada.)"

    for url in missing_file_urls(state, content):
        logger.info(f"Appending missing file URL to response: {url}")
        content = f"{content}\n{url}"
    return content
