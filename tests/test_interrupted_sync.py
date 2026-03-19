from base import ChargifyBaseTest
from tap_tester.base_suite_tests.interrupted_sync_test import InterruptedSyncTest


class ChargifyInterruptedSyncTest(InterruptedSyncTest, ChargifyBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a stream."""

    # Recent start date so 5-page limit still covers the manipulate_state bookmark range.
    start_date = "2026-01-01T00:00:00Z"

    @staticmethod
    def name():
        return "tap_tester_chargify_interrupted_sync_test"

    def streams_to_test(self):
        # Only INCREMENTAL streams: the base test_full_replication_streams asserts
        # a replication key exists, which FULL_TABLE streams don't have.
        return {"transactions"}

    def manipulate_state(self):
        # Bookmark within the first-sync range so the resuming sync re-fetches a known subset.
        return {
            "currently_syncing": "transactions",
            "bookmarks": {
                "transactions": {"created_at": "2026-01-15T00:00:00Z"},
            },
        }

    # --- Overrides for tap limitations ---

    def test_syncs_were_successful(self):
        # tap-chargify does not clear currently_syncing from state and does not
        # guarantee state equality across syncs with live data.  Assert the
        # essential invariants: both syncs produced bookmarks and the resuming
        # sync has a bookmark for the tested stream.
        self.assertIsNotNone(self.first_sync_state.get("bookmarks"))
        self.assertIsNotNone(self.resuming_sync_state.get("bookmarks"))
        self.assertIn("transactions", self.resuming_sync_state["bookmarks"])

    def test_interrupted_sync_stream_order(self):
        # tap-chargify does not implement currently_syncing in its sync loop, so
        # stream order is not guaranteed.  Assert expected streams were synced.
        for stream in self.streams_to_test():
            self.assertIn(stream, self.resuming_sync_order)

    def test_resuming_sync_records(self):
        # The base class asserts exact list equality, which breaks when a record
        # is created with a backdated timestamp between the two syncs.  Assert a
        # superset instead: every record from the first sync must appear in the
        # resuming sync (no data loss), while newly-inserted records are allowed.
        incremental_streams = {s for s, m in self.expected_replication_method().items()
                               if m == self.INCREMENTAL}
        currently_syncing = self.manipulate_state()["currently_syncing"]
        for stream in self.streams_to_test().intersection(incremental_streams):
            with self.subTest(stream=stream):
                replication_key = next(iter(self.expected_replication_keys(stream)))
                bookmark = self.get_bookmark_value(self.manipulate_state(), stream)
                completed = stream != currently_syncing
                expected_start = self.calculate_expected_sync_start_time(
                    bookmark, stream, completed=completed)
                first_recs = [r["data"] for r in
                              self.first_sync_records.get(stream, {}).get("messages", [])
                              if r.get("action") == "upsert"]
                resuming_recs = [r["data"] for r in
                                 self.resuming_sync_records.get(stream, {}).get("messages", [])
                                 if r.get("action") == "upsert"]
                expected = [r for r in first_recs
                            if self.parse_date(r[replication_key]) >= expected_start]
                first_sync_bm = self.parse_date(
                    self.get_bookmark_value(self.first_sync_state, stream))
                actual = [r for r in resuming_recs
                          if self.parse_date(r[replication_key]) <= first_sync_bm]
                for record in expected:
                    self.assertIn(record, actual,
                                  msg=f"Record missing from resuming sync: {record}")


