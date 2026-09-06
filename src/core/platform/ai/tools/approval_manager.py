"""
Human-in-the-loop approval for tool calls that change the user's machine.

Two halves that meet at the LangGraph run:

* A tool calls :func:`request_approval`, which suspends the run at that exact
  point and checkpoints it. Nothing after the call executes until a decision
  arrives. The configured in-memory checkpointer is process-local, so a
  restart or a disconnected stream rejects the pending operation rather than
  resuming it later.
* The stream driver sees the suspended run, emits an ``approval_request`` event
  to the CLI, and parks on :func:`create_pending` until ``POST
  /conversation/tool/approve`` delivers the answer via :func:`submit_decision`.

The registry below only bridges that HTTP round trip; it holds no tool state.
"""
import asyncio
from typing import Dict, Tuple

from langgraph.types import interrupt


def request_approval(tool_name: str, target: str, diff: str) -> Tuple[bool, str]:
    """Ask the user to approve a change, suspending the run until they answer.

    Only valid inside a graph node. Returns ``(approved, feedback)``, where
    feedback is the user's reason for rejecting — the model receives it so it
    can try a different approach rather than simply retrying the same edit.
    """
    decision = interrupt({
        "type": "approval_request",
        "tool": tool_name,
        "file": target,
        "diff": diff,
    })
    if isinstance(decision, dict):
        return bool(decision.get("approved")), str(decision.get("feedback") or "")
    return bool(decision), ""


def rejection_message(target: str, feedback: str) -> str:
    """The tool result shown to the model when the user says no."""
    message = f"Change to '{target}' was rejected by the user."
    if feedback:
        message += f" Reason: {feedback}. Please try a different approach."
    return message


# { request_id: (event, {"approved": bool, "feedback": str}) }
_pending: Dict[str, Tuple[asyncio.Event, dict]] = {}


def create_pending(request_id: str) -> asyncio.Event:
    """Register a new pending approval and return the event to wait on."""
    event = asyncio.Event()
    _pending[request_id] = (event, {"approved": False, "feedback": ""})
    return event


def submit_decision(request_id: str, approved: bool, feedback: str = "") -> bool:
    """Record the user's decision and unblock its waiter.

    Returns False if the request_id is unknown — already timed out, already
    answered, or never registered.
    """
    entry = _pending.get(request_id)
    if entry is None:
        return False
    event, decision = entry
    decision["approved"] = approved
    decision["feedback"] = feedback or ""
    event.set()
    return True


def take_decision(request_id: str) -> dict:
    """Read a decision and drop the request. Unknown ids read as a rejection."""
    _, decision = _pending.pop(request_id, (None, {"approved": False, "feedback": ""}))
    return decision
