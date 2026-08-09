from __future__ import annotations

"""Canonical experiment lineage helpers.

This module is deliberately tool-neutral.  MLflow/Optuna IDs may be attached as
external references, but the Aggie Analytics Engine owns the canonical
experiment/study/tournament identities.
"""

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


VOLATILE_KEYS = frozenset({
    "created_at", "updated_at", "started_at", "finished_at", "duration_seconds",
    "host", "pid", "worker_id", "mlflow_run_id", "optuna_trial_number",
})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
                if str(k) not in VOLATILE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, set):
        return sorted(_normalize(v) for v in value)
    if isinstance(value, float):
        if value == 0.0:
            return 0.0
        return float(format(value, ".17g"))
    return value


def canonical_json(payload: Any) -> str:
    """Return stable, result-independent JSON for identity hashing."""
    return json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(payload: Any) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def content_id(prefix: str, payload: Any, length: int = 24) -> str:
    if not prefix or not prefix.replace("_", "").replace("-", "").isalnum():
        raise ValueError("prefix must be non-empty and identifier-like")
    return f"{prefix}-{content_hash(payload)[:length]}"


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(root: Path, *, exclude: Sequence[str] = ()) -> str:
    excluded = set(exclude)
    rows: list[tuple[str, int, str]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        rows.append((rel, path.stat().st_size, file_sha256(path)))
    return content_hash(rows)


def assert_result_independent_identity(spec: Mapping[str, Any]) -> None:
    forbidden = {
        "metrics", "result", "results", "score", "scores", "rank", "decision",
        "protected_metrics", "promotion_decision",
    }
    present = forbidden.intersection(spec)
    if present:
        raise ValueError(f"experiment identity cannot contain result fields: {sorted(present)}")
