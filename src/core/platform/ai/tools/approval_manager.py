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
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Tuple

from langgraph.types import interrupt

logger = logging.getLogger(__name__)


def request_approval(tool_name: str, target: str, diff: str) -> Tuple[bool, str]:
    """Ask the user to approve a change, suspending the run until they answer.

    Only valid inside a graph node. Returns ``(approved, feedback)``, where
    feedback is the user's reason for rejecting — the model receives it so it
    can try a different approach rather than simply retrying the same edit.

    The request carries the server's own reading of the tool alongside it:

    * ``risk`` so a client can show what class of thing it is about to allow.
    * ``always_ask`` for the ones no blanket "stop asking me" mode may answer
      on the user's behalf. Clients used to decide that from a hardcoded list
      of tool names, which meant every new dangerous tool was auto-approved
      until somebody remembered to update each client.
    """
    from src.core.platform.ai.agent_contracts import needs_central_approval, risk_for

    risk = risk_for(tool_name)
    decision = interrupt({
        "type": "approval_request",
        "tool": tool_name,
        "file": target,
        "diff": diff,
        "risk": risk,
        "always_ask": risk in ("execute", "destructive")
        or needs_central_approval(tool_name),
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


_pending: Dict[str, Tuple[asyncio.Event, dict]] = {}

_client = None
_client_failed = False


def _approval_collection():
    """The audit collection, or None when Mongo is unavailable.

    Durability here is a bonus: the in-memory event is what actually wakes the
    live SSE stream, so losing Mongo costs resumability, not correctness.
    """
    global _client, _client_failed
    if _client_failed:
        return None
    if _client is None:
        try:
            from pymongo import MongoClient

            _client = MongoClient(
                os.getenv("DATABASE_URI", "mongodb://localhost:27017"),
                connectTimeoutMS=1_000,
                serverSelectionTimeoutMS=1_000,
            )
        except Exception:
            _client_failed = True
            return None
    try:
        return _client[os.getenv("DB_NAME", "gillie-db")]["agent_approvals"]
    except Exception:
        return None


async def _mongo(operation, *args, **kwargs):
    """Run a blocking pymongo call off the event loop, swallowing failures."""
    collection = _approval_collection()
    if collection is None:
        return None
    try:
        return await asyncio.to_thread(getattr(collection, operation), *args, **kwargs)
    except Exception as e:
        logger.warning(f"Approval audit write failed ({operation}): {e}")
        return None


async def create_pending(
    request_id: str, run_id: str = "", request: dict | None = None
) -> asyncio.Event:
    """Register a new pending approval and return the event to wait on."""
    event = asyncio.Event()
    _pending[request_id] = (event, {"approved": False, "feedback": ""})
    await _mongo(
        "update_one",
        {"request_id": request_id},
        {"$set": {
            "run_id": run_id,
            "status": "pending",
            "request": request or {},
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return event


async def submit_decision(request_id: str, approved: bool, feedback: str = "") -> bool:
    """Record the user's decision and unblock its waiter.

    Returns False if the request_id is unknown to *this* process — already
    timed out, already answered, or never registered. Mongo being reachable
    says nothing about that, so it does not affect the answer.
    """
    entry = _pending.get(request_id)
    await _mongo(
        "update_one",
        {"request_id": request_id},
        {"$set": {
            "approved": approved,
            "feedback": feedback or "",
            "decided_at": datetime.now(timezone.utc),
            "status": "decided",
        }},
        upsert=False,
    )
    if entry is None:
        return False
    event, decision = entry
    decision["approved"] = approved
    decision["feedback"] = feedback or ""
    event.set()
    return True


async def take_decision(request_id: str) -> dict:
    """Read a decision and drop the request. Unknown ids read as a rejection.

    The in-memory entry is authoritative: it is the same object
    ``submit_decision`` wrote, in the same process. Re-reading Mongo here would
    only add a way for a stale or half-written document to override a decision
    the user already gave.
    """
    _, decision = _pending.pop(request_id, (None, {"approved": False, "feedback": ""}))
    await _mongo(
        "update_one",
        {"request_id": request_id},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}},
        upsert=False,
    )
    return decision
