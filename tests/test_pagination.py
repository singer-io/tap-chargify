import unittest
from unittest.mock import MagicMock, patch

from tap_tester.base_suite_tests.pagination_test import PaginationTest
from base import ChargifyBaseTest
from tap_chargify.chargify import Chargify


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


class PaginationIntegrationMockTest(unittest.TestCase):
    """Mock-based pagination tests: verify Chargify.get() reads all pages
    and stops on a short page without any network calls."""

    @patch("tap_chargify.chargify.requests.get")
    def test_get_reads_all_pages_until_short_page(self, mock_get):
        first_page = [{"id": i} for i in range(1, 101)]
        second_page = [{"id": 101}, {"id": 102}, {"id": 103}]

        first_response = MagicMock()
        first_response.json.return_value = first_page
        first_response.raise_for_status.return_value = None

        second_response = MagicMock()
        second_response.json.return_value = second_page
        second_response.raise_for_status.return_value = None

        mock_get.side_effect = [first_response, second_response]

        client = Chargify(api_key="dummy", subdomain="example")
        pages = list(client.get("customers.json"))

        self.assertEqual(len(pages), 2)
        self.assertEqual(sum(len(p) for p in pages), 103)
        self.assertEqual(mock_get.call_count, 2)

    @patch("tap_chargify.chargify.requests.get")
    def test_get_stops_on_first_short_page(self, mock_get):
        response = MagicMock()
        response.json.return_value = [{"id": 1}, {"id": 2}]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        client = Chargify(api_key="dummy", subdomain="example")
        pages = list(client.get("events.json"))

        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]), 2)
        self.assertEqual(mock_get.call_count, 1)
