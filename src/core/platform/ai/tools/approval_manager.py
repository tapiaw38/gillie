"""
Global registry of pending tool approval requests.

When an LLM tool (edit_file, write_file) needs user approval before applying
changes, it registers a pending request here. The backend SSE stream delivers
an approval_request event to the CLI, which shows the diff and prompts the
user. Once the user responds via POST /conversation/tool/approve the decision
is recorded here and the waiting coroutine is unblocked.
"""
import asyncio
from typing import Dict, Tuple


# { request_id: (asyncio.Event, decision: list) }
# decision layout: [approved: bool, feedback: str]
# The list is used as a mutable container so the inner coroutine can write to
# it from a different call site without needing nonlocal.
_pending: Dict[str, Tuple[asyncio.Event, list]] = {}


def create_pending(request_id: str) -> asyncio.Event:
    """Register a new pending approval and return the event to wait on."""
    event = asyncio.Event()
    _pending[request_id] = (event, [False, ""])
    return event


def submit_decision(request_id: str, approved: bool, feedback: str = "") -> bool:
    """
    Record the user's decision for a pending request and unblock its waiter.

    Args:
        request_id: UUID of the pending approval.
        approved: True to apply the change, False to skip it.
        feedback: Optional rejection reason supplied by the user.

    Returns True if the request_id was found, False if it was unknown (e.g.
    already timed out or never registered).
    """
    if request_id not in _pending:
        return False
    event, decision = _pending[request_id]
    decision[0] = approved
    decision[1] = feedback or ""
    event.set()
    return True


def get_decision(request_id: str) -> bool:
    """Return the recorded decision (False if request_id is unknown)."""
    return _pending.get(request_id, (None, [False, ""]))[1][0]


def get_feedback(request_id: str) -> str:
    """Return the rejection feedback string (empty if unknown or not set)."""
    entry = _pending.get(request_id)
    if not entry:
        return ""
    _, decision = entry
    return decision[1] if len(decision) > 1 else ""


def cleanup(request_id: str) -> None:
    """Remove a completed request from the registry."""
    _pending.pop(request_id, None)
