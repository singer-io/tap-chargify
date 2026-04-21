import unittest
from unittest.mock import MagicMock

from tap_chargify.context import Context
from tap_chargify.streams import Transactions, Invoices


class TestIncrementalSyncHelpers(unittest.TestCase):
    def setUp(self):
        self.original_context = dict(Context.config)
        Context.config = {"start_date": "2025-01-01T00:00:00Z"}

    def tearDown(self):
        Context.config = self.original_context

    def test_is_bookmark_old(self):
        stream = Transactions(MagicMock())
        state = {"bookmarks": {"transactions": {"created_at": "2025-01-01T00:00:00Z"}}}

        self.assertTrue(stream.is_bookmark_old(state, "2025-01-02T00:00:00Z"))
        self.assertFalse(stream.is_bookmark_old(state, "2024-12-30T00:00:00Z"))

    def test_update_bookmark(self):
        stream = Transactions(MagicMock())
        state = {"bookmarks": {"transactions": {"created_at": "2025-01-01T00:00:00Z"}}}

        stream.update_bookmark(state, "2025-03-01T00:00:00Z")
        self.assertEqual(stream.get_bookmark(state), "2025-03-01T00:00:00Z")


class TestInvoicesBookmark(unittest.TestCase):
    """Invoices.is_bookmark_old must handle plain date strings (YYYY-MM-DD)
    returned by the Chargify API without raising a TypeError on non-UTC hosts.
    """

    def setUp(self):
        self.original_context = dict(Context.config)
        Context.config = {"start_date": "2025-01-01T00:00:00Z"}

    def tearDown(self):
        Context.config = self.original_context

    def test_date_only_value_newer_than_bookmark(self):
        stream = Invoices(MagicMock())
        state = {"bookmarks": {"invoices": {"due_date": "2025-04-01"}}}
        # 2025-04-20 > 2025-04-01 → old bookmark
        self.assertTrue(stream.is_bookmark_old(state, "2025-04-20"))

    def test_date_only_value_older_than_bookmark(self):
        stream = Invoices(MagicMock())
        state = {"bookmarks": {"invoices": {"due_date": "2025-04-20"}}}
        self.assertFalse(stream.is_bookmark_old(state, "2025-03-01"))

    def test_date_only_equal_to_bookmark(self):
        stream = Invoices(MagicMock())
        state = {"bookmarks": {"invoices": {"due_date": "2025-04-20"}}}
        self.assertFalse(stream.is_bookmark_old(state, "2025-04-20"))

    def test_fallback_to_start_date_when_no_state(self):
        stream = Invoices(MagicMock())
        state = {}
        # start_date is 2025-01-01T00:00:00Z; normalised to 2025-01-01
        # 2025-06-01 > 2025-01-01 → old bookmark
        self.assertTrue(stream.is_bookmark_old(state, "2025-06-01"))

    def test_datetime_value_compared_as_date(self):
        """Even if a value has a datetime component, only the date portion is used."""
        stream = Invoices(MagicMock())
        state = {"bookmarks": {"invoices": {"due_date": "2025-04-20"}}}
        # datetime string 2025-04-21T00:00:00Z truncates to 2025-04-21 > 2025-04-20
        self.assertTrue(stream.is_bookmark_old(state, "2025-04-21T00:00:00Z"))

    def test_does_not_raise_on_tz_naive_date(self):
        """No TypeError should occur when comparing a plain date against a start_date datetime."""
        stream = Invoices(MagicMock())
        state = {}
        Context.config = {"start_date": "2025-01-01T05:30:00+05:30"}  # non-UTC offset
        try:
            result = stream.is_bookmark_old(state, "2025-06-01")
        except TypeError as exc:
            self.fail(f"is_bookmark_old raised TypeError for a plain date: {exc}")
        self.assertTrue(result)
