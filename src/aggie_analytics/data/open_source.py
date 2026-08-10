from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from importlib import import_module
from typing import Any, Callable, Mapping, Sequence

from .adapters import AcquisitionRequest, FetchResponse


class OptionalDependencyUnavailable(RuntimeError):
    """An explicitly selected optional integration is not installed."""


_SENSITIVE_KEY_FRAGMENTS = ("api_key", "authorization", "credential", "password", "secret", "token")


def _assert_credential_free(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"credential-like field is prohibited at {path}.{key}")
            _assert_credential_free(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_credential_free(child, f"{path}[{index}]")


def _records(value: Any) -> list[dict[str, Any]] | None:
    if hasattr(value, "to_dicts"):
        rows = value.to_dicts()
        return [dict(row) for row in rows]
    if hasattr(value, "to_dict"):
        try:
            rows = value.to_dict(orient="records")
        except TypeError:
            rows = None
        if isinstance(rows, list) and all(isinstance(row, Mapping) for row in rows):
            return [dict(row) for row in rows]
    if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
        return [dict(row) for row in value]
    return None


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(child) for key, child in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_value(child) for child in value]
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    if hasattr(value, "to_dict"):
        try:
            return _json_value(value.to_dict())
        except TypeError:
            pass
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return _json_value(value.item())
    raise TypeError(f"unsupported structured client value: {type(value).__name__}")


def deterministic_json_response(value: Any) -> FetchResponse:
    """Convert client/library output into credential-free deterministic JSON."""

    rows = _records(value)
    normalized = _json_value(rows if rows is not None else value)
    _assert_credential_free(normalized)
    if isinstance(normalized, list):
        row_count = len(normalized)
        schema_fields = tuple(
            sorted({str(key) for row in normalized if isinstance(row, Mapping) for key in row})
        )
    elif isinstance(normalized, Mapping):
        row_count = 1
        schema_fields = tuple(sorted(str(key) for key in normalized))
    else:
        row_count = 1
        schema_fields = ()
    body = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return FetchResponse(
        body=body,
        status_code=200,
        headers={"Content-Type": "application/json"},
        row_count=row_count,
        schema_fields=schema_fields,
    )


@dataclass(frozen=True)
class StructuredClientTransport:
    """Bound an optional client operation to the immutable acquisition contract.

    The caller supplies the concrete operation, keeping credentials and client
    configuration outside the persisted request. Only request identity
    components under ``parameters`` are forwarded.
    """

    operation: Callable[..., Any]
    operation_id: str

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        declared = request.identity_components.get("operation")
        if declared != self.operation_id:
            raise ValueError(f"operation mismatch: expected {self.operation_id!r}, got {declared!r}")
        parameters = request.identity_components.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ValueError("identity component 'parameters' must be a mapping")
        _assert_credential_free(parameters, "parameters")
        return deterministic_json_response(self.operation(**dict(parameters)))


@dataclass(frozen=True)
class OptionalModuleContract:
    module_name: str
    distribution_name: str

    def load(self) -> Any:
        try:
            return import_module(self.module_name)
        except ModuleNotFoundError as exc:
            if exc.name != self.module_name.split(".")[0]:
                raise
            raise OptionalDependencyUnavailable(
                f"install the {self.distribution_name!r} optional dependency"
            ) from exc


SPORTSDATAVERSE = OptionalModuleContract("sportsdataverse.cfb", "sportsdataverse")
CFBD = OptionalModuleContract("cfbd", "source-clients")
OPENMETEO_REQUESTS = OptionalModuleContract("openmeteo_requests", "source-clients")


@dataclass(frozen=True)
class AnalyticalRuntime:
    """Lazy, replaceable access to the admitted analytical stack."""

    def polars(self) -> Any:
        return OptionalModuleContract("polars", "data").load()

    def pandera(self) -> Any:
        return OptionalModuleContract("pandera.polars", "data").load()

    def read_only_duckdb(self, database: str = ":memory:") -> Any:
        duckdb = OptionalModuleContract("duckdb", "data").load()
        if database == ":memory:":
            return duckdb.connect(database=database)
        return duckdb.connect(database=database, read_only=True)


def splink_settings(
    *,
    unique_id_column: str,
    match_columns: Sequence[str],
    blocking_rules: Sequence[str],
) -> dict[str, Any]:
    """Build conservative Splink settings without an automatic-link threshold."""

    columns = tuple(dict.fromkeys(str(value) for value in match_columns))
    if len(columns) < 2:
        raise ValueError("Splink admission requires at least two independent match fields")
    if not blocking_rules:
        raise ValueError("Splink admission requires an explicit bounded blocking rule")
    return {
        "link_type": "dedupe_only",
        "unique_id_column_name": unique_id_column,
        "blocking_rules_to_generate_predictions": list(blocking_rules),
        "comparisons": [{"output_column_name": column} for column in columns],
        "retain_intermediate_calculation_columns": True,
        "retain_matching_columns": True,
    }
