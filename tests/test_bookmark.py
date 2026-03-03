import unittest
from unittest.mock import MagicMock

from tap_chargify.streams import Transactions

try:
    from .base import ChargifyBaseTest
except ImportError:
    from base import ChargifyBaseTest


class BookmarkIntegrationTest(ChargifyBaseTest, unittest.TestCase):
    def test_get_bookmark_uses_existing_state(self):
        stream = Transactions(MagicMock())
        state = {"bookmarks": {"transactions": {"created_at": "2025-06-01T00:00:00Z"}}}

        bookmark = stream.get_bookmark(state)
        self.assertEqual(bookmark, "2025-06-01T00:00:00Z")

    def test_incremental_stream_updates_bookmark_with_newest_record(self):
        mock_client = MagicMock()
        stream = Transactions(mock_client)

        mock_client.transactions.return_value = iter(
            [
                {"id": 1, "created_at": "2024-12-31T00:00:00Z"},
                {"id": 2, "created_at": "2025-01-10T00:00:00Z"},
                {"id": 3, "created_at": "2025-02-15T00:00:00Z"},
                {"id": 4, "created_at": "2025-03-01T00:00:00Z"},
            ]
        )

        state = {"bookmarks": {"transactions": {"created_at": "2025-01-01T00:00:00Z"}}}
        results = list(stream.sync(state))

        self.assertEqual(len(results), 3)
        self.assertEqual(stream.get_bookmark(state), "2025-03-01T00:00:00Z")
