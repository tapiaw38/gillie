"""Fast evals for ReAct safety contracts; no provider or database needed."""
from src.core.platform.ai.agent_contracts import (
    RunBudget, can_retry, needs_central_approval, observation, redact, risk_for,
)


def test_redact_removes_secret_values_recursively():
    value = redact({"api_key": "sk-secret", "nested": ["token=abc", "safe"]})
    assert value["api_key"] == "[REDACTED]"
    assert "abc" not in value["nested"][0]


def test_budget_blocks_identical_tool_call_before_a_second_side_effect():
    budget = RunBudget(max_tools=3)
    assert budget.admit("write_file", {"path": "a.txt", "content": "x"}) is None
    assert "Repeated" in budget.admit("write_file", {"path": "a.txt", "content": "x"})


def test_budget_enforces_tool_limit():
    budget = RunBudget(max_tools=1)
    assert budget.admit("read_file", {"path": "a"}) is None
    assert "budget" in budget.admit("read_file", {"path": "b"}).lower()


def test_observation_normalizes_legacy_result_and_extracts_citations():
    result = observation("Found https://example.test/report.pdf")
    assert result.ok is True
    assert result.citations == ["https://example.test/report.pdf"]


def test_retry_and_approval_policy_never_retries_mutations():
    assert can_retry("web_search") is True
    assert can_retry("write_file") is False
    assert needs_central_approval("run_shell") is True
    assert needs_central_approval("read_file") is False
    assert risk_for("git_commit") == "destructive"


def test_budget_admits_a_replayed_call_so_approval_can_resume():
    """A node that pauses for approval re-runs from the top on resume.

    Counting that replay as a repeat would refuse the exact call the user
    just approved — the tool would never run.
    """
    budget = RunBudget()
    args = {"path": "a.txt", "content": "x"}
    assert budget.admit("write_file", args, "call-1") is None
    assert budget.admit("write_file", args, "call-1") is None
    assert budget.calls == 1, "a replay must not spend budget twice"


def test_budget_still_blocks_the_model_repeating_itself():
    budget = RunBudget()
    args = {"path": "a.txt"}
    assert budget.admit("read_file", args, "call-1") is None
    assert "Repeated" in budget.admit("read_file", args, "call-2")


def test_an_unclassified_tool_is_never_retried():
    """Most of the catalogue is unlisted; assuming those are safe reads is how
    a half-finished write gets silently run a second time."""
    for name in ("modify_docx", "write_excel", "delete_file", "insert_image_docx"):
        assert risk_for(name) == "unknown"
        assert can_retry(name) is False


def test_known_read_tools_stay_retryable():
    assert can_retry("read_file") is True
    assert can_retry("web_search") is True
