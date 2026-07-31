import unittest

from src.core.platform.managers.speech_segmentation import split_leading_sentence


def drain(text, chunk=4):
    buffer = ""
    segments = []
    for index in range(0, len(text), chunk):
        buffer += text[index:index + chunk]
        segment, buffer = split_leading_sentence(buffer)
        if segment:
            segments.append(segment)
    if buffer.strip():
        segments.append(buffer.strip())
    return segments


class SplitLeadingSentenceTests(unittest.TestCase):
    def test_holds_back_fragments_that_are_too_short_to_speak(self):
        self.assertEqual(split_leading_sentence("Hola."), ("", "Hola."))

    def test_emits_a_sentence_once_it_is_long_enough(self):
        segment, rest = split_leading_sentence("Hola Walter, todo bien por acá. Y vos")
        self.assertEqual(segment, "Hola Walter, todo bien por acá.")
        self.assertEqual(rest, "Y vos")

    def test_streams_a_paragraph_into_ordered_sentences(self):
        text = "Hola Walter, todo bien. Ya configuré la voz nueva. Probala cuando quieras."
        self.assertEqual(
            drain(text),
            [
                "Hola Walter, todo bien.",
                "Ya configuré la voz nueva.",
                "Probala cuando quieras.",
            ],
        )

    def test_reassembles_to_the_original_text(self):
        text = "Primera oración larga acá. ¿Segunda? Tercera y última, con coma."
        self.assertEqual("".join(drain(text)).replace(" ", ""), text.replace(" ", ""))

    def test_handles_question_and_exclamation_marks(self):
        segment, _ = split_leading_sentence("¿Querés que lo haga ahora mismo? Sí")
        self.assertTrue(segment.endswith("?"))

    def test_keeps_closing_quotes_with_their_sentence(self):
        segment, _ = split_leading_sentence('Me dijo "esto es lo que hay". Después')
        self.assertTrue(segment.endswith('".'))

    def test_falls_back_to_a_soft_break_when_a_clause_runs_long(self):
        text = "x" * 300 + ", sigue después"
        segment, rest = split_leading_sentence(text + " " * 40)
        self.assertTrue(segment.endswith(","))
        self.assertIn("sigue", rest)

    def test_never_splits_below_the_minimum_segment_size(self):
        for segment in drain("Sí. No. Tal vez. Puede ser. Claro que sí, obvio."):
            self.assertGreaterEqual(len(segment), 3)


class AudioQueueTests(unittest.TestCase):
    def test_plays_segments_in_arrival_order(self):
        from unittest import mock
        import cli.commands.agent as agent

        played = []
        queue = agent.AudioQueue()
        with mock.patch.object(
            agent, "_play_audio", side_effect=lambda url, on_process=None: played.append(url)
        ):
            for url in ("a", "b", "c"):
                queue.add(url)
            queue.wait()
        self.assertEqual(played, ["a", "b", "c"])

    def test_a_failing_segment_does_not_stop_the_rest(self):
        from unittest import mock
        import cli.commands.agent as agent

        played = []

        def player(url, on_process=None):
            if url == "b":
                raise OSError("player missing")
            played.append(url)

        queue = agent.AudioQueue()
        with mock.patch.object(agent, "_play_audio", side_effect=player):
            for url in ("a", "b", "c"):
                queue.add(url)
            queue.wait()
        self.assertEqual(played, ["a", "c"])

    def test_waiting_on_an_unused_queue_is_a_no_op(self):
        import cli.commands.agent as agent

        agent.AudioQueue().wait()



class AudioQueueStopTests(unittest.TestCase):
    def _queue_with_player(self, played, players):
        from unittest import mock
        import cli.commands.agent as agent

        def fake_play(url, on_process=None):
            process = mock.Mock()
            process.wait.side_effect = lambda timeout=None: None
            players.append(process)
            if on_process:
                on_process(process)
            played.append(url)
            if on_process:
                on_process(None)

        return agent.AudioQueue(), mock.patch.object(agent, "_play_audio", side_effect=fake_play)

    def test_stop_terminates_the_running_player(self):
        played, players = [], []
        queue, patcher = self._queue_with_player(played, players)
        with patcher:
            queue.add("a")
            queue.wait()
            queue._player = players[0]
            queue.stop()
        players[0].terminate.assert_called_once()

    def test_stop_discards_everything_still_queued(self):
        import threading
        from unittest import mock
        import cli.commands.agent as agent

        gate = threading.Event()
        played = []

        def blocking_play(url, on_process=None):
            played.append(url)
            gate.wait(timeout=2)

        queue = agent.AudioQueue()
        with mock.patch.object(agent, "_play_audio", side_effect=blocking_play):
            for url in ("a", "b", "c"):
                queue.add(url)
            queue.stop()
            gate.set()
            queue.wait()
        self.assertNotIn("c", played)

    def test_add_after_stop_is_ignored(self):
        from unittest import mock
        import cli.commands.agent as agent

        played = []
        queue = agent.AudioQueue()
        with mock.patch.object(agent, "_play_audio", side_effect=lambda u, on_process=None: played.append(u)):
            queue.stop()
            queue.add("a")
            queue.wait()
        self.assertEqual(played, [])

    def test_playing_stays_unset_until_a_player_actually_starts(self):
        import cli.commands.agent as agent

        queue = agent.AudioQueue()
        self.assertFalse(queue.playing.is_set())


class SleepToggleTests(unittest.TestCase):
    def _drive(self, keystrokes, samples=30, sample_delay=0.1):
        import os
        import pty
        import sys
        import time

        master, slave = pty.openpty()
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            os.close(read_fd)
            os.dup2(slave, 0)
            os.dup2(slave, 1)
            os.close(slave)
            sys.stdin = open(0, closefd=False)
            import cli.commands.agent as agent

            toggle = agent.SleepToggle().start()
            states = []
            for _ in range(samples):
                states.append(toggle.resting)
                time.sleep(sample_delay)
            toggle.close()
            os.write(write_fd, "".join("1" if s else "0" for s in states).encode())
            os.close(write_fd)
            os._exit(0)

        os.close(slave)
        os.close(write_fd)
        for delay, key in keystrokes:
            time.sleep(delay)
            os.write(master, key)
        os.waitpid(pid, 0)
        result = os.read(read_fd, 4096).decode()
        os.close(read_fd)
        os.close(master)
        return result

    def test_ctrl_p_toggles_rest_on_and_off(self):
        states = self._drive([(0.6, b"\x10"), (0.9, b"\x10")])
        self.assertTrue(states.startswith("0"))
        self.assertIn("1", states)
        self.assertTrue(states.endswith("0"))

    def test_other_keys_do_not_toggle_rest(self):
        states = self._drive([(0.6, b"x"), (0.4, b"\x03")], samples=15)
        self.assertNotIn("1", states)

    def test_restores_the_terminal_it_took_over(self):
        import os
        import pty
        import sys
        import termios
        import time

        master, slave = pty.openpty()
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(master)
            os.close(read_fd)
            os.dup2(slave, 0)
            os.dup2(slave, 1)
            os.close(slave)
            sys.stdin = open(0, closefd=False)
            import cli.commands.agent as agent

            before = termios.tcgetattr(sys.stdin)
            toggle = agent.SleepToggle().start()
            during = termios.tcgetattr(sys.stdin)
            toggle.close()
            after = termios.tcgetattr(sys.stdin)
            os.write(write_fd, f"{before != during},{before == after}".encode())
            os.close(write_fd)
            os._exit(0)

        os.close(slave)
        os.close(write_fd)
        time.sleep(1.0)
        os.waitpid(pid, 0)
        raw_applied, restored = os.read(read_fd, 64).decode().split(",")
        os.close(read_fd)
        os.close(master)
        self.assertEqual(raw_applied, "True")
        self.assertEqual(restored, "True")

    def test_is_inert_without_a_terminal(self):
        import cli.commands.agent as agent

        toggle = agent.SleepToggle().start()
        self.assertFalse(toggle.resting)
        toggle.close()


if __name__ == "__main__":
    unittest.main()
