from __future__ import annotations

import re
from typing import Any


class SchemaContractError(ValueError):
    pass


def validate_strict_output_schema(schema: dict[str, Any]) -> None:
    errors: list[str] = []

    def walk(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            errors.append(f"{path}: schema node must be an object")
            return
        node_type = node.get("type")
        types = {node_type} if isinstance(node_type, str) else set(node_type or [])
        if "object" in types:
            properties = node.get("properties")
            required = node.get("required")
            if not isinstance(properties, dict):
                errors.append(f"{path}: object requires properties")
            else:
                if set(required or []) != set(properties):
                    errors.append(f"{path}: every object property must be required")
                for key, value in properties.items():
                    walk(value, f"{path}.properties.{key}")
            if node.get("additionalProperties") is not False:
                errors.append(f"{path}: additionalProperties must be false")
        if "array" in types:
            if "items" not in node:
                errors.append(f"{path}: array requires items")
            else:
                walk(node["items"], f"{path}.items")

    walk(schema, "$")
    if errors:
        raise SchemaContractError("; ".join(errors))


def validate_instance(value: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def matches_type(item: Any, expected: str) -> bool:
        return {
            "null": item is None,
            "boolean": isinstance(item, bool),
            "integer": isinstance(item, int) and not isinstance(item, bool),
            "number": isinstance(item, (int, float)) and not isinstance(item, bool),
            "string": isinstance(item, str),
            "array": isinstance(item, list),
            "object": isinstance(item, dict),
        }.get(expected, False)

    def walk(item: Any, node: dict[str, Any], path: str) -> None:
        expected = node.get("type")
        expected_types = [expected] if isinstance(expected, str) else list(expected or [])
        if expected_types and not any(matches_type(item, kind) for kind in expected_types):
            errors.append(f"{path}: expected {expected_types}, got {type(item).__name__}")
            return
        if "enum" in node and item not in node["enum"]:
            errors.append(f"{path}: value is not in enum")
        if isinstance(item, str):
            if len(item) < int(node.get("minLength", 0)):
                errors.append(f"{path}: string is shorter than minLength")
            if "pattern" in node and re.fullmatch(node["pattern"], item) is None:
                errors.append(f"{path}: string does not match pattern")
        if isinstance(item, dict):
            properties = node.get("properties", {})
            required = set(node.get("required", []))
            missing = required - set(item)
            extra = set(item) - set(properties)
            if missing:
                errors.append(f"{path}: missing required fields {sorted(missing)}")
            if node.get("additionalProperties") is False and extra:
                errors.append(f"{path}: unexpected fields {sorted(extra)}")
            for key in set(item) & set(properties):
                walk(item[key], properties[key], f"{path}.{key}")
        if isinstance(item, list) and "items" in node:
            for index, child in enumerate(item):
                walk(child, node["items"], f"{path}[{index}]")

    walk(value, schema, "$")
    return errors


def evidence_errors(candidate: dict[str, Any], *, capture_sha256: str) -> list[str]:
    errors: list[str] = []
    if candidate.get("source_capture_sha256") != capture_sha256:
        errors.append("candidate source capture identity does not match the governed job")
    for index, fact in enumerate(candidate.get("facts", [])):
        status = fact.get("status")
        evidence = fact.get("evidence", [])
        if status == "SUPPORTED" and not evidence:
            errors.append(f"facts[{index}]: supported fact has no evidence")
        if status != "SUPPORTED" and fact.get("value") is not None:
            errors.append(f"facts[{index}]: abstained/conflicted fact must have null value")
        for locator in evidence:
            if locator.get("source_capture_sha256") != capture_sha256:
                errors.append(f"facts[{index}]: evidence points to a different capture")
    return errors
