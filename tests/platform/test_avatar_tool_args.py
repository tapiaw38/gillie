import unittest
from pathlib import Path

from pydantic import ValidationError

from src.core.platform.ai.tools.models import (
    AVATAR_ANIMATIONS,
    AvatarControlWindowArgs,
    AvatarPlayAnimationArgs,
    normalize_avatar_animation,
    installed_avatar_animations,
)


_NEEDS_ASSETS = unittest.skipUnless(
    AVATAR_ANIMATIONS,
    "needs the avatar asset manifest, which is gitignored and absent in a "
    "fresh clone; without it no animation is installed and there is nothing "
    "for the schema to advertise",
)


class AvatarAnimationArgsTests(unittest.TestCase):
    def test_missing_manifest_does_not_invent_animation_names(self):
        self.assertEqual(
            installed_avatar_animations(Path("/tmp/does-not-exist/avatar-manifest.json")),
            (),
        )

    @_NEEDS_ASSETS
    def test_the_schema_advertises_the_installed_animations(self):
        schema = AvatarPlayAnimationArgs.model_json_schema()
        self.assertEqual(
            schema["properties"]["animation"]["enum"], list(AVATAR_ANIMATIONS)
        )

    @_NEEDS_ASSETS
    def test_accepts_the_casing_and_spacing_a_model_actually_writes(self):
        for written in ("Dance", " DANCE ", "finger_gun", "fingergun"):
            with self.subTest(written=written):
                self.assertIn(
                    AvatarPlayAnimationArgs(animation=written).animation,
                    AVATAR_ANIMATIONS,
                )

    def test_maps_common_english_synonyms_onto_installed_animations(self):
        self.assertEqual(normalize_avatar_animation("wave"), "greeting")
        self.assertEqual(normalize_avatar_animation("hello"), "greeting")
        self.assertEqual(normalize_avatar_animation("smile"), "happy")
        self.assertEqual(normalize_avatar_animation("dancing"), "dance")
        self.assertEqual(normalize_avatar_animation("gun"), "finger-gun")

    def test_rejects_animations_that_are_not_installed(self):
        for written in ("idle", "talk", "volar"):
            with self.subTest(written=written):
                with self.assertRaises(ValidationError):
                    AvatarPlayAnimationArgs(animation=written)


class AvatarWindowArgsTests(unittest.TestCase):
    def test_normalizes_window_actions(self):
        self.assertEqual(AvatarControlWindowArgs(action="Hide").action, "hide")
        self.assertEqual(AvatarControlWindowArgs(action=" TOGGLE ").action, "toggle")

    def test_rejects_unknown_window_actions(self):
        with self.assertRaises(ValidationError):
            AvatarControlWindowArgs(action="minimize")


if __name__ == "__main__":
    unittest.main()
