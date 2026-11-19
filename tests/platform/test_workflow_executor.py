import asyncio
import unittest
from unittest import mock

from src.core.platform.functions.workflow_executor import WorkflowError, WorkflowExecutor


def run(coro):
    return asyncio.run(coro)


def step(name, url="https://api.test/x", **extra):
    return {"name": name, "url": url, "method": "GET", **extra}


class RecordingExecutor(WorkflowExecutor):
    """Executor whose HTTP layer is replaced by a scripted list of responses."""

    def __init__(self, responses=None):
        super().__init__()
        self.responses = list(responses or [])
        self.calls = []

    async def _assert_url_allowed(self, url):
        return None  # the guard has its own tests; these exercise orchestration

    async def _request(self, session, method, url, headers, body, timeout=30.0):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
        if not self.responses:
            return {}
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class SubstitutionTests(unittest.TestCase):
    def test_a_quote_in_a_value_cannot_break_the_body(self):
        body = WorkflowExecutor._build_body(
            '{"name": "{customer}"}', {"customer": 'Ana "La Jefa"'}
        )
        self.assertEqual(body, {"name": 'Ana "La Jefa"'})

    def test_a_placeholder_alone_keeps_the_value_type(self):
        body = WorkflowExecutor._build_body('{"n": "{count}"}', {"count": 3})
        self.assertEqual(body, {"n": 3})

    def test_a_placeholder_in_a_numeric_position_still_works(self):
        body = WorkflowExecutor._build_body('{"n": {count}}', {"count": 3})
        self.assertEqual(body, {"n": 3})

    def test_a_broken_template_raises_instead_of_sending_an_empty_body(self):
        with self.assertRaises(WorkflowError):
            WorkflowExecutor._build_body('{"n": {count}', {"count": 3})

    def test_url_values_are_encoded_so_they_cannot_rewrite_the_endpoint(self):
        url = WorkflowExecutor._substitute_url(
            "https://api.test/users/{q}", {"q": "x?admin=true&y=1"}
        )
        self.assertEqual(url, "https://api.test/users/x%3Fadmin%3Dtrue%26y%3D1")

    def test_header_values_cannot_inject_newlines(self):
        value = WorkflowExecutor._substitute_header(
            "Bearer {token}", {"token": "abc\r\nX-Admin: 1"}
        )
        self.assertEqual(value, "Bearer abcX-Admin: 1")

    def test_an_unknown_placeholder_is_left_alone(self):
        self.assertEqual(
            WorkflowExecutor._substitute_url("https://api.test/{missing}", {}),
            "https://api.test/{missing}",
        )


class ConditionTests(unittest.TestCase):
    def test_a_condition_nobody_can_parse_stops_the_workflow(self):
        self.assertFalse(WorkflowExecutor._evaluate_condition("totally bogus", {"a": 1}))

    def test_a_condition_that_raises_stops_the_workflow(self):
        self.assertFalse(
            WorkflowExecutor._evaluate_condition("greater_than:n=abc", {"n": "x"})
        )

    def test_the_supported_operators_still_work(self):
        self.assertTrue(WorkflowExecutor._evaluate_condition("ok == true", {"ok": True}))
        self.assertTrue(WorkflowExecutor._evaluate_condition("exists:id", {"id": "7"}))
        self.assertFalse(WorkflowExecutor._evaluate_condition("exists:id", {"id": None}))
        self.assertTrue(WorkflowExecutor._evaluate_condition("greater_than:n=2", {"n": 5}))


class ExecutionTests(unittest.TestCase):
    def _run(self, executor, steps, params=None, **workflow):
        return run(
            executor.execute_workflow(
                {"name": "wf", "steps": steps, **workflow}, params or {}
            )
        )

    def test_a_failed_step_aborts_instead_of_firing_the_rest(self):
        executor = RecordingExecutor([RuntimeError("500 from API")])
        result = self._run(executor, [step("login"), step("charge")])

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stopped_at"], "login")
        self.assertEqual(len(executor.calls), 1)

    def test_continue_on_error_is_opt_in(self):
        executor = RecordingExecutor([RuntimeError("nope"), {"ok": True}])
        result = self._run(
            executor, [step("optional", continue_on_error=True), step("main")]
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps_executed"], ["main"])

    def test_a_condition_guards_the_step_it_is_attached_to(self):
        executor = RecordingExecutor([{"ok": False}])
        result = self._run(
            executor,
            [
                step("check", response_mapping={"ok": "ok"}),
                step("charge", condition="ok == true"),
            ],
        )

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stopped_at"], "charge")
        self.assertEqual(len(executor.calls), 1)

    def test_response_mapping_feeds_the_next_step(self):
        executor = RecordingExecutor([{"data": {"id": "42"}}, {}])
        self._run(
            executor,
            [
                step("create", response_mapping={"booking_id": "data.id"}),
                step("confirm", url="https://api.test/b/{booking_id}"),
            ],
        )

        self.assertEqual(executor.calls[1]["url"], "https://api.test/b/42")

    def test_duplicate_step_names_are_rejected_before_anything_runs(self):
        executor = RecordingExecutor()
        with self.assertRaises(ValueError):
            self._run(executor, [step("same"), step("same")])
        self.assertEqual(executor.calls, [])

    def test_two_concurrent_runs_do_not_share_a_context(self):
        executor = RecordingExecutor([{}, {}, {}, {}])
        steps = [
            step("one", url="https://api.test/first"),
            step("two", url="https://api.test/{token}"),
        ]

        async def both():
            return await asyncio.gather(
                executor.execute_workflow({"name": "a", "steps": steps}, {"token": "AAA"}),
                executor.execute_workflow({"name": "b", "steps": steps}, {"token": "BBB"}),
            )

        first, second = run(both())
        self.assertEqual(first["context"]["token"], "AAA")
        self.assertEqual(second["context"]["token"], "BBB")

        self.assertEqual(
            sorted(c["url"] for c in executor.calls),
            [
                "https://api.test/AAA",
                "https://api.test/BBB",
                "https://api.test/first",
                "https://api.test/first",
            ],
        )


class UrlGuardTests(unittest.TestCase):
    def _assert(self, url, ip):
        """Run the guard with DNS pinned to `ip`, so no test touches the network."""
        loop = mock.Mock()
        loop.getaddrinfo = mock.AsyncMock(return_value=[(2, 1, 6, "", (ip, 80))])

        async def go():
            with mock.patch("asyncio.get_running_loop", return_value=loop):
                await WorkflowExecutor._assert_url_allowed(url)

        return run(go())

    def test_the_cloud_metadata_endpoint_is_blocked(self):
        with self.assertRaises(WorkflowError):
            self._assert("http://169.254.169.254/latest/meta-data/", "169.254.169.254")

    def test_private_ranges_are_blocked_by_default(self):
        with self.assertRaises(WorkflowError):
            self._assert("http://internal.corp/admin", "10.0.0.5")

    def test_loopback_stays_reachable_for_the_built_in_workflows(self):
        self._assert("http://localhost:8000/api/v1/calendar", "127.0.0.1")

    def test_public_addresses_are_allowed(self):
        self._assert("https://api.stripe.com/v1/charges", "93.184.216.34")


if __name__ == "__main__":
    unittest.main()


class RedactionTests(unittest.TestCase):
    def test_headers_never_reach_the_prompt(self):
        from src.core.platform.functions.global_workflows import redact_functions_for_prompt

        rendered = redact_functions_for_prompt(
            '[{"name": "book", "headers": {"Authorization": "Bearer sk-live-123"}, '
            '"steps": [{"name": "s", "url": "https://x.test", "headers": {"X-Key": "sk-live-456"}}]}]'
        )

        self.assertNotIn("sk-live-123", rendered)
        self.assertNotIn("sk-live-456", rendered)
        self.assertIn("book", rendered)
        self.assertIn("[redacted]", rendered)

    def test_unparseable_config_is_omitted_rather_than_leaked(self):
        from src.core.platform.functions.global_workflows import redact_functions_for_prompt

        self.assertEqual(redact_functions_for_prompt("{not json, token=sk-live"), "")
