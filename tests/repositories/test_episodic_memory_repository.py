import unittest

from bson import ObjectId

from src.adapters.datasources.repositories.episodic_memory.repository import (
    _build_id_candidates,
    _normalize_document_id,
)


class EpisodicMemoryRepositoryTests(unittest.TestCase):
    def test_normalize_document_id_converts_objectid_to_string(self):
        object_id = ObjectId()
        normalized = _normalize_document_id({"_id": object_id, "content": "hello"})
        self.assertEqual(normalized["_id"], str(object_id))
        self.assertEqual(normalized["content"], "hello")

    def test_build_id_candidates_keeps_string_and_objectid_for_legacy_ids(self):
        object_id = ObjectId()
        candidates = _build_id_candidates(str(object_id))
        self.assertEqual(candidates[0], str(object_id))
        self.assertIn(object_id, candidates)

    def test_build_id_candidates_keeps_uuid_only_as_string(self):
        candidates = _build_id_candidates("6d0f1ed2-b0b8-4d2e-b8f1-f51939b7f1d4")
        self.assertEqual(candidates, ["6d0f1ed2-b0b8-4d2e-b8f1-f51939b7f1d4"])

