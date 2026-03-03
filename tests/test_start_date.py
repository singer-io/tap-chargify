import unittest
from unittest.mock import MagicMock

from tap_chargify.context import Context
from tap_chargify.streams import Invoices

try:
    from .base import ChargifyBaseTest
except ImportError:
    from base import ChargifyBaseTest


class StartDateIntegrationTest(ChargifyBaseTest, unittest.TestCase):
    def test_get_bookmark_uses_start_date_when_state_missing(self):
        stream = Invoices(MagicMock())
        state = {}

        bookmark = stream.get_bookmark(state)
        self.assertEqual(bookmark, "2025-01-01T00:00:00Z")

    def test_sync_calls_client_with_start_date_when_no_bookmark(self):
        mock_client = MagicMock()
        stream = Invoices(mock_client)
        state = {}

        record = {"id": 100, "due_date": "2025-04-20T10:30:00Z"}
        mock_client.invoices.return_value = iter([record])

        results = list(stream.sync(state))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1]["due_date"], "2025-04-20T10:30:00Z")
        mock_client.invoices.assert_called_once_with(Context.config["start_date"])
