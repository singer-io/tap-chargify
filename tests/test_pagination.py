from tap_tester.base_suite_tests.pagination_test import PaginationTest
from base import ChargifyBaseTest


class ChargifyPaginationTest(PaginationTest, ChargifyBaseTest):
    """Ensure tap can replicate multiple pages of data for streams that use
    pagination."""

    @staticmethod
    def name():
        return "tap_tester_chargify_pagination_test"

    def streams_to_test(self):
        # Only include streams with API_LIMIT=100 that have enough data to exceed one page.
        # Streams verified to have >100 records in the test account:
        #   customers (131), subscriptions (117), transactions (442+),
        #   statements (200+), events (3000+)
        return {"customers", "subscriptions", "transactions", "statements", "events"}
