
# 
# Module dependencies.
# 

import os
import json
import singer
import sys
from tap_chargify.streams import STREAMS


def discover_streams(client):
  streams = []

  for s in STREAMS.values():
    s = s(client)
    schema = singer.resolve_schema_references(s.load_schema())

    # If stream is `users`, then get dynamic fields via API.
    if s.name == "users":
      res = s.client.get_user_fields()
      fields = res["fields"]
      # Merge `fields` with schema.
      field_schema = translate_to_schema(fields)     
      schema = merge(schema, field_schema)

    streams.append({'stream': s.name, 'tap_stream_id': s.name, 'schema': schema, 'metadata': s.load_metadata()})
  return streams

#
# Helper function to infer schema datatype.
# 

def get_schema_datatype(v):
  NUMBER_TYPES = set([
    'double'
  ])
  INTEGER_TYPES = set([
    'long'
  ])
  DATE_TYPES = set([
    'date'
  ])
  STRING_TYPES = set([
    'string'
  ])
  BOOLEAN_TYPES = set([
    'boolean'
  ])

  dt = ""

  # Check datatypes.
  if v in NUMBER_TYPES:
    dt = "number"
  elif v in INTEGER_TYPES:
    dt = "integer"
  elif v in DATE_TYPES:
    dt = "string"
  elif v in STRING_TYPES:
    dt = "string"
  elif v in BOOLEAN_TYPES:
    dt = "boolean"

  datatype = {
    "type": [
      "null",
      dt
    ]
  }

  if v in DATE_TYPES:
    datatype["format"] = "date-time"

  return datatype

# 
# Helper function to translate `user.fields` => singer schema.
# 

def translate_to_schema(fields):
  schema = {
    "properties": {}
  }
  for k, v in fields.items():
    # If k has a ".", k is an object.
    if "." in k:
      # Create the object.
      k_name = k.split(".")[0]
      k_value = k.split(".")[1]

      # If key not created, then create.
      if k_name not in schema["properties"]:
        schema["properties"][k_name] = { "type": ["null", "object"], "properties": {} }

      schema["properties"][k_name]["properties"][k_value] = get_schema_datatype(v)

    else:
      if v != "object":
        schema['properties'][k] = get_schema_datatype(v)

  return schema


def merge(left, right):
  """This is a deep merge implementation.
  It's called on manifest_table dicts with the intent of merging all of
  them into a superset of all of their contents. The tricky part is that
  the values need to be merged as well."""
  merged = left

  for table_key, table_value in right.items():
    if left.get(table_key):
      for key in table_value.keys():
        if left[table_key].get(key):
          merged[table_key][key] = merged[table_key][key] or table_value[key]
    else:
      merged[table_key] = right[table_key]

  return merged

