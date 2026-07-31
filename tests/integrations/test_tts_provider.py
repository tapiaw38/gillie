import unittest
from unittest import mock

from src.core.platform.config.service import TTSConfig
from src.adapters.web.integrations.tts.tts import TTSIntegration


def _integration(tts_config):
    config_service = mock.Mock()
    config_service.tts_config = tts_config
    return TTSIntegration(config_service)


class ProviderSelectionTests(unittest.TestCase):
    def test_uses_openai_when_a_key_is_configured(self):
        tts = _integration(TTSConfig(api_key="sk-test"))
        with mock.patch.object(tts, "_generate_openai_speech_file") as openai, \
             mock.patch.object(tts, "_generate_gtts_speech_file") as gtts:
            tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        openai.assert_called_once()
        gtts.assert_not_called()

    def test_falls_back_to_gtts_without_a_key(self):
        tts = _integration(TTSConfig(api_key=""))
        with mock.patch.object(tts, "_generate_openai_speech_file") as openai, \
             mock.patch.object(tts, "_generate_gtts_speech_file") as gtts:
            tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        openai.assert_not_called()
        gtts.assert_called_once()

    def test_falls_back_to_gtts_when_openai_fails(self):
        tts = _integration(TTSConfig(api_key="sk-test"))
        with mock.patch.object(tts, "_generate_openai_speech_file", side_effect=RuntimeError("429")), \
             mock.patch.object(tts, "_generate_gtts_speech_file") as gtts:
            tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        gtts.assert_called_once()

    def test_falls_back_to_gtts_without_tts_config(self):
        config_service = mock.Mock(spec=[])
        tts = TTSIntegration(config_service)
        with mock.patch.object(tts, "_generate_gtts_speech_file") as gtts:
            tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        gtts.assert_called_once()


class VoiceResolutionTests(unittest.TestCase):
    def _post_payload(self, config, settings):
        tts = _integration(config)
        response = mock.Mock(content=b"RIFF")
        with mock.patch("requests.post", return_value=response) as post, \
             mock.patch.object(tts, "_transcode_to_pcm"), \
             mock.patch("os.path.exists", return_value=True), \
             mock.patch("os.path.getsize", return_value=50_000), \
             mock.patch("os.unlink"), \
             mock.patch("builtins.open", mock.mock_open()):
            tts._generate_openai_speech_file("hola", "/tmp/out.wav", settings, config)
        return post.call_args.kwargs["json"], post.call_args

    def test_per_profile_voice_overrides_the_configured_default(self):
        payload, _ = self._post_payload(TTSConfig(api_key="sk", voice="nova"), {"voice": "shimmer"})
        self.assertEqual(payload["voice"], "shimmer")

    def test_uses_the_configured_voice_when_the_profile_has_none(self):
        payload, _ = self._post_payload(TTSConfig(api_key="sk", voice="onyx"), {})
        self.assertEqual(payload["voice"], "onyx")

    def test_sends_the_key_as_a_bearer_token_to_the_configured_base_url(self):
        config = TTSConfig(api_key="sk-abc", base_url="https://example.test/v1")
        _, call = self._post_payload(config, {})
        self.assertEqual(call.args[0], "https://example.test/v1/audio/speech")
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer sk-abc")

    def test_requests_wav_format(self):
        payload, _ = self._post_payload(TTSConfig(api_key="sk"), {})
        self.assertEqual(payload["response_format"], "wav")



class OpenAIKeyResolutionTests(unittest.TestCase):
    def _resolve(self, api_key, current_key, provider_keys):
        import cli.commands.provider as provider
        with mock.patch.object(
            provider, "get_provider_data", return_value={"provider_keys": provider_keys}
        ), mock.patch.object(provider.typer, "prompt", return_value="sk-typed"):
            return provider._resolve_openai_key(api_key, current_key)

    def test_reuses_the_stored_openai_provider_key(self):
        self.assertEqual(self._resolve(None, "", {"openai": "sk-stored"}), ("sk-stored", "openai provider"))

    def test_the_flag_wins_over_every_stored_key(self):
        self.assertEqual(self._resolve("sk-flag", "sk-voice", {"openai": "sk-stored"})[0], "sk-flag")

    def test_an_existing_voice_key_wins_over_the_provider_key(self):
        self.assertEqual(self._resolve(None, "sk-voice", {"openai": "sk-stored"})[0], "sk-voice")

    def test_prompts_only_when_no_key_is_stored_anywhere(self):
        self.assertEqual(self._resolve(None, "", {}), ("sk-typed", "prompt"))


class ProfileVoicePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_non_default_voice_survives_the_profile_update(self):
        from src.schemas import ProfileInput
        from src.core.use_cases.profile.update_use_case import UpdateUseCase

        saved = {}

        async def update(profile_id, profile):
            saved["tts_voice"] = profile.tts_voice
            return profile_id

        context = mock.Mock()
        context.repositories.profile.find_by_user_id = mock.AsyncMock(
            return_value=mock.Mock(id="p1")
        )
        context.repositories.profile.update = update
        context.repositories.profile.find_by_id = mock.AsyncMock(
            return_value=_profile_stub(tts_voice="shimmer")
        )
        context.repositories.conversation.update_profile_by_user_id = mock.AsyncMock()

        result = await UpdateUseCase(lambda: context).execute(
            "u1", ProfileInput(tts_voice="shimmer")
        )

        self.assertEqual(saved["tts_voice"], "shimmer")
        self.assertEqual(result.data.tts_voice, "shimmer")


def _profile_stub(**overrides):
    from src.core.domain import Profile

    defaults = dict(
        id="p1", user_id="u1", assistant_name="Ana", is_active=True,
        api_keys=[], contacts=[], files=[], integrations=[],
        created_at=None, updated_at=None,
    )
    return Profile(**{**defaults, **overrides})


class EngineSelectionTests(unittest.TestCase):
    def _engine_used(self, config):
        tts = _integration(config)
        used = []
        for name in ("openai", "edge", "gtts"):
            attr = f"_generate_{name}_speech_file"
            patcher = mock.patch.object(
                tts, attr, side_effect=lambda *a, _n=name, **k: used.append(_n)
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        return used

    def test_an_explicit_edge_engine_wins_over_a_stored_api_key(self):
        config = TTSConfig(engine="edge", api_key="sk-test")
        self.assertEqual(self._engine_used(config), ["edge"])

    def test_an_explicit_gtts_engine_skips_both_network_engines(self):
        self.assertEqual(self._engine_used(TTSConfig(engine="gtts", api_key="sk")), ["gtts"])

    def test_defaults_to_openai_when_only_a_key_is_present(self):
        self.assertEqual(self._engine_used(TTSConfig(api_key="sk")), ["openai"])

    def test_defaults_to_gtts_with_neither_engine_nor_key(self):
        self.assertEqual(self._engine_used(TTSConfig()), ["gtts"])

    def test_edge_failure_falls_back_to_gtts(self):
        tts = _integration(TTSConfig(engine="edge"))
        with mock.patch.object(tts, "_generate_edge_speech_file", side_effect=OSError("offline")), \
             mock.patch.object(tts, "_generate_gtts_speech_file") as gtts:
            tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es"})
        gtts.assert_called_once()

    def test_picks_an_argentine_voice_for_spanish_when_none_is_set(self):
        self.assertEqual(TTSIntegration._default_edge_voice("es"), "es-AR-ElenaNeural")
        self.assertEqual(TTSIntegration._default_edge_voice("en"), "en-US-AvaNeural")


class ProfileEngineOverrideTests(unittest.TestCase):
    def _engine_used(self, config, requested):
        tts = _integration(config)
        used = []
        for name in ("openai", "edge", "gtts"):
            patcher = mock.patch.object(
                tts, f"_generate_{name}_speech_file",
                side_effect=lambda *a, _n=name, **k: used.append(_n),
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        tts._generate_speech_file("hola", "/tmp/out.wav", {"language": "es", "engine": requested})
        return used

    def test_the_profile_engine_overrides_the_configured_engine(self):
        config = TTSConfig(engine="edge", api_key="sk-test")
        self.assertEqual(self._engine_used(config, "openai"), ["openai"])

    def test_choosing_openai_without_a_key_degrades_to_gtts(self):
        self.assertEqual(self._engine_used(TTSConfig(engine="edge"), "openai"), ["gtts"])

    def test_an_empty_profile_engine_keeps_the_configured_engine(self):
        self.assertEqual(self._engine_used(TTSConfig(engine="edge"), None), ["edge"])


class VoiceStatusSourceTests(unittest.TestCase):
    def _status(self, config_engine, config_key, profile):
        import cli.commands.provider as provider
        from typer.testing import CliRunner

        cfg = mock.Mock()
        cfg.services.tts = mock.Mock(
            enabled=True, engine=config_engine, api_key=config_key,
            voice="", model="", base_url="",
        )
        with mock.patch("cli.config.manager.config_exists", return_value=True), \
             mock.patch("cli.config.manager.load_config", return_value=cfg), \
             mock.patch.object(provider, "get_voice_data", return_value=profile):
            return CliRunner().invoke(provider.voice_app, ["status"]).output

    def test_reports_the_profile_engine_when_it_overrides_the_cli(self):
        out = self._status("edge", "", {"tts_engine": "openai", "tts_voice": "onyx"})
        self.assertIn("openai", out)
        self.assertIn("overrides the CLI setting", out)

    def test_reports_the_cli_engine_when_the_profile_has_no_override(self):
        out = self._status("edge", "", {})
        self.assertIn("edge", out)
        self.assertIn("no profile override", out)

    def test_warns_when_openai_is_selected_without_a_key(self):
        out = self._status("edge", "", {"tts_engine": "openai"})
        self.assertIn("no API key is configured", out)


class UnspeakableTextTests(unittest.TestCase):
    def setUp(self):
        self.tts = _integration(TTSConfig())

    def clean(self, text, language="es"):
        return self.tts._strip_unspeakable(text, language)

    def test_strips_emoji_outside_the_old_hardcoded_list(self):
        for emoji in ("🕺", "🎉", "✨", "🔊", "🐙", "👋", "🥑", "🛸"):
            self.assertNotIn(emoji, self.clean(f"hola {emoji} chau"))

    def test_strips_composed_emoji_sequences(self):
        for text in ("👨‍👩‍👧‍👦", "👍🏽", "🇦🇷"):
            self.assertEqual(self.clean(f"a {text} b"), "a b")

    def test_replaces_urls_instead_of_spelling_them_out(self):
        out = self.clean("mirá https://ejemplo.com/x?a=1 ahora")
        self.assertNotIn("https", out)
        self.assertNotIn("ejemplo.com", out)
        self.assertIn("un enlace", out)

    def test_replaces_email_addresses(self):
        self.assertIn("un enlace", self.clean("escribime a walter@mail.com"))

    def test_replaces_filesystem_paths(self):
        out = self.clean("el archivo /home/tapia/main.py falla")
        self.assertNotIn("home", out)
        self.assertIn("una ruta", out)

    def test_summarizes_fenced_code_blocks(self):
        out = self.clean("corré:\n```bash\nrm -rf /tmp/x\n```\nlisto")
        self.assertNotIn("rm", out)
        self.assertIn("un bloque de código", out)

    def test_drops_inline_code_spans(self):
        self.assertNotIn("main.py", self.clean("abrí `main.py` ahora"))

    def test_keeps_markdown_link_text_but_not_the_target(self):
        out = self.clean("ver [la docs](https://x.com/a) ahora")
        self.assertIn("la docs", out)
        self.assertNotIn("x.com", out)

    def test_strips_heading_and_bullet_markers(self):
        out = self.clean("## Titulo\n- item uno\n- item dos")
        self.assertNotIn("#", out)
        self.assertNotIn("- ", out)
        self.assertIn("Titulo", out)

    def test_leaves_ordinary_prose_untouched(self):
        text = "Hola Walter, todo bien por acá."
        self.assertEqual(self.clean(text), text)

    def test_uses_english_placeholders_for_english(self):
        self.assertIn("a link", self.clean("see https://x.com now", "en"))

    def test_full_preprocessing_removes_every_emoji(self):
        message = "Hola 😊 bailando 🕺 fiesta 🎉 ✨🔊 chau 👋"
        out = self.tts._preprocess_text_for_natural_speech(message, "es")
        self.assertFalse(
            self.tts._EMOJI_AND_SYMBOLS.search(out), f"emoji survived: {out!r}"
        )


class MarkdownMarkupTests(unittest.TestCase):
    def setUp(self):
        self.tts = _integration(TTSConfig())

    def clean(self, text):
        return self.tts._preprocess_text_for_natural_speech(text, "es")

    def test_does_not_read_blockquote_markers_as_greater_than(self):
        out = self.clean("> Todo bien, todo bien, a pesar de los problemas")
        self.assertNotIn("mayor que", out)
        self.assertIn("Todo bien", out)

    def test_strips_nested_blockquote_markers(self):
        self.assertNotIn("mayor que", self.clean(">> cita anidada bastante larga acá"))

    def test_keeps_a_real_greater_than_comparison(self):
        self.assertIn("mayor que", self.clean("El precio 5 > 3 es verdadero"))

    def test_removes_emphasis_markers_but_keeps_the_words(self):
        out = self.clean("**negrita** y *cursiva* y ~~tachado~~ juntos acá")
        for word in ("negrita", "cursiva", "tachado"):
            self.assertIn(word, out)
        self.assertNotIn("*", out)
        self.assertNotIn("~", out)

    def test_drops_horizontal_rules(self):
        self.assertEqual(self.clean("---"), "")

    def test_handles_a_full_quoted_song_reply(self):
        out = self.clean(
            "🎵\n\n> *\"Todo bien, todo bien...*\n> *a pesar de los problemas...*\n\n"
            "🎶👈😎\n\nAhí va, un temita para vos."
        )
        for banned in ("mayor que", "*", "🎵", "🎶", "👈", "😎"):
            self.assertNotIn(banned, out)
        self.assertIn("Todo bien", out)
        self.assertIn("temita", out)


class StreamSentinelTests(unittest.TestCase):
    def test_the_done_sentinel_only_matches_after_json_parsing(self):
        import json

        payload = json.dumps("[DONE]")
        self.assertNotEqual(payload, "[DONE]")
        self.assertEqual(json.loads(payload), "[DONE]")


class StreamedFragmentMarkupTests(unittest.TestCase):
    """Sentence-level streaming cuts replies mid-markup, so a fragment can hold
    an opening marker whose partner lives in the next segment."""

    def setUp(self):
        self.tts = _integration(TTSConfig())

    def clean(self, text):
        return self.tts._preprocess_text_for_natural_speech(text, "es")

    def test_drops_an_unmatched_opening_asterisk(self):
        self.assertNotIn("*", self.clean('*"Todo bien, todo bien, a pesar de todo'))

    def test_drops_an_unmatched_closing_asterisk(self):
        self.assertNotIn("*", self.clean("a pesar de los problemas, todo bien...*"))

    def test_drops_a_stray_asterisk_mid_sentence(self):
        out = self.clean("texto con * suelto en el medio de la frase")
        self.assertNotIn("*", out)
        self.assertIn("suelto", out)

    def test_drops_unmatched_double_asterisks(self):
        self.assertNotIn("*", self.clean("**sin cerrar del todo esta frase"))

    def test_drops_orphan_backticks_and_pipes(self):
        for text in ("codigo `sin cerrar en el fragmento", "col a | col b | col c"):
            out = self.clean(text)
            self.assertNotIn("`", out)
            self.assertNotIn("|", out)

    def test_every_segment_of_a_split_song_is_clean(self):
        fragments = [
            '> *"Todo bien, todo bien...',
            "*a pesar de los problemas, todo bien...*",
            "*La vida sigue y vamos viendo...*",
        ]
        for fragment in fragments:
            out = self.clean(fragment)
            self.assertNotIn("*", out)
            self.assertNotIn("mayor que", out)


if __name__ == "__main__":
    unittest.main()
