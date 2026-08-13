from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import parse_rfc3339
from .orchestration import ATOMIC_EXECUTABLE, load_inventory, validate_work_unit_roles


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
            unmet_without_packets: list[str] = []
            unmet_pending_review: list[str] = []
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
                        inventory_source_path = self.inventory_path
                    else:
                        inventory_time = parse_rfc3339(str(pointer["refreshed_at"]))
                        snapshot_path = Path(str(pointer["snapshot_path"]))
                        snapshot_data = snapshot_path.read_bytes()
                        if hashlib.sha256(snapshot_data).hexdigest() != pointer.get("snapshot_sha256"):
                            raise ValueError("WATCHDOG_INVENTORY_POINTER_HASH_MISMATCH")
                        snapshot = json.loads(snapshot_data)
                        inventory_source_path = snapshot_path
                    inventory_age = max(0.0, (moment - inventory_time).total_seconds())
                    if inventory_age > self.evidence_max_age_seconds:
                        operational_findings.append("SCHEDULER_INVENTORY_STALE")
                    roles = snapshot.get("work_unit_roles")
                    if roles is not None:
                        if not isinstance(roles, dict):
                            raise ValueError("WATCHDOG_WORK_UNIT_ROLES_INVALID")
                        role_validation = validate_work_unit_roles(
                            load_inventory(inventory_source_path).units, roles
                        )
                        if role_validation != snapshot.get("work_unit_role_validation"):
                            raise ValueError("WATCHDOG_WORK_UNIT_ROLE_VALIDATION_MISMATCH")
                    routable = {"DIRECT_OPENAI", "OPENROUTER", "CURSOR", "LOCAL_QWEN", "REMOTE_CPU_WORKER"}
                    eligible_units = sum(
                        item.get("disposition") in routable
                        and snapshot.get("work_unit_roles", {}).get(
                            str(item.get("work_unit_id")), ATOMIC_EXECUTABLE
                        ) == ATOMIC_EXECUTABLE
                        for item in snapshot.get("route_decisions", [])
                    )
                    demand = snapshot.get("operational_demand", {})
                    if demand.get("enabled") is True:
                        unmet_without_packets = [
                            str(item) for item in demand.get("unmet_without_packets", [])
                        ]
                        if unmet_without_packets:
                            operational_findings.append(
                                "AUTHORIZED_CAMPAIGN_BACKLOG_HAS_NO_EXECUTABLE_PACKETS:"
                                + ",".join(sorted(unmet_without_packets))
                            )
                        unmet_pending_review = [
                            str(item) for item in demand.get("unmet_pending_review", [])
                        ]
                        if unmet_pending_review:
                            operational_findings.append(
                                "CAMPAIGN_REVIEW_BACKLOG_REQUIRES_DISPOSITION:"
                                + ",".join(sorted(unmet_pending_review))
                            )
                    watermarks = snapshot.get("producer_watermarks")
                    if not isinstance(watermarks, dict):
                        operational_findings.append("PRODUCER_WATERMARKS_MISSING")
                    else:
                        sources = watermarks.get("sources", {})
                        if not isinstance(sources, dict) or not sources:
                            operational_findings.append("PRODUCER_WATERMARKS_EMPTY")
                        else:
                            incomplete = sorted(
                                str(name)
                                for name, item in sources.items()
                                if not isinstance(item, dict) or item.get("scan_status") != "PASS"
                            )
                            if incomplete:
                                operational_findings.append(
                                    "PRODUCER_SOURCE_SCAN_INCOMPLETE:" + ",".join(incomplete)
                                )
                except (OSError, KeyError, ValueError, json.JSONDecodeError):
                    operational_findings.append("SCHEDULER_INVENTORY_INVALID")

            scheduler_age = None
            scheduler_dispatched = 0
            scheduler_provider_calls = 0
            latest_scheduler_dispatched = 0
            latest_scheduler_provider_calls = 0
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
                    latest_scheduler_dispatched = int(scheduler_report.get("dispatched_units", 0))
                    latest_scheduler_provider_calls = int(scheduler_report.get("provider_calls", 0))
                    scheduler_idle = len(scheduler_report.get("idle_units", []))
                    if scheduler_age > self.evidence_max_age_seconds:
                        operational_findings.append("SCHEDULER_COMPLETENESS_EVIDENCE_STALE")
                    if scheduler_report.get("result") in {"FAIL", "BLOCKED"}:
                        operational_findings.append("SCHEDULER_EVALUATION_FAILED")
                    if latest_scheduler_provider_calls > latest_scheduler_dispatched:
                        operational_findings.append("SCHEDULER_PROVIDER_CALL_DISPATCH_MISMATCH")
                    if scheduler_idle:
                        operational_findings.append("ELIGIBLE_UNITS_IDLING")
                    if scheduler_report.get("operational_completion") not in {"INCOMPLETE", None}:
                        operational_findings.append("OPERATIONAL_CLAIM_EXCEEDS_EVIDENCE")
                except (OSError, KeyError, ValueError, json.JSONDecodeError):
                    operational_findings.append("SCHEDULER_COMPLETENESS_EVIDENCE_INVALID")

            release_started_at = leader["acquired_at"] if leader else None
            if release_started_at is not None:
                release_runs = connection.execute(
                    "SELECT p.resource_json FROM provider_runs p "
                    "JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                    "WHERE p.status='SETTLED' AND a.state='CLOSED' AND a.started_at>=?",
                    (release_started_at,),
                ).fetchall()
                scheduler_dispatched = len(release_runs)
                for row in release_runs:
                    try:
                        resource = json.loads(row["resource_json"] or "{}")
                        scheduler_provider_calls += int(resource.get("provider_calls", 1))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        operational_findings.append("PROVIDER_RESOURCE_USAGE_INVALID")
                if scheduler_provider_calls > scheduler_dispatched:
                    operational_findings.append("RELEASE_PROVIDER_CALL_DISPATCH_MISMATCH")
            if eligible_units and scheduler_dispatched == 0:
                operational_findings.append("ZERO_DISPATCH_WHILE_ADMITTED_WORK_EXISTS")

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
            closed_without_core_evidence = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND ("
                "(SELECT COUNT(*) FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id WHERE a.work_unit_id=w.work_unit_id AND p.status='SETTLED')=0 OR "
                "(SELECT COUNT(*) FROM validation_results v WHERE v.work_unit_id=w.work_unit_id)=0 OR "
                "(SELECT COUNT(*) FROM reviews r WHERE r.work_unit_id=w.work_unit_id)=0 OR "
                "(SELECT COUNT(*) FROM cleanup_actions c WHERE c.work_unit_id=w.work_unit_id)=0)"
            ).fetchone()[0]
            closed_without_execution_artifacts = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND (NOT EXISTS ("
                "SELECT 1 FROM execution_artifacts e JOIN dispatch_attempts a ON a.attempt_id=e.attempt_id "
                "WHERE a.work_unit_id=w.work_unit_id AND e.artifact_type='PROVIDER_REQUEST_ENVELOPE') OR NOT EXISTS ("
                "SELECT 1 FROM execution_artifacts e JOIN dispatch_attempts a ON a.attempt_id=e.attempt_id "
                "WHERE a.work_unit_id=w.work_unit_id AND e.artifact_type='PROVIDER_REQUEST_RESPONSE'))"
            ).fetchone()[0]
            closed_without_reconciliation = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND NOT EXISTS ("
                "SELECT 1 FROM reconciliation_records r WHERE r.work_unit_id=w.work_unit_id "
                "AND r.jira_identity=w.jira_identity)"
            ).fetchone()[0]
            reconciliation_identity_mismatches = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND EXISTS ("
                "SELECT 1 FROM reconciliation_records r WHERE r.work_unit_id=w.work_unit_id) AND NOT EXISTS ("
                "SELECT 1 FROM reconciliation_records r JOIN dispatch_attempts a "
                "ON a.work_unit_id=w.work_unit_id AND a.result_sha256=r.result_identity "
                "WHERE r.work_unit_id=w.work_unit_id AND r.jira_identity=w.jira_identity "
                "AND a.state='CLOSED' AND a.result_sha256 IS NOT NULL)"
            ).fetchone()[0]
            execution_artifact_identity_mismatches = 0
            if self.operational_audit_enabled:
                artifact_rows = connection.execute(
                    "SELECT e.path,e.sha256,e.bytes FROM execution_artifacts e "
                    "JOIN dispatch_attempts a ON a.attempt_id=e.attempt_id "
                    "JOIN work_units w ON w.work_unit_id=a.work_unit_id "
                    "WHERE w.current_state='CLOSED' AND e.artifact_type IN "
                    "('PROVIDER_REQUEST_ENVELOPE','PROVIDER_REQUEST_RESPONSE')"
                ).fetchall()
                for row in artifact_rows:
                    path = Path(str(row["path"]))
                    try:
                        data = path.read_bytes()
                    except OSError:
                        execution_artifact_identity_mismatches += 1
                        continue
                    if len(data) != int(row["bytes"]) or hashlib.sha256(data).hexdigest() != row["sha256"]:
                        execution_artifact_identity_mismatches += 1
            closed_without_evidence = connection.execute(
                "SELECT COUNT(*) FROM work_units w WHERE w.current_state='CLOSED' AND ("
                "NOT EXISTS (SELECT 1 FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                "WHERE a.work_unit_id=w.work_unit_id AND p.status='SETTLED') OR "
                "NOT EXISTS (SELECT 1 FROM validation_results v WHERE v.work_unit_id=w.work_unit_id) OR "
                "NOT EXISTS (SELECT 1 FROM reviews r WHERE r.work_unit_id=w.work_unit_id) OR "
                "NOT EXISTS (SELECT 1 FROM cleanup_actions c WHERE c.work_unit_id=w.work_unit_id) OR "
                "NOT EXISTS (SELECT 1 FROM execution_artifacts e JOIN dispatch_attempts a ON a.attempt_id=e.attempt_id "
                "WHERE a.work_unit_id=w.work_unit_id AND e.artifact_type='PROVIDER_REQUEST_ENVELOPE') OR "
                "NOT EXISTS (SELECT 1 FROM execution_artifacts e JOIN dispatch_attempts a ON a.attempt_id=e.attempt_id "
                "WHERE a.work_unit_id=w.work_unit_id AND e.artifact_type='PROVIDER_REQUEST_RESPONSE') OR "
                "NOT EXISTS (SELECT 1 FROM reconciliation_records r WHERE r.work_unit_id=w.work_unit_id "
                "AND r.jira_identity=w.jira_identity))"
            ).fetchone()[0]
            if self.operational_audit_enabled and closed_without_core_evidence:
                operational_findings.append("CLOSED_UNIT_EVIDENCE_INCOMPLETE")
            if self.operational_audit_enabled and closed_without_execution_artifacts:
                operational_findings.append("CLOSED_UNIT_EXECUTION_ARTIFACT_MISSING")
            if self.operational_audit_enabled and execution_artifact_identity_mismatches:
                operational_findings.append("CLOSED_UNIT_EXECUTION_ARTIFACT_IDENTITY_MISMATCH")
            if self.operational_audit_enabled and closed_without_reconciliation:
                operational_findings.append("CLOSED_UNIT_RECONCILIATION_MISSING")
            if self.operational_audit_enabled and reconciliation_identity_mismatches:
                operational_findings.append("CLOSED_UNIT_RECONCILIATION_IDENTITY_MISMATCH")
            run_mismatches = connection.execute(
                "SELECT COUNT(*) FROM provider_runs p JOIN dispatch_attempts a ON a.attempt_id=p.attempt_id "
                "WHERE (a.state='CLOSED' AND p.status<>'SETTLED') OR "
                "(p.response_sha256 IS NOT NULL AND a.result_sha256 IS NULL)"
            ).fetchone()[0]
            if self.operational_audit_enabled and run_mismatches:
                operational_findings.append("PROVIDER_RESULT_SETTLEMENT_MISMATCH")
            table_names = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            unjustified_direct_execution = (
                connection.execute(
                    "SELECT COUNT(*) FROM pre_routing_decisions "
                    "WHERE disposition='UNJUSTIFIED_DIRECT_EXECUTION'"
                ).fetchone()[0]
                if "pre_routing_decisions" in table_names
                else 0
            )
            if self.operational_audit_enabled and unjustified_direct_execution:
                operational_findings.append("UNJUSTIFIED_DIRECT_EXECUTION_PRESENT")
            active_operational_incidents = (
                connection.execute(
                    "SELECT COUNT(*) FROM operational_conditions "
                    "WHERE resolved_at IS NULL AND incident_opened=1"
                ).fetchone()[0]
                if "operational_conditions" in table_names
                else 0
            )
            if self.operational_audit_enabled and active_operational_incidents:
                operational_findings.append("ACTIVE_P0_OPERATIONAL_INCIDENTS_PRESENT")
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
                "unmet_campaigns_without_packets": unmet_without_packets,
                "unmet_campaigns_pending_review": unmet_pending_review,
                "scheduler_evidence_age_seconds": scheduler_age,
                "scheduler_dispatched_units": scheduler_dispatched,
                "scheduler_provider_calls": scheduler_provider_calls,
                "scheduler_cached_or_local_reuse_dispatches": max(
                    0, scheduler_dispatched - scheduler_provider_calls
                ),
                "latest_scheduler_evaluation_dispatched_units": latest_scheduler_dispatched,
                "latest_scheduler_evaluation_provider_calls": latest_scheduler_provider_calls,
                "latest_scheduler_evaluation_cached_or_local_reuse_dispatches": max(
                    0, latest_scheduler_dispatched - latest_scheduler_provider_calls
                ),
                "release_evidence_started_at": release_started_at,
                "scheduler_idle_units": scheduler_idle,
                "abandoned_work_leases": int(expired_leases),
                "unreconciled_inflight_provider_attempts": int(inflight_without_lease),
                "closed_units_missing_evidence": int(closed_without_evidence),
                "closed_units_missing_core_evidence": int(closed_without_core_evidence),
                "closed_units_missing_execution_artifacts": int(closed_without_execution_artifacts),
                "closed_unit_execution_artifact_identity_mismatches": int(
                    execution_artifact_identity_mismatches
                ),
                "closed_units_missing_reconciliation": int(closed_without_reconciliation),
                "closed_unit_reconciliation_identity_mismatches": int(
                    reconciliation_identity_mismatches
                ),
                "provider_result_settlement_mismatches": int(run_mismatches),
                "unjustified_direct_execution_count": int(unjustified_direct_execution),
                "active_p0_operational_incidents": int(active_operational_incidents),
                "overall_operational_completion": "INCOMPLETE",
            }
        finally:
            connection.close()
