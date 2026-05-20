import unittest

from src.core.use_cases.conversation.add_message_use_case import AddMessageUseCase


class AddMessageUseCaseLanguageTests(unittest.TestCase):
    def test_tts_prefers_inferred_spanish_over_default_english_profile(self):
        language = AddMessageUseCase._resolve_tts_language(
            "¡Hola Walter! ¿En qué puedo ayudarte hoy?",
            "en",
        )

        self.assertEqual(language, "es")

    def test_tts_keeps_supported_profile_language_when_it_matches(self):
        language = AddMessageUseCase._resolve_tts_language(
            "Hello Walter, what do you need today?",
            "en",
        )

        self.assertEqual(language, "en")

    def test_tts_falls_back_to_inferred_language_when_profile_missing(self):
        language = AddMessageUseCase._resolve_tts_language(
            "Gracias por escribir. Estoy acá para ayudarte.",
            None,
        )

        self.assertEqual(language, "es")
