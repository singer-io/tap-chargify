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
        # Must be before earliest transaction (2026-01-01) to ensure sync 1 gets all data
        return "2025-06-01T00:00:00Z"

    @property
    def start_date_2(self):
        # Use microsecond format (.000000Z) so that parse_date in the framework uses the
        # same code path (%Y-%m-%dT%H:%M:%S.%fZ, naive datetime) as record timestamps,
        # avoiding an IST → UTC conversion mismatch on this WSL environment (IST = UTC+5:30).
        #
        # "2026-02-01T10:30:00.000000Z" → naive IST → UTC = 2026-02-01T05:00:00Z.
        # The Chargify API uses since_date (date-only), which interprets "2026-02-01"
        # as midnight EST (UTC-5) = 2026-02-01T05:00:00Z.  This ensures that the
        # framework's IST-adjusted filter threshold exactly matches the API's cutoff,
        # so no transactions fall through the gap between the two date interpretations.
        #
        # singer.utils.strptime_with_tz("2026-02-01T10:30:00.000000Z") returns
        # 2026-02-01T10:30:00+00:00, and .strftime("%Y-%m-%d") = "2026-02-01", so
        # the tap correctly queries since_date=2026-02-01 for the second sync.
        return "2026-02-01T10:30:00.000000Z"


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
