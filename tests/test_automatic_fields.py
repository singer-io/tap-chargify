"""Test that with no fields selected for a stream automatic fields are still
replicated."""
import unittest
from unittest.mock import MagicMock

from base import ChargifyBaseTest, ChargifyBaseMockTest
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest
from tap_chargify.discover import discover_streams


class ChargifyAutomaticFieldsTest(MinimumSelectionTest, ChargifyBaseTest):
    """Test that with no fields selected for a stream automatic fields are
    still replicated."""

    @staticmethod
    def name():
        return "tap_tester_chargify_automatic_fields_test"

    def streams_to_test(self):
        # Exclude streams whose tap-side implementation produces duplicate records
        # (coupons/components/price_points iterate per product family and can duplicate)
        # or where the 'id' field is not present in all records (invoices).
        streams_to_exclude = {"coupons", "components", "price_points", "invoices"}
        return self.expected_stream_names().difference(streams_to_exclude)


class AutomaticFieldsIntegrationMockTest(ChargifyBaseMockTest, unittest.TestCase):
    """Mock-based: verify primary keys and replication keys have
    inclusion=automatic in the discovered catalog."""

    def test_primary_and_replication_keys_are_automatic(self):
        mock_client = MagicMock()
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
