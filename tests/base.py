import json
import os

from tap_chargify.context import Context
from tap_chargify.streams import STREAMS


class ChargifyBaseTest:
    default_start_date = "2025-01-01T00:00:00Z"
    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"
    REPLICATION_KEYS = "replication_keys"
    OBEYS_START_DATE = "obeys_start_date"
    API_LIMIT = "api_limit"

    def setUp(self):
        self.original_context_config = dict(Context.config)
        Context.config = {
            "api_key": "dummy-key",
            "subdomain": "dummy-subdomain",
            "start_date": self.default_start_date,
        }

    def tearDown(self):
        Context.config = self.original_context_config

    @classmethod
    def expected_metadata(cls):
        expected = {}
        for stream_name, stream_cls in STREAMS.items():
            instance = stream_cls()
            replication_key = getattr(instance, "replication_key", None)
            replication_method = getattr(instance, "replication_method", "FULL_TABLE")
            expected[stream_name] = {
                cls.PRIMARY_KEYS: set(getattr(instance, "key_properties", ["id"])),
                cls.REPLICATION_METHOD: replication_method,
                cls.REPLICATION_KEYS: {replication_key} if replication_key else set(),
                cls.OBEYS_START_DATE: replication_method == "INCREMENTAL",
                cls.API_LIMIT: 1,
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
            non_null = [item for item in schema_type if item != "null"]
            return non_null[0] if non_null else "null"
        return schema_type

    @staticmethod
    def _generate_value(schema, date_value="2025-01-01T00:00:00Z"):
        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]

        schema_type = ChargifyBaseTest._schema_type(schema)
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = set(schema.get("required", []))
            return {
                key: ChargifyBaseTest._generate_value(value, date_value=date_value)
                for key, value in properties.items()
                if key in required or ChargifyBaseTest._schema_type(value) != "null"
            }
        if schema_type == "array":
            return [
                ChargifyBaseTest._generate_value(
                    schema.get("items", {"type": "string"}),
                    date_value=date_value,
                )
            ]
        if schema_type == "string":
            return date_value if schema.get("format") == "date-time" else "mock"
        return {"integer": 1, "number": 1.0, "boolean": True}.get(schema_type)

    @classmethod
    def _generate_stream_record(cls, stream_name, date_value="2025-01-01T00:00:00Z"):
        return cls._generate_value(cls._load_schema(stream_name), date_value=date_value)
