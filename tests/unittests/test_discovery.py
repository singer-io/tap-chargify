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
        streams = discover_streams(mock_client)

        self.assertEqual(set(stream["tap_stream_id"] for stream in streams), set(STREAMS.keys()))
