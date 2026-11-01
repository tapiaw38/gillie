"""Safe, auditable contracts shared by every ReAct tool execution."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

Risk = Literal["read", "network", "write", "execute", "destructive", "unknown"]

_SECRET = re.compile(r"(?i)(api[_-]?key|authorization|token|password|secret)\s*[:=]\s*[^\s,]+")
_URL = re.compile(r"https?://[^\s\]\)\"']+", re.I)

_RISK: dict[str, Risk] = {
    "run_shell": "execute", "run_command": "execute", "git_commit": "destructive",
    "system_propose": "execute", "system_confirm": "execute",
    "write_file": "write", "edit_file": "write", "download_file": "write",
    "browser_evaluate": "execute", "browser_connect": "destructive",
    "fetch_url": "network", "web_search": "network",
    "read_file": "read", "read_files": "read", "list_directory": "read",
    "find_files": "read", "search_content": "read", "search_documents": "read",
    "search_images": "read", "search_memory": "read",
}

_CENTRAL_APPROVAL = {"run_shell", "run_command", "git_commit", "download_file"}


def risk_for(tool_name: str) -> Risk:
    """How dangerous this tool is, for display and for the retry decision.

    Unlisted tools read as "unknown" rather than "read": claiming a tool is
    harmless because nobody wrote it down is how a mutation gets retried.
    """
    return _RISK.get(tool_name, "unknown")


def needs_central_approval(tool_name: str) -> bool:
    return tool_name in _CENTRAL_APPROVAL


def can_retry(tool_name: str) -> bool:
    """Whether a failed call may be re-run automatically.

    Opt-in by name. A tool has to be *known* idempotent to qualify, because a
    silent second run of a half-finished write is worse than the error the
    retry was meant to paper over.
    """
    return risk_for(tool_name) in ("read", "network")


def redact(value: Any) -> Any:
    """Remove credentials before events, traces and model-visible failures."""
    if isinstance(value, str):
        return _SECRET.sub(r"\1=[REDACTED]", value)
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(word in k.lower() for word in
                ("api_key", "apikey", "authorization", "token", "password", "secret")) else redact(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


@dataclass
class ToolObservation:
    ok: bool
    data: Any = None
    error: str | None = None
    retryable: bool = False
    artifacts: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)

    def as_json(self) -> str:
        return json.dumps({"ok": self.ok, "data": redact(self.data), "error": redact(self.error),
                           "retryable": self.retryable, "artifacts": self.artifacts,
                           "citations": self.citations}, ensure_ascii=False)


def observation(result: Any, *, error: Exception | None = None) -> ToolObservation:
    """Normalize legacy str/dict tool results without changing every tool."""
    if error is not None:
        message = str(error)
        return ToolObservation(False, error=message, retryable=not isinstance(error, (ValueError, PermissionError)))
    data = result
    if isinstance(result, str):
        try: data = json.loads(result)
        except Exception: pass
    if isinstance(data, dict) and data.get("ok") is not None:
        return ToolObservation(bool(data["ok"]), data=data.get("data"), error=data.get("error"),
                               retryable=bool(data.get("retryable", False)),
                               artifacts=list(data.get("artifacts") or []), citations=list(data.get("citations") or []))
    text = json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
    return ToolObservation(not text.lower().startswith("error"), data=data,
                           error=text if text.lower().startswith("error") else None,
                           citations=_URL.findall(text))


@dataclass
class RunBudget:
    """Caps one agent run: wall clock, tool count, and pointless repetition.

    Admission is keyed by the model's tool_call id, which makes it safe to
    replay. A node that pauses for approval is re-run from the top on resume,
    so a check that counted every *evaluation* would refuse the very call the
    user just approved.
    """

    max_tools: int = 30
    max_seconds: float = 300.0
    started: float = field(default_factory=time.monotonic)
    calls: int = 0
    seen: set[str] = field(default_factory=set)
    admitted: set[str] = field(default_factory=set)
    epoch: int = 0

    def admit(self, name: str, args: dict, call_id: str = "") -> str | None:
        """Verdict for one tool call: None to proceed, else why it is refused."""
        if call_id and call_id in self.admitted:
            return None  # replay of a call already let through

        if time.monotonic() - self.started > self.max_seconds:
            return "Agent time budget exhausted. Return final answer."
        if self.calls >= self.max_tools:
            return "Agent tool budget exhausted. Return final answer."

        mutates = risk_for(name) not in ("read", "unknown")
        fingerprint = self._fingerprint(name, args, mutates)
        if fingerprint in self.seen:
            return (
                "Repeated identical tool call blocked. Use its observation or "
                "choose another action."
            )

        self.calls += 1
        self.seen.add(fingerprint)
        if call_id:
            self.admitted.add(call_id)
        # Anything that changed state invalidates the observations taken before
        # it, so re-reading the same path afterwards is new work rather than a
        # repeat. Bumping the epoch retires the reads recorded so far in one
        # step, without touching the budget counters.
        if mutates:
            self.epoch += 1
        return None

    def _fingerprint(self, name: str, args: dict, mutates: bool) -> str:
        """Identity of one call, for the repeat check.

        A read is scoped to the epoch it happened in: once something has
        changed, asking again is a different question. A call that changes
        something is scoped to the whole run instead, because running the same
        side effect twice is a repeat however much happened in between — which
        is what this check is mainly here to stop.
        """
        payload = json.dumps(redact(args), sort_keys=True, default=str)
        epoch = "*" if mutates else self.epoch
        return f"{epoch}:{name}:{payload}"
