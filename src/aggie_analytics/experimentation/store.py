from __future__ import annotations

"""SQLite-backed local reference store for experiment governance.

This is not a distributed scheduler.  It is a deterministic single-machine
reference implementation suitable for the local-first Phase 1-4 target and for
integration testing.  Canonical JSON payloads are stored alongside immutable IDs.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any, Iterable, Iterator, Mapping

from .lineage import canonical_json, content_id, utc_now


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS experiment_specs (
    experiment_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    spec_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS queue_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    event_index INTEGER NOT NULL,
    state TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,
    previous_event_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(experiment_id) REFERENCES experiment_specs(experiment_id),
    UNIQUE(experiment_id, event_index)
);
CREATE TABLE IF NOT EXISTS result_packets (
    result_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    result_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(experiment_id) REFERENCES experiment_specs(experiment_id),
    UNIQUE(experiment_id, attempt)
);
CREATE TABLE IF NOT EXISTS artifact_records (
    artifact_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    class_name TEXT NOT NULL,
    uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sensitivity TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(experiment_id) REFERENCES experiment_specs(experiment_id)
);
CREATE TABLE IF NOT EXISTS replay_reports (
    replay_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    source_result_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    replay_sha256 TEXT NOT NULL,
    replay_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(experiment_id) REFERENCES experiment_specs(experiment_id),
    FOREIGN KEY(source_result_id) REFERENCES result_packets(result_id)
);
CREATE INDEX IF NOT EXISTS idx_queue_events_experiment ON queue_events(experiment_id, event_index);
CREATE INDEX IF NOT EXISTS idx_result_packets_experiment ON result_packets(experiment_id, attempt);
CREATE INDEX IF NOT EXISTS idx_artifact_records_experiment ON artifact_records(experiment_id, attempt);
"""


@dataclass(frozen=True)
class StoredExperiment:
    experiment_id: str
    payload: Mapping[str, Any]
    created_at: str


class ExperimentStore:
    """A small local evidence store with explicit transactions and append-only events."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def add_experiment(self, spec: Mapping[str, Any]) -> str:
        from .lineage import assert_result_independent_identity, content_hash
        assert_result_independent_identity(spec)
        payload = canonical_json(spec)
        experiment_id = str(spec.get("experiment_id") or content_id("EXP", spec))
        created_at = utc_now()
        spec_hash = content_hash(spec)
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT payload_json FROM experiment_specs WHERE experiment_id=?",
                (experiment_id,),
            ).fetchone()
            if existing:
                if existing["payload_json"] != payload:
                    raise ValueError("experiment_id collision with different canonical spec")
                return experiment_id
            conn.execute(
                "INSERT INTO experiment_specs(experiment_id,payload_json,created_at,spec_sha256) VALUES (?,?,?,?)",
                (experiment_id, payload, created_at, spec_hash),
            )
        return experiment_id

    def get_experiment(self, experiment_id: str) -> StoredExperiment | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT experiment_id,payload_json,created_at FROM experiment_specs WHERE experiment_id=?",
                (experiment_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredExperiment(row["experiment_id"], json.loads(row["payload_json"]), row["created_at"])

    def list_experiments(self, limit: int = 100) -> list[StoredExperiment]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT experiment_id,payload_json,created_at FROM experiment_specs ORDER BY created_at, experiment_id LIMIT ?",
                (limit,),
            ).fetchall()
        return [StoredExperiment(r["experiment_id"], json.loads(r["payload_json"]), r["created_at"]) for r in rows]

    def append_queue_event(self, event: Mapping[str, Any]) -> None:
        required = {
            "experiment_id", "event_index", "state", "actor_role", "reason",
            "event_hash", "previous_event_hash",
        }
        missing = required.difference(event)
        if missing:
            raise ValueError(f"queue event missing {sorted(missing)}")
        with self.connect() as conn:
            last = conn.execute(
                "SELECT event_index,event_hash FROM queue_events WHERE experiment_id=? ORDER BY event_index DESC LIMIT 1",
                (event["experiment_id"],),
            ).fetchone()
            expected_index = 0 if last is None else int(last["event_index"]) + 1
            expected_prev = "" if last is None else str(last["event_hash"])
            if int(event["event_index"]) != expected_index:
                raise ValueError(f"queue event_index must be {expected_index}")
            if str(event["previous_event_hash"]) != expected_prev:
                raise ValueError("queue previous_event_hash does not match append-only chain")
            conn.execute(
                """INSERT INTO queue_events(
                    experiment_id,event_index,state,actor_role,reason,event_hash,previous_event_hash,created_at
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    event["experiment_id"], int(event["event_index"]), event["state"],
                    event["actor_role"], event["reason"], event["event_hash"],
                    event["previous_event_hash"], utc_now(),
                ),
            )

    def queue_history(self, experiment_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM queue_events WHERE experiment_id=? ORDER BY event_index",
                (experiment_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_result(self, result: Mapping[str, Any]) -> str:
        from .lineage import content_hash
        exp = str(result["experiment_id"])
        attempt = int(result.get("attempt", 1))
        if attempt < 1:
            raise ValueError("attempt must be >=1")
        payload = canonical_json(result)
        result_id = str(result.get("result_id") or content_id("RES", {"experiment_id": exp, "attempt": attempt, "payload": result}))
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO result_packets(result_id,experiment_id,attempt,payload_json,result_sha256,created_at) VALUES (?,?,?,?,?,?)",
                (result_id, exp, attempt, payload, content_hash(result), utc_now()),
            )
        return result_id

    def add_artifact(self, *, experiment_id: str, attempt: int, class_name: str, uri: str,
                     sha256: str, size_bytes: int, sensitivity: str = "INTERNAL") -> str:
        if size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        artifact = {
            "experiment_id": experiment_id, "attempt": attempt, "class_name": class_name,
            "uri": uri, "sha256": sha256, "size_bytes": size_bytes, "sensitivity": sensitivity,
        }
        artifact_id = content_id("ART", artifact)
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO artifact_records(
                    artifact_id,experiment_id,attempt,class_name,uri,sha256,size_bytes,sensitivity,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (artifact_id, experiment_id, attempt, class_name, uri, sha256, size_bytes, sensitivity, utc_now()),
            )
        return artifact_id

    def integrity_check(self) -> list[str]:
        findings: list[str] = []
        with self.connect() as conn:
            pragma = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if pragma != "ok":
                findings.append(f"sqlite integrity_check: {pragma}")
            rows = conn.execute(
                """SELECT q.experiment_id,q.event_index,q.previous_event_hash,
                          lag(q.event_hash) OVER(PARTITION BY q.experiment_id ORDER BY q.event_index) AS prior_hash
                   FROM queue_events q"""
            ).fetchall()
            for r in rows:
                if r["event_index"] == 0:
                    if r["previous_event_hash"] != "":
                        findings.append(f"{r['experiment_id']} event0 has previous hash")
                elif r["previous_event_hash"] != r["prior_hash"]:
                    findings.append(f"{r['experiment_id']} event {r['event_index']} broken hash chain")
        return findings
