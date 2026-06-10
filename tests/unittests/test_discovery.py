import unittest
from unittest.mock import MagicMock

from tap_chargify.discover import discover_streams, get_schema_datatype, merge, translate_to_schema
from tap_chargify.streams import STREAMS


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
        mock_client.check_access.return_value = True
        streams = discover_streams(mock_client)

        self.assertEqual(set(stream["tap_stream_id"] for stream in streams), set(STREAMS.keys()))


class TestDiscoverStreamsAccessCheck(unittest.TestCase):
    def _make_client(self, forbidden_paths=()):
        """Return a mock client where check_access returns False for forbidden_paths."""
        mock_client = MagicMock()
        mock_client.check_access.side_effect = lambda path: path not in forbidden_paths
        return mock_client

    def test_all_accessible_returns_all_streams(self):
        client = self._make_client()
        streams = discover_streams(client)
        self.assertEqual(
            {s["tap_stream_id"] for s in streams},
            set(STREAMS.keys()),
        )

    def test_forbidden_stream_is_excluded(self):
        client = self._make_client(forbidden_paths={"customers.json"})
        streams = discover_streams(client)
        names = {s["tap_stream_id"] for s in streams}
        self.assertNotIn("customers", names)
        # All other streams that don't use customers.json should still be present
        self.assertIn("subscriptions", names)

    def test_product_families_forbidden_excludes_dependent_streams(self):
        """products, price_points, coupons, components all share product_families.json as access_path."""
        client = self._make_client(forbidden_paths={"product_families.json"})
        streams = discover_streams(client)
        names = {s["tap_stream_id"] for s in streams}
        for dependent in ("product_families", "products", "price_points", "coupons", "components"):
            self.assertNotIn(dependent, names)
        # Independent streams must still be present
        self.assertIn("customers", names)
        self.assertIn("subscriptions", names)

    def test_all_forbidden_raises_exception(self):
        # Compute every effective path the same way check_access() does
        all_paths = {
            cls.access_path if cls.access_path is not None else "{}.json".format(cls.name)
            for cls in STREAMS.values()
        }
        client = self._make_client(forbidden_paths=all_paths)
        with self.assertRaises(Exception) as ctx:
            discover_streams(client)
        self.assertIn("403", str(ctx.exception))
