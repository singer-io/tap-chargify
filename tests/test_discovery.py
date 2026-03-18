"""Test tap discovery mode and metadata."""
import unittest
from unittest.mock import MagicMock

from singer import metadata

from base import ChargifyBaseTest, ChargifyBaseMockTest
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest
from tap_chargify.discover import discover_streams


class ChargifyDiscoveryTest(DiscoveryTest, ChargifyBaseTest):
    """Test tap discovery mode and metadata conforms to standards."""

    @staticmethod
    def name():
        return "tap_tester_chargify_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()


class DiscoveryIntegrationMockTest(ChargifyBaseMockTest, unittest.TestCase):
    """Mock-based discovery tests: verify all streams and their metadata
    are correctly produced by discover_streams() without any network calls."""

    def test_discovery_expected_streams_and_metadata(self):
        mock_client = MagicMock()
        streams = discover_streams(mock_client)
        stream_map = {stream["tap_stream_id"]: stream for stream in streams}
        expected = self.expected_metadata()

        self.assertEqual(set(stream_map.keys()), set(expected.keys()))

        for stream_name, expected_stream in expected.items():
            with self.subTest(stream=stream_name):
                root_metadata = metadata.to_map(stream_map[stream_name]["metadata"])[()]
                self.assertEqual(
                    set(root_metadata.get("table-key-properties", [])),
                    expected_stream[self.PRIMARY_KEYS],
                )
                self.assertEqual(
                    root_metadata.get("forced-replication-method"),
                    expected_stream[self.REPLICATION_METHOD],
                )
                actual_replication_keys = root_metadata.get("valid-replication-keys", [])
                if isinstance(actual_replication_keys, str):
                    actual_replication_keys = {actual_replication_keys}
                else:
                    actual_replication_keys = {
                        v for v in actual_replication_keys if v is not None
                    }
                self.assertEqual(
                    actual_replication_keys,
                    expected_stream[self.REPLICATION_KEYS],
                )
