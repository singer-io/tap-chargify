import unittest

from base import ChargifyBaseTest, ChargifyBaseMockTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest
from tap_chargify.streams import STREAMS

KNOWN_MISSING_FIELDS = {
    # invoices: these fields are not always returned by the API
    "invoices": {
        "payments_and_credits",
        "statement_id",
        "paid_at",
        "total_amount_in_cents",
        "amount_due_in_cents",
        "state",
        "charges",
        "id",
    },
    # price_points: component-specific fields absent on product price points
    "price_points": {
        "pricing_scheme",
        "default",
        "component_id",
        "prices",
    },
    # statements: rendered view fields not always returned
    "statements": {
        "text_view",
        "basic_html_view",
        "html_view",
    },
}


class ChargifyAllFieldsTest(AllFieldsTest, ChargifyBaseTest):
    """Ensure running the tap with all streams and fields selected results in
    the replication of all fields."""

    MISSING_FIELDS = KNOWN_MISSING_FIELDS
    # 1 record per stream is enough to verify all fields; 2 pages is a safe minimum.
    MAX_PAGES = 2

    @staticmethod
    def name():
        return "tap_tester_chargify_all_fields_test"

    def streams_to_test(self):
        streams_to_exclude = {}
        return self.expected_stream_names().difference(streams_to_exclude)


class AllFieldsIntegrationMockTest(ChargifyBaseMockTest, unittest.TestCase):
    """Mock-based: verify every stream schema generates a valid record
    that includes the replication key field."""

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
