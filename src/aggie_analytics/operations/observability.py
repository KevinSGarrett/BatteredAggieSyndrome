from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json, re, threading
from typing import Any, Mapping

SENSITIVE_KEY = re.compile(r"(?i)(authorization|cookie|password|passwd|secret|token|api[_-]?key|credential)")
BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}")
CREDENTIAL_ASSIGNMENT = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]{8,}")


def _clean_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    text = BEARER.sub("Bearer [REDACTED]", text)
    text = CREDENTIAL_ASSIGNMENT.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return text[:2048]


def sanitize_metadata(value: Any, *, key: str = "") -> Any:
    """Redact sensitive keys and credential-like values before logging.

    Operational callers should send identifiers/metrics, not raw source payloads.
    This function is a second safety boundary, not permission to log restricted data.
    """
    if key and SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): sanitize_metadata(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_metadata(v) for v in value]
    return _clean_scalar(value)


@dataclass(frozen=True)
class OperationalEvent:
    event: str
    component: str
    level: str = "INFO"
    run_id: str | None = None
    metadata: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        if not self.event or not self.component:
            raise ValueError("event and component are required")
        return {
            "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "level": self.level.upper(),
            "event": self.event,
            "component": self.component,
            "run_id": self.run_id,
            "metadata": sanitize_metadata(dict(self.metadata or {})),
        }


class JsonlEventSink:
    """Append-only JSONL operational event sink for the single-host starter."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def emit(self, record: OperationalEvent | None = None, **kwargs: Any) -> dict[str, Any]:
        record = record or OperationalEvent(**kwargs)
        payload = record.as_dict()
        line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)
        return payload


class MetricRegistry:
    """Small in-process metrics registry; external exporters can adapt later."""
    def __init__(self):
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}

    @staticmethod
    def _name(name: str) -> str:
        if not re.fullmatch(r"[a-zA-Z_:][a-zA-Z0-9_:.-]*", name):
            raise ValueError(f"invalid metric name: {name}")
        return name

    def increment(self, name: str, amount: float = 1.0) -> None:
        name = self._name(name); self._counters[name] = self._counters.get(name, 0.0) + float(amount)

    def gauge(self, name: str, value: float) -> None:
        self._gauges[self._name(name)] = float(value)

    def snapshot(self) -> dict[str, Any]:
        return {"counters": dict(sorted(self._counters.items())), "gauges": dict(sorted(self._gauges.items()))}
