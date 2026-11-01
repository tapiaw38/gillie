"""Reconnecting to a run must not replay the turn, and must not leak the ask."""

import asyncio

import pytest
from langchain_core.messages import HumanMessage

from src.core.platform.ai.langchain_service import _resume_payload
from src.core.platform.ai.tools.approval_manager import (
    create_pending,
    discard_pending,
    submit_decision,
)


class Snapshot:
    def __init__(self, values):
        self.values = values


def fresh():
    return {"messages": [HumanMessage(content="hola")], "file_urls": {}}


def test_a_thread_that_already_holds_the_turn_resumes_from_the_checkpoint():
    """`add_messages` keys on message id, and these are new objects, so sending
    them again appends the user's question a second time."""
    snapshot = Snapshot({"messages": [HumanMessage(content="hola")]})

    assert _resume_payload(snapshot, fresh()) is None


def test_a_finished_run_also_resumes_rather_than_replaying():
    """A reconnect after the run completed carries no pending approval, which
    used to leave the fresh messages in place and duplicate the turn."""
    snapshot = Snapshot(
        {"messages": [HumanMessage(content="hola")], "file_urls": {}}
    )

    assert _resume_payload(snapshot, fresh()) is None


def test_a_run_id_naming_nothing_starts_the_turn_normally():
    """An expired checkpoint, or a client inventing a run_id. Returning None
    here would hand the graph no input at all and answer nothing."""
    payload = fresh()

    assert _resume_payload(Snapshot({}), payload) is payload
    assert _resume_payload(Snapshot(None), payload) is payload


@pytest.mark.asyncio
async def test_discarding_a_pending_approval_leaves_nothing_behind():
    """The teardown path when a client goes away mid-prompt. The entry is only
    ever read by the stream that asked, so holding it leaks until restart."""
    await create_pending("req-1", "thread-1", {"tool": "run_shell"})

    discard_pending("req-1")

    assert await submit_decision("req-1", True) is False


@pytest.mark.asyncio
async def test_discarding_is_safe_to_repeat():
    discard_pending("never-registered")
    await create_pending("req-2", "thread-2", {})
    discard_pending("req-2")
    discard_pending("req-2")

    assert await submit_decision("req-2", True) is False


@pytest.mark.asyncio
async def test_a_live_request_still_takes_its_decision():
    """The control: discarding is what closes the entry, not registration
    failing in the first place."""
    event = await create_pending("req-3", "thread-3", {})

    assert await submit_decision("req-3", True, "ok") is True
    assert event.is_set()

    discard_pending("req-3")
