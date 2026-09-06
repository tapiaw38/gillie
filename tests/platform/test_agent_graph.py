"""Checks on the agent loop's shape: rounds, tool isolation, approvals, links."""

import asyncio
import json

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel

from src.core.platform.ai.graph import (
    TAG_FILE_URL,
    TAG_LOCAL_FILE,
    TAG_NEEDS_APPROVAL,
    approval_target,
    brief_result,
    build_agent_graph,
    final_text,
    pending_tool_calls,
    result_payload,
)
from src.core.platform.ai.tools.approval_manager import request_approval


def text_chunk(text: str) -> AIMessageChunk:
    return AIMessageChunk(content=text)


def call_chunk(name: str, args: dict, call_id: str) -> AIMessageChunk:
    return AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"name": name, "args": json.dumps(args), "id": call_id,
             "index": int(call_id) - 1 if call_id.isdigit() else 0}
        ],
    )


class ScriptedLLM:
    """Replays a fixed sequence of model turns, one per astream() call."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []

    async def astream(self, messages):
        self.seen.append(list(messages))
        for chunk in self.turns.pop(0):
            yield chunk


def run(graph, payload, config):
    return asyncio.run(graph.ainvoke(payload, config))


def make_tool(name, func, schema=None, tags=None):
    class _Args(BaseModel):
        pass

    return StructuredTool(
        name=name,
        description=name,
        args_schema=schema or _Args,
        coroutine=func,
        tags=tags,
    )


def config_for(thread: str) -> dict:
    return {"configurable": {"thread_id": thread}, "recursion_limit": 25}


def test_pending_tool_calls_ignores_answered_ones():
    llm = ScriptedLLM([[call_chunk("a", {}, "1"), call_chunk("b", {}, "2")]])
    messages = asyncio.run(_collect(llm))
    assert {c["id"] for c in pending_tool_calls(messages)} == {"1", "2"}

    messages.append(ToolMessage(content="done", tool_call_id="1"))
    assert [c["id"] for c in pending_tool_calls(messages)] == ["2"]


async def _collect(llm):
    merged = None
    async for chunk in llm.astream([]):
        merged = chunk if merged is None else merged + chunk
    return [merged]


def test_tools_run_one_per_step_and_loop_back_to_the_model():
    order = []

    async def first(**_):
        order.append("first")
        return "ok-first"

    async def second(**_):
        order.append("second")
        return "ok-second"

    llm = ScriptedLLM([
        [call_chunk("first", {}, "1"), call_chunk("second", {}, "2")],
        [text_chunk("both done")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("first", first), make_tool("second", second)],
        checkpointer=InMemorySaver(),
    )

    state = run(graph, {"messages": [HumanMessage("go")], "file_urls": {}}, config_for("t1"))

    assert order == ["first", "second"], "tools must run once each, in order"
    assert final_text(state, str) == "both done"
    # Two tool calls answered in one round, so the model is called twice total.
    assert len(llm.seen) == 2


def test_a_rejected_change_is_reported_without_running_the_tool():
    applied = []

    async def write(**_):
        approved, feedback = request_approval("write_file", "notes.md", "+ hi")
        if not approved:
            return f"rejected: {feedback}"
        applied.append("written")
        return "written"

    llm = ScriptedLLM([
        [call_chunk("write_file", {}, "1")],
        [text_chunk("understood, leaving it alone")],
    ])
    graph = build_agent_graph(llm, [make_tool("write_file", write)], checkpointer=InMemorySaver())
    config = config_for("t2")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("write")], "file_urls": {}}, config)
        snapshot = await graph.aget_state(config)
        request = snapshot.tasks[0].interrupts[0].value
        assert request["tool"] == "write_file"
        assert request["file"] == "notes.md"
        return await graph.ainvoke(
            Command(resume={"approved": False, "feedback": "wrong file"}), config
        )

    state = asyncio.run(drive())

    assert applied == [], "a rejected tool must not touch anything"
    results = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    assert result_payload(results[-1].content) == "rejected: wrong file"


def test_an_approved_change_resumes_and_applies():
    applied = []

    async def write(**_):
        approved, _ = request_approval("write_file", "notes.md", "+ hi")
        if not approved:
            return "rejected"
        applied.append("written")
        return "written"

    llm = ScriptedLLM([
        [call_chunk("write_file", {}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(llm, [make_tool("write_file", write)], checkpointer=InMemorySaver())
    config = config_for("t3")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("write")], "file_urls": {}}, config)
        return await graph.ainvoke(Command(resume={"approved": True, "feedback": ""}), config)

    state = asyncio.run(drive())

    assert applied == ["written"], "approval must let the tool through exactly once"
    assert final_text(state, str) == "done"


def test_a_dropped_file_link_is_appended_to_the_answer():
    url = "https://files.example.com/report.pdf"

    async def send(**_):
        return f"uploaded to {url}"

    llm = ScriptedLLM([
        [call_chunk("send_file", {}, "1")],
        [text_chunk("I sent you the report.")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("send_file", send, tags=[TAG_FILE_URL])], checkpointer=InMemorySaver()
    )

    state = run(graph, {"messages": [HumanMessage("send it")], "file_urls": {}}, config_for("t4"))

    assert final_text(state, str) == f"I sent you the report.\n{url}"


def test_an_unknown_tool_is_reported_back_to_the_model():
    llm = ScriptedLLM([
        [call_chunk("does_not_exist", {}, "1")],
        [text_chunk("my mistake")],
    ])
    graph = build_agent_graph(llm, [], checkpointer=InMemorySaver())

    state = run(graph, {"messages": [HumanMessage("go")], "file_urls": {}}, config_for("t5"))

    results = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    assert "not found" in results[0].content
    assert final_text(state, str) == "my mistake"


def test_missing_required_args_tell_the_model_to_retry():
    class NeedsPath(BaseModel):
        path: str

    async def reader(path: str):
        return f"read {path}"

    llm = ScriptedLLM([
        [call_chunk("read_file", {}, "1")],
        [text_chunk("retrying")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("read_file", reader, schema=NeedsPath)], checkpointer=InMemorySaver()
    )

    state = run(graph, {"messages": [HumanMessage("read")], "file_urls": {}}, config_for("t6"))

    result = [m for m in state["messages"] if isinstance(m, ToolMessage)][0].content
    assert "missing required fields: path" in result
    assert "MUST retry" in result


def test_a_failing_tool_does_not_kill_the_turn():
    async def boom(**_):
        raise RuntimeError("disk on fire")

    llm = ScriptedLLM([
        [call_chunk("boom", {}, "1")],
        [text_chunk("that failed, sorry")],
    ])
    graph = build_agent_graph(llm, [make_tool("boom", boom)], checkpointer=InMemorySaver())

    state = run(graph, {"messages": [HumanMessage("go")], "file_urls": {}}, config_for("t7"))

    result = [m for m in state["messages"] if isinstance(m, ToolMessage)][0].content
    assert "disk on fire" in result
    assert final_text(state, str) == "that failed, sorry"


def test_a_turn_with_no_tools_returns_the_text_directly():
    llm = ScriptedLLM([[text_chunk("hello "), text_chunk("there")]])
    graph = build_agent_graph(llm, [], checkpointer=InMemorySaver())

    state = run(graph, {"messages": [HumanMessage("hi")], "file_urls": {}}, config_for("t8"))

    assert final_text(state, str) == "hello there"
    assert len(llm.seen) == 1


def test_custom_events_reach_a_streaming_caller():
    async def touch(**_):
        return "ok"

    llm = ScriptedLLM([
        [call_chunk("touch", {}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(llm, [make_tool("touch", touch)], checkpointer=InMemorySaver())

    async def drive():
        events = []
        async for mode, item in graph.astream(
            {"messages": [HumanMessage("go")], "file_urls": {}},
            config_for("t9"),
            stream_mode=["messages", "custom"],
        ):
            if mode == "custom":
                events.append(item)
        return events

    events = asyncio.run(drive())
    kinds = [e["type"] for e in events]

    assert "tool_call" in kinds, "the CLI needs to know a tool started"
    assert "tool_result" in kinds, "the CLI needs to know how it ended"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


class _PromptProfileStub:
    name = "test"
    max_tool_rounds = 8
    max_history_messages = 20
    max_context_chars = 24000


class _ConfigStub:
    base_url = "https://api.openai.com/v1"
    model = "gpt-4o"
    provider_name = "openai"


def _service(llm, tools):
    """A LangChainService with only the pieces the stream driver touches."""
    from src.core.platform.ai.langchain_service import LangChainService

    service = object.__new__(LangChainService)
    service.config = _ConfigStub()
    service.llm = llm
    service.semaphore = asyncio.Semaphore(1)
    service._consecutive_failures = 0
    service._max_failures = 3
    service._circuit_open_until = None
    service.memory_manager = type("M", (), {
        "create_thread_id": staticmethod(lambda c, u: f"{u}_{c}"),
    })()
    service.checkpointer = InMemorySaver()
    service._prepare_run = lambda **kwargs: (
        _PromptProfileStub(), [HumanMessage("go")], tools
    )

    async def _bind(question, tool_list):
        return llm, tool_list

    service._bind_tools = _bind
    return service


def _drain(service, **kwargs):
    async def go():
        out = []
        async for item in service.generate_response_stream(
            question="go", context=None, previous_messages=[],
            profile=type("P", (), {"user_id": "u1"})(), conversation_id="c1",
            **kwargs,
        ):
            out.append(item)
        return out

    return asyncio.run(go())


def test_stream_emits_text_tokens_and_tool_events():
    async def touch(**_):
        return "ok"

    llm = ScriptedLLM([
        [call_chunk("touch", {}, "1")],
        [text_chunk("all "), text_chunk("done")],
    ])
    items = _drain(_service(llm, [make_tool("touch", touch)]))

    assert "".join(i for i in items if isinstance(i, str)) == "all done"
    kinds = [i["type"] for i in items if isinstance(i, dict)]
    # agent_run comes first so a client can resume this run after a drop.
    assert kinds == ["agent_run", "tool_call", "tool_result"]


def test_stream_does_not_leak_tool_call_chunks_as_text():
    async def touch(**_):
        return "ok"

    llm = ScriptedLLM([
        [call_chunk("touch", {}, "1")],
        [text_chunk("done")],
    ])
    items = _drain(_service(llm, [make_tool("touch", touch)]))

    assert "".join(i for i in items if isinstance(i, str)) == "done"


def test_stream_asks_for_approval_then_resumes_on_yes():
    from src.core.platform.ai.tools.approval_manager import submit_decision

    applied = []

    async def write(**_):
        approved, _feedback = request_approval("write_file", "notes.md", "+ hi")
        if not approved:
            return "rejected"
        applied.append("written")
        return "written"

    llm = ScriptedLLM([
        [call_chunk("write_file", {}, "1")],
        [text_chunk("saved it")],
    ])
    service = _service(llm, [make_tool("write_file", write)])

    async def go():
        out = []
        agen = service.generate_response_stream(
            question="go", context=None, previous_messages=[],
            profile=type("P", (), {"user_id": "u1"})(), conversation_id="c1",
        )
        async for item in agen:
            out.append(item)
            if isinstance(item, dict) and item["type"] == "approval_request":
                # Stand in for POST /conversation/tool/approve.
                assert await submit_decision(item["request_id"], True, "")
        return out

    items = asyncio.run(go())
    requests = [i for i in items if isinstance(i, dict) and i["type"] == "approval_request"]

    assert len(requests) == 1
    assert requests[0]["file"] == "notes.md"
    assert requests[0]["diff"] == "+ hi"
    assert applied == ["written"]
    assert "".join(i for i in items if isinstance(i, str)) == "saved it"


def test_stream_treats_an_unanswered_approval_as_a_rejection():
    applied = []

    async def write(**_):
        approved, _feedback = request_approval("write_file", "notes.md", "+ hi")
        if not approved:
            return "rejected"
        applied.append("written")
        return "written"

    llm = ScriptedLLM([
        [call_chunk("write_file", {}, "1")],
        [text_chunk("left it alone")],
    ])
    service = _service(llm, [make_tool("write_file", write)])

    items = _drain(service, approval_timeout=0.05)

    assert applied == [], "nobody answered, so nothing may be written"
    assert "".join(i for i in items if isinstance(i, str)) == "left it alone"


def test_stream_appends_a_file_link_the_model_left_out():
    url = "https://files.example.com/report.pdf"

    async def send(**_):
        return f"uploaded to {url}"

    llm = ScriptedLLM([
        [call_chunk("send_file", {}, "1")],
        [text_chunk("I sent the report.")],
    ])
    items = _drain(_service(llm, [make_tool("send_file", send, tags=[TAG_FILE_URL])]))

    assert "".join(i for i in items if isinstance(i, str)) == f"I sent the report.\n{url}"


def test_an_untagged_tool_does_not_get_its_urls_appended():
    """Only a tool that declares TAG_FILE_URL contributes links.

    Otherwise any tool that happens to mention a URL — a web search, an error
    message — would have it stapled onto the answer.
    """
    async def search(**_):
        return "see https://example.com/unrelated.pdf for background"

    llm = ScriptedLLM([
        [call_chunk("web_search", {}, "1")],
        [text_chunk("Here is what I found.")],
    ])
    graph = build_agent_graph(llm, [make_tool("web_search", search)], checkpointer=InMemorySaver())

    state = run(graph, {"messages": [HumanMessage("go")], "file_urls": {}}, config_for("t10"))

    assert final_text(state, str) == "Here is what I found."


def test_a_tagged_local_file_tool_reports_the_path_it_touched():
    async def edit(**_):
        return json.dumps({"saved_to": "/work/report.docx"})

    llm = ScriptedLLM([
        [call_chunk("modify_docx", {}, "1")],
        [text_chunk("updated")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("modify_docx", edit, tags=[TAG_LOCAL_FILE])],
        checkpointer=InMemorySaver(),
    )

    async def drive():
        events = []
        async for mode, item in graph.astream(
            {"messages": [HumanMessage("go")], "file_urls": {}},
            config_for("t11"),
            stream_mode=["messages", "custom"],
        ):
            if mode == "custom":
                events.append(item)
        return events

    touched = [e for e in asyncio.run(drive()) if e["type"] == "local_file_used"]

    assert len(touched) == 1
    assert touched[0]["path"] == "/work/report.docx"
    assert touched[0]["tool"] == "modify_docx"


def test_an_untagged_tool_reports_no_local_file():
    async def edit(**_):
        return json.dumps({"saved_to": "/work/report.docx"})

    llm = ScriptedLLM([
        [call_chunk("modify_docx", {}, "1")],
        [text_chunk("updated")],
    ])
    graph = build_agent_graph(llm, [make_tool("modify_docx", edit)], checkpointer=InMemorySaver())

    async def drive():
        events = []
        async for mode, item in graph.astream(
            {"messages": [HumanMessage("go")], "file_urls": {}},
            config_for("t12"),
            stream_mode=["messages", "custom"],
        ):
            if mode == "custom":
                events.append(item)
        return events

    assert [e for e in asyncio.run(drive()) if e["type"] == "local_file_used"] == []


def test_the_real_tool_factory_tags_the_tools_the_loop_reacts_to():
    """Guards the wiring: the loop is useless if nothing ever opts in."""
    from src.core.platform.ai.graph import declares
    from src.core.platform.ai.tools.models import create_langchain_tools

    profile = type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": None, "integrations": None, "files": None,
        "assistant_name": "g", "business_context": "", "response_language": "en",
    })()
    tools = {t.name: t for t in create_langchain_tools(None, profile) if t}

    for name in ("send_file", "send_screenshot"):
        assert name in tools, f"{name} disappeared from the tool set"
        assert declares(tools[name], TAG_FILE_URL), f"{name} lost its {TAG_FILE_URL} tag"

    for name in ("read_docx", "write_docx", "modify_docx", "modify_excel", "analyze_excel"):
        assert name in tools, f"{name} disappeared from the tool set"
        assert declares(tools[name], TAG_LOCAL_FILE), f"{name} lost its {TAG_LOCAL_FILE} tag"


def test_result_payload_unwraps_the_observation_envelope():
    """brief_result and _touched_path read the tool's own fields, which now
    live one level down inside the envelope."""
    from src.core.platform.ai.agent_contracts import observation
    from src.core.platform.ai.graph import _touched_path

    wrapped = observation(json.dumps({"saved_to": "/w/report.docx"})).as_json()

    assert result_payload(wrapped) == {"saved_to": "/w/report.docx"}
    assert _touched_path(wrapped, {}) == "/w/report.docx"
    assert brief_result("modify_docx", wrapped) == "saved → report.docx"


def test_result_payload_passes_through_a_bare_result():
    assert result_payload(json.dumps({"paragraphs": [1, 2]})) == {"paragraphs": [1, 2]}
    assert result_payload("not json") is None


def test_an_approved_tool_runs_once_when_the_node_replays():
    """The approval pause replays the node; the tool must not run twice."""
    runs = []

    async def write(**_):
        approved, _feedback = request_approval("write_file", "notes.md", "+ hi")
        if not approved:
            return "rejected"
        runs.append("written")
        return "written"

    llm = ScriptedLLM([
        [call_chunk("write_file", {}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("write_file", write)],
        checkpointer=InMemorySaver(), approvals_enabled=True,
    )
    config = config_for("replay")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("go")], "file_urls": {}}, config)
        return await graph.ainvoke(Command(resume={"approved": True, "feedback": ""}), config)

    state = asyncio.run(drive())

    assert runs == ["written"], "the approved tool ran once, not zero or twice"
    assert final_text(state, str) == "done"


def _profile(integrations=None):
    return type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": None, "integrations": integrations, "files": None,
        "assistant_name": "g", "business_context": "", "response_language": "en",
    })()


def _system_integration(require_confirmation: bool):
    from datetime import datetime, timezone

    from src.core.domain import Integration

    now = datetime.now(timezone.utc)
    return [Integration(
        name="system_commands",
        type="system",
        activated=True,
        config={"require_confirmation": require_confirmation},
        created_at=now,
        updated_at=now,
    )]


def _find(profile, name):
    from src.core.platform.ai.tools.models import create_langchain_tools

    for t in create_langchain_tools(None, profile) if True else []:
        if t and t.name == name:
            return t
    return None


def test_system_propose_asks_when_it_runs_the_command_itself():
    """With the profile's own confirmation off, nothing else stands between
    the model and a shell on the server."""
    from src.core.platform.ai.graph import TAG_NEEDS_APPROVAL, declares

    tool = _find(_profile(_system_integration(False)), "system_propose")

    assert tool is not None
    assert declares(tool, TAG_NEEDS_APPROVAL)


def test_system_propose_does_not_double_ask_when_a_code_is_required():
    """With confirmation on it only proposes; the user still has to send the
    code back, so prompting here too would be two asks for one command."""
    from src.core.platform.ai.graph import TAG_NEEDS_APPROVAL, declares

    tool = _find(_profile(_system_integration(True)), "system_propose")

    assert tool is not None
    assert not declares(tool, TAG_NEEDS_APPROVAL)


def test_a_tool_tagged_for_approval_is_paused_by_the_graph():
    ran = []

    async def shell(**_):
        ran.append("ran")
        return "output"

    llm = ScriptedLLM([
        [call_chunk("system_propose", {"command": "rm -rf /tmp/x"}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(
        llm,
        [make_tool("system_propose", shell, tags=[TAG_NEEDS_APPROVAL])],
        checkpointer=InMemorySaver(),
        approvals_enabled=True,
    )
    config = config_for("tagged-approval")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("go")], "file_urls": {}}, config)
        snapshot = await graph.aget_state(config)
        assert ran == [], "the command must not run before the user answers"
        request = snapshot.tasks[0].interrupts[0].value
        assert request["tool"] == "system_propose"
        return await graph.ainvoke(
            Command(resume={"approved": False, "feedback": "no"}), config
        )

    asyncio.run(drive())

    assert ran == [], "a rejected command must never reach the shell"


def test_an_untagged_tool_is_not_paused():
    ran = []

    async def harmless(**_):
        ran.append("ran")
        return "ok"

    llm = ScriptedLLM([
        [call_chunk("read_file", {"path": "a"}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("read_file", harmless)],
        checkpointer=InMemorySaver(), approvals_enabled=True,
    )

    run(graph, {"messages": [HumanMessage("go")], "file_urls": {}}, config_for("no-approval"))

    assert ran == ["ran"]


def test_the_approval_prompt_shows_the_whole_command():
    """key_arg basenames a path to keep the progress line short. Reusing it
    here showed 'x' for 'rm -rf /tmp/x' — the user would be approving blind."""
    from src.core.platform.ai.graph import key_arg

    args = {"command": "rm -rf /tmp/x"}

    assert approval_target(args) == "rm -rf /tmp/x"
    assert key_arg("system_propose", args) == "x", "the shortening is the point of key_arg"


def test_the_approval_prompt_shows_a_full_path_not_its_basename():
    assert approval_target({"path": "/etc/nginx/nginx.conf"}) == "/etc/nginx/nginx.conf"
    assert approval_target({"url": "https://bank.example/transfer"}) == (
        "https://bank.example/transfer"
    )


def test_the_command_reaches_the_approval_request_unmangled():
    class ShellArgs(BaseModel):
        command: str

    async def shell(command: str):
        return "ran"

    llm = ScriptedLLM([
        [call_chunk("system_propose", {"command": "rm -rf /tmp/x"}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(
        llm,
        [make_tool("system_propose", shell, schema=ShellArgs, tags=[TAG_NEEDS_APPROVAL])],
        checkpointer=InMemorySaver(), approvals_enabled=True,
    )
    config = config_for("approval-target")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("go")], "file_urls": {}}, config)
        snapshot = await graph.aget_state(config)
        return snapshot.tasks[0].interrupts[0].value

    request = asyncio.run(drive())

    assert request["file"] == "rm -rf /tmp/x"
    assert "rm -rf /tmp/x" in request["diff"]


def test_the_approval_request_carries_the_servers_own_verdict():
    """Clients used to keep their own list of dangerous tool names, so each
    one auto-approved every new dangerous tool until it was updated."""
    class ShellArgs(BaseModel):
        command: str

    async def shell(command: str):
        return "ran"

    llm = ScriptedLLM([
        [call_chunk("run_shell", {"command": "rm -rf /"}, "1")],
        [text_chunk("done")],
    ])
    graph = build_agent_graph(
        llm, [make_tool("run_shell", shell, schema=ShellArgs)],
        checkpointer=InMemorySaver(), approvals_enabled=True,
    )
    config = config_for("verdict")

    async def drive():
        await graph.ainvoke({"messages": [HumanMessage("go")], "file_urls": {}}, config)
        return (await graph.aget_state(config)).tasks[0].interrupts[0].value

    request = asyncio.run(drive())

    assert request["risk"] == "execute"
    assert request["always_ask"] is True


def test_a_write_is_flagged_but_left_auto_approvable():
    """auto-edit mode exists to skip these; flagging them always_ask would
    make the mode useless."""
    from src.core.platform.ai.agent_contracts import needs_central_approval, risk_for

    assert risk_for("write_file") == "write"
    assert not needs_central_approval("write_file")


def test_every_shell_capable_tool_reads_as_always_ask():
    from src.core.platform.ai.agent_contracts import needs_central_approval, risk_for

    for name in ("run_shell", "run_command", "system_propose", "system_confirm",
                 "git_commit", "browser_evaluate", "browser_connect", "download_file"):
        verdict = risk_for(name) in ("execute", "destructive") or needs_central_approval(name)
        assert verdict, f"{name} would be auto-approved by a yolo client"
