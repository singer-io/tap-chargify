import unittest
from unittest.mock import MagicMock, patch

import requests

from tap_chargify.chargify import Chargify
from tap_chargify.discover import discover_streams, get_schema_datatype, merge, translate_to_schema
from tap_chargify.streams import STREAMS, ProductFamilyNestedStream, Products, PricePoints, Coupons, Components


class TestDiscoveryHelpers(unittest.TestCase):
    def test_translate_to_schema_maps_primitive_types(self):
        fields = {
            "name": "string",
            "active": "boolean",
            "created": "date",
            "metrics.score": "double",
        }
        schema = translate_to_schema(fields)

        self.assertIn("name", schema["properties"])
        self.assertIn("active", schema["properties"])
        self.assertEqual(schema["properties"]["created"]["format"], "date-time")
        self.assertIn("metrics", schema["properties"])

    def test_get_schema_datatype(self):
        self.assertEqual(get_schema_datatype("long")["type"], ["null", "integer"])
        self.assertEqual(get_schema_datatype("double")["type"], ["null", "number"])
        self.assertEqual(get_schema_datatype("date")["format"], "date-time")

    def test_merge_adds_missing_top_level_keys(self):
        left = {"properties": {"a": {"type": ["null", "string"]}}}
        right = {"metadata": {"b": {"type": ["null", "integer"]}}}
        merged = merge(left, right)
        self.assertIn("a", merged["properties"])
        self.assertIn("metadata", merged)

    def test_discover_streams_returns_all_streams(self):
        mock_client = MagicMock()
        mock_client.get_user_fields.return_value = {"fields": {}}
        streams = discover_streams(mock_client)

        self.assertEqual(set(stream["tap_stream_id"] for stream in streams), set(STREAMS.keys()))


class TestCheckAccessUrl(unittest.TestCase):
    """check_access_url derivation for streams."""

    def test_default_property_derives_from_stream_name(self):
        # spot-check: standard streams use "{name}.json"
        from tap_chargify.streams import Customers, Invoices
        self.assertEqual(Customers(client=None).check_access_url, "customers.json")
        self.assertEqual(Invoices(client=None).check_access_url, "invoices.json")

    def test_nested_streams_probe_product_families(self):
        for cls in (Products, PricePoints, Coupons, Components):
            with self.subTest(stream=cls.name):
                self.assertEqual(cls(client=None).check_access_url, "product_families.json")

    def test_all_streams_have_non_none_url(self):
        for name, cls in STREAMS.items():
            with self.subTest(stream=name):
                self.assertIsNotNone(cls(client=None).check_access_url)


class TestCheckAccess(unittest.TestCase):
    """Chargify.check_access() behaviour."""

    def _error_response(self, status_code):
        resp = MagicMock()
        resp.status_code = status_code
        err = requests.exceptions.HTTPError(response=resp)
        err.response = resp
        resp.raise_for_status.side_effect = err
        return resp

    @patch("tap_chargify.chargify.requests.get")
    def test_returns_true_on_200(self, mock_get):
        mock_get.return_value = MagicMock(raise_for_status=MagicMock(return_value=None))
        self.assertTrue(Chargify(api_key="k", subdomain="t").check_access("customers.json"))

    @patch("tap_chargify.chargify.requests.get")
    def test_returns_false_on_401_and_403(self, mock_get):
        client = Chargify(api_key="k", subdomain="t")
        for code in (401, 403):
            with self.subTest(status=code):
                mock_get.return_value = self._error_response(code)
                self.assertFalse(client.check_access("customers.json"))

    @patch("tap_chargify.chargify.requests.get")
    def test_reraises_non_auth_http_errors(self, mock_get):
        mock_get.return_value = self._error_response(500)
        with self.assertRaises(requests.exceptions.HTTPError):
            Chargify(api_key="k", subdomain="t").check_access("customers.json")

    @patch("tap_chargify.chargify.requests.get")
    def test_no_retry_on_auth_failure(self, mock_get):
        mock_get.return_value = self._error_response(401)
        Chargify(api_key="k", subdomain="t").check_access("customers.json")
        self.assertEqual(mock_get.call_count, 1)


class TestDiscoverStreamsAccessFilter(unittest.TestCase):
    """discover_streams filters out unauthorized streams."""

    def _client(self, unauthorized_urls=()):
        client = MagicMock()
        client.check_access.side_effect = lambda path: path not in unauthorized_urls
        return client

    def test_all_included_when_all_authorized(self):
        streams = discover_streams(self._client())
        self.assertEqual({s["tap_stream_id"] for s in streams}, set(STREAMS.keys()))

    def test_unauthorized_stream_excluded(self):
        streams = discover_streams(self._client(unauthorized_urls={"invoices.json"}))
        self.assertNotIn("invoices", {s["tap_stream_id"] for s in streams})

    def test_nested_streams_excluded_when_product_families_unauthorized(self):
        streams = discover_streams(self._client(unauthorized_urls={"product_families.json"}))
        names = {s["tap_stream_id"] for s in streams}
        for stream in ("products", "price_points", "coupons", "components", "product_families"):
            with self.subTest(stream=stream):
                self.assertNotIn(stream, names)
