from dateutil.parser import parse as dateutil_parse
import pytz

from base import ChargifyBaseTest
from tap_tester.base_suite_tests.bookmark_test import BookmarkTest


class ChargifyBookmarkTest(BookmarkTest, ChargifyBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""

    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    initial_bookmarks = {
        "bookmarks": {
            "transactions": {"created_at": "2026-01-01T00:00:00Z"},
        }
    }
    # Fixed midpoint bookmark so sync 2 always has data to retrieve.
    # The API uses `since_date` (date-only, exclusive of the given date),
    # so we set the midpoint to 2026-01-31 which leaves ~45 days of records
    # for sync 2 (Feb–Mar 2026 data in the test account).
    SYNC2_BOOKMARK = "2026-01-31T00:00:00Z"

    @staticmethod
    def name():
        return "tap_tester_chargify_bookmark_test"

    def streams_to_test(self):
        # BookmarkTest is designed for INCREMENTAL streams only (requires replication key).
        # Invoices are excluded: the API returns due_date as a plain date string (YYYY-MM-DD)
        # and invoices have no 'id', making bookmark comparison unreliable.
        return {"transactions"}

    def get_bookmark_value(self, state, stream):
        """Override to normalize the tap's bookmark (stored in -04:00 / -05:00
        timezone-offset format) to UTC .000000Z format.

        The tap stores bookmarks as the raw Chargify API value, e.g.
        '2026-03-18T01:45:57-04:00'.  Singer's Transformer writes records to
        the target in UTC .000000Z format, e.g. '2026-03-18T01:45:57.000000Z'.
        tap-tester's parse_date() treats the .000000Z form as a *naive* local
        datetime and calls astimezone(UTC), giving a result that is always
        offset by the machine's local timezone (IST = UTC+5:30 on this WSL).
        If the bookmark value is in a different format it goes through a
        different code path and ends up at a different UTC instant.

        By converting the bookmark to UTC .000000Z here, both the bookmark and
        record timestamps pass through the same (IST-naive) parse_date path and
        receive the same systematic offset, making assertEqual() succeed.
        """
        raw_value = super().get_bookmark_value(state, stream)
        if raw_value is None:
            return None
        try:
            dt = dateutil_parse(raw_value)
            if dt.tzinfo is not None:
                dt_utc = dt.astimezone(pytz.UTC)
                return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
        except Exception:
            pass
        return raw_value

    def calculate_new_bookmarks(self):
        """Override to return a fixed midpoint bookmark.

        The default implementation picks `replication_values[-2]` from sync 1
        data, which can land on today's date causing the Chargify API's
        date-only `since_date` filter to return 0 records in sync 2.
        Instead, use a fixed date known to be mid-range in the test data so
        sync 2 always retrieves a meaningful set of records.
        """
        replication_keys = self.expected_replication_keys()
        new_bookmarks = {}
        for stream in self.streams_to_test():
            replication_key = next(iter(replication_keys[stream]))
            new_bookmarks[self.get_stream_id(stream)] = {
                replication_key: self.SYNC2_BOOKMARK
            }
        return new_bookmarks
