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


def test_budget_allows_re_reading_a_path_after_something_changed_it():
    """A read-after-write is new work, not a repeat.

    Without this the obvious edit loop — read a file, change it, read it back
    to check — is refused on its last step, and the model is told to use an
    observation that the write in between made stale.
    """
    budget = RunBudget()
    assert budget.admit("read_file", {"path": "a.txt"}) is None
    assert "Repeated" in budget.admit("read_file", {"path": "a.txt"})

    assert budget.admit("write_file", {"path": "a.txt", "content": "x"}) is None

    assert budget.admit("read_file", {"path": "a.txt"}) is None


def test_budget_still_blocks_a_repeated_side_effect_across_epochs():
    """The counterpart: a mutation is scoped to the whole run.

    Letting the epoch retire these too would mean any write could be replayed
    by sandwiching another one between the attempts.
    """
    budget = RunBudget()
    assert budget.admit("write_file", {"path": "a.txt", "content": "x"}) is None
    assert budget.admit("write_file", {"path": "b.txt", "content": "y"}) is None

    assert "Repeated" in budget.admit("write_file", {"path": "a.txt", "content": "x"})


def test_budget_does_not_let_an_unknown_tool_retire_the_repeat_check():
    """`risk_for` reads an unlisted tool as "unknown", which is not a licence
    to treat it as a mutation: that would hand any unclassified tool a way to
    clear the check."""
    budget = RunBudget()
    assert budget.admit("read_file", {"path": "a.txt"}) is None
    assert budget.admit("some_unlisted_tool", {"x": 1}) is None

    assert "Repeated" in budget.admit("read_file", {"path": "a.txt"})
