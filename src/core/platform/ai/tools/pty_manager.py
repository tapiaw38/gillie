"""
Global registry of pending PTY command requests.

When the LLM wants to run a shell command through the user's active PTY
session (e.g. an open SSH connection), it registers a pending request here.
The backend SSE stream delivers a pty_command event to GTerm, which writes
the command to the PTY and captures the output. Once the output is captured
GTerm POSTs it to POST /conversation/{id}/pty-result, which unblocks the
waiting coroutine and returns the output to the LLM as the tool result.
"""
import asyncio
from typing import Dict, Tuple


# { request_id: (asyncio.Event, result: list) }
# result layout: [output: str]
_pending: Dict[str, Tuple[asyncio.Event, list]] = {}


def create_pending(request_id: str) -> asyncio.Event:
    """Register a new pending PTY request and return the event to wait on."""
    event = asyncio.Event()
    _pending[request_id] = (event, [""])
    return event


def submit_result(request_id: str, output: str) -> bool:
    """
    Record the PTY command output and unblock its waiter.

    Returns True if request_id was found, False if unknown (timed out or
    never registered).
    """
    if request_id not in _pending:
        return False
    event, result = _pending[request_id]
    result[0] = output
    event.set()
    return True


def get_result(request_id: str) -> str:
    """Return the recorded output (empty string if request_id is unknown)."""
    entry = _pending.get(request_id)
    if not entry:
        return ""
    _, result = entry
    return result[0]


def cleanup(request_id: str) -> None:
    """Remove a completed request from the registry."""
    _pending.pop(request_id, None)
