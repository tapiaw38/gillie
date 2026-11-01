"""A tool that needs approving must not run where nothing can ask.

`interrupt()` needs a live stream to suspend onto, so the blocking
`generate_response` path builds the graph with `approvals_enabled=False`. That
path serves WhatsApp, MercadoLibre and the internal managers. Letting a tool
through there because nobody could be asked is the one outcome the approval is
meant to prevent, so it is refused instead.
"""

import json
from datetime import datetime, timezone

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from langgraph.checkpoint.memory import InMemorySaver

from src.core.domain import Integration
from src.core.platform.ai.graph import TAG_NEEDS_APPROVAL, build_agent_graph
from src.core.platform.ai.tools.models import create_langchain_tools


class ScriptedLLM:
    """Emits one tool call, then whatever the model would say afterwards."""

    def __init__(self, tool_name: str, args: dict):
        self._tool_name = tool_name
        self._args = args
        self.rounds = 0

    async def astream(self, messages):
        self.rounds += 1
        if self.rounds == 1:
            yield AIMessage(
                content="",
                tool_calls=[
                    {"name": self._tool_name, "args": self._args, "id": "1"}
                ],
            )
        else:
            yield AIMessage(content="done")


class _Command(BaseModel):
    command: str


class _Path(BaseModel):
    path: str


def tool(name: str, fn, schema, tags=None) -> StructuredTool:
    return StructuredTool(
        name=name, description=name, args_schema=schema,
        coroutine=fn, tags=tags,
    )


async def run(tool_name: str, args: dict, tool_obj, *, approvals_enabled: bool):
    llm = ScriptedLLM(tool_name, args)
    graph = build_agent_graph(
        llm, [tool_obj],
        checkpointer=InMemorySaver(),
        approvals_enabled=approvals_enabled,
    )
    state = await graph.ainvoke(
        {"messages": [HumanMessage(content="go")], "file_urls": {}},
        {"configurable": {"thread_id": "t1"}, "recursion_limit": 10},
    )
    tool_messages = [m for m in state["messages"] if m.type == "tool"]
    assert tool_messages, "the tool call produced no result"
    return json.loads(tool_messages[0].content)


@pytest.mark.asyncio
async def test_a_central_approval_tool_is_refused_with_no_channel_to_ask():
    ran = []

    async def shell(command: str) -> str:
        ran.append(command)
        return "output"

    result = await run(
        "run_shell", {"command": "rm -rf /tmp/x"},
        tool("run_shell", shell, _Command), approvals_enabled=False,
    )

    assert ran == [], "the tool ran without anybody approving it"
    assert result["ok"] is False
    assert "cannot ask" in result["error"]
    assert result["retryable"] is False


@pytest.mark.asyncio
async def test_a_tagged_tool_is_refused_with_no_channel_to_ask():
    """The same holds for a tool that opts in by tag rather than by name."""
    ran = []

    async def propose(command: str) -> str:
        ran.append(command)
        return "output"

    result = await run(
        "system_propose", {"command": "shutdown now"},
        tool("system_propose", propose, _Command, tags=[TAG_NEEDS_APPROVAL]),
        approvals_enabled=False,
    )

    assert ran == []
    assert result["ok"] is False
    assert "cannot ask" in result["error"]


@pytest.mark.asyncio
async def test_a_tool_that_needs_no_approval_still_runs():
    """The control: refusing is about the approval, not about the channel.

    Without this, the tests above would pass just as well against a graph that
    had stopped running tools altogether.
    """
    ran = []

    async def reader(path: str) -> str:
        ran.append(path)
        return "contents"

    result = await run(
        "read_file", {"path": "a.txt"},
        tool("read_file", reader, _Path), approvals_enabled=False,
    )

    assert ran == ["a.txt"]
    assert result["ok"] is True


def integration(name: str, config: dict | None = None) -> Integration:
    now = datetime.now(timezone.utc)
    return Integration(
        name=name, type=name, activated=True, config=config or {},
        created_at=now, updated_at=now,
    )


def profile():
    return type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": None, "integrations": [integration("system_commands")],
        "files": None, "assistant_name": "g", "business_context": "",
        "response_language": "en",
    })()


def file_tool(name: str, workspace, *, approvals_enabled: bool):
    # The workspace has to contain the target, or the sandbox check refuses the
    # path before the approval gate is ever reached and the test would pass
    # without exercising it.
    tools = create_langchain_tools(
        None, profile(), approvals_enabled=approvals_enabled,
        client_workspace=str(workspace),
    )
    found = [t for t in tools if t.name == name]
    assert found, f"{name} was not registered"
    return found[0]


@pytest.mark.asyncio
async def test_write_file_refuses_rather_than_writing_unasked(tmp_path):
    """`write_file` gates itself rather than through the graph, so it needs its
    own check: its approval is skipped on the blocking path, and skipping the
    ask used to mean going ahead with the write."""
    target = tmp_path / "out.txt"

    result = await file_tool("write_file", tmp_path, approvals_enabled=False).ainvoke(
        {"path": str(target), "content": "x"}
    )

    assert not target.exists(), "the file was written with nobody approving it"
    assert result.get("skipped") is True
    assert "cannot ask" in result["message"]


@pytest.mark.asyncio
async def test_edit_file_refuses_rather_than_editing_unasked(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("hello world", encoding="utf-8")

    result = await file_tool("edit_file", tmp_path, approvals_enabled=False).ainvoke(
        {"path": str(target), "old_string": "hello", "new_string": "goodbye"}
    )

    assert target.read_text(encoding="utf-8") == "hello world"
    assert result.get("skipped") is True
    assert "cannot ask" in result["message"]
