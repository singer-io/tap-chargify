import unittest
from unittest.mock import MagicMock, patch

import requests

from tap_chargify.chargify import (
    Chargify,
    ChargifyForbiddenError,
    ChargifyUnauthorizedError,
    giveup,
)


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

    @patch("tap_chargify.chargify.requests.get")
    def test_price_points_results_key_drives_pagination(self, mock_get):
        """price_points pages are dicts {"price_points": [...]}.  The paginator
        must inspect the *list* length (not the dict length) to decide whether
        there are more pages.  Passing results_key='price_points' achieves this.
        """
        # First page: full 100-item list  →  has_more should stay True
        first_page = {"price_points": [{"id": i} for i in range(100)]}
        # Second page: partial list (< 100)  →  has_more should become False
        second_page = {"price_points": [{"id": i} for i in range(5)]}

        resp1, resp2 = MagicMock(), MagicMock()
        resp1.json.return_value = first_page
        resp1.raise_for_status.return_value = None
        resp2.json.return_value = second_page
        resp2.raise_for_status.return_value = None

        mock_get.side_effect = [resp1, resp2]

        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("products/1/price_points.json", results_key="price_points"))

        # Exactly two HTTP calls and two pages yielded
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]["price_points"]), 100)
        self.assertEqual(len(pages[1]["price_points"]), 5)

    @patch("tap_chargify.chargify.requests.get")
    def test_fetch_page_raises_unauthorized_and_forbidden(self, mock_get):
        client = Chargify(api_key="token", subdomain="tenant")

        unauthorized = MagicMock(status_code=401)
        forbidden = MagicMock(status_code=403, text="forbidden")

        mock_get.return_value = unauthorized
        with self.assertRaises(ChargifyUnauthorizedError):
            client._fetch_page("https://example.com", stream=False)

        mock_get.return_value = forbidden
        with self.assertRaises(ChargifyForbiddenError):
            client._fetch_page("https://example.com", stream=False)

    def test_verify_credentials_handles_forbidden(self):
        client = Chargify(api_key="token", subdomain="tenant")
        with patch.object(client, "_fetch_page", side_effect=ChargifyForbiddenError("403")) as fetch:
            client.verify_credentials()
            fetch.assert_called_once()

    def test_resource_iterators(self):
        client = Chargify(api_key="token", subdomain="tenant")

        def fake_get(path, *args, **kwargs):
            if path == "customers.json":
                return iter([[{"customer": {"id": 1}}]])
            if path == "product_families.json":
                return iter([[{"product_family": {"id": 10}}]])
            if path == "product_families/10/products.json":
                return iter([[{"product": {"id": 100}}]])
            if path == "products/100/price_points.json":
                return iter([{"price_points": [{"id": 1000}]}])
            if path == "product_families/10/coupons.json":
                return iter([[{"coupon": {"id": 200}}]])
            if path == "product_families/10/components.json":
                return iter([[{"component": {"id": 300}}]])
            if path == "subscriptions.json":
                return iter([[{"subscription": {"id": 400}}]])
            if path == "transactions.json":
                return iter([[{"transaction": {"id": 500}}]])
            if path == "statements.json":
                return iter([[{"statement": {"id": 600}}]])
            if path == "invoices.json":
                return iter([{"invoices": [{"id": 700}]}])
            if path == "events.json":
                return iter([[{"event": {"id": 800}}]])
            raise AssertionError("unexpected path: {}".format(path))

        with patch.object(client, "get", side_effect=fake_get):
            self.assertEqual(list(client.customers()), [{"id": 1}])
            self.assertEqual(list(client.product_families()), [{"id": 10}])
            self.assertEqual(list(client.products()), [{"id": 100}])
            self.assertEqual(list(client.price_points()), [{"id": 1000}])
            self.assertEqual(list(client.coupons()), [{"id": 200}])
            self.assertEqual(list(client.components()), [{"id": 300}])
            self.assertEqual(list(client.subscriptions("2025-01-01T00:00:00Z")), [{"id": 400}])
            self.assertEqual(list(client.transactions("2025-01-01T00:00:00Z")), [{"id": 500}])
            self.assertEqual(list(client.statements("2025-01-01T00:00:00Z")), [{"id": 600}])
            self.assertEqual(list(client.invoices("2025-01-01T00:00:00Z")), [{"id": 700}])
            self.assertEqual(list(client.events()), [{"id": 800}])


class TestGiveup(unittest.TestCase):
    """Tests for the giveup predicate."""

    def _http_error(self, status_code):
        """Build a requests.exceptions.HTTPError with a given status code."""
        resp = MagicMock()
        resp.status_code = status_code
        exc = requests.exceptions.HTTPError(response=resp)
        return exc

    # --- 4xx non-429 → should give up (True) ---

    def test_400_is_fatal(self):
        self.assertTrue(giveup(self._http_error(400)))

    def test_401_is_fatal(self):
        self.assertTrue(giveup(self._http_error(401)))

    def test_403_is_fatal(self):
        self.assertTrue(giveup(self._http_error(403)))

    def test_404_is_fatal(self):
        self.assertTrue(giveup(self._http_error(404)))

    def test_422_is_fatal(self):
        self.assertTrue(giveup(self._http_error(422)))

    # --- 429 → should retry (False) ---

    def test_429_is_not_fatal(self):
        self.assertFalse(giveup(self._http_error(429)))

    # --- 5xx → should retry (False) ---

    def test_500_is_not_fatal(self):
        self.assertFalse(giveup(self._http_error(500)))

    def test_502_is_not_fatal(self):
        self.assertFalse(giveup(self._http_error(502)))

    def test_503_is_not_fatal(self):
        self.assertFalse(giveup(self._http_error(503)))

    # --- HTTPError with no response object → should retry (False) ---

    def test_http_error_no_response_is_not_fatal(self):
        exc = requests.exceptions.HTTPError(response=None)
        self.assertFalse(giveup(exc))

    # --- Connection-level errors → should retry (False) ---

    def test_connection_error_is_not_fatal(self):
        self.assertFalse(giveup(requests.exceptions.ConnectionError()))

    def test_timeout_is_not_fatal(self):
        self.assertFalse(giveup(requests.exceptions.Timeout()))

    def test_chunked_encoding_error_is_not_fatal(self):
        self.assertFalse(giveup(requests.exceptions.ChunkedEncodingError()))

    def test_connection_reset_error_is_not_fatal(self):
        # ConnectionResetError is a subclass of OSError; when wrapped by
        # requests it surfaces as a ConnectionError.
        exc = requests.exceptions.ConnectionError(ConnectionResetError())
        self.assertFalse(giveup(exc))


class TestBackoffRetry(unittest.TestCase):
    """Verify that non-fatal errors trigger retries and fatal 4xx errors do not.

    ``time.sleep`` is patched to zero so backoff waits are instantaneous.
    """

    def _ok_response(self, body):
        resp = MagicMock()
        resp.json.return_value = body
        resp.raise_for_status.return_value = None
        return resp

    def _error_response(self, status_code):
        resp = MagicMock()
        resp.status_code = status_code
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=resp
        )
        return resp

    @patch("time.sleep")
    @patch("tap_chargify.chargify.requests.get")
    def test_retries_on_429(self, mock_get, _sleep):
        """A 429 response should be retried; second call succeeds."""
        mock_get.side_effect = [
            self._error_response(429),
            self._ok_response([{"id": 1}]),
        ]
        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("events.json"))
        self.assertEqual(len(pages), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("time.sleep")
    @patch("tap_chargify.chargify.requests.get")
    def test_retries_on_500(self, mock_get, _sleep):
        """A 500 response should be retried; second call succeeds."""
        mock_get.side_effect = [
            self._error_response(500),
            self._ok_response([{"id": 2}]),
        ]
        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("events.json"))
        self.assertEqual(len(pages), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("tap_chargify.chargify.requests.get")
    def test_no_retry_on_404(self, mock_get):
        """A 404 should raise immediately without retrying."""
        mock_get.return_value = self._error_response(404)
        client = Chargify(api_key="token", subdomain="tenant")
        with self.assertRaises(requests.exceptions.HTTPError):
            list(client.get("events.json"))
        # Called exactly once — no retry
        self.assertEqual(mock_get.call_count, 1)

    @patch("time.sleep")
    @patch("tap_chargify.chargify.requests.get")
    def test_retries_on_connection_error(self, mock_get, _sleep):
        """A ConnectionError should be retried; second call succeeds."""
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            self._ok_response([{"id": 3}]),
        ]
        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("events.json"))
        self.assertEqual(len(pages), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("time.sleep")
    @patch("tap_chargify.chargify.requests.get")
    def test_retries_on_timeout(self, mock_get, _sleep):
        """A Timeout should be retried; second call succeeds."""
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            self._ok_response([{"id": 4}]),
        ]
        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("events.json"))
        self.assertEqual(len(pages), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("time.sleep")
    @patch("tap_chargify.chargify.requests.get")
    def test_retries_on_chunked_encoding_error(self, mock_get, _sleep):
        """A ChunkedEncodingError should be retried; second call succeeds."""
        mock_get.side_effect = [
            requests.exceptions.ChunkedEncodingError(),
            self._ok_response([{"id": 5}]),
        ]
        client = Chargify(api_key="token", subdomain="tenant")
        pages = list(client.get("events.json"))
        self.assertEqual(len(pages), 1)
        self.assertEqual(mock_get.call_count, 2)
