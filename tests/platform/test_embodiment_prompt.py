import unittest

from src.adapters.web.integrations.openapi.context import EMBODIMENT_INSTRUCTION


class EmbodimentInstructionTests(unittest.TestCase):
    def setUp(self):
        self.text = EMBODIMENT_INSTRUCTION.format(assistant_name="Ana")

    def test_addresses_the_assistant_by_name(self):
        self.assertIn("Ana", self.text)

    def test_states_the_character_is_the_assistant(self):
        lowered = self.text.lower()
        self.assertIn("not an avatar you operate", lowered)
        self.assertIn("first person", lowered)

    def test_forbids_denying_the_body(self):
        self.assertIn("Never say you have no body", self.text)

    def test_separates_automatic_speech_motion_from_deliberate_gestures(self):
        lowered = self.text.lower()
        self.assertIn("move on their own while you speak", lowered)
        self.assertIn("avatar_play_animation", lowered)


if __name__ == "__main__":
    unittest.main()
