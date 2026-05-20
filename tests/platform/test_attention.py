import unittest
from datetime import datetime, timedelta, timezone

from src.core.platform.brain.attention import AttentionSystem


class AttentionSystemTests(unittest.TestCase):
    def test_recency_accepts_naive_datetime(self):
        created_at = (datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None)

        score = AttentionSystem._recency(created_at)

        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_recency_accepts_aware_datetime(self):
        created_at = datetime.now(timezone.utc) - timedelta(days=2)

        score = AttentionSystem._recency(created_at)

        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
