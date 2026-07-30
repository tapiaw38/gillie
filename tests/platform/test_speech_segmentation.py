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
        with mock.patch.object(agent, "_play_audio", side_effect=played.append):
            for url in ("a", "b", "c"):
                queue.add(url)
            queue.wait()
        self.assertEqual(played, ["a", "b", "c"])

    def test_a_failing_segment_does_not_stop_the_rest(self):
        from unittest import mock
        import cli.commands.agent as agent

        played = []

        def player(url):
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


if __name__ == "__main__":
    unittest.main()
