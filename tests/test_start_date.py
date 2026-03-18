from base import ChargifyBaseTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest


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
