import unittest
from unittest.mock import MagicMock, patch

from tap_chargify.sync import sync_stream


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
