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



class SpawnOutputTests(unittest.TestCase):
    def test_electron_output_goes_to_a_log_file_not_the_conversation(self):
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured.update(kwargs)
            return mock.Mock()

        with mock.patch.object(avatar, "_check_avatar_dir"), \
             mock.patch.object(avatar, "_ensure_dependencies"), \
             mock.patch.object(avatar, "_ensure_build"), \
             mock.patch.object(avatar, "_build_launch", return_value=(["electron"], {})), \
             mock.patch.object(avatar.subprocess, "Popen", side_effect=fake_popen):
            avatar.spawn()

        self.assertIsNotNone(captured.get("stdout"))
        self.assertIsNotNone(captured.get("stderr"))
        self.assertNotEqual(captured["stdout"], 1)
        self.assertEqual(captured["stdin"], subprocess.DEVNULL)

    def test_the_log_lives_under_the_state_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(avatar.os.environ, {"XDG_STATE_HOME": tmp}):
                path = avatar.log_path()
        self.assertTrue(str(path).endswith("gillie/avatar.log"))



class LayoutEnvTests(unittest.TestCase):
    def _env(self, layout):
        with mock.patch.object(avatar, "get_avatar_layout", return_value=layout):
            return avatar._layout_env()

    def test_passes_saved_layout_to_the_launcher(self):
        self.assertEqual(
            self._env({"avatar_width": 500, "avatar_height": 900, "avatar_zoom": 2.0}),
            {
                "AVATAR_WINDOW_WIDTH": "500",
                "AVATAR_WINDOW_HEIGHT": "900",
                "AVATAR_ZOOM": "2.0",
            },
        )

    def test_an_unset_profile_leaves_the_app_defaults_alone(self):
        self.assertEqual(self._env({}), {})

    def test_drops_individual_fields_that_were_never_set(self):
        self.assertEqual(self._env({"avatar_zoom": 1.2}), {"AVATAR_ZOOM": "1.2"})

    def test_rejects_values_that_would_produce_an_unusable_window(self):
        self.assertEqual(self._env({"avatar_width": 0, "avatar_height": -10}), {})

    def test_survives_a_non_numeric_value(self):
        self.assertEqual(self._env({"avatar_width": "wide", "avatar_zoom": 1.5}),
                         {"AVATAR_ZOOM": "1.5"})

    def test_reaches_the_launch_environment(self):
        with mock.patch.object(avatar, "get_avatar_layout", return_value={"avatar_zoom": 2.5}), \
             mock.patch.object(avatar.Path, "exists", return_value=True):
            _, env = avatar._build_launch()
        self.assertEqual(env["AVATAR_ZOOM"], "2.5")



class ChatAvatarLifecycleTests(unittest.TestCase):
    def test_starting_registers_cleanup_and_leaves_the_terminal_visible(self):
        import cli.commands.agent as agent

        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch.object(avatar, "spawn", return_value=process), \
             mock.patch.object(avatar, "wait_for_bridge", return_value=True), \
             mock.patch.object(avatar, "terminal_hidden") as hide, \
             mock.patch.object(agent.atexit, "register") as register:
            started = agent._start_avatar()

        self.assertIs(started, process)
        hide.assert_not_called()
        register.assert_called_once_with(agent._stop_avatar, process)

    def test_a_bridge_that_never_answers_stops_the_process_and_continues(self):
        import cli.commands.agent as agent

        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch.object(avatar, "spawn", return_value=process), \
             mock.patch.object(avatar, "wait_for_bridge", return_value=False):
            self.assertIsNone(agent._start_avatar())
        process.terminate.assert_called_once()

    def test_stopping_is_a_no_op_when_nothing_was_started(self):
        import cli.commands.agent as agent

        agent._stop_avatar(None)

    def test_stopping_skips_a_process_that_already_exited(self):
        import cli.commands.agent as agent

        process = mock.Mock()
        process.poll.return_value = 0
        agent._stop_avatar(process)
        process.terminate.assert_not_called()



class OrphanPlayerTests(unittest.TestCase):
    """Closing the terminal must not leave a speech player talking to nobody."""

    def _run_child(self, signal_number):
        import os
        import signal as signal_module
        import subprocess as sp
        import sys
        import time

        read_fd, write_fd = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            import cli.commands.agent as agent

            agent._install_player_reaper()
            player = sp.Popen(["sleep", "120"])
            agent._track_player(player)
            os.write(write_fd, str(player.pid).encode())
            os.close(write_fd)
            time.sleep(30)
            os._exit(0)

        os.close(write_fd)
        player_pid = int(os.read(read_fd, 32))
        os.close(read_fd)
        time.sleep(1.5)
        os.kill(child, signal_number)
        os.waitpid(child, 0)
        time.sleep(1.0)
        try:
            with open(f"/proc/{player_pid}/stat") as handle:
                state = handle.read().split(") ", 1)[1][0]
        except FileNotFoundError:
            state = "gone"
        sp.run(["kill", "-9", str(player_pid)], stderr=sp.DEVNULL)
        return state

    def test_a_hangup_stops_the_player(self):
        import signal as signal_module

        self.assertIn(self._run_child(signal_module.SIGHUP), ("gone", "Z"))

    def test_a_terminate_stops_the_player(self):
        import signal as signal_module

        self.assertIn(self._run_child(signal_module.SIGTERM), ("gone", "Z"))

    def test_tracking_forgets_a_player_once_it_finishes(self):
        import cli.commands.agent as agent

        process = mock.Mock()
        agent._track_player(process)
        agent._untrack_player(process)
        self.assertNotIn(process, agent._live_players)

    def test_killing_skips_players_that_already_exited(self):
        import cli.commands.agent as agent

        process = mock.Mock()
        process.poll.return_value = 0
        agent._track_player(process)
        agent._kill_live_players()
        process.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
