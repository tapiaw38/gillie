"""`disabled_tools` has to reach every tool, however it was registered."""

from datetime import datetime, timezone

from src.core.domain import Integration
from src.core.platform.ai.tools.models import (
    AVATAR_ANIMATIONS,
    create_langchain_tools,
)


def integration(name: str, config: dict | None = None) -> Integration:
    now = datetime.now(timezone.utc)
    return Integration(
        name=name, type=name, activated=True, config=config or {},
        created_at=now, updated_at=now,
    )


def profile(disabled=None):
    return type("P", (), {
        "user_id": "u1", "functions": None, "tool_prompts": None,
        "disabled_tools": disabled,
        "integrations": [
            integration("google_calendar"),
            integration("system_commands", {"require_confirmation": False}),
        ],
        "files": None, "assistant_name": "g", "business_context": "",
        "response_language": "en",
    })()


class FakeAvatar:
    """A reachable avatar client is what registers the avatar tools."""

    def avatar_available(self):
        return True

    async def avatar_play_animation(self, *a, **k):
        return True

    async def avatar_control_window(self, *a, **k):
        return True

    async def avatar_status(self):
        return {}


def build(disabled=None):
    return create_langchain_tools(None, profile(disabled), avatar_mcp=FakeAvatar())


def test_the_widest_catalogue_registers_the_conditional_blocks():
    """Guards the fixture: if these stop registering, the test below would
    pass while proving nothing."""
    names = {t.name for t in build()}

    assert "calendar_create_event" in names
    assert "system_propose" in names
    if AVATAR_ANIMATIONS:
        # Only registered when the avatar asset manifest is present, and that
        # file is gitignored — so in a fresh clone its absence is the expected
        # state, not a regression in the registration it guards.
        assert "avatar_play_animation" in names


def test_every_registered_tool_can_be_disabled():
    """Blocks that append StructuredTool directly each repeat the disabled
    check by hand, and some forgot. Disabling everything must leave nothing —
    that holds no matter how a tool was registered."""
    names = sorted(t.name for t in build())

    survivors = sorted(t.name for t in build(disabled=names))

    assert survivors == [], f"these ignore disabled_tools: {survivors}"


def test_disabling_one_tool_leaves_the_rest():
    full = {t.name for t in build()}

    remaining = {t.name for t in build(disabled=["calendar_delete_event"])}

    assert "calendar_delete_event" not in remaining
    assert remaining == full - {"calendar_delete_event"}


def test_no_none_slips_into_the_tool_list():
    assert all(t is not None for t in build())
