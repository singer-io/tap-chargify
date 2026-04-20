import unittest
from unittest.mock import MagicMock, patch

from tap_chargify.chargify import Chargify


class TestClient(unittest.TestCase):
    @patch("tap_chargify.chargify.requests.get")
    def test_get_includes_pagination_and_extra_params(self, mock_get):
        response = MagicMock()
        response.json.return_value = [{"id": 1}]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("transactions.json", since_date="2025-01-01"))

        self.assertEqual(len(pages), 1)
        called_url = mock_get.call_args.args[0]
        self.assertIn("page=1", called_url)
        self.assertIn("per_page=100", called_url)
        self.assertIn("since_date=2025-01-01", called_url)
