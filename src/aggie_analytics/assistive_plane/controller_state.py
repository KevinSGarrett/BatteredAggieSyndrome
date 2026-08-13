from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 2
ALLOWED_STATES = {
    "DISCOVERED",
    "ELIGIBLE",
    "ADMITTED",
    "LEASED",
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
TERMINAL_STATES = {"ACCEPTED", "MODIFIED", "REVIEW_ONLY", "QUARANTINED", "REJECTED", "FAILED", "CANCELLED", "DEAD_LETTER"}


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
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def owner_pid(owner_id: str) -> int:
    parts = owner_id.split(":")
    if len(parts) < 3:
        raise RuntimeError("CONTROLLER_RECOVERY_OWNER_ID_FORMAT_INVALID")
    try:
        return int(parts[1])
    except ValueError as exc:  # pragma: no cover - explicit defensive path
        raise RuntimeError("CONTROLLER_RECOVERY_OWNER_ID_FORMAT_INVALID") from exc


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
                """
            )
            existing = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if existing and int(existing[0]) > SCHEMA_VERSION:
                raise RuntimeError("CONTROLLER_SCHEMA_NEWER_THAN_CODE")
            connection.execute(
                "INSERT INTO metadata(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            connection.commit()
        finally:
            connection.close()

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
        if len(recovery_evidence_sha256) != 64:
            raise ValueError("RECOVERY_EVIDENCE_IDENTITY_INVALID")
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

    def register_work_unit(self, *, work_unit_id: str, identity_sha256: str, jira_identity: str, effort_points: int, actor: str, now: datetime | None = None) -> None:
        if effort_points not in {1, 2, 3, 5, 8}:
            raise ValueError("INVALID_PRE_ROUTING_EFFORT")
        if len(identity_sha256) != 64:
            raise ValueError("WORK_UNIT_IDENTITY_INVALID")
        stamp = rfc3339(now or utc_now())
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM work_units WHERE work_unit_id=?", (work_unit_id,)).fetchone()
            if row:
                expected = (identity_sha256, jira_identity, effort_points)
                observed = (row["identity_sha256"], row["jira_identity"], row["effort_points"])
                if observed != expected:
                    raise RuntimeError("IMMUTABLE_WORK_UNIT_IDENTITY_CONFLICT")
                return
            connection.execute(
                "INSERT INTO work_units(work_unit_id,identity_sha256,jira_identity,effort_points,current_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (work_unit_id, identity_sha256, jira_identity, effort_points, "DISCOVERED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO transitions(work_unit_id,from_state,to_state,reason,actor,occurred_at,unit_version) VALUES(?,?,?,?,?,?,0)",
                (work_unit_id, None, "DISCOVERED", "REGISTERED", actor, stamp),
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

    def status(self) -> dict[str, Any]:
        connection = self.connect()
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
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
            return {
                "schema_version": SCHEMA_VERSION,
                "database": str(self.database),
                "journal_mode": str(mode).upper(),
                "integrity_check": integrity,
                "leader": dict(leader) if leader else None,
                "work_unit_counts": counts,
                "scheduler_cycles": int(cycle_summary["cycles"]),
                "scheduler_dispatched_units": int(cycle_summary["dispatched"]),
                "scheduler_no_change_cycles": int(cycle_summary["no_change"]),
                "scheduler_latest_cycle": dict(latest_cycle) if latest_cycle else None,
                "active_idle_intervals": int(active_idle),
            }
        finally:
            connection.close()

    def append_event(self, event_type: str, payload: dict[str, Any], *, now: datetime | None = None) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO controller_events(event_type,payload_json,occurred_at) VALUES(?,?,?)",
                (event_type, json.dumps(payload, sort_keys=True, separators=(",", ":")), rfc3339(now or utc_now())),
            )
