import unittest

from src.core.domain.whatsapp.whatsapp_device import WhatsAppDevicePolicies


class WhatsAppDevicePoliciesTests(unittest.TestCase):
    def test_normalize_contact_strips_jid_and_symbols(self):
        self.assertEqual(
            WhatsAppDevicePolicies.normalize_contact("+54 9 11 1234-5678@s.whatsapp.net"),
            "5491112345678",
        )

    def test_blacklist_has_priority(self):
        policies = WhatsAppDevicePolicies(
            allowed_numbers=["5491112345678"],
            blocked_numbers=["5491112345678"],
            incoming_filter_mode="both",
        )
        self.assertFalse(policies.contact_allowed("5491112345678@s.whatsapp.net", "incoming"))

    def test_whitelist_blocks_unknown_incoming_contacts(self):
        policies = WhatsAppDevicePolicies(
            allowed_numbers=["5491112345678"],
            incoming_filter_mode="whitelist",
        )
        self.assertTrue(policies.contact_allowed("5491112345678@s.whatsapp.net", "incoming"))
        self.assertFalse(policies.contact_allowed("5491199999999@s.whatsapp.net", "incoming"))

    def test_blacklist_mode_allows_non_blocked_outgoing_contacts(self):
        policies = WhatsAppDevicePolicies(
            blocked_numbers=["5491112345678"],
            outgoing_filter_mode="blacklist",
        )
        self.assertFalse(policies.contact_allowed("5491112345678@s.whatsapp.net", "outgoing"))
        self.assertTrue(policies.contact_allowed("5491199999999@s.whatsapp.net", "outgoing"))

    def test_whitelist_accepts_any_matching_candidate_contact(self):
        policies = WhatsAppDevicePolicies(
            allowed_numbers=["5491112345678"],
            incoming_filter_mode="whitelist",
        )
        self.assertTrue(
            policies.contact_allowed_any(
                ["186362959515799@lid", "5491112345678@s.whatsapp.net"],
                "incoming",
            )
        )


if __name__ == "__main__":
    unittest.main()
