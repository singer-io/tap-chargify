
#
# Module dependencies.
#

import os
import json
import datetime
import pytz
import singer
import time
from singer import metadata
from singer import utils
from singer.metrics import Point
from dateutil.parser import parse
from tap_chargify.context import Context


logger = singer.get_logger()
KEY_PROPERTIES = ['id']


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def epoch_to_datetime_string(milliseconds):
    datetime_string = None
    try:
        datetime_string = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(milliseconds / 1000))
    except TypeError:
        # If fails, it means format already datetime string.
        datetime_string = milliseconds
        pass
    return datetime_string


class Stream():
    name = None
    replication_method = None
    replication_key = None
    stream = None
    key_properties = KEY_PROPERTIES
    session_bookmark = None


    def __init__(self, client=None):
        self.client = client


    def is_session_bookmark_old(self, value):
        if self.session_bookmark is None:
            return True
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(self.session_bookmark)


    def update_session_bookmark(self, value):
        # Assume value is epoch milliseconds.
        value_in_date_time = epoch_to_datetime_string(value)
        if self.is_session_bookmark_old(value_in_date_time):
            self.session_bookmark = value_in_date_time


    # Reads and converts bookmark from state.
    def get_bookmark(self, state, name=None):
        name = self.name if not name else name
        return (singer.get_bookmark(state, name, self.replication_key)) or Context.config["start_date"]


    # Converts and writes bookmark to state.
    def update_bookmark(self, state, value, name=None):
        name = self.name if not name else name
        # when `value` is None, it means to set the bookmark to None
        if value is None or self.is_after_bookmark(state, value, name):
            singer.write_bookmark(state, name, self.replication_key, value)


    def is_after_bookmark(self, state, value, name=None):
        current_bookmark = self.get_bookmark(state, name)
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(current_bookmark)


    def load_schema(self):
        schema_file = "schemas/{}.json".format(self.name)
        with open(get_abs_path(schema_file)) as f:
            schema = json.load(f)
        return schema


    def load_metadata(self):
        mdata = metadata.get_standard_metadata(
            schema=self.load_schema(),
            key_properties=self.key_properties,
            valid_replication_keys=[self.replication_key] if self.replication_key else None,
            replication_method=self.replication_method
        )
        if self.replication_key:
            mdata = metadata.to_list(
                metadata.write(
                    metadata.to_map(mdata),
                    ('properties', self.replication_key),
                    'inclusion',
                    'automatic'
                )
            )
        return mdata


    # The main sync function.
    def sync(self, state):
        get_data = getattr(self.client, self.name)
        bookmark = self.get_bookmark(state)
        # res = get_data(self.replication_key, bookmark)
        res = get_data(bookmark)

        if self.replication_method == "INCREMENTAL":
            # These streams results may not be ordered,
            # so store highest value bookmark in session.
            for item in res:
                # if item is bigger than bookmark, then
                if self.is_after_bookmark(state, item[self.replication_key]):
                    self.update_bookmark(state, item[self.replication_key])
                    yield (self.stream, item)
        else:
            for item in res:
                yield (self.stream, item)



class Customers(Stream):
    name = "customers"
    replication_method = "FULL_TABLE"
    # incremental


class ProductFamilies(Stream):
    name = "product_families"
    replication_method = "FULL_TABLE"


class Products(Stream):
    name = "products"
    replication_method = "FULL_TABLE"


class PricePoints(Stream):
    name = "price_points"
    replication_method = "FULL_TABLE"


class Coupons(Stream):
    name = "coupons"
    replication_method = "FULL_TABLE"


class Components(Stream):
    name = "components"
    replication_method = "FULL_TABLE"


class Subscriptions(Stream):
    name = "subscriptions"
    replication_method = "FULL_TABLE"
    # replication_key = "updated_at"


class Transactions(Stream):
    name = "transactions"
    replication_method = "INCREMENTAL"
    replication_key = "created_at"
    # since API endpoint filter is only on date (and not datetime),
    # make sure to filter out redundant rows.


class Statements(Stream):
    name = "statements"
    replication_method = "FULL_TABLE"
    # replication_key = "updated_at"


class Invoices(Stream):
    name = "invoices"
    replication_method = "INCREMENTAL"
    replication_key = "due_date"
    # API endpoint filters only on `due_date`.
    key_properties = ['number']  # 'id' is absent in actual API responses; 'number' is the unique invoice identifier

    @staticmethod
    def _to_date_str(value):
        """Normalize a date, datetime string, or epoch timestamp to YYYY-MM-DD.

        Handles:
        - Plain date strings (e.g. ``2025-04-20``)
        - ISO 8601 datetime strings with or without timezone
        - Unix epoch timestamps (int or float, seconds since epoch)
        """
        if not value:
            return value
        if isinstance(value, (int, float)):
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc).strftime('%Y-%m-%d')
        return str(parse(str(value)).date())

    def is_after_bookmark(self, state, value, name=None):
        """Return True if *value* is after the current bookmark.

        Compares due_date values as YYYY-MM-DD date strings, which is safe
        because the Chargify invoices endpoint only accepts a plain date for
        its ``start_date`` filter, so sub-day precision is meaningless.
        """
        current_bookmark = self.get_bookmark(state, name)
        return self._to_date_str(value) > self._to_date_str(current_bookmark)


class Events(Stream):
    name = "events"
    replication_method = "FULL_TABLE"



STREAMS = {
    "customers": Customers,
    "product_families": ProductFamilies,
    "products": Products,
    "price_points": PricePoints,
    "coupons": Coupons,
    "components": Components,
    "subscriptions": Subscriptions,
    "transactions": Transactions,
    "statements": Statements,
    "invoices": Invoices,
    "events": Events
}
