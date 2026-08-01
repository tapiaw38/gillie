import asyncio
import unittest

from src.core.platform.ai.tools.models import (
    _JS_CLICK_BY_IDX,
    _JS_EXISTS_BY_IDX,
    _JS_FOCUS_BY_IDX,
    _browser_state,
    _clip_snapshot,
    _dom_snapshot,
    _execute_actions,
)


class FakeLocator:
    def __init__(self, frame, selector):
        self.frame = frame
        self.selector = selector

    async def click(self, timeout=None):
        self.frame.calls.append(("click", self.selector))

    async def fill(self, text, timeout=None):
        self.frame.calls.append(("fill", self.selector, text))

    async def select_option(self, label=None, timeout=None):
        self.frame.calls.append(("select", self.selector, label))


class FakeFrame:
    """Frame whose live element set can change mid-batch, like a real re-render."""

    def __init__(self, url="https://example.test/", present=(1, 2), snapshot=""):
        self.url = url
        self.present = set(present)
        self.snapshot = snapshot
        self.calls = []

    def locator(self, selector):
        return FakeLocator(self, selector)

    async def evaluate(self, script, arg=None):
        if script == _JS_EXISTS_BY_IDX:
            return arg[0] in self.present
        if script in (_JS_CLICK_BY_IDX, _JS_FOCUS_BY_IDX):
            if arg[0] not in self.present:
                return False
            self.calls.append(("js", arg[0]))
            return True
        # DOM serializer
        start = arg or 0
        indices = [start + i + 1 for i in range(len(self.present))]
        return {"snapshot": self.snapshot or "body", "indices": indices}


class FakeKeyboard:
    def __init__(self):
        self.pressed = []

    async def press(self, key):
        self.pressed.append(key)


class FakePage(FakeFrame):
    def __init__(self, frames=None, **kwargs):
        super().__init__(**kwargs)
        self.keyboard = FakeKeyboard()
        self.frames = frames or [self]
        self.main_frame = self

    async def wait_for_load_state(self, state, timeout=None):
        return None

    async def goto(self, url, wait_until=None, timeout=None):
        self.calls.append(("goto", url))


def run(coro):
    return asyncio.run(coro)


class ExecuteActionsTests(unittest.TestCase):
    def setUp(self):
        _browser_state["frames"] = {}
        _browser_state["prev_indices"] = set()

    def test_index_zero_is_a_real_index(self):
        page = FakePage(present={0})
        results = run(_execute_actions(page, [{"type": "click", "index": 0}]))
        self.assertEqual(results, ["clicked [0]"])

    def test_it_prefers_playwrights_click_over_synthetic_js(self):
        page = FakePage(present={1})
        run(_execute_actions(page, [{"type": "click", "index": 1}]))
        self.assertEqual(page.calls, [("click", "[data-ai-idx='1']")])

    def test_it_stops_when_the_page_no_longer_matches_the_snapshot(self):
        page = FakePage(present={1})  # [2] was re-rendered away after the click
        results = run(_execute_actions(page, [
            {"type": "click", "index": 1},
            {"type": "click", "index": 2},
        ]))
        self.assertEqual(results[0], "clicked [1]")
        self.assertIn("stopped before click[2]", results[1])
        self.assertEqual(len(page.calls), 1)

    def test_select_passes_the_visible_label_not_the_value(self):
        page = FakePage(present={3})
        run(_execute_actions(page, [{"type": "select", "index": 3, "text": "Argentina"}]))
        self.assertEqual(page.calls, [("select", "[data-ai-idx='3']", "Argentina")])

    def test_actions_run_against_the_frame_that_owns_the_index(self):
        iframe = FakeFrame(url="https://pay.test/", present={5})
        page = FakePage(present={1})
        _browser_state["frames"] = {5: iframe}
        run(_execute_actions(page, [{"type": "type", "index": 5, "text": "4111"}]))
        self.assertEqual(iframe.calls, [("fill", "[data-ai-idx='5']", "4111")])
        self.assertEqual(page.calls, [])


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        _browser_state["frames"] = {}
        _browser_state["prev_indices"] = set()

    def test_iframes_are_indexed_without_colliding_with_the_main_frame(self):
        iframe = FakeFrame(url="https://pay.test/", present={1, 2}, snapshot="card form")
        page = FakePage(present={1, 2, 3}, snapshot="main body")
        page.frames = [page, iframe]

        snap = run(_dom_snapshot(page))

        self.assertEqual(snap["indices"], [1, 2, 3, 4, 5])
        self.assertEqual(len(set(snap["indices"])), 5)
        self.assertIn("[iframe https://pay.test/]", snap["snapshot"])
        self.assertEqual(_browser_state["frames"][4], iframe)
        self.assertEqual(_browser_state["frames"][1], page)

    def test_truncation_says_so_instead_of_cutting_mid_element(self):
        text = "\n".join(f"[{i}]<a />" for i in range(200))
        clipped = _clip_snapshot(text, 100)
        self.assertIn("truncated", clipped)
        self.assertFalse(clipped.split("\n")[-2].endswith("<a"))


if __name__ == "__main__":
    unittest.main()
