from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import parse_rfc3339


class ReadOnlyWatchdog:
    def __init__(self, database: Path, heartbeat_max_age_seconds: int = 90) -> None:
        self.database = database
        self.heartbeat_max_age_seconds = heartbeat_max_age_seconds

    def inspect(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        findings: list[str] = []
        if not self.database.is_file():
            return {
                "result": "INCOMPLETE",
                "scope": "CONTROLLER_DATABASE_AND_HEARTBEAT_HEALTH_ONLY",
                "findings": ["CONTROLLER_DATABASE_MISSING"],
                "controller_alive": False,
                "overall_operational_completion": "INCOMPLETE",
            }
        uri = f"file:{self.database.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).upper()
            leader = connection.execute("SELECT * FROM leader_lease WHERE singleton=1").fetchone()
            if integrity != "ok":
                findings.append("SQLITE_INTEGRITY_FAILURE")
            if mode != "WAL":
                findings.append("SQLITE_NOT_WAL")
            if leader is None:
                findings.append("CONTROLLER_LEADER_MISSING")
                age = None
                alive = False
            else:
                age = max(0.0, (moment - parse_rfc3339(leader["heartbeat_at"])).total_seconds())
                alive = age <= self.heartbeat_max_age_seconds and parse_rfc3339(leader["expires_at"]) >= moment
                if age > self.heartbeat_max_age_seconds:
                    findings.append("CONTROLLER_HEARTBEAT_STALE")
                if parse_rfc3339(leader["expires_at"]) < moment:
                    findings.append("CONTROLLER_LEASE_EXPIRED")
            return {
                "result": "PASS" if not findings else "FAIL",
                "scope": "CONTROLLER_DATABASE_AND_HEARTBEAT_HEALTH_ONLY",
                "findings": findings,
                "controller_alive": alive,
                "heartbeat_age_seconds": age,
                "database_integrity": integrity,
                "journal_mode": mode,
                "leader_owner_id": leader["owner_id"] if leader else None,
                "controller_build_commit": leader["build_commit"] if leader else None,
                "overall_operational_completion": "INCOMPLETE",
            }
        finally:
            connection.close()
