import unittest
from unittest import mock

from cli.commands import agent


class AudioQueueTests(unittest.TestCase):
    def _played(self, urls, stop_after=None):
        """Run the queue with a fake player and return what it played, in order."""
        played = []
        queue = agent.AudioQueue()

        def fake_play(url, on_process=None):
            played.append(url)
            if stop_after is not None and len(played) == stop_after:
                queue.stop()

        with mock.patch.object(agent, "_play_audio", side_effect=fake_play):
            for url in urls:
                queue.add(url)
            if stop_after is None:
                queue.wait()
            else:
                queue._thread.join(timeout=5)
        return played

    def test_every_segment_of_a_reply_is_spoken_in_order(self):
        urls = [f"http://tts/seg{i}.mp3" for i in range(5)]
        self.assertEqual(self._played(urls), urls)

    def test_stop_discards_what_is_still_queued(self):
        urls = [f"http://tts/seg{i}.mp3" for i in range(5)]
        self.assertEqual(self._played(urls, stop_after=2), urls[:2])

    def test_playing_survives_the_gap_between_segments(self):
        queue = agent.AudioQueue()
        seen = []

        def fake_play(url, on_process=None):
            if on_process:
                on_process(None)
            seen.append(queue.playing.is_set())

        with mock.patch.object(agent, "_play_audio", side_effect=fake_play):
            queue.add("http://tts/seg0.mp3")
            queue.wait()

        self.assertEqual(seen, [True])
        self.assertFalse(queue.playing.is_set())


class PlayAudioTests(unittest.TestCase):
    class FakeProc:
        def __init__(self, code):
            self._code = code
            self.killed = False

        def wait(self, timeout=None):
            return self._code

        def kill(self):
            self.killed = True

    def _run(self, codes):
        """Return the players that were actually launched for one URL."""
        launched = []
        procs = list(codes)

        def fake_popen(cmd, *a, **kw):
            launched.append(cmd[0])
            return self.FakeProc(procs.pop(0))

        with mock.patch.object(agent.subprocess, "Popen", side_effect=fake_popen):
            with mock.patch.object(agent.console, "print"):
                agent._play_audio("http://tts/seg0.mp3")
        return launched

    def test_a_player_that_cannot_play_the_url_falls_through_to_the_next(self):
        self.assertEqual(self._run([1, 0]), ["mpv", "ffplay"])

    def test_a_segment_that_played_does_not_start_a_second_player(self):
        self.assertEqual(self._run([0, 0]), ["mpv"])

    def test_a_segment_killed_by_barge_in_is_not_retried(self):
        self.assertEqual(self._run([-15, 0]), ["mpv"])


if __name__ == "__main__":
    unittest.main()
