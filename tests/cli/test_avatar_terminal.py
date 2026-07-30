import subprocess
import unittest
from unittest import mock

from cli.commands import avatar


class TerminalHiddenTests(unittest.TestCase):
    def _patch_environment(self, matches, isatty=True, wlrctl="/usr/bin/wlrctl"):
        calls = []

        def fake_wlrctl(action, marker):
            calls.append(action)
            return matches if action == "list" else []

        patches = [
            mock.patch.object(avatar.sys.stdout, "isatty", return_value=isatty),
            mock.patch.dict(avatar.os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False),
            mock.patch.object(avatar.shutil, "which", return_value=wlrctl),
            mock.patch.object(avatar, "_wlrctl", side_effect=fake_wlrctl),
            mock.patch.object(avatar, "_set_terminal_title"),
            mock.patch.object(avatar.time, "sleep"),
            mock.patch.object(avatar.atexit, "register"),
            mock.patch.object(avatar.signal, "signal"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return calls

    def test_restores_the_terminal_after_a_normal_exit(self):
        calls = self._patch_environment(["ghostty: marker"])
        with avatar.terminal_hidden() as hidden:
            self.assertTrue(hidden)
        self.assertEqual(calls, ["list", "minimize", "activate"])

    def test_restores_the_terminal_when_the_body_raises(self):
        calls = self._patch_environment(["ghostty: marker"])
        with self.assertRaises(KeyboardInterrupt):
            with avatar.terminal_hidden():
                raise KeyboardInterrupt
        self.assertIn("activate", calls)

    def test_does_not_hide_when_the_window_is_ambiguous(self):
        calls = self._patch_environment(["one: a", "two: b"])
        with avatar.terminal_hidden() as hidden:
            self.assertFalse(hidden)
        self.assertNotIn("minimize", calls)

    def test_does_not_hide_when_no_window_matches(self):
        calls = self._patch_environment([])
        with avatar.terminal_hidden() as hidden:
            self.assertFalse(hidden)
        self.assertNotIn("minimize", calls)

    def test_does_not_hide_without_wlrctl(self):
        calls = self._patch_environment(["ghostty: marker"], wlrctl=None)
        with avatar.terminal_hidden() as hidden:
            self.assertFalse(hidden)
        self.assertEqual(calls, [])

    def test_does_not_hide_when_stdout_is_not_a_tty(self):
        calls = self._patch_environment(["ghostty: marker"], isatty=False)
        with avatar.terminal_hidden() as hidden:
            self.assertFalse(hidden)
        self.assertEqual(calls, [])

    def test_disabled_flag_skips_everything(self):
        calls = self._patch_environment(["ghostty: marker"])
        with avatar.terminal_hidden(enabled=False) as hidden:
            self.assertFalse(hidden)
        self.assertEqual(calls, [])

    def test_survives_a_wlrctl_failure_while_listing(self):
        patches = [
            mock.patch.object(avatar.sys.stdout, "isatty", return_value=True),
            mock.patch.dict(avatar.os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False),
            mock.patch.object(avatar.shutil, "which", return_value="/usr/bin/wlrctl"),
            mock.patch.object(avatar, "_wlrctl", side_effect=subprocess.TimeoutExpired("wlrctl", 5)),
            mock.patch.object(avatar, "_set_terminal_title"),
            mock.patch.object(avatar.time, "sleep"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        with avatar.terminal_hidden() as hidden:
            self.assertFalse(hidden)


class WaitForBridgeTests(unittest.TestCase):
    def test_returns_true_once_the_port_accepts(self):
        with mock.patch.object(avatar.socket, "create_connection"):
            self.assertTrue(avatar.wait_for_bridge(port=47831, timeout=1))

    def test_returns_false_when_the_port_never_opens(self):
        with mock.patch.object(avatar.socket, "create_connection", side_effect=OSError), \
             mock.patch.object(avatar.time, "sleep"):
            self.assertFalse(avatar.wait_for_bridge(port=47831, timeout=0.5))


if __name__ == "__main__":
    unittest.main()
