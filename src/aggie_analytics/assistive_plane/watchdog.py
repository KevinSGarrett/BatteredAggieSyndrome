from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import parse_rfc3339


class ReadOnlyWatchdog:
    def __init__(
        self,
        database: Path,
        heartbeat_max_age_seconds: int = 90,
        *,
        inventory_path: Path | None = None,
        scheduler_report_path: Path | None = None,
        expected_build_commit: str | None = None,
        evidence_max_age_seconds: int = 360,
    ) -> None:
        self.database = database
        self.heartbeat_max_age_seconds = heartbeat_max_age_seconds
        self.operational_audit_enabled = bool(
            inventory_path is not None or scheduler_report_path is not None or expected_build_commit is not None
        )
        runtime_root = database.parent.parent
        self.inventory_path = inventory_path or runtime_root.parent / "inventory" / "current" / "inventory.json"
        self.scheduler_report_path = scheduler_report_path or runtime_root / "evidence" / "current" / "scheduler-evaluation.json"
        self.expected_build_commit = expected_build_commit
        self.evidence_max_age_seconds = evidence_max_age_seconds

    def inspect(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        structural_findings: list[str] = []
        operational_findings: list[str] = []
        if not self.database.is_file():
            return {
                "result": "INCOMPLETE",
                "scope": "STRUCTURAL_AND_OPERATIONAL_READINESS",
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
                structural_findings.append("SQLITE_INTEGRITY_FAILURE")
            if mode != "WAL":
                structural_findings.append("SQLITE_NOT_WAL")
            if leader is None:
                structural_findings.append("CONTROLLER_LEADER_MISSING")
                age = None
                alive = False
            else:
                age = max(0.0, (moment - parse_rfc3339(leader["heartbeat_at"])).total_seconds())
                alive = age <= self.heartbeat_max_age_seconds and parse_rfc3339(leader["expires_at"]) >= moment
                if age > self.heartbeat_max_age_seconds:
                    structural_findings.append("CONTROLLER_HEARTBEAT_STALE")
                if parse_rfc3339(leader["expires_at"]) < moment:
                    structural_findings.append("CONTROLLER_LEASE_EXPIRED")
                if self.expected_build_commit and leader["build_commit"] != self.expected_build_commit:
                    operational_findings.append("CONTROLLER_RELEASE_IDENTITY_MISMATCH")

            inventory_age = None
            eligible_units = 0
            if not self.operational_audit_enabled:
                pass
            elif not self.inventory_path.is_file():
                operational_findings.append("SCHEDULER_INVENTORY_MISSING")
            else:
                try:
                    pointer = json.loads(self.inventory_path.read_text(encoding="utf-8"))
                    if pointer.get("artifact_type") != "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
                        operational_findings.append("SCHEDULER_INVENTORY_POINTER_NOT_RUNTIME_REFRESHED")
                        inventory_time = parse_rfc3339(str(pointer["generated_at"]))
                        snapshot = pointer
                    else:
                        inventory_time = parse_rfc3339(str(pointer["refreshed_at"]))
                        snapshot_path = Path(str(pointer["snapshot_path"]))
                        snapshot_data = snapshot_path.read_bytes()
                        if hashlib.sha256(snapshot_data).hexdigest() != pointer.get("snapshot_sha256"):
                            raise ValueError("WATCHDOG_INVENTORY_POINTER_HASH_MISMATCH")
                        snapshot = json.loads(snapshot_data)
                    inventory_age = max(0.0, (moment - inventory_time).total_seconds())
                    if inventory_age > self.evidence_max_age_seconds:
                        operational_findings.append("SCHEDULER_INVENTORY_STALE")
                    routable = {"DIRECT_OPENAI", "OPENROUTER", "CURSOR", "LOCAL_QWEN", "REMOTE_CPU_WORKER"}
                    eligible_units = sum(
                        item.get("disposition") in routable for item in snapshot.get("route_decisions", [])
                    )
                except (OSError, KeyError, ValueError, json.JSONDecodeError):
                    operational_findings.append("SCHEDULER_INVENTORY_INVALID")

            scheduler_age = None
            scheduler_dispatched = 0
            scheduler_provider_calls = 0
            scheduler_idle = 0
            if not self.operational_audit_enabled:
                pass
            elif not self.scheduler_report_path.is_file():
                operational_findings.append("SCHEDULER_COMPLETENESS_EVIDENCE_MISSING")
            else:
                try:
                    scheduler_report = json.loads(self.scheduler_report_path.read_text(encoding="utf-8"))
                    scheduler_time = parse_rfc3339(str(scheduler_report["observed_at"]))
                    scheduler_age = max(0.0, (moment - scheduler_time).total_seconds())
                    scheduler_dispatched = int(scheduler_report.get("dispatched_units", 0))
                    scheduler_provider_calls = int(scheduler_report.get("provider_calls", 0))
                    scheduler_idle = len(scheduler_report.get("idle_units", []))
                    if scheduler_age > self.evidence_max_age_seconds:
                        operational_findings.append("SCHEDULER_COMPLETENESS_EVIDENCE_STALE")
                    if scheduler_report.get("result") in {"FAIL", "BLOCKED"}:
                        operational_findings.append("SCHEDULER_EVALUATION_FAILED")
                    if scheduler_dispatched != scheduler_provider_calls:
                        operational_findings.append("SCHEDULER_PROVIDER_CALL_DISPATCH_MISMATCH")
                    if eligible_units and scheduler_dispatched == 0:
                        operational_findings.append("ZERO_DISPATCH_WHILE_ADMITTED_WORK_EXISTS")
                    if scheduler_idle:
                        operational_findings.append("ELIGIBLE_UNITS_IDLING")
                    if scheduler_report.get("operational_completion") not in {"INCOMPLETE", None}:
                        operational_findings.append("OPERATIONAL_CLAIM_EXCEEDS_EVIDENCE")
                except (OSError, KeyError, ValueError, json.JSONDecodeError):
                    operational_findings.append("SCHEDULER_COMPLETENESS_EVIDENCE_INVALID")

            expired_leases = connection.execute(
                "SELECT COUNT(*) FROM work_leases WHERE status='ACTIVE' AND expires_at<?",
                (moment.isoformat().replace("+00:00", "Z"),),
            ).fetchone()[0]
            if self.operational_audit_enabled and expired_leases:
                operational_findings.append("ABANDONED_WORK_LEASES_PRESENT")
            inflight_without_lease = connection.execute(
                "SELECT COUNT(*) FROM dispatch_attempts a JOIN work_units w ON w.work_unit_id=a.work_unit_id "
                "WHERE a.state IN ('DISPATCHED','RESULT_RECEIVED') AND w.current_state<>'CLOSED' AND NOT EXISTS ("
                "SELECT 1 FROM work_leases l WHERE l.work_unit_id=w.work_unit_id AND l.status='ACTIVE')"
            ).fetchone()[0]
            if self.operational_audit_enabled and inflight_without_lease:
                operational_findings.append("UNRECONCILED_INFLIGHT_PROVIDER_ATTEMPT")
            closed_without_evidence = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND ("
                "(SELECT COUNT(*) FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id WHERE a.work_unit_id=w.work_unit_id AND p.status='SETTLED')=0 OR "
                "(SELECT COUNT(*) FROM validation_results v WHERE v.work_unit_id=w.work_unit_id)=0 OR "
                "(SELECT COUNT(*) FROM reviews r WHERE r.work_unit_id=w.work_unit_id)=0 OR "
                "(SELECT COUNT(*) FROM cleanup_actions c WHERE c.work_unit_id=w.work_unit_id)=0)"
            ).fetchone()[0]
            if self.operational_audit_enabled and closed_without_evidence:
                operational_findings.append("CLOSED_UNIT_EVIDENCE_INCOMPLETE")
            run_mismatches = connection.execute(
                "SELECT COUNT(*) FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                "WHERE (a.state='CLOSED' AND p.status<>'SETTLED') OR "
                "(p.response_sha256 IS NOT NULL AND a.result_sha256 IS NULL)"
            ).fetchone()[0]
            if self.operational_audit_enabled and run_mismatches:
                operational_findings.append("PROVIDER_RESULT_SETTLEMENT_MISMATCH")
            findings = structural_findings + operational_findings
            return {
                "result": "PASS" if not findings else "FAIL",
                "scope": "STRUCTURAL_AND_OPERATIONAL_READINESS",
                "findings": findings,
                "structural_result": "PASS" if not structural_findings else "FAIL",
                "structural_findings": structural_findings,
                "operational_result": "PASS" if not operational_findings else "FAIL",
                "operational_findings": operational_findings,
                "controller_alive": alive,
                "heartbeat_age_seconds": age,
                "database_integrity": integrity,
                "journal_mode": mode,
                "leader_owner_id": leader["owner_id"] if leader else None,
                "controller_build_commit": leader["build_commit"] if leader else None,
                "inventory_age_seconds": inventory_age,
                "eligible_units": eligible_units,
                "scheduler_evidence_age_seconds": scheduler_age,
                "scheduler_dispatched_units": scheduler_dispatched,
                "scheduler_provider_calls": scheduler_provider_calls,
                "scheduler_idle_units": scheduler_idle,
                "abandoned_work_leases": int(expired_leases),
                "unreconciled_inflight_provider_attempts": int(inflight_without_lease),
                "closed_units_missing_evidence": int(closed_without_evidence),
                "provider_result_settlement_mismatches": int(run_mismatches),
                "overall_operational_completion": "INCOMPLETE",
            }
        finally:
            connection.close()
