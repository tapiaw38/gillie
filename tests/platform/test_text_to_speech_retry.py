import asyncio
import unittest
from unittest import mock

from src.core.platform.managers.text_to_speech_manager import TextToSpeechService


class FakeTTS:
    """TTS integration whose calls can be scripted to fail."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def text_to_speech_stream(self, text, settings):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeStore:
    def put_object(self, **kwargs):
        return "s3/key.mp3"

    def generate_url(self, key):
        return f"https://cdn.test/{key}"


def run(coro):
    return asyncio.run(coro)


class GenerateAndStoreAudioTests(unittest.TestCase):
    def _service(self, results):
        tts = FakeTTS(results)
        service = TextToSpeechService(tts, FakeStore())
        return service, tts

    def _generate(self, service):
        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()):
            return run(
                service.generate_and_store_audio(
                    text="Una frase.", user_id="u1", conversation_id="c1"
                )
            )

    def test_a_transient_failure_does_not_lose_the_sentence(self):
        service, tts = self._service([RuntimeError("502 from provider"), b"ID3audio"])
        self.assertEqual(self._generate(service), "https://cdn.test/s3/key.mp3")
        self.assertEqual(tts.calls, 2)

    def test_empty_audio_counts_as_a_failure_worth_retrying(self):
        service, tts = self._service([b"", b"ID3audio"])
        self.assertEqual(self._generate(service), "https://cdn.test/s3/key.mp3")
        self.assertEqual(tts.calls, 2)

    def test_it_gives_up_after_two_attempts(self):
        service, tts = self._service([RuntimeError("down"), RuntimeError("still down")])
        self.assertIsNone(self._generate(service))
        self.assertEqual(tts.calls, 2)

    def test_a_segment_with_nothing_speakable_is_not_retried(self):
        service, tts = self._service([ValueError("no speakable text")])
        self.assertIsNone(self._generate(service))
        self.assertEqual(tts.calls, 1)

    def test_a_first_try_success_stays_a_single_call(self):
        service, tts = self._service([b"ID3audio"])
        self.assertEqual(self._generate(service), "https://cdn.test/s3/key.mp3")
        self.assertEqual(tts.calls, 1)


if __name__ == "__main__":
    unittest.main()
