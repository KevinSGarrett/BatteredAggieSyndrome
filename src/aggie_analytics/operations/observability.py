from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import re
import threading
from typing import Any, Mapping

SCHEMA_VERSION = "aggie.operations.observability.v2"
SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|cookie|password|passwd|secret|token|api[_-]?key|credential)"
)
BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}")
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]{8,}"
)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
IDENTITY_FIELDS = (
    "run_id",
    "stage_id",
    "source_id",
    "snapshot_id",
    "entity_id",
    "matrix_id",
    "feature_set_id",
    "model_id",
    "product_id",
    "correlation_id",
)
LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
STATUSES = {
    "OBSERVED",
    "STARTED",
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
    "DEGRADED",
    "HEALTHY",
    "EXPECTED_MISSING",
    "DEFECT",
}
MISSINGNESS_CLASSES = {"NOT_APPLICABLE", "EXPECTED", "DEFECT"}


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _clean_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    text = BEARER.sub("Bearer [REDACTED]", text)
    text = CREDENTIAL_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]", text
    )
    return text[:2048]


def sanitize_metadata(value: Any, *, key: str = "") -> Any:
    """Redact sensitive keys and credential-like values before logging.

    Operational callers must send identifiers and metrics, not raw source payloads.
    This is a second safety boundary, not permission to log restricted data.
    """
    if key and SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): sanitize_metadata(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_metadata(v) for v in value]
    return _clean_scalar(value)


def _identifier(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def _utc_timestamp(value: str | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    else:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _nonnegative_number(value: float | int | None, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class OperationalEvent:
    event: str
    component: str
    level: str = "INFO"
    run_id: str | None = None
    stage_id: str | None = None
    source_id: str | None = None
    snapshot_id: str | None = None
    entity_id: str | None = None
    matrix_id: str | None = None
    feature_set_id: str | None = None
    model_id: str | None = None
    product_id: str | None = None
    correlation_id: str | None = None
    occurred_at_utc: str | None = None
    duration_ms: float | None = None
    count: int | None = None
    status: str = "OBSERVED"
    blocker_code: str | None = None
    missingness: str = "NOT_APPLICABLE"
    metadata: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        if not self.event or not self.component:
            raise ValueError("event and component are required")
        event = _identifier(self.event, "event")
        component = _identifier(self.component, "component")
        level = self.level.upper()
        status = self.status.upper()
        missingness = self.missingness.upper()
        if level not in LEVELS:
            raise ValueError(f"invalid level: {self.level}")
        if status not in STATUSES:
            raise ValueError(f"invalid status: {self.status}")
        if missingness not in MISSINGNESS_CLASSES:
            raise ValueError(f"invalid missingness: {self.missingness}")
        if missingness == "EXPECTED" and status == "DEFECT":
            raise ValueError("expected missingness cannot have DEFECT status")
        if missingness == "DEFECT" and status in {"SUCCEEDED", "EXPECTED_MISSING"}:
            raise ValueError("defect missingness cannot have a success status")
        blocker = _identifier(self.blocker_code, "blocker_code")
        if status == "BLOCKED" and blocker is None:
            raise ValueError("BLOCKED status requires blocker_code")
        if blocker is not None and status not in {"BLOCKED", "DEGRADED", "FAILED"}:
            raise ValueError("blocker_code requires BLOCKED, DEGRADED, or FAILED status")
        if self.count is not None and (
            isinstance(self.count, bool)
            or not isinstance(self.count, int)
            or self.count < 0
        ):
            raise ValueError("count must be a nonnegative integer")

        identities = {
            field: _identifier(getattr(self, field), field) for field in IDENTITY_FIELDS
        }
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "timestamp_utc": _utc_timestamp(self.occurred_at_utc),
            "level": level,
            "event": event,
            "component": component,
            "run_id": identities["run_id"],
            "identities": identities,
            "duration_ms": _nonnegative_number(self.duration_ms, "duration_ms"),
            "count": self.count,
            "status": status,
            "blocker_code": blocker,
            "missingness": missingness,
            "metadata": sanitize_metadata(dict(self.metadata or {})),
        }
        payload["event_identity"] = _canonical_hash(payload)
        return payload


def validate_operational_event(payload: Mapping[str, Any]) -> None:
    """Fail closed on malformed, schema-incompatible, or mutated event payloads."""
    required = {
        "schema_version",
        "timestamp_utc",
        "level",
        "event",
        "component",
        "run_id",
        "identities",
        "duration_ms",
        "count",
        "status",
        "blocker_code",
        "missingness",
        "metadata",
        "event_identity",
    }
    if set(payload) != required:
        raise ValueError("operational event field set mismatch")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("operational event schema mismatch")
    identities = payload["identities"]
    if not isinstance(identities, Mapping) or set(identities) != set(IDENTITY_FIELDS):
        raise ValueError("operational event identities mismatch")
    rebuilt = OperationalEvent(
        event=payload["event"],
        component=payload["component"],
        level=payload["level"],
        occurred_at_utc=payload["timestamp_utc"],
        duration_ms=payload["duration_ms"],
        count=payload["count"],
        status=payload["status"],
        blocker_code=payload["blocker_code"],
        missingness=payload["missingness"],
        metadata=payload["metadata"],
        **dict(identities),
    ).as_dict()
    if payload["run_id"] != identities["run_id"]:
        raise ValueError("top-level run_id disagrees with identities")
    if dict(payload) != rebuilt:
        raise ValueError("operational event content identity mismatch")


class JsonlEventSink:
    """Append-only JSONL operational event sink for the single-host starter."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def emit(
        self, record: OperationalEvent | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        record = record or OperationalEvent(**kwargs)
        payload = record.as_dict()
        validate_operational_event(payload)
        line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
        return payload


class MetricRegistry:
    """Thread-safe in-process metrics registry; external exporters can adapt later."""

    def __init__(self):
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _name(name: str) -> str:
        if not re.fullmatch(r"[a-zA-Z_:][a-zA-Z0-9_:.-]*", name):
            raise ValueError(f"invalid metric name: {name}")
        return name

    def increment(self, name: str, amount: float = 1.0) -> None:
        name = self._name(name)
        value = _nonnegative_number(amount, "counter increment")
        assert value is not None
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value

    def gauge(self, name: str, value: float) -> None:
        numeric = _nonnegative_number(value, "gauge value")
        assert numeric is not None
        with self._lock:
            self._gauges[self._name(name)] = numeric

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(sorted(self._counters.items())),
                "gauges": dict(sorted(self._gauges.items())),
            }

    def observed_snapshot(
        self,
        *,
        component: str,
        identities: Mapping[str, str | None],
        observed_at_utc: str,
        status: str,
        expected_missing_count: int = 0,
        defect_count: int = 0,
        blockers: list[str] | tuple[str, ...] = (),
        max_age_seconds: int = 900,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if set(identities) != set(IDENTITY_FIELDS):
            raise ValueError("metric snapshot requires the complete identity field set")
        normalized_identities = {
            field: _identifier(identities[field], field) for field in IDENTITY_FIELDS
        }
        normalized_status = status.upper()
        if normalized_status not in {"HEALTHY", "DEGRADED", "BLOCKED"}:
            raise ValueError("invalid health status")
        counts = {
            "expected_missing": expected_missing_count,
            "defect": defect_count,
        }
        for field, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} count must be a nonnegative integer")
        if not isinstance(max_age_seconds, int) or max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be a positive integer")
        normalized_blockers = [_identifier(value, "blocker") for value in blockers]
        if normalized_status == "BLOCKED" and not normalized_blockers:
            raise ValueError("BLOCKED health requires at least one blocker")
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "snapshot_type": "METRIC_HEALTH",
            "observed_at_utc": _utc_timestamp(observed_at_utc),
            "component": _identifier(component, "component"),
            "status": normalized_status,
            "identities": normalized_identities,
            "missingness_counts": counts,
            "blockers": normalized_blockers,
            "freshness": {"max_age_seconds": max_age_seconds},
            "metrics": self.snapshot(),
            "metadata": sanitize_metadata(dict(metadata or {})),
        }
        payload["snapshot_identity"] = _canonical_hash(payload)
        return payload


def validate_metric_snapshot(
    payload: Mapping[str, Any], *, now_utc: str | None = None
) -> None:
    """Validate identity, schema, freshness, health, metrics, and redaction shape."""
    required = {
        "schema_version",
        "snapshot_type",
        "observed_at_utc",
        "component",
        "status",
        "identities",
        "missingness_counts",
        "blockers",
        "freshness",
        "metrics",
        "metadata",
        "snapshot_identity",
    }
    if set(payload) != required or payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("metric snapshot schema or field set mismatch")
    if payload["snapshot_type"] != "METRIC_HEALTH":
        raise ValueError("metric snapshot type mismatch")
    canonical = dict(payload)
    claimed = canonical.pop("snapshot_identity")
    if claimed != _canonical_hash(canonical):
        raise ValueError("metric snapshot content identity mismatch")
    identities = payload["identities"]
    if not isinstance(identities, Mapping) or set(identities) != set(IDENTITY_FIELDS):
        raise ValueError("metric snapshot identities mismatch")
    for field in IDENTITY_FIELDS:
        _identifier(identities[field], field)
    _identifier(payload["component"], "component")
    status = payload["status"]
    blockers = payload["blockers"]
    if status not in {"HEALTHY", "DEGRADED", "BLOCKED"}:
        raise ValueError("metric snapshot health status mismatch")
    if not isinstance(blockers, list):
        raise ValueError("metric snapshot blockers must be a list")
    for blocker in blockers:
        _identifier(blocker, "blocker")
    if status == "BLOCKED" and not blockers:
        raise ValueError("blocked metric snapshot has no blocker")
    counts = payload["missingness_counts"]
    if not isinstance(counts, Mapping) or set(counts) != {"expected_missing", "defect"}:
        raise ValueError("metric snapshot missingness counts mismatch")
    for value in counts.values():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("metric snapshot missingness count invalid")
    metrics = payload["metrics"]
    if not isinstance(metrics, Mapping) or set(metrics) != {"counters", "gauges"}:
        raise ValueError("metric snapshot metrics mismatch")
    for group in metrics.values():
        if not isinstance(group, Mapping):
            raise ValueError("metric group must be an object")
        for name, value in group.items():
            MetricRegistry._name(name)
            _nonnegative_number(value, "metric value")
    freshness = payload["freshness"]
    if not isinstance(freshness, Mapping) or set(freshness) != {"max_age_seconds"}:
        raise ValueError("metric snapshot freshness mismatch")
    max_age = freshness["max_age_seconds"]
    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age <= 0:
        raise ValueError("metric snapshot max age invalid")
    observed = datetime.fromisoformat(payload["observed_at_utc"].replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("metric snapshot timestamp must be timezone-aware")
    if now_utc is not None:
        now = datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
        if now.tzinfo is None:
            raise ValueError("consumer time must be timezone-aware")
        age = (now.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
        if age < 0 or age > max_age:
            raise ValueError("metric snapshot is future-dated or stale")
