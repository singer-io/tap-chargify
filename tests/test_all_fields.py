import unittest

from tap_chargify.streams import STREAMS

try:
    from .base import ChargifyBaseTest
except ImportError:
    from base import ChargifyBaseTest


class AllFieldsIntegrationTest(ChargifyBaseTest, unittest.TestCase):
    def test_all_stream_schemas_generate_valid_records(self):
        expected = self.expected_metadata()

        for stream_name in STREAMS.keys():
            with self.subTest(stream=stream_name):
                schema = self._load_schema(stream_name)
                record = self._generate_value(schema, date_value="2025-02-01T00:00:00Z")

                self.assertIsInstance(record, dict)
                replication_keys = expected[stream_name][self.REPLICATION_KEYS]
                for replication_key in replication_keys:
                    if replication_key in schema.get("properties", {}):
                        self.assertIn(replication_key, record)
