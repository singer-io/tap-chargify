import unittest
import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tap_chargify as tap_main
from tap_chargify.sync import sync_stream
from tap_chargify.chargify import ChargifyUnauthorizedError


class TestSyncStream(unittest.TestCase):
    @patch("tap_chargify.sync.singer.write_record")
    @patch("tap_chargify.sync.singer.write_state")
    def test_sync_stream_writes_records_and_state_for_incremental(
        self,
        mock_write_state,
        mock_write_record,
    ):
        stream = MagicMock()
        stream.tap_stream_id = "transactions"
        stream.schema.to_dict.return_value = {"type": "object", "properties": {"id": {"type": "integer"}}}
        stream.metadata = []

        instance = MagicMock()
        instance.stream = stream
        instance.replication_method = "INCREMENTAL"
        instance.sync.return_value = iter([(stream, {"id": 1}), (stream, {"id": 2})])

        counter = sync_stream({}, instance)

        self.assertEqual(counter, 2)
        self.assertEqual(mock_write_record.call_count, 2)
        mock_write_state.assert_called_once()


class TestTapEntrypoint(unittest.TestCase):
    def test_discover_writes_catalog(self):
        with patch("tap_chargify.discover_streams", return_value=[{"tap_stream_id": "customers"}]):
            with patch("sys.stdout", new=io.StringIO()) as fake_stdout:
                tap_main.discover(client=MagicMock())
                self.assertIn("customers", fake_stdout.getvalue())

    def test_stream_is_selected_true_and_false(self):
        self.assertTrue(tap_main.stream_is_selected({(): {"selected": True}}))
        self.assertFalse(tap_main.stream_is_selected({(): {"selected": False}}))
        self.assertFalse(tap_main.stream_is_selected({}))

    def test_get_selected_streams_filters(self):
        selected = SimpleNamespace(tap_stream_id="customers", metadata="selected")
        skipped = SimpleNamespace(tap_stream_id="events", metadata="skipped")
        catalog = SimpleNamespace(streams=[selected, skipped])

        with patch("tap_chargify.metadata.to_map", side_effect=[{(): {"selected": True}}, {(): {"selected": False}}]):
            self.assertEqual(tap_main.get_selected_streams(catalog), ["customers"])

    def test_sync_runs_selected_streams_and_skips_others(self):
        selected_stream = SimpleNamespace(
            tap_stream_id="customers",
            metadata="selected-metadata",
            schema=SimpleNamespace(to_dict=lambda: {"type": "object"}),
        )
        unselected_stream = SimpleNamespace(
            tap_stream_id="events",
            metadata="unselected-metadata",
            schema=SimpleNamespace(to_dict=lambda: {"type": "object"}),
        )
        catalog = SimpleNamespace(streams=[unselected_stream, selected_stream])
        state = {}

        fake_instance = MagicMock()
        fake_instance.stream = None

        with patch("tap_chargify.get_selected_streams", return_value=["customers"]):
            with patch("tap_chargify.metadata.to_map", side_effect=[{(): {}}, {(): {"table-key-properties": ["id"]}}]):
                with patch("tap_chargify.metadata.get", return_value=["id"]):
                    with patch("tap_chargify.singer.write_schema") as write_schema:
                        with patch("tap_chargify.singer.write_state") as write_state:
                            with patch.dict("tap_chargify.STREAMS", {"customers": lambda client: fake_instance}):
                                with patch("tap_chargify.sync_stream", return_value=2) as sync_stream_call:
                                    tap_main.sync(client=MagicMock(), catalog=catalog, state=state)
                                    write_schema.assert_called_once()
                                    sync_stream_call.assert_called_once()
                                    write_state.assert_called_once_with(state)

    def test_main_discover_branch(self):
        args = SimpleNamespace(
            config={"start_date": "2020-01-01T00:00:00Z", "api_key": "key", "subdomain": "sub"},
            discover=True,
            catalog=None,
            state=None,
        )
        fake_client = MagicMock()

        with patch("tap_chargify.singer.utils.parse_args", return_value=args):
            with patch("tap_chargify.Chargify", return_value=fake_client):
                with patch("tap_chargify.discover") as discover_call:
                    tap_main.main.__wrapped__()
                    discover_call.assert_called_once_with(fake_client)

    def test_main_catalog_branch_with_default_state(self):
        args = SimpleNamespace(
            config={"start_date": "2020-01-01T00:00:00Z", "api_key": "key", "subdomain": "sub"},
            discover=False,
            catalog=SimpleNamespace(streams=[]),
            state=None,
        )
        fake_client = MagicMock()

        with patch("tap_chargify.singer.utils.parse_args", return_value=args):
            with patch("tap_chargify.Chargify", return_value=fake_client):
                with patch("tap_chargify.sync") as sync_call:
                    tap_main.main.__wrapped__()
                    sync_call.assert_called_once_with(fake_client, args.catalog, {})

    def test_main_unauthorized_exits(self):
        args = SimpleNamespace(
            config={"start_date": "2020-01-01T00:00:00Z", "api_key": "bad", "subdomain": "sub"},
            discover=False,
            catalog=None,
            state=None,
        )
        fake_client = MagicMock()
        fake_client.verify_credentials.side_effect = ChargifyUnauthorizedError("nope")

        with patch("tap_chargify.singer.utils.parse_args", return_value=args):
            with patch("tap_chargify.Chargify", return_value=fake_client):
                with self.assertRaises(SystemExit):
                    tap_main.main.__wrapped__()
