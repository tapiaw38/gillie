import unittest

from src.adapters.web.integrations.neonize.neonize_integration import (
    _prefer_contact_jid,
    _select_reply_jid,
)


class WhatsAppSenderResolutionTests(unittest.TestCase):
    def test_prefers_non_lid_sender_when_available(self):
        selected = _prefer_contact_jid([
            "5491112345678@s.whatsapp.net",
            "186362959515799@lid",
            "",
        ])
        self.assertEqual(selected, "5491112345678@s.whatsapp.net")

    def test_falls_back_to_lid_when_no_phone_like_jid_exists(self):
        selected = _prefer_contact_jid([
            "",
            "186362959515799@lid",
        ])
        self.assertEqual(selected, "186362959515799@lid")

    def test_reply_target_prefers_original_sender_when_present(self):
        self.assertEqual(
            _select_reply_jid("186362959515799@lid", "5493837430889@s.whatsapp.net"),
            "186362959515799@lid",
        )

    def test_reply_target_falls_back_to_resolved_when_sender_missing(self):
        self.assertEqual(
            _select_reply_jid("", "5493837430889@s.whatsapp.net"),
            "5493837430889@s.whatsapp.net",
        )
