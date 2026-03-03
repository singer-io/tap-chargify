import unittest
from unittest.mock import MagicMock, patch

from tap_chargify import sync


def _stream_metadata(selected):
    return [{"breadcrumb": [], "metadata": {"selected": selected, "table-key-properties": ["id"]}}]


class SyncIntegrationTest(unittest.TestCase):
    @patch("tap_chargify.singer.write_state")
    @patch("tap_chargify.singer.write_schema")
    @patch("tap_chargify.sync_stream", return_value=1)
    def test_sync_runs_only_selected_streams(
        self,
        mock_sync_stream,
        mock_write_schema,
        mock_write_state,
    ):
        selected_stream = MagicMock()
        selected_stream.tap_stream_id = "customers"
        selected_stream.metadata = _stream_metadata(True)
        selected_stream.schema.to_dict.return_value = {"type": "object", "properties": {"id": {"type": "integer"}}}

        skipped_stream = MagicMock()
        skipped_stream.tap_stream_id = "events"
        skipped_stream.metadata = _stream_metadata(False)
        skipped_stream.schema.to_dict.return_value = {"type": "object", "properties": {"id": {"type": "integer"}}}

        catalog = MagicMock()
        catalog.streams = [selected_stream, skipped_stream]

        sync(MagicMock(), catalog, state={})

        self.assertEqual(mock_write_schema.call_count, 1)
        self.assertEqual(mock_sync_stream.call_count, 1)
        mock_write_state.assert_called_once()
