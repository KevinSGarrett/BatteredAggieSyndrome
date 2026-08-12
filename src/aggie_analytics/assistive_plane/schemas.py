from __future__ import annotations

from typing import Any


def validate_strict_schema(schema: dict[str, Any], path: str = "$") -> None:
    if schema.get("type") == "object":
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{path}: object properties required")
        if schema.get("additionalProperties") is not False:
            raise ValueError(f"{path}: additionalProperties must be false")
        if set(schema.get("required", [])) != set(properties):
            raise ValueError(f"{path}: every property must be required")
        for key, value in properties.items():
            validate_strict_schema(value, f"{path}.{key}")
    elif schema.get("type") == "array":
        if "items" not in schema:
            raise ValueError(f"{path}: array items required")
        validate_strict_schema(schema["items"], f"{path}[]")


def validate_output(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected object")
        properties = schema["properties"]
        if set(value) != set(properties):
            raise ValueError(f"{path}: output fields disagree with strict schema")
        for key, child in value.items():
            validate_output(child, properties[key], f"{path}.{key}")
    elif expected == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected array")
        for index, child in enumerate(value):
            validate_output(child, schema["items"], f"{path}[{index}]")
    elif expected == "string" and not isinstance(value, str):
        raise ValueError(f"{path}: expected string")
    elif expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValueError(f"{path}: expected integer")
    elif expected == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise ValueError(f"{path}: expected number")
    elif expected == "boolean" and not isinstance(value, bool):
        raise ValueError(f"{path}: expected boolean")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value is outside enum")
