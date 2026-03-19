import unittest
from unittest.mock import MagicMock

from base import ChargifyBaseTest, ChargifyBaseMockTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest
from tap_chargify.streams import Invoices
from tap_chargify.context import Context


class ChargifyStartDateTest(StartDateTest, ChargifyBaseTest):
    """Instantiate start date according to the desired data set and run the
    test."""

    @staticmethod
    def name():
        return "tap_tester_chargify_start_date_test"

    def streams_to_test(self):
        # StartDateTest.test_replication_key_values asserts exactly 1 replication key.
        # Only INCREMENTAL streams have replication keys.
        # Invoices excluded: API returns due_date as plain date (YYYY-MM-DD), not datetime.
        return {"transactions"}

    @property
    def start_date_1(self):
        # Earlier than all transactions in the account so sync 1 gets the full set.
        return "2025-06-01T00:00:00Z"

    @property
    def start_date_2(self):
        # Recent enough that sync 2 returns far fewer records than sync 1.
        # Use .000000Z format so parse_date treats it as a naive datetime (same
        # code-path as record timestamps), avoiding the IST→UTC offset mismatch
        # on this WSL environment.
        # At ~5 transactions/day, 2 days back gives ~10 records vs ~122 for sync 1.
        return "2026-03-17T00:00:00.000000Z"


class StartDateIntegrationMockTest(ChargifyBaseMockTest, unittest.TestCase):
    """Mock-based start date tests: verify streams use start_date / bookmark
    as the API filter without any network calls."""

    def test_get_bookmark_uses_start_date_when_state_missing(self):
        stream = Invoices(MagicMock())
        state = {}
        bookmark = stream.get_bookmark(state)
        self.assertEqual(bookmark, self.default_start_date)

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
