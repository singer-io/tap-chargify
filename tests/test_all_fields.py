from base import ChargifyBaseTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest

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

    @staticmethod
    def name():
        return "tap_tester_chargify_all_fields_test"

    def streams_to_test(self):
        streams_to_exclude = {}
        return self.expected_stream_names().difference(streams_to_exclude)
