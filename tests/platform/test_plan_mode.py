"""Plan mode has to describe, never act — including the system_* shell tools.

These two are the ones with no plan_mode branch of their own: `propose_command`
runs the command on the spot when confirmation is off, and `confirm_command`
always runs it. The CLI's approval policy returns "do not ask" for plan mode on
the stated grounds that nothing executes there, so if the guard regresses a
shell command runs with no prompt at all.
"""

from datetime import datetime, timezone

import pytest

from src.core.domain import Integration
from src.core.platform.ai.tools.models import create_langchain_tools


def integration(name: str, config: dict | None = None) -> Integration:
    now = datetime.now(timezone.utc)
    return Integration(
        name=name, type=name, activated=True, config=config or {},
        created_at=now, updated_at=now,
    )


def profile(require_confirmation: bool):
    return type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": None,
        "integrations": [
            integration(
                "system_commands",
                {"require_confirmation": require_confirmation},
            ),
        ],
        "files": None, "assistant_name": "g", "business_context": "",
        "response_language": "en",
    })()


def tool_named(name: str, *, require_confirmation: bool, plan_mode: bool):
    tools = create_langchain_tools(
        None, profile(require_confirmation), plan_mode=plan_mode
    )
    found = [t for t in tools if t.name == name]
    assert found, f"{name} was not registered"
    return found[0]


@pytest.mark.asyncio
async def test_system_propose_runs_the_command_when_not_planning(tmp_path):
    """The control: without plan mode the command really does execute.

    Without this, the test below would pass just as well against a tool that
    never worked in the first place.
    """
    marker = tmp_path / "ran.txt"
    tool = tool_named("system_propose", require_confirmation=False, plan_mode=False)

    result = await tool.ainvoke({"command": f"touch {marker}"})

    assert marker.exists(), f"command did not run: {result}"


@pytest.mark.asyncio
async def test_system_propose_only_describes_in_plan_mode(tmp_path):
    marker = tmp_path / "ran.txt"
    tool = tool_named("system_propose", require_confirmation=False, plan_mode=True)

    result = await tool.ainvoke({"command": f"touch {marker}"})

    assert result.get("plan_only") is True
    assert not marker.exists(), "plan mode executed the command"


@pytest.mark.asyncio
async def test_system_propose_banks_no_pending_code_in_plan_mode():
    """With confirmation on, proposing stores a code to execute later.

    Plan mode must not leave that behind either: the user asked for a plan,
    not for a command parked and ready to run.
    """
    tool = tool_named("system_propose", require_confirmation=True, plan_mode=True)

    result = await tool.ainvoke({"command": "echo hi"})

    assert result.get("plan_only") is True
    assert "code" not in result


@pytest.mark.asyncio
async def test_system_confirm_only_describes_in_plan_mode(tmp_path):
    """`system_confirm` is reachable in plan mode via a code from an earlier,
    non-planning turn, so its own guard is what has to stop it."""
    from src.core.platform.tools import system_monitor

    marker = tmp_path / "ran.txt"
    system_monitor._pending["ABC123"] = f"touch {marker}"
    try:
        tool = tool_named(
            "system_confirm", require_confirmation=True, plan_mode=True
        )

        result = await tool.ainvoke({"code": "ABC123"})

        assert result.get("plan_only") is True
        assert not marker.exists(), "plan mode executed the pending command"
        assert "ABC123" in system_monitor._pending, "plan mode consumed the code"
    finally:
        system_monitor._pending.pop("ABC123", None)
