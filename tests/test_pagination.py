import unittest
from unittest.mock import MagicMock, patch

from tap_chargify.chargify import Chargify


class PaginationIntegrationTest(unittest.TestCase):
    @patch("tap_chargify.chargify.requests.get")
    def test_get_reads_all_pages_until_short_page(self, mock_get):
        first_page = [{"id": index} for index in range(1, 101)]
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
        self.assertEqual(sum(len(page) for page in pages), 103)
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
