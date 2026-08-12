import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

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
from tap_chargify.streams import Stream, Invoices, epoch_to_datetime_string
from tap_chargify.context import Context


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
        # Verify key_properties is present in each stream
        for stream in streams:
            self.assertIn("key_properties", stream)
            self.assertIsInstance(stream["key_properties"], list)
            self.assertTrue(len(stream["key_properties"]) > 0)


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
            self.assertIn("No streams are accessible", str(ctx.exception))
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

    def test_product_family_streams_share_single_access_probe(self):
        mock_client = MagicMock()
        mock_client.uri = "https://test.chargify.com/"
        streams = [
            {"stream": n, "tap_stream_id": n, "schema": {}, "metadata": []}
            for n in ["products", "price_points", "coupons", "components"]
        ]

        _apply_access_checks(mock_client, streams)

        self.assertEqual(mock_client._fetch_page.call_count, 1)
        called_url = mock_client._fetch_page.call_args[0][0]
        self.assertIn("product_families", called_url)


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


class DummyStream(Stream):
    name = "dummy"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"


class DummyFullTableStream(Stream):
    name = "dummy_full"
    replication_method = "FULL_TABLE"


class TestAdditionalDiscoveryAndStreamCoverage(unittest.TestCase):
    def setUp(self):
        Context.config = {"start_date": "2020-01-01T00:00:00Z"}

    def test_prune_inaccessible_children_logs_and_removes(self):
        original = STREAMS.get("child_test")

        class ChildStream:
            parent = "missing_parent"

        STREAMS["child_test"] = ChildStream
        streams = [{"tap_stream_id": "child_test"}, {"tap_stream_id": "customers"}]

        try:
            with self.assertLogs(level="WARNING"):
                _prune_inaccessible_children(streams)
            self.assertEqual([s["tap_stream_id"] for s in streams], ["customers"])
        finally:
            if original is None:
                del STREAMS["child_test"]
            else:
                STREAMS["child_test"] = original

    def test_discover_streams_users_dynamic_fields_branch(self):
        original = STREAMS.get("users")

        class UsersStream:
            name = "users"
            key_properties = ["id"]

            def __init__(self, client):
                self.client = client

            def load_schema(self):
                return {"properties": {"id": {"type": ["null", "integer"]}}}

            def load_metadata(self):
                return []

        STREAMS["users"] = UsersStream
        mock_client = MagicMock()
        mock_client.get_user_fields.return_value = {"fields": {"id": "string"}}

        try:
            with patch("tap_chargify.discover._apply_access_checks"):
                streams = discover_streams(mock_client)
            users_schema = next(s["schema"] for s in streams if s["tap_stream_id"] == "users")
            self.assertIn("id", users_schema["properties"])
        finally:
            if original is None:
                del STREAMS["users"]
            else:
                STREAMS["users"] = original

    def test_merge_updates_existing_key(self):
        left = {"properties": {"a": "left"}}
        right = {"properties": {"a": "right"}}
        merged = merge(left, right)
        self.assertEqual(merged["properties"]["a"], "left")

    def test_epoch_to_datetime_string_helper_paths(self):
        self.assertEqual(epoch_to_datetime_string("already-date"), "already-date")
        self.assertTrue(isinstance(epoch_to_datetime_string(0), str))

    def test_stream_sync_paths_and_helpers(self):
        s = Stream(client=MagicMock())
        s.parent = "root"
        self.assertTrue(s.check_access())

        ds = DummyStream(client=MagicMock())
        ds.session_bookmark = "2026-01-01T00:00:00Z"
        self.assertFalse(ds.is_session_bookmark_old("2025-01-01T00:00:00Z"))

        ds.session_bookmark = None
        ds.update_session_bookmark("2025-01-01T00:00:00Z")
        self.assertIsNotNone(ds.session_bookmark)

        ds.stream = "dummy_stream"
        client = MagicMock()
        client.dummy.return_value = [
            {"updated_at": "2020-01-01T00:00:00Z", "id": 1},
            {"updated_at": "2020-01-02T00:00:00Z", "id": 2},
        ]
        ds.client = client
        state = {"bookmarks": {"dummy": {"updated_at": "2020-01-01T00:00:00Z"}}}
        rows = list(ds.sync(state))
        self.assertEqual(rows, [("dummy_stream", {"updated_at": "2020-01-02T00:00:00Z", "id": 2})])

        ft = DummyFullTableStream(client=MagicMock())
        ft.stream = "full_stream"
        ft.client.dummy_full.return_value = [{"id": 1}, {"id": 2}]
        rows = list(ft.sync({}))
        self.assertEqual(rows, [("full_stream", {"id": 1}), ("full_stream", {"id": 2})])

    def test_invoice_to_date_str_none(self):
        self.assertIsNone(Invoices._to_date_str(None))

