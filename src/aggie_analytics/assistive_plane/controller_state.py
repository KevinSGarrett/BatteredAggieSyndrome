from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 7
PRE_ROUTING_DISPOSITIONS = frozenset(
    {
        "ROUTED_TO_ASSISTIVE_PLANE",
        "DETERMINISTIC_LOCAL_TOOL_REQUIRED",
        "CODEX_AUTHORITY_ONLY",
        "PROVIDER_ROUTE_EMPIRICALLY_REJECTED",
        "PROVIDER_SECURITY_INELIGIBLE",
        "PROVIDER_BUDGET_EXHAUSTED",
        "USER_EXPLICITLY_RESERVED_FOR_CODEX",
        "EMERGENCY_PIPELINE_REPAIR",
        "UNJUSTIFIED_DIRECT_EXECUTION",
    }
)
ALLOWED_STATES = {
    "DISCOVERED",
    "ELIGIBLE",
    "ADMITTED",
    "LEASED",
    "DISPATCHED",
    "RESULT_RECEIVED",
    "VALIDATED",
    "REVIEWED",
    "SETTLED",
    "CLEANED",
    "CLOSED",
    "RETRY_WAIT",
    "RUNNING",
    "VALIDATING",
    "REVIEW",
    "ACCEPTED",
    "MODIFIED",
    "REVIEW_ONLY",
    "QUARANTINED",
    "REJECTED",
    "FAILED",
    "CANCELLED",
    "DEAD_LETTER",
}
TERMINAL_STATES = {
    "CLOSED", "ACCEPTED", "MODIFIED", "REVIEW_ONLY", "QUARANTINED", "REJECTED",
    "FAILED", "CANCELLED", "DEAD_LETTER",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_rfc3339(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def usd_cents(value: str | Decimal) -> int:
    amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError("NEGATIVE_BUDGET_AMOUNT")
    return int(amount * 100)


def process_is_live(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # On Windows, os.kill(pid, 0) calls TerminateProcess rather than acting
        # as the non-mutating POSIX existence probe. Query a minimal process
        # handle instead and fail closed when Windows cannot prove absence.
        import ctypes

        process_query_limited_information = 0x1000
        error_invalid_parameter = 87
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() != error_invalid_parameter
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def owner_pid(owner_id: str) -> int:
    match = re.fullmatch(r"[^:]+:([1-9][0-9]*):[0-9a-fA-F]{32}", owner_id)
    if match is None:
        raise RuntimeError("CONTROLLER_RECOVERY_OWNER_ID_FORMAT_INVALID")
    return int(match.group(1))


class LeaderLock:
    """Cross-platform nonblocking process lock for the single controller leader."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: Any | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            handle.close()
            raise RuntimeError("CONTROLLER_LEADER_LOCK_HELD") from exc
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._handle = None

    def __enter__(self) -> "LeaderLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


@dataclass(frozen=True)
class BudgetSnapshot:
    provider: str
    hard_limit_cents: int
    released_cents: int
    settled_cents: int
    reserved_cents: int

    @property
    def available_cents(self) -> int:
        return min(self.hard_limit_cents, self.released_cents) - self.settled_cents - self.reserved_cents


class ControllerState:
    def __init__(self, database: Path) -> None:
        self.database = database

    def connect(self) -> sqlite3.Connection:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        connection = self.connect()
        try:
            mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(mode).lower() != "wal":
                raise RuntimeError("SQLITE_WAL_NOT_ENABLED")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leader_lease (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    owner_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    build_commit TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_units (
                    work_unit_id TEXT PRIMARY KEY,
                    identity_sha256 TEXT NOT NULL,
                    jira_identity TEXT NOT NULL,
                    effort_points INTEGER NOT NULL CHECK (effort_points IN (1,2,3,5,8)),
                    current_state TEXT NOT NULL,
                    route_identity TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS work_unit_revisions (
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    identity_sha256 TEXT NOT NULL,
                    jira_identity TEXT NOT NULL,
                    effort_points INTEGER NOT NULL CHECK (effort_points IN (1,2,3,5,8)),
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    superseded_at TEXT,
                    superseded_by_sha256 TEXT,
                    PRIMARY KEY (work_unit_id, identity_sha256)
                );
                CREATE TABLE IF NOT EXISTS work_unit_revision_observations (
                    work_unit_id TEXT NOT NULL,
                    identity_sha256 TEXT NOT NULL,
                    inventory_sha256 TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY (work_unit_id, identity_sha256, inventory_sha256),
                    FOREIGN KEY (work_unit_id, identity_sha256)
                        REFERENCES work_unit_revisions(work_unit_id, identity_sha256)
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_sha256 TEXT,
                    actor TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    unit_version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS budgets (
                    provider TEXT PRIMARY KEY,
                    hard_limit_cents INTEGER NOT NULL,
                    released_cents INTEGER NOT NULL,
                    settled_cents INTEGER NOT NULL DEFAULT 0,
                    authorization_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK (hard_limit_cents >= 0 AND released_cents >= 0 AND settled_cents >= 0),
                    CHECK (released_cents <= hard_limit_cents AND settled_cents <= hard_limit_cents)
                );
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL REFERENCES budgets(provider),
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    estimated_cents INTEGER NOT NULL CHECK (estimated_cents >= 0),
                    actual_cents INTEGER,
                    status TEXT NOT NULL CHECK (status IN ('RESERVED','SETTLED','RELEASED')),
                    created_at TEXT NOT NULL,
                    settled_at TEXT
                );
                CREATE TABLE IF NOT EXISTS scheduler_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    inventory_sha256 TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    eligible_units INTEGER NOT NULL,
                    dispatched_units INTEGER NOT NULL,
                    no_change INTEGER NOT NULL CHECK (no_change IN (0,1)),
                    result TEXT NOT NULL,
                    evidence_sha256 TEXT
                );
                CREATE TABLE IF NOT EXISTS idle_intervals (
                    idle_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    inventory_sha256 TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    last_observed_at TEXT NOT NULL,
                    resolved_at TEXT,
                    evidence_sha256 TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_idle_interval_per_unit
                    ON idle_intervals(work_unit_id) WHERE resolved_at IS NULL;
                CREATE TABLE IF NOT EXISTS controller_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_dependencies (
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    dependency_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY (work_unit_id, dependency_id)
                );
                CREATE TABLE IF NOT EXISTS work_leases (
                    lease_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    owner_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('ACTIVE','CLOSED','ABANDONED'))
                );
                CREATE TABLE IF NOT EXISTS dispatch_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    provider TEXT NOT NULL,
                    route_identity TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    request_sha256 TEXT,
                    result_sha256 TEXT,
                    error_code TEXT
                );
                CREATE TABLE IF NOT EXISTS provider_runs (
                    provider_run_id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL REFERENCES dispatch_attempts(attempt_id),
                    provider TEXT NOT NULL,
                    remote_identity TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    response_sha256 TEXT,
                    status TEXT NOT NULL,
                    actual_cost_cents INTEGER NOT NULL DEFAULT 0,
                    resource_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS retry_records (
                    retry_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    prior_attempt_id TEXT REFERENCES dispatch_attempts(attempt_id),
                    reason TEXT NOT NULL,
                    eligible_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS route_readiness_observations (
                    observation_id TEXT PRIMARY KEY,
                    route_identity TEXT NOT NULL,
                    state TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS execution_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    attempt_id TEXT REFERENCES dispatch_attempts(attempt_id),
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS validation_results (
                    validation_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    attempt_id TEXT NOT NULL REFERENCES dispatch_attempts(attempt_id),
                    validator TEXT NOT NULL,
                    result TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    attempt_id TEXT NOT NULL REFERENCES dispatch_attempts(attempt_id),
                    reviewer TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    review_seconds REAL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS useful_work_evidence (
                    useful_work_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    attempt_id TEXT NOT NULL UNIQUE REFERENCES dispatch_attempts(attempt_id),
                    bas_decision_unit TEXT NOT NULL,
                    downstream_consumer TEXT NOT NULL,
                    delegation_preference_reason TEXT NOT NULL,
                    input_documents INTEGER NOT NULL CHECK (input_documents >= 0),
                    input_bytes INTEGER NOT NULL CHECK (input_bytes >= 0),
                    input_records INTEGER NOT NULL CHECK (input_records >= 0),
                    candidate_count INTEGER NOT NULL CHECK (candidate_count >= 0),
                    provider TEXT NOT NULL,
                    model TEXT,
                    task_format TEXT NOT NULL,
                    route_identity TEXT NOT NULL,
                    wall_seconds REAL NOT NULL CHECK (wall_seconds >= 0),
                    compute_json TEXT NOT NULL,
                    direct_baseline_seconds REAL,
                    orchestration_seconds REAL NOT NULL CHECK (orchestration_seconds >= 0),
                    review_seconds REAL NOT NULL CHECK (review_seconds >= 0),
                    disposition TEXT NOT NULL,
                    validated INTEGER NOT NULL CHECK (validated IN (0,1)),
                    reviewed INTEGER NOT NULL CHECK (reviewed IN (0,1)),
                    downstream_consumed INTEGER NOT NULL CHECK (downstream_consumed IN (0,1)),
                    changed_project_artifact INTEGER NOT NULL CHECK (changed_project_artifact IN (0,1)),
                    consumed_artifact_identity TEXT,
                    net_time_saved_seconds REAL NOT NULL,
                    duplicated_by_codex INTEGER NOT NULL CHECK (duplicated_by_codex IN (0,1)),
                    accepted_useful_offload INTEGER NOT NULL CHECK (accepted_useful_offload IN (0,1)),
                    evidence_sha256 TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS downstream_review_dispositions (
                    downstream_review_id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL UNIQUE REFERENCES dispatch_attempts(attempt_id),
                    disposition TEXT NOT NULL CHECK (disposition IN ('ACCEPTED','MODIFIED','REJECTED','UNUSED')),
                    downstream_consumer TEXT NOT NULL,
                    consumed_artifact_identity TEXT,
                    changed_project_artifact INTEGER NOT NULL CHECK (changed_project_artifact IN (0,1)),
                    net_time_saved_seconds REAL NOT NULL,
                    duplicated_by_codex INTEGER NOT NULL CHECK (duplicated_by_codex IN (0,1)),
                    review_seconds REAL NOT NULL CHECK (review_seconds >= 0),
                    reason TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cleanup_actions (
                    cleanup_id TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL REFERENCES work_units(work_unit_id),
                    attempt_id TEXT NOT NULL REFERENCES dispatch_attempts(attempt_id),
                    action TEXT NOT NULL,
                    bytes_removed INTEGER NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    work_unit_id TEXT REFERENCES work_units(work_unit_id),
                    attempt_id TEXT REFERENCES dispatch_attempts(attempt_id),
                    finding TEXT NOT NULL,
                    evidence_sha256 TEXT,
                    opened_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE TABLE IF NOT EXISTS reconciliation_records (
                    reconciliation_id TEXT PRIMARY KEY,
                    work_unit_id TEXT REFERENCES work_units(work_unit_id),
                    jira_identity TEXT,
                    git_identity TEXT,
                    pr_identity TEXT,
                    result_identity TEXT,
                    result TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pre_routing_decisions (
                    decision_sha256 TEXT PRIMARY KEY,
                    work_unit_id TEXT NOT NULL,
                    jira_identity TEXT,
                    repository_identity TEXT NOT NULL,
                    source_commit TEXT NOT NULL,
                    task_category TEXT NOT NULL,
                    effort_points INTEGER NOT NULL CHECK (effort_points IN (1,2,3,5,8)),
                    candidate_routes_json TEXT NOT NULL,
                    selected_route TEXT,
                    route_identity TEXT,
                    budget_admission TEXT NOT NULL,
                    packet_identity TEXT,
                    lease_identity TEXT,
                    disposition TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_pre_routing_decision_per_work_identity
                    ON pre_routing_decisions(work_unit_id, repository_identity, source_commit, task_category);
                CREATE TABLE IF NOT EXISTS operational_conditions (
                    condition_id TEXT PRIMARY KEY,
                    finding TEXT NOT NULL,
                    first_observed_at TEXT NOT NULL,
                    last_observed_at TEXT NOT NULL,
                    threshold_seconds INTEGER NOT NULL,
                    evidence_sha256 TEXT,
                    incident_opened INTEGER NOT NULL DEFAULT 0 CHECK (incident_opened IN (0,1)),
                    resolved_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_work_lease_per_unit
                    ON work_leases(work_unit_id) WHERE status='ACTIVE';
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO work_unit_revisions("
                "work_unit_id,identity_sha256,jira_identity,effort_points,first_seen_at,last_seen_at) "
                "SELECT work_unit_id,identity_sha256,jira_identity,effort_points,created_at,updated_at FROM work_units"
            )
            existing = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if existing and int(existing[0]) > SCHEMA_VERSION:
                raise RuntimeError("CONTROLLER_SCHEMA_NEWER_THAN_CODE")
            connection.execute(
                "INSERT INTO metadata(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            connection.execute(
                "UPDATE incidents SET resolved_at=? WHERE resolved_at IS NULL AND work_unit_id IN "
                "(SELECT work_unit_id FROM work_units WHERE current_state IN "
                "('CLOSED','ACCEPTED','MODIFIED','REVIEW_ONLY','QUARANTINED','REJECTED','FAILED','CANCELLED','DEAD_LETTER'))",
                (rfc3339(utc_now()),),
            )
            connection.commit()
        finally:
            connection.close()

    def record_pre_routing_decision(
        self,
        *,
        decision: dict[str, Any],
        now: datetime | None = None,
    ) -> str:
        """Persist the immutable before-work routing interlock decision."""
        required = {
            "work_unit_id",
            "repository_identity",
            "source_commit",
            "task_category",
            "effort_points",
            "candidate_routes",
            "budget_admission",
            "disposition",
            "reason_code",
            "evidence_sha256",
            "discovered_at",
        }
        missing = sorted(required - set(decision))
        if missing:
            raise ValueError("PRE_ROUTING_DECISION_FIELDS_MISSING:" + ",".join(missing))
        disposition = str(decision["disposition"])
        if disposition not in PRE_ROUTING_DISPOSITIONS:
            raise ValueError("PRE_ROUTING_DISPOSITION_INVALID")
        routes = decision["candidate_routes"]
        if not isinstance(routes, list) or not all(isinstance(item, str) and item for item in routes):
            raise ValueError("PRE_ROUTING_CANDIDATE_ROUTES_INVALID")
        effort_points = int(decision["effort_points"])
        if effort_points not in {1, 2, 3, 5, 8}:
            raise ValueError("INVALID_PRE_ROUTING_EFFORT")
        source_commit = str(decision["source_commit"])
        evidence_sha256 = str(decision["evidence_sha256"])
        if len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit):
            raise ValueError("PRE_ROUTING_SOURCE_COMMIT_INVALID")
        if len(evidence_sha256) != 64 or any(character not in "0123456789abcdef" for character in evidence_sha256):
            raise ValueError("PRE_ROUTING_EVIDENCE_IDENTITY_INVALID")
        canonical = {
            key: decision.get(key)
            for key in (
                "work_unit_id",
                "jira_identity",
                "repository_identity",
                "source_commit",
                "task_category",
                "effort_points",
                "candidate_routes",
                "selected_route",
                "route_identity",
                "budget_admission",
                "packet_identity",
                "lease_identity",
                "disposition",
                "reason_code",
                "evidence_sha256",
                "discovered_at",
            )
        }
        decision_sha256 = hashlib.sha256(
            (json.dumps(canonical, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).hexdigest()
        stamp = rfc3339(now or utc_now())
        values = (
            decision_sha256,
            str(canonical["work_unit_id"]),
            canonical["jira_identity"],
            str(canonical["repository_identity"]),
            source_commit,
            str(canonical["task_category"]),
            effort_points,
            json.dumps(routes, sort_keys=True, separators=(",", ":")),
            canonical["selected_route"],
            canonical["route_identity"],
            str(canonical["budget_admission"]),
            canonical["packet_identity"],
            canonical["lease_identity"],
            disposition,
            str(canonical["reason_code"]),
            evidence_sha256,
            str(canonical["discovered_at"]),
            stamp,
        )
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT decision_sha256 FROM pre_routing_decisions WHERE "
                "work_unit_id=? AND repository_identity=? AND source_commit=? AND task_category=?",
                (values[1], values[3], values[4], values[5]),
            ).fetchone()
            if existing is not None and existing["decision_sha256"] != decision_sha256:
                raise RuntimeError("PRE_ROUTING_DECISION_IMMUTABILITY_CONFLICT")
            connection.execute(
                "INSERT OR IGNORE INTO pre_routing_decisions("
                "decision_sha256,work_unit_id,jira_identity,repository_identity,source_commit,"
                "task_category,effort_points,candidate_routes_json,selected_route,route_identity,"
                "budget_admission,packet_identity,lease_identity,disposition,reason_code,"
                "evidence_sha256,discovered_at,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                values,
            )
            if disposition == "UNJUSTIFIED_DIRECT_EXECUTION":
                incident_id = hashlib.sha256(
                    f"P0_UNJUSTIFIED_DIRECT_EXECUTION:{decision_sha256}".encode("utf-8")
                ).hexdigest()
                connection.execute(
                    "INSERT OR IGNORE INTO incidents(incident_id,work_unit_id,finding,evidence_sha256,opened_at) "
                    "VALUES(?,?,?,?,?)",
                    (
                        incident_id,
                        None,
                        "P0_UNJUSTIFIED_DIRECT_EXECUTION:" + str(canonical["work_unit_id"]),
                        evidence_sha256,
                        stamp,
                    ),
                )
        return decision_sha256

    def observe_operational_condition(
        self,
        *,
        condition_id: str,
        finding: str,
        threshold_seconds: int,
        evidence_sha256: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Track a persistent fault and open one incident after its SLO is exceeded."""
        if threshold_seconds < 0:
            raise ValueError("OPERATIONAL_CONDITION_THRESHOLD_INVALID")
        stamp_value = now or utc_now()
        stamp = rfc3339(stamp_value)
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM operational_conditions WHERE condition_id=?",
                (condition_id,),
            ).fetchone()
            if row is None or row["resolved_at"] is not None:
                connection.execute(
                    "INSERT INTO operational_conditions(condition_id,finding,first_observed_at,last_observed_at,"
                    "threshold_seconds,evidence_sha256,incident_opened,resolved_at) VALUES(?,?,?,?,?,?,0,NULL) "
                    "ON CONFLICT(condition_id) DO UPDATE SET finding=excluded.finding,"
                    "first_observed_at=excluded.first_observed_at,last_observed_at=excluded.last_observed_at,"
                    "threshold_seconds=excluded.threshold_seconds,evidence_sha256=excluded.evidence_sha256,"
                    "incident_opened=0,resolved_at=NULL",
                    (condition_id, finding, stamp, stamp, threshold_seconds, evidence_sha256),
                )
                first_observed = stamp_value
                incident_opened = False
            else:
                connection.execute(
                    "UPDATE operational_conditions SET finding=?,last_observed_at=?,threshold_seconds=?,"
                    "evidence_sha256=? WHERE condition_id=?",
                    (finding, stamp, threshold_seconds, evidence_sha256, condition_id),
                )
                first_observed = parse_rfc3339(str(row["first_observed_at"]))
                incident_opened = bool(row["incident_opened"])
            elapsed = max(0.0, (stamp_value - first_observed).total_seconds())
            if elapsed >= threshold_seconds and not incident_opened:
                incident_id = hashlib.sha256(f"P0:{condition_id}:{first_observed}".encode("utf-8")).hexdigest()
                connection.execute(
                    "INSERT OR IGNORE INTO incidents(incident_id,finding,evidence_sha256,opened_at) VALUES(?,?,?,?)",
                    (incident_id, finding, evidence_sha256, stamp),
                )
                connection.execute(
                    "UPDATE operational_conditions SET incident_opened=1 WHERE condition_id=?",
                    (condition_id,),
                )
                return True
        return False

    def resolve_operational_conditions(
        self,
        active_condition_ids: set[str],
        *,
        managed_prefixes: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> None:
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT condition_id FROM operational_conditions WHERE resolved_at IS NULL"
            ).fetchall()
            for row in rows:
                condition_id = str(row["condition_id"])
                if managed_prefixes and not condition_id.startswith(managed_prefixes):
                    continue
                if condition_id not in active_condition_ids:
                    connection.execute(
                        "UPDATE operational_conditions SET resolved_at=? WHERE condition_id=?",
                        (stamp, condition_id),
                    )
                    connection.execute(
                        "UPDATE incidents SET resolved_at=? WHERE resolved_at IS NULL AND finding LIKE ?",
                        (stamp, "%" + condition_id + "%"),
                    )

    def acquire_leader(self, owner_id: str, build_commit: str, *, now: datetime | None = None, ttl_seconds: int = 120) -> None:
        moment = now or utc_now()
        expires = moment + timedelta(seconds=ttl_seconds)
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM leader_lease WHERE singleton=1").fetchone()
            if row and parse_rfc3339(row["expires_at"]) > moment and row["owner_id"] != owner_id:
                raise RuntimeError("CONTROLLER_DATABASE_LEADER_ACTIVE")
            connection.execute(
                "INSERT INTO leader_lease(singleton,owner_id,acquired_at,heartbeat_at,expires_at,build_commit) "
                "VALUES(1,?,?,?,?,?) ON CONFLICT(singleton) DO UPDATE SET "
                "owner_id=excluded.owner_id,acquired_at=excluded.acquired_at,heartbeat_at=excluded.heartbeat_at,"
                "expires_at=excluded.expires_at,build_commit=excluded.build_commit",
                (owner_id, rfc3339(moment), rfc3339(moment), rfc3339(expires), build_commit),
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key,value) VALUES(?,?)",
                ("release_epoch:" + build_commit, rfc3339(moment)),
            )

    def heartbeat(self, owner_id: str, *, now: datetime | None = None, ttl_seconds: int = 120) -> None:
        moment = now or utc_now()
        with self.transaction() as connection:
            result = connection.execute(
                "UPDATE leader_lease SET heartbeat_at=?,expires_at=? WHERE singleton=1 AND owner_id=?",
                (rfc3339(moment), rfc3339(moment + timedelta(seconds=ttl_seconds)), owner_id),
            )
            if result.rowcount != 1:
                raise RuntimeError("CONTROLLER_LEADER_OWNERSHIP_LOST")

    def release_leader(self, owner_id: str) -> None:
        """Release only the caller's lease during a graceful shutdown."""
        with self.transaction() as connection:
            result = connection.execute(
                "DELETE FROM leader_lease WHERE singleton=1 AND owner_id=?",
                (owner_id,),
            )
            if result.rowcount != 1:
                raise RuntimeError("CONTROLLER_LEADER_OWNERSHIP_LOST")

    def release_orphaned_leader(
        self,
        *,
        expected_owner_id: str,
        expected_build_commit: str,
        expected_owner_pid: int,
        recovery_evidence_sha256: str,
        now: datetime | None = None,
    ) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", recovery_evidence_sha256) is None:
            raise ValueError("RECOVERY_EVIDENCE_IDENTITY_INVALID")
        if re.fullmatch(r"[0-9a-f]{40}", expected_build_commit) is None:
            raise ValueError("RECOVERY_BUILD_IDENTITY_INVALID")
        bound_owner_pid = owner_pid(expected_owner_id)
        if bound_owner_pid != expected_owner_pid:
            raise RuntimeError("CONTROLLER_RECOVERY_OWNER_PID_MISMATCH")
        if process_is_live(expected_owner_pid):
            raise RuntimeError("CONTROLLER_RECOVERY_OWNER_PROCESS_LIVE")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            lease = connection.execute("SELECT * FROM leader_lease WHERE singleton=1").fetchone()
            if lease is None:
                raise RuntimeError("CONTROLLER_RECOVERY_LEASE_MISSING")
            if lease["owner_id"] != expected_owner_id or lease["build_commit"] != expected_build_commit:
                raise RuntimeError("CONTROLLER_RECOVERY_LEASE_MISMATCH")
            removed = connection.execute(
                "DELETE FROM leader_lease WHERE singleton=1 AND owner_id=? AND build_commit=?",
                (expected_owner_id, expected_build_commit),
            )
            if removed.rowcount != 1:
                raise RuntimeError("CONTROLLER_RECOVERY_OWNERSHIP_LOST")
            payload = {
                "expected_owner_id": expected_owner_id,
                "expected_build_commit": expected_build_commit,
                "expected_owner_pid": expected_owner_pid,
                "recovery_evidence_sha256": recovery_evidence_sha256,
                "lease_acquired_at": lease["acquired_at"],
                "lease_heartbeat_at": lease["heartbeat_at"],
                "lease_expires_at": lease["expires_at"],
            }
            connection.execute(
                "INSERT INTO controller_events(event_type,payload_json,occurred_at) VALUES(?,?,?)",
                ("CONTROLLER_ORPHAN_LEASE_RECOVERED", json.dumps(payload, sort_keys=True, separators=(",", ":")), stamp),
            )

    def register_work_unit(
        self,
        *,
        work_unit_id: str,
        identity_sha256: str,
        jira_identity: str,
        effort_points: int,
        actor: str,
        inventory_sha256: str | None = None,
        now: datetime | None = None,
    ) -> None:
        if effort_points not in {1, 2, 3, 5, 8}:
            raise ValueError("INVALID_PRE_ROUTING_EFFORT")
        if re.fullmatch(r"[0-9a-f]{64}", identity_sha256) is None:
            raise ValueError("WORK_UNIT_IDENTITY_INVALID")
        if inventory_sha256 is not None and re.fullmatch(r"[0-9a-f]{64}", inventory_sha256) is None:
            raise ValueError("INVENTORY_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM work_units WHERE work_unit_id=?", (work_unit_id,)).fetchone()
            if row:
                expected = (identity_sha256, jira_identity, effort_points)
                observed = (row["identity_sha256"], row["jira_identity"], row["effort_points"])
                if observed == expected:
                    connection.execute(
                        "UPDATE work_unit_revisions SET last_seen_at=? WHERE work_unit_id=? AND identity_sha256=?",
                        (stamp, work_unit_id, identity_sha256),
                    )
                    self._record_revision_observation(
                        connection, work_unit_id, identity_sha256, inventory_sha256, stamp
                    )
                    return
                consequential_transition = connection.execute(
                    "SELECT 1 FROM transitions WHERE work_unit_id=? "
                    "AND reason NOT IN ('REGISTERED','INVENTORY_REVISION_SUPERSEDED') LIMIT 1",
                    (work_unit_id,),
                ).fetchone()
                reservation = connection.execute(
                    "SELECT 1 FROM reservations WHERE work_unit_id=? LIMIT 1",
                    (work_unit_id,),
                ).fetchone()
                if (
                    row["current_state"] != "DISCOVERED"
                    or row["route_identity"] is not None
                    or consequential_transition is not None
                    or reservation is not None
                ):
                    raise RuntimeError("IMMUTABLE_ACTIVE_WORK_UNIT_IDENTITY_CONFLICT")
                prior_revision = connection.execute(
                    "SELECT 1 FROM work_unit_revisions WHERE work_unit_id=? AND identity_sha256=?",
                    (work_unit_id, identity_sha256),
                ).fetchone()
                if prior_revision is not None:
                    raise RuntimeError("WORK_UNIT_REVISION_REAPPEARANCE_CONFLICT")
                version = int(row["version"]) + 1
                connection.execute(
                    "UPDATE idle_intervals SET resolved_at=?,last_observed_at=? "
                    "WHERE work_unit_id=? AND resolved_at IS NULL",
                    (stamp, stamp, work_unit_id),
                )
                connection.execute(
                    "UPDATE work_unit_revisions SET superseded_at=?,superseded_by_sha256=? "
                    "WHERE work_unit_id=? AND identity_sha256=? AND superseded_at IS NULL",
                    (stamp, identity_sha256, work_unit_id, row["identity_sha256"]),
                )
                connection.execute(
                    "UPDATE work_units SET identity_sha256=?,jira_identity=?,effort_points=?,updated_at=?,version=? "
                    "WHERE work_unit_id=?",
                    (identity_sha256, jira_identity, effort_points, stamp, version, work_unit_id),
                )
                connection.execute(
                    "INSERT INTO work_unit_revisions("
                    "work_unit_id,identity_sha256,jira_identity,effort_points,first_seen_at,last_seen_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (work_unit_id, identity_sha256, jira_identity, effort_points, stamp, stamp),
                )
                connection.execute(
                    "INSERT INTO transitions(work_unit_id,from_state,to_state,reason,evidence_sha256,actor,occurred_at,unit_version) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (
                        work_unit_id,
                        "DISCOVERED",
                        "DISCOVERED",
                        "INVENTORY_REVISION_SUPERSEDED",
                        row["identity_sha256"],
                        actor,
                        stamp,
                        version,
                    ),
                )
                self._record_revision_observation(
                    connection, work_unit_id, identity_sha256, inventory_sha256, stamp
                )
                return
            connection.execute(
                "INSERT INTO work_units(work_unit_id,identity_sha256,jira_identity,effort_points,current_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (work_unit_id, identity_sha256, jira_identity, effort_points, "DISCOVERED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO work_unit_revisions("
                "work_unit_id,identity_sha256,jira_identity,effort_points,first_seen_at,last_seen_at) "
                "VALUES(?,?,?,?,?,?)",
                (work_unit_id, identity_sha256, jira_identity, effort_points, stamp, stamp),
            )
            self._record_revision_observation(
                connection, work_unit_id, identity_sha256, inventory_sha256, stamp
            )
            connection.execute(
                "INSERT INTO transitions(work_unit_id,from_state,to_state,reason,actor,occurred_at,unit_version) VALUES(?,?,?,?,?,?,0)",
                (work_unit_id, None, "DISCOVERED", "REGISTERED", actor, stamp),
            )

    @staticmethod
    def _record_revision_observation(
        connection: sqlite3.Connection,
        work_unit_id: str,
        identity_sha256: str,
        inventory_sha256: str | None,
        stamp: str,
    ) -> None:
        if inventory_sha256 is None:
            return
        connection.execute(
            "INSERT INTO work_unit_revision_observations("
            "work_unit_id,identity_sha256,inventory_sha256,observed_at) VALUES(?,?,?,?) "
            "ON CONFLICT(work_unit_id,identity_sha256,inventory_sha256) "
            "DO UPDATE SET observed_at=excluded.observed_at",
            (work_unit_id, identity_sha256, inventory_sha256, stamp),
        )

    def transition(self, *, work_unit_id: str, expected_state: str, new_state: str, reason: str, actor: str, evidence_sha256: str | None = None, now: datetime | None = None) -> int:
        if expected_state not in ALLOWED_STATES or new_state not in ALLOWED_STATES:
            raise ValueError("WORK_UNIT_STATE_INVALID")
        if evidence_sha256 is not None and len(evidence_sha256) != 64:
            raise ValueError("TRANSITION_EVIDENCE_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            row = connection.execute("SELECT current_state,version FROM work_units WHERE work_unit_id=?", (work_unit_id,)).fetchone()
            if row is None:
                raise KeyError(work_unit_id)
            if row["current_state"] != expected_state:
                raise RuntimeError(f"COMPARE_AND_SWAP_STATE_CONFLICT:{row['current_state']}")
            version = int(row["version"]) + 1
            result = connection.execute(
                "UPDATE work_units SET current_state=?,updated_at=?,version=? WHERE work_unit_id=? AND version=?",
                (new_state, stamp, version, work_unit_id, row["version"]),
            )
            if result.rowcount != 1:
                raise RuntimeError("COMPARE_AND_SWAP_VERSION_CONFLICT")
            connection.execute(
                "INSERT INTO transitions(work_unit_id,from_state,to_state,reason,evidence_sha256,actor,occurred_at,unit_version) VALUES(?,?,?,?,?,?,?,?)",
                (work_unit_id, expected_state, new_state, reason, evidence_sha256, actor, stamp, version),
            )
            return version

    def configure_budget(self, provider: str, hard_limit_usd: str, released_usd: str, authorization_id: str, *, now: datetime | None = None) -> None:
        hard = usd_cents(hard_limit_usd)
        released = usd_cents(released_usd)
        if released > hard:
            raise ValueError("RELEASE_EXCEEDS_HARD_LIMIT")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            prior = connection.execute("SELECT settled_cents FROM budgets WHERE provider=?", (provider,)).fetchone()
            settled = int(prior[0]) if prior else 0
            if settled > hard:
                raise RuntimeError("HARD_LIMIT_BELOW_SETTLED_SPEND")
            connection.execute(
                "INSERT INTO budgets(provider,hard_limit_cents,released_cents,settled_cents,authorization_id,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(provider) DO UPDATE SET hard_limit_cents=excluded.hard_limit_cents,released_cents=excluded.released_cents,authorization_id=excluded.authorization_id,updated_at=excluded.updated_at",
                (provider, hard, released, settled, authorization_id, stamp),
            )

    def budget_snapshot(self, provider: str, connection: sqlite3.Connection | None = None) -> BudgetSnapshot:
        owned = connection is None
        conn = connection or self.connect()
        try:
            row = conn.execute(
                "SELECT b.*,COALESCE(SUM(CASE WHEN r.status='RESERVED' THEN r.estimated_cents ELSE 0 END),0) AS reserved "
                "FROM budgets b LEFT JOIN reservations r ON r.provider=b.provider WHERE b.provider=? GROUP BY b.provider",
                (provider,),
            ).fetchone()
            if row is None:
                raise KeyError(provider)
            return BudgetSnapshot(provider, row["hard_limit_cents"], row["released_cents"], row["settled_cents"], row["reserved"])
        finally:
            if owned:
                conn.close()

    def reserve(self, *, reservation_id: str, provider: str, work_unit_id: str, estimated_usd: str, now: datetime | None = None) -> BudgetSnapshot:
        estimate = usd_cents(estimated_usd)
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            existing = connection.execute("SELECT * FROM reservations WHERE reservation_id=?", (reservation_id,)).fetchone()
            if existing:
                if (existing["provider"], existing["work_unit_id"], existing["estimated_cents"]) != (provider, work_unit_id, estimate):
                    raise RuntimeError("RESERVATION_IDEMPOTENCY_CONFLICT")
                return self.budget_snapshot(provider, connection)
            snapshot = self.budget_snapshot(provider, connection)
            if estimate > snapshot.available_cents:
                raise RuntimeError("PROVIDER_BUDGET_ADMISSION_REJECTED")
            connection.execute(
                "INSERT INTO reservations(reservation_id,provider,work_unit_id,estimated_cents,status,created_at) VALUES(?,?,?,?, 'RESERVED',?)",
                (reservation_id, provider, work_unit_id, estimate, stamp),
            )
            return self.budget_snapshot(provider, connection)

    def settle(self, reservation_id: str, actual_usd: str, *, now: datetime | None = None) -> BudgetSnapshot:
        actual = usd_cents(actual_usd)
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM reservations WHERE reservation_id=?", (reservation_id,)).fetchone()
            if row is None:
                raise KeyError(reservation_id)
            if row["status"] == "SETTLED":
                if row["actual_cents"] != actual:
                    raise RuntimeError("SETTLEMENT_IDEMPOTENCY_CONFLICT")
                return self.budget_snapshot(row["provider"], connection)
            if row["status"] != "RESERVED":
                raise RuntimeError("RESERVATION_NOT_SETTLEABLE")
            snapshot = self.budget_snapshot(row["provider"], connection)
            available_with_reservation = snapshot.available_cents + row["estimated_cents"]
            if actual > available_with_reservation:
                raise RuntimeError("ACTUAL_COST_EXCEEDS_AVAILABLE_BUDGET")
            connection.execute(
                "UPDATE reservations SET actual_cents=?,status='SETTLED',settled_at=? WHERE reservation_id=?",
                (actual, stamp, reservation_id),
            )
            connection.execute(
                "UPDATE budgets SET settled_cents=settled_cents+?,updated_at=? WHERE provider=?",
                (actual, stamp, row["provider"]),
            )
            return self.budget_snapshot(row["provider"], connection)

    def record_cycle(self, *, cycle_id: str, inventory_sha256: str, eligible_units: int, dispatched_units: int, no_change: bool, result: str, evidence_sha256: str | None = None, now: datetime | None = None) -> bool:
        if len(inventory_sha256) != 64:
            raise ValueError("INVENTORY_IDENTITY_INVALID")
        if no_change and dispatched_units:
            raise ValueError("NO_CHANGE_CYCLE_DISPATCH_CONFLICT")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT inventory_sha256,eligible_units,dispatched_units,no_change,result,evidence_sha256 "
                "FROM scheduler_cycles WHERE cycle_id=?",
                (cycle_id,),
            ).fetchone()
            expected = (inventory_sha256, eligible_units, dispatched_units, int(no_change), result, evidence_sha256)
            if existing is not None:
                observed = tuple(existing)
                if observed != expected:
                    raise RuntimeError("SCHEDULER_CYCLE_IDEMPOTENCY_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO scheduler_cycles(cycle_id,inventory_sha256,started_at,completed_at,eligible_units,dispatched_units,no_change,result,evidence_sha256) VALUES(?,?,?,?,?,?,?,?,?)",
                (cycle_id, inventory_sha256, stamp, stamp, eligible_units, dispatched_units, int(no_change), result, evidence_sha256),
            )
            return True

    def record_idle_interval(
        self,
        *,
        idle_id: str,
        work_unit_id: str,
        inventory_sha256: str,
        provider: str,
        reason: str,
        evidence_sha256: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        if len(inventory_sha256) != 64:
            raise ValueError("INVENTORY_IDENTITY_INVALID")
        if evidence_sha256 is not None and len(evidence_sha256) != 64:
            raise ValueError("IDLE_EVIDENCE_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            active = connection.execute(
                "SELECT * FROM idle_intervals WHERE work_unit_id=? AND resolved_at IS NULL",
                (work_unit_id,),
            ).fetchone()
            if active is not None:
                if active["provider"] != provider or active["reason"] != reason:
                    connection.execute(
                        "UPDATE idle_intervals SET resolved_at=?,last_observed_at=? WHERE idle_id=?",
                        (stamp, stamp, active["idle_id"]),
                    )
                else:
                    connection.execute(
                        "UPDATE idle_intervals SET inventory_sha256=?,last_observed_at=?,evidence_sha256=? WHERE idle_id=?",
                        (inventory_sha256, stamp, evidence_sha256, active["idle_id"]),
                    )
                    return False
            connection.execute(
                "INSERT INTO idle_intervals(idle_id,work_unit_id,inventory_sha256,provider,reason,opened_at,last_observed_at,evidence_sha256) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (idle_id, work_unit_id, inventory_sha256, provider, reason, stamp, stamp, evidence_sha256),
            )
            return True

    def resolve_idle_intervals(self, active_work_unit_ids: set[str], *, now: datetime | None = None) -> int:
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT idle_id,work_unit_id FROM idle_intervals WHERE resolved_at IS NULL"
            ).fetchall()
            closing = [row["idle_id"] for row in rows if row["work_unit_id"] not in active_work_unit_ids]
            for idle_id in closing:
                connection.execute(
                    "UPDATE idle_intervals SET resolved_at=?,last_observed_at=? WHERE idle_id=?",
                    (stamp, stamp, idle_id),
                )
            return len(closing)

    def work_unit_states(self, work_unit_ids: set[str]) -> dict[str, str]:
        if not work_unit_ids:
            return {}
        placeholders = ",".join("?" for _ in work_unit_ids)
        connection = self.connect()
        try:
            rows = connection.execute(
                f"SELECT work_unit_id,current_state FROM work_units WHERE work_unit_id IN ({placeholders})",
                tuple(sorted(work_unit_ids)),
            ).fetchall()
            return {str(row["work_unit_id"]): str(row["current_state"]) for row in rows}
        finally:
            connection.close()

    @staticmethod
    def _validate_sha256(value: str, finding: str) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(finding)

    @staticmethod
    def _transition_in_connection(
        connection: sqlite3.Connection,
        *,
        work_unit_id: str,
        expected_state: str,
        new_state: str,
        reason: str,
        actor: str,
        stamp: str,
        evidence_sha256: str | None = None,
    ) -> None:
        row = connection.execute(
            "SELECT current_state,version FROM work_units WHERE work_unit_id=?", (work_unit_id,)
        ).fetchone()
        if row is None:
            raise KeyError(work_unit_id)
        if row["current_state"] != expected_state:
            raise RuntimeError("WORK_UNIT_STATE_CONFLICT")
        version = int(row["version"]) + 1
        connection.execute(
            "UPDATE work_units SET current_state=?,updated_at=?,version=? WHERE work_unit_id=?",
            (new_state, stamp, version, work_unit_id),
        )
        connection.execute(
            "INSERT INTO transitions(work_unit_id,from_state,to_state,reason,evidence_sha256,actor,occurred_at,unit_version) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (work_unit_id, expected_state, new_state, reason, evidence_sha256, actor, stamp, version),
        )
        if new_state in TERMINAL_STATES:
            connection.execute(
                "UPDATE incidents SET resolved_at=? WHERE work_unit_id=? AND resolved_at IS NULL",
                (stamp, work_unit_id),
            )

    def claim_dispatch(
        self,
        *,
        work_unit_id: str,
        dependencies: tuple[str, ...],
        lease_id: str,
        attempt_id: str,
        owner_id: str,
        provider: str,
        route_identity: str,
        readiness_evidence_sha256: str,
        now: datetime | None = None,
        ttl_seconds: int = 600,
    ) -> bool:
        self._validate_sha256(route_identity, "ROUTE_IDENTITY_INVALID")
        self._validate_sha256(readiness_evidence_sha256, "ROUTE_READINESS_EVIDENCE_INVALID")
        if ttl_seconds <= 0:
            raise ValueError("WORK_LEASE_TTL_INVALID")
        moment = now or utc_now()
        stamp = rfc3339(moment)
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT current_state FROM work_units WHERE work_unit_id=?", (work_unit_id,)
            ).fetchone()
            if row is None:
                raise KeyError(work_unit_id)
            if row["current_state"] == "CLOSED":
                return False
            active = connection.execute(
                "SELECT lease_id,expires_at FROM work_leases WHERE work_unit_id=? AND status='ACTIVE'",
                (work_unit_id,),
            ).fetchone()
            if active is not None:
                if parse_rfc3339(active["expires_at"]) > moment:
                    return False
                connection.execute(
                    "UPDATE work_leases SET status='ABANDONED',heartbeat_at=? WHERE lease_id=?",
                    (stamp, active["lease_id"]),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO incidents(incident_id,work_unit_id,finding,opened_at) VALUES(?,?,?,?)",
                    (hashlib.sha256(f"{active['lease_id']}:abandoned".encode()).hexdigest(), work_unit_id, "ABANDONED_WORK_LEASE_RECOVERED", stamp),
                )
            starting_state = str(row["current_state"])
            if starting_state == "RETRY_WAIT":
                retry = connection.execute(
                    "SELECT eligible_at FROM retry_records WHERE work_unit_id=? ORDER BY created_at DESC LIMIT 1",
                    (work_unit_id,),
                ).fetchone()
                if retry is None or parse_rfc3339(retry["eligible_at"]) > moment:
                    return False
            elif starting_state != "DISCOVERED":
                return False
            for dependency in dependencies:
                connection.execute(
                    "INSERT OR IGNORE INTO work_dependencies(work_unit_id,dependency_id,observed_at) VALUES(?,?,?)",
                    (work_unit_id, dependency, stamp),
                )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state=starting_state, new_state="ELIGIBLE",
                reason="DEPENDENCIES_AND_ROUTE_READY", actor=owner_id, stamp=stamp,
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="ELIGIBLE", new_state="LEASED",
                reason="ATOMIC_WORK_LEASE_ACQUIRED", actor=owner_id, stamp=stamp,
            )
            connection.execute(
                "INSERT INTO work_leases(lease_id,work_unit_id,owner_id,acquired_at,heartbeat_at,expires_at,status) "
                "VALUES(?,?,?,?,?,?,'ACTIVE')",
                (lease_id, work_unit_id, owner_id, stamp, stamp, rfc3339(moment + timedelta(seconds=ttl_seconds))),
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="LEASED", new_state="ADMITTED",
                reason="EXACT_ROUTE_ADMISSION_PASSED", actor=owner_id, stamp=stamp,
            )
            connection.execute(
                "UPDATE work_units SET route_identity=? WHERE work_unit_id=?", (route_identity, work_unit_id)
            )
            readiness_observation_id = hashlib.sha256(
                f"{route_identity}:{readiness_evidence_sha256}".encode()
            ).hexdigest()
            connection.execute(
                "INSERT OR IGNORE INTO route_readiness_observations(observation_id,route_identity,state,evidence_sha256,observed_at) "
                "VALUES(?,?,'READY',?,?)",
                (readiness_observation_id, route_identity, readiness_evidence_sha256, stamp),
            )
            connection.execute(
                "INSERT INTO dispatch_attempts(attempt_id,work_unit_id,provider,route_identity,state,started_at) "
                "VALUES(?,?,?,?,?,?)",
                (attempt_id, work_unit_id, provider, route_identity, "ADMITTED", stamp),
            )
            return True

    def dispatch_attempt_count(self, work_unit_id: str) -> int:
        connection = self.connect()
        try:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM dispatch_attempts WHERE work_unit_id=?", (work_unit_id,)
                ).fetchone()[0]
            )
        finally:
            connection.close()

    def provider_last_dispatch_times(self, providers: set[str]) -> dict[str, str | None]:
        """Return durable recency used to prevent a busy provider from starving peers."""
        if not providers:
            return {}
        connection = self.connect()
        try:
            placeholders = ",".join("?" for _ in providers)
            rows = connection.execute(
                f"SELECT provider,MAX(started_at) AS last_started_at FROM dispatch_attempts "
                f"WHERE provider IN ({placeholders}) GROUP BY provider",
                tuple(sorted(providers)),
            ).fetchall()
            observed = {str(row["provider"]): str(row["last_started_at"]) for row in rows}
            return {provider: observed.get(provider) for provider in providers}
        finally:
            connection.close()

    def inflight_provider_runs(self, provider: str) -> list[dict[str, Any]]:
        connection = self.connect()
        try:
            rows = connection.execute(
                "SELECT p.provider_run_id,p.remote_identity,p.resource_json,p.started_at,"
                "a.attempt_id,a.work_unit_id,a.route_identity,l.lease_id,l.expires_at "
                "FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                "JOIN work_units w ON w.work_unit_id=a.work_unit_id "
                "JOIN work_leases l ON l.work_unit_id=w.work_unit_id AND l.status='ACTIVE' "
                "WHERE p.provider=? AND p.status='DISPATCHED' AND a.state='DISPATCHED' "
                "AND w.current_state='DISPATCHED' ORDER BY p.started_at,p.provider_run_id",
                (provider,),
            ).fetchall()
            return [
                {
                    **dict(row),
                    "resource": json.loads(row["resource_json"] or "{}"),
                }
                for row in rows
            ]
        finally:
            connection.close()

    def heartbeat_work_lease(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        lease_id: str,
        ttl_seconds: int = 600,
        now: datetime | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("WORK_LEASE_TTL_INVALID")
        moment = now or utc_now()
        stamp = rfc3339(moment)
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT l.status,a.state,w.current_state FROM work_leases l "
                "JOIN dispatch_attempts a ON a.work_unit_id=l.work_unit_id "
                "JOIN work_units w ON w.work_unit_id=l.work_unit_id "
                "WHERE l.lease_id=? AND l.work_unit_id=? AND a.attempt_id=?",
                (lease_id, work_unit_id, attempt_id),
            ).fetchone()
            if (
                row is None
                or row["status"] != "ACTIVE"
                or row["state"] != "DISPATCHED"
                or row["current_state"] != "DISPATCHED"
            ):
                raise RuntimeError("INFLIGHT_WORK_LEASE_IDENTITY_MISMATCH")
            connection.execute(
                "UPDATE work_leases SET heartbeat_at=?,expires_at=? WHERE lease_id=?",
                (stamp, rfc3339(moment + timedelta(seconds=ttl_seconds)), lease_id),
            )

    def reconcile_expired_work_leases(self, *, now: datetime | None = None) -> dict[str, int]:
        """Recover only pre-dispatch leases; quarantine in-flight ambiguity from automatic retry."""
        moment = now or utc_now()
        stamp = rfc3339(moment)
        recovered_pre_dispatch = 0
        review_required = 0
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT l.lease_id,l.work_unit_id,w.current_state,a.attempt_id,a.state AS attempt_state "
                "FROM work_leases l JOIN work_units w ON w.work_unit_id=l.work_unit_id "
                "LEFT JOIN dispatch_attempts a ON a.attempt_id=("
                "SELECT a2.attempt_id FROM dispatch_attempts a2 WHERE a2.work_unit_id=l.work_unit_id "
                "ORDER BY a2.started_at DESC,a2.attempt_id DESC LIMIT 1) "
                "WHERE l.status='ACTIVE' AND l.expires_at<? ORDER BY l.lease_id",
                (stamp,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE work_leases SET status='ABANDONED',heartbeat_at=? WHERE lease_id=? AND status='ACTIVE'",
                    (stamp, row["lease_id"]),
                )
                attempt_id = row["attempt_id"]
                if row["current_state"] == "ADMITTED" and row["attempt_state"] == "ADMITTED" and attempt_id:
                    connection.execute(
                        "UPDATE dispatch_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?",
                        (stamp, "ABANDONED_BEFORE_PROVIDER_DISPATCH", attempt_id),
                    )
                    self._transition_in_connection(
                        connection,
                        work_unit_id=row["work_unit_id"],
                        expected_state="ADMITTED",
                        new_state="RETRY_WAIT",
                        reason="EXPIRED_PRE_DISPATCH_LEASE_RECOVERED",
                        actor="controller-startup-recovery",
                        stamp=stamp,
                    )
                    retry_id = hashlib.sha256(f"{attempt_id}:startup-retry".encode()).hexdigest()
                    connection.execute(
                        "INSERT OR IGNORE INTO retry_records(retry_id,work_unit_id,prior_attempt_id,reason,eligible_at,created_at) "
                        "VALUES(?,?,?,?,?,?)",
                        (
                            retry_id,
                            row["work_unit_id"],
                            attempt_id,
                            "ABANDONED_BEFORE_PROVIDER_DISPATCH",
                            stamp,
                            stamp,
                        ),
                    )
                    finding = "ABANDONED_PRE_DISPATCH_WORK_LEASE_RECOVERED"
                    recovered_pre_dispatch += 1
                else:
                    finding = "ABANDONED_INFLIGHT_PROVIDER_RECONCILIATION_REQUIRED"
                    review_required += 1
                incident_id = hashlib.sha256(f"{row['lease_id']}:{finding}".encode()).hexdigest()
                connection.execute(
                    "INSERT OR IGNORE INTO incidents(incident_id,work_unit_id,attempt_id,finding,opened_at) "
                    "VALUES(?,?,?,?,?)",
                    (incident_id, row["work_unit_id"], attempt_id, finding, stamp),
                )
        return {
            "expired_leases_observed": recovered_pre_dispatch + review_required,
            "recovered_pre_dispatch": recovered_pre_dispatch,
            "provider_reconciliation_required": review_required,
        }

    def recover_cursor_inflight_leases(
        self,
        *,
        owner_id: str,
        now: datetime | None = None,
        ttl_seconds: int = 600,
    ) -> int:
        """Rebind only durable, already-submitted Cursor runs after leader restart."""
        if ttl_seconds <= 0:
            raise ValueError("WORK_LEASE_TTL_INVALID")
        moment = now or utc_now()
        stamp = rfc3339(moment)
        recovered = 0
        with self.transaction() as connection:
            leader = connection.execute(
                "SELECT owner_id FROM leader_lease WHERE singleton=1"
            ).fetchone()
            if leader is None or leader["owner_id"] != owner_id:
                raise RuntimeError("CURSOR_RECOVERY_REQUIRES_CURRENT_LEADER")
            rows = connection.execute(
                "SELECT l.lease_id,l.work_unit_id,a.attempt_id,p.provider_run_id "
                "FROM work_leases l JOIN work_units w ON w.work_unit_id=l.work_unit_id "
                "JOIN dispatch_attempts a ON a.work_unit_id=w.work_unit_id "
                "JOIN provider_runs p ON p.attempt_id=a.attempt_id "
                "WHERE l.status='ABANDONED' AND w.current_state='DISPATCHED' "
                "AND a.state='DISPATCHED' AND p.status='DISPATCHED' AND p.provider='cursor' "
                "AND NOT EXISTS (SELECT 1 FROM work_leases active WHERE active.work_unit_id=w.work_unit_id "
                "AND active.status='ACTIVE') ORDER BY l.lease_id"
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE work_leases SET owner_id=?,heartbeat_at=?,expires_at=?,status='ACTIVE' "
                    "WHERE lease_id=? AND status='ABANDONED'",
                    (
                        owner_id,
                        stamp,
                        rfc3339(moment + timedelta(seconds=ttl_seconds)),
                        row["lease_id"],
                    ),
                )
                connection.execute(
                    "UPDATE incidents SET resolved_at=? WHERE work_unit_id=? AND attempt_id=? "
                    "AND finding='ABANDONED_INFLIGHT_PROVIDER_RECONCILIATION_REQUIRED' "
                    "AND resolved_at IS NULL",
                    (stamp, row["work_unit_id"], row["attempt_id"]),
                )
                connection.execute(
                    "INSERT INTO controller_events(event_type,payload_json,occurred_at) VALUES(?,?,?)",
                    (
                        "CURSOR_INFLIGHT_LEASE_RECOVERED_WITHOUT_RESUBMISSION",
                        json.dumps(
                            {
                                "work_unit_id": row["work_unit_id"],
                                "attempt_id": row["attempt_id"],
                                "provider_run_id": row["provider_run_id"],
                                "lease_id": row["lease_id"],
                                "owner_id": owner_id,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        stamp,
                    ),
                )
                recovered += 1
        return recovered

    def record_dispatch(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        provider_run_id: str,
        provider: str,
        remote_identity: str,
        request_sha256: str,
        request_artifact_path: Path,
        actor: str,
        resource: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._validate_sha256(request_sha256, "DISPATCH_REQUEST_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        request_artifact_sha256 = hashlib.sha256(request_artifact_path.read_bytes()).hexdigest()
        with self.transaction() as connection:
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="ADMITTED", new_state="DISPATCHED",
                reason="PROVIDER_REQUEST_SUBMITTED", actor=actor, stamp=stamp, evidence_sha256=request_sha256,
            )
            connection.execute(
                "UPDATE dispatch_attempts SET state='DISPATCHED',request_sha256=? WHERE attempt_id=? AND work_unit_id=?",
                (request_sha256, attempt_id, work_unit_id),
            )
            connection.execute(
                "INSERT INTO provider_runs(provider_run_id,attempt_id,provider,remote_identity,request_sha256,status,resource_json,started_at) "
                "VALUES(?,?,?,?,?,'DISPATCHED',?,?)",
                (provider_run_id, attempt_id, provider, remote_identity, request_sha256, json.dumps(resource or {}, sort_keys=True), stamp),
            )
            connection.execute(
                "INSERT INTO execution_artifacts(artifact_id,work_unit_id,attempt_id,artifact_type,path,sha256,bytes,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    request_artifact_sha256,
                    work_unit_id,
                    attempt_id,
                    "PROVIDER_REQUEST_ENVELOPE",
                    str(request_artifact_path),
                    request_artifact_sha256,
                    request_artifact_path.stat().st_size,
                    stamp,
                ),
            )

    def record_result_and_artifact(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        provider_run_id: str,
        result_sha256: str,
        artifact_path: Path,
        actor: str,
        now: datetime | None = None,
    ) -> None:
        self._validate_sha256(result_sha256, "DISPATCH_RESULT_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        artifact_bytes = artifact_path.stat().st_size
        artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        with self.transaction() as connection:
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="DISPATCHED", new_state="RESULT_RECEIVED",
                reason="CONTENT_ADDRESSED_PROVIDER_RESULT_RECEIVED", actor=actor, stamp=stamp,
                evidence_sha256=artifact_sha256,
            )
            connection.execute(
                "UPDATE dispatch_attempts SET state='RESULT_RECEIVED',result_sha256=? WHERE attempt_id=?",
                (result_sha256, attempt_id),
            )
            connection.execute(
                "UPDATE provider_runs SET response_sha256=?,status='RESULT_RECEIVED',completed_at=? WHERE provider_run_id=?",
                (result_sha256, stamp, provider_run_id),
            )
            connection.execute(
                "INSERT INTO execution_artifacts(artifact_id,work_unit_id,attempt_id,artifact_type,path,sha256,bytes,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (artifact_sha256, work_unit_id, attempt_id, "PROVIDER_REQUEST_RESPONSE", str(artifact_path), artifact_sha256, artifact_bytes, stamp),
            )

    def complete_validated_review_only(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        lease_id: str,
        validation_sha256: str,
        review_sha256: str,
        cleanup_sha256: str,
        actor: str,
        now: datetime | None = None,
    ) -> None:
        self.complete_candidate_work(
            work_unit_id=work_unit_id,
            attempt_id=attempt_id,
            lease_id=lease_id,
            validation_sha256=validation_sha256,
            review_sha256=review_sha256,
            cleanup_sha256=cleanup_sha256,
            validator="CPU_WORKER_EXACT_LOCAL_REPLAY",
            validation_result="PASS",
            reviewer="DETERMINISTIC_POLICY",
            disposition="REVIEW_ONLY",
            actual_cost_usd="0.000000",
            settlement_reason="NONBILLABLE_CPU_RESOURCE_SETTLED",
            cleanup_action="NO_RECONSTRUCTIBLE_TEMP_CREATED",
            actor=actor,
            now=now,
        )

    def complete_candidate_work(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        lease_id: str,
        validation_sha256: str,
        review_sha256: str,
        cleanup_sha256: str,
        validator: str,
        validation_result: str,
        reviewer: str,
        disposition: str,
        actual_cost_usd: str,
        settlement_reason: str,
        cleanup_action: str,
        actor: str,
        review_seconds: float = 0.0,
        bytes_removed: int = 0,
        resource: dict[str, Any] | None = None,
        useful_work: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        for value, finding in (
            (validation_sha256, "VALIDATION_IDENTITY_INVALID"),
            (review_sha256, "REVIEW_IDENTITY_INVALID"),
            (cleanup_sha256, "CLEANUP_IDENTITY_INVALID"),
        ):
            self._validate_sha256(value, finding)
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="RESULT_RECEIVED", new_state="VALIDATED",
                reason="CANDIDATE_DETERMINISTIC_VALIDATION_COMPLETE", actor=actor, stamp=stamp, evidence_sha256=validation_sha256,
            )
            connection.execute(
                "INSERT INTO validation_results(validation_id,work_unit_id,attempt_id,validator,result,evidence_sha256,recorded_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (validation_sha256, work_unit_id, attempt_id, validator, validation_result, validation_sha256, stamp),
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="VALIDATED", new_state="REVIEWED",
                reason="CANDIDATE_ONLY_REVIEW_QUEUE_DISPOSITION", actor=actor, stamp=stamp, evidence_sha256=review_sha256,
            )
            connection.execute(
                "INSERT INTO reviews(review_id,work_unit_id,attempt_id,reviewer,disposition,evidence_sha256,review_seconds,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (review_sha256, work_unit_id, attempt_id, reviewer, disposition, review_sha256, review_seconds, stamp),
            )
            substance = dict(useful_work or {})
            downstream_consumed = bool(substance.get("downstream_consumed", False))
            changed_project_artifact = bool(substance.get("changed_project_artifact", False))
            duplicated_by_codex = bool(substance.get("duplicated_by_codex", False))
            accepted_useful = (
                validation_result == "PASS"
                and disposition in {"ACCEPTED", "MODIFIED"}
                and downstream_consumed
                and changed_project_artifact
                and not duplicated_by_codex
                and bool(substance.get("consumed_artifact_identity"))
            )
            evidence_payload = {
                "work_unit_id": work_unit_id,
                "attempt_id": attempt_id,
                "bas_decision_unit": str(substance.get("bas_decision_unit", "UNSPECIFIED_BAS_DECISION_UNIT")),
                "downstream_consumer": str(substance.get("downstream_consumer", "DURABLE_REVIEW_QUEUE_ONLY")),
                "delegation_preference_reason": str(
                    substance.get("delegation_preference_reason", "PROVIDER_ROUTE_SELECTED_BY_GOVERNED_ROUTER")
                ),
                "input_documents": max(0, int(substance.get("input_documents", 0))),
                "input_bytes": max(0, int(substance.get("input_bytes", 0))),
                "input_records": max(0, int(substance.get("input_records", 0))),
                "candidate_count": max(0, int(substance.get("candidate_count", 0))),
                "provider": str(substance.get("provider", "UNKNOWN_PROVIDER")),
                "model": substance.get("model"),
                "task_format": str(substance.get("task_format", "UNKNOWN_TASK_FORMAT")),
                "route_identity": str(substance.get("route_identity", "UNKNOWN_ROUTE_IDENTITY")),
                "wall_seconds": max(0.0, float(substance.get("wall_seconds", 0.0))),
                "compute": dict(substance.get("compute", resource or {})),
                "direct_baseline_seconds": substance.get("direct_baseline_seconds"),
                "orchestration_seconds": max(0.0, float(substance.get("orchestration_seconds", 0.0))),
                "review_seconds": max(0.0, float(review_seconds)),
                "disposition": disposition,
                "validated": validation_result == "PASS",
                "reviewed": True,
                "downstream_consumed": downstream_consumed,
                "changed_project_artifact": changed_project_artifact,
                "consumed_artifact_identity": substance.get("consumed_artifact_identity"),
                "net_time_saved_seconds": float(substance.get("net_time_saved_seconds", 0.0)),
                "duplicated_by_codex": duplicated_by_codex,
                "accepted_useful_offload": accepted_useful,
            }
            useful_sha256 = hashlib.sha256(
                json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            baseline = evidence_payload["direct_baseline_seconds"]
            connection.execute(
                "INSERT INTO useful_work_evidence("
                "useful_work_id,work_unit_id,attempt_id,bas_decision_unit,downstream_consumer,"
                "delegation_preference_reason,input_documents,input_bytes,input_records,candidate_count,"
                "provider,model,task_format,route_identity,wall_seconds,compute_json,direct_baseline_seconds,"
                "orchestration_seconds,review_seconds,disposition,validated,reviewed,downstream_consumed,"
                "changed_project_artifact,consumed_artifact_identity,net_time_saved_seconds,duplicated_by_codex,"
                "accepted_useful_offload,evidence_sha256,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    useful_sha256, work_unit_id, attempt_id, evidence_payload["bas_decision_unit"],
                    evidence_payload["downstream_consumer"], evidence_payload["delegation_preference_reason"],
                    evidence_payload["input_documents"], evidence_payload["input_bytes"],
                    evidence_payload["input_records"], evidence_payload["candidate_count"],
                    evidence_payload["provider"], evidence_payload["model"], evidence_payload["task_format"],
                    evidence_payload["route_identity"], evidence_payload["wall_seconds"],
                    json.dumps(evidence_payload["compute"], sort_keys=True, separators=(",", ":")),
                    None if baseline is None else max(0.0, float(baseline)),
                    evidence_payload["orchestration_seconds"], evidence_payload["review_seconds"], disposition,
                    int(evidence_payload["validated"]), 1, int(downstream_consumed), int(changed_project_artifact),
                    evidence_payload["consumed_artifact_identity"], evidence_payload["net_time_saved_seconds"],
                    int(duplicated_by_codex), int(accepted_useful), useful_sha256, stamp,
                ),
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="REVIEWED", new_state="SETTLED",
                reason=settlement_reason, actor=actor, stamp=stamp,
            )
            actual_cost_cents = int((Decimal(actual_cost_usd) * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            connection.execute(
                "UPDATE provider_runs SET status='SETTLED',actual_cost_cents=?,resource_json=? WHERE attempt_id=?",
                (actual_cost_cents, json.dumps(resource or {}, sort_keys=True), attempt_id),
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="SETTLED", new_state="CLEANED",
                reason="NO_RECONSTRUCTIBLE_TEMP_REMAINS", actor=actor, stamp=stamp, evidence_sha256=cleanup_sha256,
            )
            connection.execute(
                "INSERT INTO cleanup_actions(cleanup_id,work_unit_id,attempt_id,action,bytes_removed,evidence_sha256,recorded_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (cleanup_sha256, work_unit_id, attempt_id, cleanup_action, bytes_removed, cleanup_sha256, stamp),
            )
            self._transition_in_connection(
                connection, work_unit_id=work_unit_id, expected_state="CLEANED", new_state="CLOSED",
                reason="CONTROLLER_ROUTED_CANDIDATE_ONLY_UNIT_CLOSED", actor=actor, stamp=stamp,
                evidence_sha256=review_sha256,
            )
            connection.execute(
                "UPDATE dispatch_attempts SET state='CLOSED',completed_at=? WHERE attempt_id=?", (stamp, attempt_id)
            )
            connection.execute(
                "UPDATE work_leases SET status='CLOSED',heartbeat_at=? WHERE lease_id=?", (stamp, lease_id)
            )
            reconciliation_id = hashlib.sha256(f"{work_unit_id}:{attempt_id}:reconciled".encode()).hexdigest()
            jira_identity = connection.execute(
                "SELECT jira_identity FROM work_units WHERE work_unit_id=?", (work_unit_id,)
            ).fetchone()[0]
            result_identity = connection.execute(
                "SELECT result_sha256 FROM dispatch_attempts WHERE attempt_id=?", (attempt_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO reconciliation_records(reconciliation_id,work_unit_id,jira_identity,result_identity,result,recorded_at) "
                "VALUES(?,?,?,?,?,?)",
                (
                    reconciliation_id,
                    work_unit_id,
                    jira_identity,
                    result_identity,
                    "EXTERNAL_CANDIDATE_RESULT_BOUND_TO_EXISTING_JIRA_UMBRELLA_NO_GIT_OR_PR_MUTATION",
                    stamp,
                ),
            )
            connection.execute(
                "UPDATE incidents SET resolved_at=? WHERE work_unit_id=? AND resolved_at IS NULL",
                (stamp, work_unit_id),
            )

    def record_dispatch_failure(
        self,
        *,
        work_unit_id: str,
        attempt_id: str,
        lease_id: str,
        error_code: str,
        actor: str,
        retryable: bool = True,
        retry_delay_seconds: int = 60,
        now: datetime | None = None,
    ) -> None:
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT current_state FROM work_units WHERE work_unit_id=?", (work_unit_id,)
            ).fetchone()
            next_state = "RETRY_WAIT" if retryable else "FAILED"
            if row and row["current_state"] not in TERMINAL_STATES:
                self._transition_in_connection(
                    connection, work_unit_id=work_unit_id, expected_state=row["current_state"], new_state=next_state,
                    reason=error_code, actor=actor, stamp=stamp,
                )
            connection.execute(
                "UPDATE dispatch_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?",
                (stamp, error_code, attempt_id),
            )
            connection.execute(
                "UPDATE provider_runs SET status='FAILED',completed_at=? WHERE attempt_id=?",
                (stamp, attempt_id),
            )
            connection.execute("UPDATE work_leases SET status='CLOSED',heartbeat_at=? WHERE lease_id=?", (stamp, lease_id))
            incident_id = hashlib.sha256(f"{attempt_id}:{error_code}".encode()).hexdigest()
            connection.execute(
                "INSERT OR IGNORE INTO incidents(incident_id,work_unit_id,attempt_id,finding,opened_at) VALUES(?,?,?,?,?)",
                (incident_id, work_unit_id, attempt_id, error_code, stamp),
            )
            if retryable:
                retry_id = hashlib.sha256(f"{attempt_id}:retry".encode()).hexdigest()
                connection.execute(
                    "INSERT INTO retry_records(retry_id,work_unit_id,prior_attempt_id,reason,eligible_at,created_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        retry_id,
                        work_unit_id,
                        attempt_id,
                        error_code,
                        rfc3339((now or utc_now()) + timedelta(seconds=retry_delay_seconds)),
                        stamp,
                    ),
                )

    def record_downstream_review_disposition(
        self,
        *,
        attempt_id: str,
        disposition: str,
        downstream_consumer: str,
        reason: str,
        consumed_artifact_identity: str | None = None,
        changed_project_artifact: bool = False,
        net_time_saved_seconds: float = 0.0,
        duplicated_by_codex: bool = False,
        review_seconds: float = 0.0,
        now: datetime | None = None,
    ) -> str:
        if disposition not in {"ACCEPTED", "MODIFIED", "REJECTED", "UNUSED"}:
            raise ValueError("DOWNSTREAM_REVIEW_DISPOSITION_INVALID")
        if disposition in {"ACCEPTED", "MODIFIED"} and (
            not changed_project_artifact or not consumed_artifact_identity or duplicated_by_codex
        ):
            raise ValueError("DOWNSTREAM_ACCEPTANCE_CONSUMPTION_EVIDENCE_INCOMPLETE")
        if consumed_artifact_identity is not None:
            self._validate_sha256(consumed_artifact_identity, "CONSUMED_ARTIFACT_IDENTITY_INVALID")
        payload = {
            "attempt_id": attempt_id,
            "disposition": disposition,
            "downstream_consumer": downstream_consumer,
            "consumed_artifact_identity": consumed_artifact_identity,
            "changed_project_artifact": changed_project_artifact,
            "net_time_saved_seconds": float(net_time_saved_seconds),
            "duplicated_by_codex": duplicated_by_codex,
            "review_seconds": max(0.0, float(review_seconds)),
            "reason": reason,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO downstream_review_dispositions("
                "downstream_review_id,attempt_id,disposition,downstream_consumer,consumed_artifact_identity,"
                "changed_project_artifact,net_time_saved_seconds,duplicated_by_codex,review_seconds,reason,"
                "evidence_sha256,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    digest, attempt_id, disposition, downstream_consumer, consumed_artifact_identity,
                    int(changed_project_artifact), float(net_time_saved_seconds), int(duplicated_by_codex),
                    max(0.0, float(review_seconds)), reason, digest, rfc3339(now or utc_now()),
                ),
            )
        return digest
    def status(self) -> dict[str, Any]:
        connection = self.connect()
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            schema_row = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            schema_version = int(schema_row[0]) if schema_row else 0
            leader = connection.execute("SELECT * FROM leader_lease WHERE singleton=1").fetchone()
            counts = {row["current_state"]: row["count"] for row in connection.execute("SELECT current_state,COUNT(*) AS count FROM work_units GROUP BY current_state")}
            cycle_summary = connection.execute(
                "SELECT COUNT(*) AS cycles,COALESCE(SUM(dispatched_units),0) AS dispatched,"
                "COALESCE(SUM(no_change),0) AS no_change FROM scheduler_cycles"
            ).fetchone()
            latest_cycle = connection.execute(
                "SELECT * FROM scheduler_cycles ORDER BY completed_at DESC,cycle_id DESC LIMIT 1"
            ).fetchone()
            active_idle = connection.execute(
                "SELECT COUNT(*) FROM idle_intervals WHERE resolved_at IS NULL"
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "dispatch_attempts" in tables:
                execution = connection.execute(
                    "SELECT COUNT(*) AS attempts,"
                    "SUM(CASE WHEN state='CLOSED' THEN 1 ELSE 0 END) AS closed_attempts FROM dispatch_attempts"
                ).fetchone()
                attempts = int(execution["attempts"])
                closed_attempts = int(execution["closed_attempts"] or 0)
            else:
                attempts = 0
                closed_attempts = 0
            review_counts = (
                {
                    row["disposition"]: int(row["count"])
                    for row in connection.execute("SELECT disposition,COUNT(*) AS count FROM reviews GROUP BY disposition")
                }
                if "reviews" in tables
                else {}
            )
            useful_work_summary = (
                dict(
                    connection.execute(
                        "SELECT COUNT(*) AS raw_activity,"
                        "COALESCE(SUM(validated),0) AS validated_candidates,"
                        "COALESCE(SUM(reviewed),0) AS reviewed_outputs,"
                        "COALESCE(SUM(CASE WHEN d.disposition IN ('ACCEPTED','MODIFIED') THEN 1 ELSE 0 END),0) AS downstream_consumed_outputs,"
                        "COALESCE(SUM(CASE WHEN d.disposition IN ('ACCEPTED','MODIFIED') AND u.validated=1 "
                        "AND d.changed_project_artifact=1 AND d.consumed_artifact_identity IS NOT NULL "
                        "AND d.duplicated_by_codex=0 AND d.net_time_saved_seconds>0 "
                        "THEN 1 ELSE 0 END),0) AS accepted_useful_outputs,"
                        "COALESCE(SUM(d.net_time_saved_seconds),0.0) AS measured_net_time_saved_seconds,"
                        "COALESCE(SUM(d.duplicated_by_codex),0) AS duplicated_by_codex "
                        "FROM useful_work_evidence u LEFT JOIN downstream_review_dispositions d ON d.attempt_id=u.attempt_id"
                    ).fetchone()
                )
                if "useful_work_evidence" in tables
                else {}
            )
            downstream_review_summary = (
                {
                    row["disposition"]: int(row["count"])
                    for row in connection.execute(
                        "SELECT disposition,COUNT(*) AS count FROM downstream_review_dispositions GROUP BY disposition"
                    )
                }
                if "downstream_review_dispositions" in tables
                else {}
            )
            pre_routing_counts = (
                {
                    row["disposition"]: int(row["count"])
                    for row in connection.execute(
                        "SELECT disposition,COUNT(*) AS count FROM pre_routing_decisions GROUP BY disposition"
                    )
                }
                if "pre_routing_decisions" in tables
                else {}
            )
            active_operational_conditions = (
                int(
                    connection.execute(
                        "SELECT COUNT(*) FROM operational_conditions WHERE resolved_at IS NULL"
                    ).fetchone()[0]
                )
                if "operational_conditions" in tables
                else 0
            )
            release_dispatched_units = 0
            release_provider_calls = 0
            scheduler_provider_calls = 0
            if {"dispatch_attempts", "provider_runs"} <= tables:
                settled_runs = connection.execute(
                    "SELECT a.started_at,p.resource_json FROM provider_runs p "
                    "JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                    "WHERE p.status='SETTLED' AND a.state='CLOSED'",
                ).fetchall()
                for row in settled_runs:
                    try:
                        resource = json.loads(row["resource_json"] or "{}")
                        provider_calls = int(resource.get("provider_calls", 1))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                    scheduler_provider_calls += provider_calls
                    if leader and row["started_at"] >= leader["acquired_at"]:
                        release_dispatched_units += 1
                        release_provider_calls += provider_calls
            return {
                "schema_version": schema_version,
                "database": str(self.database),
                "journal_mode": str(mode).upper(),
                "integrity_check": integrity,
                "leader": dict(leader) if leader else None,
                "work_unit_counts": counts,
                "scheduler_cycles": int(cycle_summary["cycles"]),
                "scheduler_dispatched_units": int(cycle_summary["dispatched"]),
                "scheduler_provider_calls": scheduler_provider_calls,
                "release_scheduler_dispatched_units": release_dispatched_units,
                "release_scheduler_provider_calls": release_provider_calls,
                "scheduler_no_change_cycles": int(cycle_summary["no_change"]),
                "scheduler_latest_cycle": dict(latest_cycle) if latest_cycle else None,
                "active_idle_intervals": int(active_idle),
                "dispatch_attempts": attempts,
                "closed_dispatch_attempts": closed_attempts,
                "review_dispositions": review_counts,
                "useful_work_summary": useful_work_summary,
                "downstream_review_dispositions": downstream_review_summary,
                "pre_routing_dispositions": pre_routing_counts,
                "unjustified_direct_execution_count": pre_routing_counts.get(
                    "UNJUSTIFIED_DIRECT_EXECUTION", 0
                ),
                "active_operational_conditions": active_operational_conditions,
            }
        finally:
            connection.close()

    def provider_run_summary(self, *, current_release_only: bool = False) -> dict[str, dict[str, Any]]:
        """Return durable controller-routed workload totals grouped by provider."""
        connection = self.connect()
        try:
            since_clause = ""
            parameters: tuple[Any, ...] = ()
            if current_release_only:
                leader = connection.execute(
                    "SELECT build_commit FROM leader_lease WHERE singleton=1"
                ).fetchone()
                if leader is None:
                    return {}
                epoch = connection.execute(
                    "SELECT value FROM metadata WHERE key=?",
                    ("release_epoch:" + str(leader["build_commit"]),),
                ).fetchone()
                if epoch is None:
                    return {}
                since_clause = " WHERE a.started_at>=?"
                parameters = (str(epoch["value"]),)
            rows = connection.execute(
                "SELECT p.provider,COUNT(*) AS runs,"
                "SUM(CASE WHEN p.status='SETTLED' AND a.state='CLOSED' THEN 1 ELSE 0 END) AS closed_runs,"
                "COALESCE(SUM(CASE WHEN p.status='SETTLED' AND a.state='CLOSED' THEN w.effort_points ELSE 0 END),0) AS closed_effort "
                "FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                "JOIN work_units w ON w.work_unit_id=a.work_unit_id" + since_clause + " GROUP BY p.provider",
                parameters,
            ).fetchall()
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                provider = str(row["provider"])
                dispositions = {
                    str(item["disposition"]): int(item["count"])
                    for item in connection.execute(
                        "SELECT r.disposition,COUNT(*) AS count FROM reviews r "
                        "JOIN dispatch_attempts a ON a.attempt_id=r.attempt_id "
                        "JOIN provider_runs p ON p.attempt_id=a.attempt_id "
                        "WHERE p.provider=?" + (" AND a.started_at>=?" if parameters else "") + " GROUP BY r.disposition",
                        (provider, *parameters),
                    )
                }
                result[provider] = {
                    "runs": int(row["runs"]),
                    "closed_runs": int(row["closed_runs"] or 0),
                    "closed_effort_points": int(row["closed_effort"] or 0),
                    "review_dispositions": dispositions,
                }
                useful = connection.execute(
                    "SELECT COUNT(*) AS raw_activity,COALESCE(SUM(validated),0) AS validated_candidates,"
                    "COALESCE(SUM(reviewed),0) AS reviewed_outputs,"
                    "COALESCE(SUM(CASE WHEN d.disposition IN ('ACCEPTED','MODIFIED') THEN 1 ELSE 0 END),0) AS downstream_consumed_outputs,"
                    "COALESCE(SUM(CASE WHEN d.disposition IN ('ACCEPTED','MODIFIED') AND u.validated=1 "
                    "AND d.changed_project_artifact=1 AND d.consumed_artifact_identity IS NOT NULL "
                    "AND d.duplicated_by_codex=0 AND d.net_time_saved_seconds>0 "
                    "THEN 1 ELSE 0 END),0) AS accepted_useful_outputs,"
                    "COALESCE(SUM(d.net_time_saved_seconds),0.0) AS measured_net_time_saved_seconds,"
                    "COALESCE(SUM(d.duplicated_by_codex),0) AS duplicated_by_codex "
                    "FROM useful_work_evidence u JOIN dispatch_attempts a ON a.attempt_id=u.attempt_id "
                    "LEFT JOIN downstream_review_dispositions d ON d.attempt_id=u.attempt_id "
                    "WHERE u.provider=?" + (" AND a.started_at>=?" if parameters else ""),
                    (provider, *parameters),
                ).fetchone()
                result[provider]["useful_work"] = dict(useful)
                pending = connection.execute(
                    "SELECT COUNT(*) FROM reviews r JOIN dispatch_attempts a ON a.attempt_id=r.attempt_id "
                    "JOIN provider_runs p ON p.attempt_id=a.attempt_id "
                    "WHERE p.provider=? AND r.disposition IN ('REVIEW_ONLY','ACCEPTED','MODIFIED') AND NOT EXISTS ("
                    "SELECT 1 FROM downstream_review_dispositions d WHERE d.attempt_id=a.attempt_id)" +
                    (" AND a.started_at>=?" if parameters else ""),
                    (provider, *parameters),
                ).fetchone()[0]
                result[provider]["pending_downstream_review"] = int(pending)
            return result
        finally:
            connection.close()

    def pending_downstream_reviews(
        self,
        *,
        limit: int = 16,
        result_artifact_sha256s: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return a bounded identity-complete review queue without mutating it."""
        if limit <= 0:
            raise ValueError("PENDING_DOWNSTREAM_REVIEW_BOUND_INVALID")
        if result_artifact_sha256s is not None:
            if not result_artifact_sha256s:
                return []
            for digest in result_artifact_sha256s:
                self._validate_sha256(digest, "PENDING_DOWNSTREAM_REVIEW_RESULT_HASH_INVALID")
        connection = self.connect()
        try:
            hashes = sorted(result_artifact_sha256s or ())
            artifact_filter = (
                "AND e.sha256 IN (" + ",".join("?" for _ in hashes) + ") "
                if hashes
                else ""
            )
            query = (
                "SELECT a.attempt_id,a.work_unit_id,p.provider,r.disposition AS source_disposition,"
                "r.evidence_sha256 AS source_review_sha256,r.recorded_at AS review_recorded_at,"
                "e.path AS result_artifact_path,e.sha256 AS result_artifact_sha256,"
                "(SELECT pr.task_category FROM pre_routing_decisions pr "
                "WHERE pr.work_unit_id=a.work_unit_id ORDER BY pr.recorded_at DESC,pr.decision_sha256 DESC LIMIT 1) "
                "AS task_category,"
                "(SELECT pr.decision_sha256 FROM pre_routing_decisions pr "
                "WHERE pr.work_unit_id=a.work_unit_id ORDER BY pr.recorded_at DESC,pr.decision_sha256 DESC LIMIT 1) "
                "AS pre_routing_decision_sha256,"
                "(SELECT pr.packet_identity FROM pre_routing_decisions pr "
                "WHERE pr.work_unit_id=a.work_unit_id ORDER BY pr.recorded_at DESC,pr.decision_sha256 DESC LIMIT 1) "
                "AS packet_identity "
                "FROM reviews r JOIN dispatch_attempts a ON a.attempt_id=r.attempt_id "
                "JOIN provider_runs p ON p.attempt_id=a.attempt_id "
                "JOIN execution_artifacts e ON e.attempt_id=a.attempt_id "
                "AND e.artifact_type='PROVIDER_REQUEST_RESPONSE' "
                "WHERE r.disposition IN ('REVIEW_ONLY','ACCEPTED','MODIFIED') AND NOT EXISTS ("
                "SELECT 1 FROM downstream_review_dispositions d WHERE d.attempt_id=a.attempt_id) "
                + artifact_filter
                + "ORDER BY r.recorded_at,a.attempt_id LIMIT ?"
            )
            rows = connection.execute(query, (*hashes, limit)).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def append_event(self, event_type: str, payload: dict[str, Any], *, now: datetime | None = None) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO controller_events(event_type,payload_json,occurred_at) VALUES(?,?,?)",
                (event_type, json.dumps(payload, sort_keys=True, separators=(",", ":")), rfc3339(now or utc_now())),
            )
