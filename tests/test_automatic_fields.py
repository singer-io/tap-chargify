import unittest
from unittest.mock import MagicMock

from tap_chargify.discover import discover_streams

try:
    from .base import ChargifyBaseTest
except ImportError:
    from base import ChargifyBaseTest


class AutomaticFieldsIntegrationTest(ChargifyBaseTest, unittest.TestCase):
    def test_primary_and_replication_keys_are_automatic(self):
        mock_client = MagicMock()
        mock_client.get_user_fields.return_value = {"fields": {}}

        streams = discover_streams(mock_client)
        expected = self.expected_metadata()

        for stream in streams:
            stream_name = stream["tap_stream_id"]
            actual_automatic = set()
            inclusion_by_property = {}
            for entry in stream["metadata"]:
                breadcrumb = entry.get("breadcrumb", ())
                if len(breadcrumb) == 2 and breadcrumb[0] == "properties":
                    property_name = breadcrumb[1]
                    inclusion = entry.get("metadata", {}).get("inclusion")
                    inclusion_by_property[property_name] = inclusion
                    if inclusion == "automatic":
                        actual_automatic.add(property_name)

            primary_keys = expected[stream_name][self.PRIMARY_KEYS]
            for primary_key in primary_keys:
                if primary_key in inclusion_by_property:
                    with self.subTest(stream=stream_name, primary_key=primary_key):
                        self.assertIn(primary_key, actual_automatic)
