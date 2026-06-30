import unittest
from unittest.mock import MagicMock

from tap_chargify.chargify import ChargifyForbiddenError
from tap_chargify.discover import (
    discover_streams,
    get_schema_datatype,
    merge,
    translate_to_schema,
    _apply_access_checks,
    _prune_inaccessible_children,
)
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


class TestApplyAccessChecks(unittest.TestCase):
    """Tests for _apply_access_checks and _prune_inaccessible_children."""

    def _make_streams(self, names=None):
        """Return a minimal list of stream dicts for the given names."""
        names = names or list(STREAMS.keys())
        return [{"stream": n, "tap_stream_id": n, "schema": {}, "metadata": []} for n in names]

    def test_all_streams_accessible(self):
        """When all streams are accessible, list is unchanged."""
        mock_client = MagicMock()
        streams = self._make_streams()
        original_names = {s["tap_stream_id"] for s in streams}

        _apply_access_checks(mock_client, streams)

        self.assertEqual({s["tap_stream_id"] for s in streams}, original_names)

    def test_inaccessible_stream_excluded(self):
        """A stream returning check_access()=False is removed from the catalog."""
        mock_client = MagicMock()
        streams = self._make_streams(["customers", "subscriptions", "events"])

        original_check = STREAMS["customers"].check_access
        try:
            STREAMS["customers"].check_access = lambda self_inner: False
            _apply_access_checks(mock_client, streams)
            remaining = {s["tap_stream_id"] for s in streams}
            self.assertNotIn("customers", remaining)
            self.assertIn("subscriptions", remaining)
            self.assertIn("events", remaining)
        finally:
            STREAMS["customers"].check_access = original_check

    def test_all_inaccessible_raises(self):
        """When ALL streams are inaccessible, ChargifyForbiddenError is raised."""
        mock_client = MagicMock()
        streams = self._make_streams(["customers", "events"])

        original_checks = {name: cls.check_access for name, cls in STREAMS.items()}
        try:
            for cls in STREAMS.values():
                cls.check_access = lambda self_inner: False

            with self.assertRaises(ChargifyForbiddenError) as ctx:
                _apply_access_checks(mock_client, streams)
            self.assertIn("403", str(ctx.exception))
        finally:
            for name, cls in STREAMS.items():
                cls.check_access = original_checks[name]

    def test_prune_inaccessible_children_no_op_when_no_children(self):
        """All tap-chargify streams are top-level (parent=None); pruning is a no-op."""
        streams = self._make_streams()
        original = list(streams)
        _prune_inaccessible_children(streams)
        self.assertEqual([s["tap_stream_id"] for s in streams],
                         [s["tap_stream_id"] for s in original])

    def test_partial_access_logs_warning(self):
        """A warning is logged when some but not all streams are excluded."""
        mock_client = MagicMock()
        streams = self._make_streams(["customers", "events"])

        original_check_customers = STREAMS["customers"].check_access
        try:
            STREAMS["customers"].check_access = lambda self_inner: False

            with self.assertLogs(level="WARNING") as log_ctx:
                _apply_access_checks(mock_client, streams)

            self.assertTrue(any("customers" in msg for msg in log_ctx.output))
            self.assertEqual({s["tap_stream_id"] for s in streams}, {"events"})
        finally:
            STREAMS["customers"].check_access = original_check_customers


class TestCheckAccessMethod(unittest.TestCase):
    """Tests for Stream.check_access()."""

    def test_check_access_returns_true_on_success(self):
        mock_client = MagicMock()
        stream = STREAMS["customers"](client=mock_client)
        self.assertTrue(stream.check_access())
        mock_client._fetch_page.assert_called_once()

    def test_check_access_returns_false_on_403(self):
        mock_client = MagicMock()
        mock_client._fetch_page.side_effect = ChargifyForbiddenError("403 Forbidden")
        stream = STREAMS["customers"](client=mock_client)
        self.assertFalse(stream.check_access())

    def test_check_access_uses_product_families_path_for_products(self):
        mock_client = MagicMock()
        mock_client.uri = "https://test.chargify.com/"
        stream = STREAMS["products"](client=mock_client)
        stream.check_access()
        called_url = mock_client._fetch_page.call_args[0][0]
        self.assertIn("product_families", called_url)

    def test_check_access_uses_correct_path_for_direct_streams(self):
        mock_client = MagicMock()
        mock_client.uri = "https://test.chargify.com/"
        for name in ["customers", "subscriptions", "transactions", "statements", "invoices", "events"]:
            stream = STREAMS[name](client=mock_client)
            mock_client._fetch_page.reset_mock()
            stream.check_access()
            called_url = mock_client._fetch_page.call_args[0][0]
            self.assertIn(name, called_url, f"URL for stream '{name}' should contain the stream name")


class TestDiscoverStreamsExclusion(unittest.TestCase):
    """Integration-style tests (mock-based) verifying that discover_streams()
    correctly excludes unauthorized streams from the returned catalog."""

    def test_forbidden_stream_excluded_from_catalog(self):
        """A stream returning check_access()=False must not appear in the catalog."""
        mock_client = MagicMock()
        original_check = STREAMS["customers"].check_access
        try:
            STREAMS["customers"].check_access = lambda self_inner: False
            streams = discover_streams(mock_client)
            stream_ids = {s["tap_stream_id"] for s in streams}
            self.assertNotIn("customers", stream_ids)
        finally:
            STREAMS["customers"].check_access = original_check

    def test_authorized_streams_unaffected_when_one_excluded(self):
        """All accessible streams still appear in the catalog when one is excluded."""
        mock_client = MagicMock()
        original_check = STREAMS["customers"].check_access
        try:
            STREAMS["customers"].check_access = lambda self_inner: False
            streams = discover_streams(mock_client)
            stream_ids = {s["tap_stream_id"] for s in streams}
            self.assertEqual(stream_ids, set(STREAMS.keys()) - {"customers"})
        finally:
            STREAMS["customers"].check_access = original_check

    def test_all_forbidden_raises_error(self):
        """Discovery must raise ChargifyForbiddenError when no streams are accessible."""
        mock_client = MagicMock()
        original_checks = {name: cls.check_access for name, cls in STREAMS.items()}
        try:
            for cls in STREAMS.values():
                cls.check_access = lambda self_inner: False
            with self.assertRaises(ChargifyForbiddenError):
                discover_streams(mock_client)
        finally:
            for name, cls in STREAMS.items():
                cls.check_access = original_checks[name]

