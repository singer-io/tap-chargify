import unittest
from unittest.mock import MagicMock

from tap_chargify.context import Context
from tap_chargify.streams import Transactions


class TestIncrementalSyncHelpers(unittest.TestCase):
    def setUp(self):
        self.original_context = dict(Context.config)
        Context.config = {"start_date": "2025-01-01T00:00:00Z"}

    def tearDown(self):
        Context.config = self.original_context

    def test_is_bookmark_old(self):
        stream = Transactions(MagicMock())
        state = {"bookmarks": {"transactions": {"created_at": "2025-01-01T00:00:00Z"}}}

        self.assertTrue(stream.is_bookmark_old(state, "2025-01-02T00:00:00Z"))
        self.assertFalse(stream.is_bookmark_old(state, "2024-12-30T00:00:00Z"))

    def test_update_bookmark(self):
        stream = Transactions(MagicMock())
        state = {"bookmarks": {"transactions": {"created_at": "2025-01-01T00:00:00Z"}}}

        stream.update_bookmark(state, "2025-03-01T00:00:00Z")
        self.assertEqual(stream.get_bookmark(state), "2025-03-01T00:00:00Z")
