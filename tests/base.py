import json
import os

from tap_tester import connections, menagerie, runner
from tap_tester.logger import LOGGER
from tap_tester.base_suite_tests.base_case import BaseCase


class ChargifyBaseTest(BaseCase):
    """Setup expectations for test sub classes.

    Metadata describing streams. Shared methods that are used in
    tap-tester tests. Shared tap-specific methods (as needed).
    """

    start_date = "2025-01-01T00:00:00Z"

    @staticmethod
    def tap_name():
        """The name of the tap."""
        return "tap-chargify"

    @staticmethod
    def get_type():
        """The name of the tap."""
        return "platform.chargify"

    @classmethod
    def expected_metadata(cls):
        """The expected streams and metadata about the streams."""
        return {
            "customers": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "product_families": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "products": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "price_points": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "coupons": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "components": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "subscriptions": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "transactions": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"created_at"},
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "statements": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "invoices": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"due_date"},
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
            "events": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            },
        }

    @staticmethod
    def get_credentials():
        """Authentication information for the test account."""
        return {
            "api_key": os.getenv("TAP_CHARGIFY_API_KEY"),
            "subdomain": os.getenv("TAP_CHARGIFY_SUBDOMAIN"),
        }

    def get_properties(self, original: bool = True):
        """Configuration of properties required for the tap.

        The start_date is driven by self.start_date (defaulting to the
        class-level attribute).  Tests such as StartDateTest update
        self.start_date before each sync so that the tap config file is
        written with the correct start date for each run.
        """
        if original:
            return {
                "start_date": self.start_date,
            }
        # Non-original: reset back to the class-level default
        return {
            "start_date": "2026-01-01T00:00:00Z",
        }


class ChargifyBaseMockTest:
    """Base helpers for mock/unit tests of tap-chargify.

    Provides schema loading, record generation, and metadata expectations
    without requiring a live Chargify connection.
    """

    default_start_date = "2025-01-01T00:00:00Z"
    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"
    REPLICATION_KEYS = "replication_keys"
    OBEYS_START_DATE = "obeys_start_date"
    API_LIMIT = "api_limit"

    def setUp(self):
        from tap_chargify.context import Context
        self._original_context_config = dict(Context.config)
        Context.config = {
            "api_key": "dummy-key",
            "subdomain": "dummy-subdomain",
            "start_date": self.default_start_date,
        }

    def tearDown(self):
        from tap_chargify.context import Context
        Context.config = self._original_context_config

    @classmethod
    def expected_metadata(cls):
        from tap_chargify.streams import STREAMS
        expected = {}
        for stream_name, stream_cls in STREAMS.items():
            instance = stream_cls()
            replication_key = getattr(instance, "replication_key", None)
            replication_method = getattr(instance, "replication_method", "FULL_TABLE")
            expected[stream_name] = {
                cls.PRIMARY_KEYS: set(instance.key_properties or []),
                cls.REPLICATION_METHOD: replication_method,
                cls.REPLICATION_KEYS: {replication_key} if replication_key else set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100,
            }
        return expected

    @staticmethod
    def _schema_path(stream_name):
        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        return os.path.join(base_dir, "tap_chargify", "schemas", f"{stream_name}.json")

    @classmethod
    def _load_schema(cls, stream_name):
        with open(cls._schema_path(stream_name), "r", encoding="utf-8") as schema_file:
            return json.load(schema_file)

    @staticmethod
    def _schema_type(schema):
        schema_type = schema.get("type", "object")
        if isinstance(schema_type, list):
            return next((t for t in schema_type if t != "null"), schema_type[0])
        return schema_type

    @staticmethod
    def _generate_value(schema, date_value="2025-01-01T00:00:00Z"):
        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]
        schema_type = ChargifyBaseMockTest._schema_type(schema)
        if schema_type == "object":
            return {
                k: ChargifyBaseMockTest._generate_value(v, date_value)
                for k, v in schema.get("properties", {}).items()
            }
        if schema_type == "array":
            items_schema = schema.get("items", {})
            return [ChargifyBaseMockTest._generate_value(items_schema, date_value)]
        if schema_type == "string":
            if "date" in schema.get("format", ""):
                return date_value
            return "sample"
        return {"integer": 1, "number": 1.0, "boolean": True}.get(schema_type)

    @classmethod
    def _generate_stream_record(cls, stream_name, date_value="2025-01-01T00:00:00Z"):
        return cls._generate_value(cls._load_schema(stream_name), date_value=date_value)


class ChargifyRealApiMockBase(ChargifyBaseMockTest):
    """Base class for integration tests that make real API calls.

    Requires TAP_CHARGIFY_API_KEY and TAP_CHARGIFY_SUBDOMAIN env vars.
    Mirrors the tap-amazon-ads integration test style.
    """

    default_start_date = "2023-01-01T00:00:00Z"

    def setUp(self):
        super().setUp()
        from tap_chargify.chargify import Chargify
        from tap_chargify.context import Context
        from tap_chargify.streams import STREAMS as _STREAMS
        api_key = os.environ.get("TAP_CHARGIFY_API_KEY")
        subdomain = os.environ.get("TAP_CHARGIFY_SUBDOMAIN")
        if not api_key or not subdomain:
            self.skipTest("TAP_CHARGIFY_API_KEY and TAP_CHARGIFY_SUBDOMAIN must be set")
        Context.config = {
            "api_key": api_key,
            "subdomain": subdomain,
            "start_date": self.default_start_date,
        }
        self.client = Chargify(api_key=api_key, subdomain=subdomain, start_date=self.default_start_date)
        self._streams = _STREAMS

    def _sync_stream(self, stream_name, state=None):
        """Sync a single stream against the real API and return (stream_name, record) pairs."""
        instance = self._streams[stream_name](self.client)
        instance.stream = stream_name
        return list(instance.sync(state or {}))
