"""Test that with no fields selected for a stream automatic fields are still
replicated."""
from base import ChargifyBaseTest
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest


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
