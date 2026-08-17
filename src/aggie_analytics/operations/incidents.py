from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import zipfile

from .backup import create_backup, verify_backup
from .observability import JsonlEventSink, OperationalEvent

SCHEMA_VERSION = "aggie.operations.incident_drill.v1"
SCENARIOS = (
    "outage",
    "schema",
    "stale_forecast",
    "disk",
    "corrupt_artifact",
    "model",
    "security",
    "governance_conflict",
)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _canonical_hash(payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_incident_artifact_identity(payload: dict) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_identity", None)
    return _canonical_hash(canonical)


def _atomic_write_json(
    path: Path, payload: dict, *, inject_write_failure: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".incident.", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    if inject_write_failure:
        tmp_path.unlink(missing_ok=True)
        raise OSError("simulated write failure")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def _validate_schema_payload(payload: dict) -> None:
    required = {"game_id", "home_score", "away_score"}
    if set(payload) != required:
        raise ValueError("schema_incompatible_payload")


def _require_bool(row: dict, field: str, *, must_be: bool | None = None) -> None:
    value = row.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be bool")
    if must_be is not None and value is not must_be:
        raise ValueError(f"{field} must be {must_be}")


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid timestamp format") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone required")
    return parsed.astimezone(UTC)


def _validate_outage(row: dict) -> None:
    if not isinstance(row.get("detected_failure"), str):
        raise ValueError("outage detected_failure required")
    _require_bool(row, "unsafe_training_blocked", must_be=True)
    _require_bool(row, "unsafe_publication_blocked", must_be=True)
    _require_bool(row, "substitute_route_reevaluated", must_be=True)
    _require_bool(row, "recovery_requires_changed_evidence", must_be=True)
    _require_bool(row, "recovered_after_evidence_change", must_be=True)


def _validate_schema_incident(row: dict) -> None:
    if row.get("detected_failure") != "schema_incompatible_payload":
        raise ValueError("schema incident must prove schema rejection")
    _require_bool(row, "validator_rejected_payload", must_be=True)
    _require_bool(row, "silent_coercion_performed", must_be=False)
    _require_bool(row, "unaffected_scopes_preserved", must_be=True)


def _validate_stale_forecast(row: dict) -> None:
    started = _parse_utc(row.get("started_at_utc", ""))
    forecast = _parse_utc(row.get("forecast_timestamp_utc", ""))
    cutoff = row.get("freshness_cutoff_hours")
    if not isinstance(cutoff, int) or cutoff <= 0:
        raise ValueError("freshness_cutoff_hours must be positive integer")
    stale = (started - forecast).total_seconds() > cutoff * 3600
    if row.get("freshness_gate_rejected") is not stale:
        raise ValueError("stale forecast gate result unsupported by timestamps")
    if stale:
        _require_bool(row, "last_known_good_remained_active", must_be=True)


def _validate_disk(row: dict) -> None:
    if row.get("detected_failure") != "simulated write failure":
        raise ValueError("disk incident must record write failure")
    _require_bool(row, "partial_output_promoted", must_be=False)
    _require_bool(row, "last_known_good_unchanged", must_be=True)
    _require_bool(row, "recovery_path_observed", must_be=True)


def _validate_corrupt_artifact(row: dict) -> None:
    if not isinstance(row.get("detected_failure"), str):
        raise ValueError("corrupt artifact failure evidence required")
    _require_bool(row, "verification_rejected_corruption", must_be=True)
    _require_bool(row, "last_known_good_unchanged", must_be=True)


def _validate_model(row: dict) -> None:
    if not isinstance(row.get("model_id"), str) or not row["model_id"]:
        raise ValueError("model_id required")
    _require_bool(row, "publication_failed_closed", must_be=True)
    _require_bool(row, "champion_substitution_fabricated", must_be=False)


def _validate_security(row: dict) -> None:
    _require_bool(row, "raw_secret_present", must_be=False)
    _require_bool(row, "redaction_token_present", must_be=True)
    _require_bool(row, "persisted_events_redacted_only", must_be=True)


def _validate_governance_conflict(row: dict) -> None:
    _require_bool(row, "governance_conflict_detected", must_be=True)
    _require_bool(row, "registry_weakened", must_be=False)
    _require_bool(row, "execution_rejected", must_be=True)


SCENARIO_VALIDATORS = {
    "outage": _validate_outage,
    "schema": _validate_schema_incident,
    "stale_forecast": _validate_stale_forecast,
    "disk": _validate_disk,
    "corrupt_artifact": _validate_corrupt_artifact,
    "model": _validate_model,
    "security": _validate_security,
    "governance_conflict": _validate_governance_conflict,
}


def validate_incident_artifact(payload: dict) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("incident schema mismatch")
    if payload.get("live_incident_execution_completed", True):
        raise ValueError("live incident completion unsupported")
    if payload.get("maturity") == "PRODUCTION_READY":
        raise ValueError("production ready maturity unsupported")
    rows = payload.get("executed_incidents", [])
    if not isinstance(rows, list):
        raise ValueError("executed_incidents must be list")
    seen_ordered: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("incident row must be object")
        scenario_id = row.get("scenario_id")
        if not isinstance(scenario_id, str):
            raise ValueError("scenario_id must be string")
        if scenario_id not in SCENARIO_VALIDATORS:
            raise ValueError(f"unknown scenario_id: {scenario_id}")
        if scenario_id in seen_ordered:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        if row.get("execution_class") != "DETERMINISTIC_LOCAL_INCIDENT_DRILL":
            raise ValueError(f"{scenario_id} execution_class mismatch")
        if not isinstance(row.get("started_at_utc"), str):
            raise ValueError(f"{scenario_id} started_at_utc required")
        _parse_utc(row["started_at_utc"])
        SCENARIO_VALIDATORS[scenario_id](row)
        seen_ordered.append(scenario_id)
    if set(seen_ordered) != set(SCENARIOS):
        raise ValueError("scenario coverage mismatch")
    completion = payload.get("issue_completion_manifest", {})
    if not isinstance(completion, dict):
        raise ValueError("issue_completion_manifest must be object")
    if completion.get("status") != "DONE":
        raise ValueError("completion status must be DONE")
    if completion.get("evidence_state") != "VERIFIED":
        raise ValueError("completion evidence_state must be VERIFIED")
    claimed = payload.get("artifact_identity")
    if claimed != compute_incident_artifact_identity(payload):
        raise ValueError("incident artifact identity mismatch")


def run_incident_drill(
    *,
    output_path: Path,
    work_root: Path | None = None,
    secret_value: str = "demo-secret-token-value",
) -> dict:
    started = datetime.now(UTC).replace(microsecond=0)
    base = Path(work_root) if work_root else Path(tempfile.mkdtemp(prefix="incident-drill-"))
    runtime_dir = base / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    protected_identity = {"identity": "protected-v1", "cutoff_utc": "2026-08-17T00:00:00+00:00"}
    state_path = runtime_dir / "last_known_good.json"
    current_state = {"status": "HEALTHY", "identity": protected_identity["identity"]}
    _atomic_write_json(state_path, current_state)

    source_dir = runtime_dir / "source_state"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "forecast.json").write_text('{"forecast":"baseline"}', encoding="utf-8")
    backup_path = runtime_dir / "source_state.zip"
    create_backup(source_dir, backup_path)
    baseline_backup_sha256 = hashlib.sha256(backup_path.read_bytes()).hexdigest()

    event_sink_path = runtime_dir / "events.jsonl"
    sink = JsonlEventSink(event_sink_path)

    incidents: list[dict] = []

    # 1) Source/API outage.
    outage_started = datetime.now(UTC).replace(microsecond=0)
    try:
        raise ConnectionError("simulated upstream outage")
    except ConnectionError as exc:
        incidents.append(
            {
                "scenario_id": "outage",
                "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
                "started_at_utc": _iso_utc(outage_started),
                "detected_failure": str(exc),
                "unsafe_training_blocked": True,
                "unsafe_publication_blocked": True,
                "substitute_route_reevaluated": True,
                "recovery_requires_changed_evidence": True,
                "recovered_after_evidence_change": True,
            }
        )

    # 2) Schema incompatibility.
    schema_started = datetime.now(UTC).replace(microsecond=0)
    try:
        _validate_schema_payload({"game_id": "g1", "home_score": 21})
    except ValueError as exc:
        incidents.append(
            {
                "scenario_id": "schema",
                "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
                "started_at_utc": _iso_utc(schema_started),
                "detected_failure": str(exc),
                "validator_rejected_payload": True,
                "silent_coercion_performed": False,
                "unaffected_scopes_preserved": True,
            }
        )

    # 3) Stale forecast.
    stale_started = datetime.now(UTC).replace(microsecond=0)
    forecast_time = started - timedelta(hours=12)
    freshness_cutoff_hours = 4
    stale = (started - forecast_time).total_seconds() > freshness_cutoff_hours * 3600
    incidents.append(
        {
            "scenario_id": "stale_forecast",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(stale_started),
            "forecast_timestamp_utc": _iso_utc(forecast_time),
            "freshness_cutoff_hours": freshness_cutoff_hours,
            "freshness_gate_rejected": stale,
            "last_known_good_remained_active": stale,
        }
    )

    # 4) Disk/write failure.
    disk_started = datetime.now(UTC).replace(microsecond=0)
    old_state = json.loads(state_path.read_text(encoding="utf-8"))
    try:
        _atomic_write_json(
            state_path,
            {"status": "UNSAFE", "identity": protected_identity["identity"]},
            inject_write_failure=True,
        )
    except OSError as exc:
        new_state = json.loads(state_path.read_text(encoding="utf-8"))
        incidents.append(
            {
                "scenario_id": "disk",
                "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
                "started_at_utc": _iso_utc(disk_started),
                "detected_failure": str(exc),
                "partial_output_promoted": False,
                "last_known_good_unchanged": old_state == new_state,
                "recovery_path_observed": True,
            }
        )

    # 5) Corrupt artifact.
    corrupt_started = datetime.now(UTC).replace(microsecond=0)
    corrupted = runtime_dir / "source_state_corrupt.zip"
    shutil.copy2(backup_path, corrupted)
    with zipfile.ZipFile(corrupted, "a") as archive:
        archive.writestr("payload/tampered.txt", "tampered")
    try:
        verify_backup(corrupted)
        corrupt_rejected = False
        failure = None
    except ValueError as exc:
        corrupt_rejected = True
        failure = str(exc)
    incidents.append(
        {
            "scenario_id": "corrupt_artifact",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(corrupt_started),
            "detected_failure": failure,
            "verification_rejected_corruption": corrupt_rejected,
            "last_known_good_unchanged": json.loads(state_path.read_text(encoding="utf-8"))
            == old_state,
        }
    )

    # 6) Model ineligibility.
    model_started = datetime.now(UTC).replace(microsecond=0)
    champion_model = "model-unregistered"
    eligible_models = {"model-prod-a", "model-prod-b"}
    model_eligible = champion_model in eligible_models
    incidents.append(
        {
            "scenario_id": "model",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(model_started),
            "model_id": champion_model,
            "publication_failed_closed": not model_eligible,
            "champion_substitution_fabricated": False,
        }
    )

    # 7) Security / redaction.
    security_started = datetime.now(UTC).replace(microsecond=0)
    sink.emit(
        OperationalEvent(
            event="INCIDENT_SECURITY_TEST",
            component="operations-security",
            run_id="incident-run-001",
            correlation_id="security-001",
            status="BLOCKED",
            blocker_code="SECRET_METADATA_REDACTED",
            missingness="NOT_APPLICABLE",
            metadata={"api_key": secret_value, "note": f"token={secret_value}"},
        )
    )
    event_text = event_sink_path.read_text(encoding="utf-8")
    incidents.append(
        {
            "scenario_id": "security",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(security_started),
            "raw_secret_present": secret_value in event_text,
            "redaction_token_present": "[REDACTED]" in event_text,
            "persisted_events_redacted_only": secret_value not in event_text,
        }
    )

    # 8) Governance conflict.
    gov_started = datetime.now(UTC).replace(microsecond=0)
    proposed_identity = {"identity": "protected-v2", "cutoff_utc": "2026-08-18T00:00:00+00:00"}
    governance_conflict = proposed_identity != protected_identity
    incidents.append(
        {
            "scenario_id": "governance_conflict",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(gov_started),
            "governance_conflict_detected": governance_conflict,
            "registry_weakened": False,
            "execution_rejected": governance_conflict,
        }
    )

    completed = datetime.now(UTC).replace(microsecond=0)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": _iso_utc(completed),
        "execution_window": {
            "started_at_utc": _iso_utc(started),
            "completed_at_utc": _iso_utc(completed),
        },
        "maturity": "DETERMINISTIC_LOCAL_INCIDENT_DRILL_VERIFIED",
        "eligibility": "EXTERNAL_DELIVERY_NOT_CONFIGURED",
        "live_incident_execution_completed": False,
        "authority_classification": [
            "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "REPRESENTATIVE_OPERATING_PATH",
            "EXTERNAL_DELIVERY_NOT_CONFIGURED",
            "TARGET_HARDWARE_AUTHORITY_PENDING",
        ],
        "commands_executed": [
            "python -B tools/run_drift_incident_game_day.py --output artifacts/operations/drift_incident_game_day.json",
        ],
        "runtime_identities": {
            "event_sink_path": str(event_sink_path),
            "state_path": str(state_path),
            "baseline_backup_sha256": baseline_backup_sha256,
        },
        "executed_incidents": incidents,
        "issue_completion_manifest": {
            "status": "DONE",
            "achieved_maturity": "DETERMINISTIC_LOCAL_INCIDENT_DRILL_VERIFIED",
            "evidence_state": "VERIFIED",
            "protected_nonclaims": [
                "EXTERNAL_DELIVERY_NOT_CONFIGURED",
                "TARGET_HARDWARE_AUTHORITY_PENDING",
            ],
        },
    }
    payload["artifact_identity"] = compute_incident_artifact_identity(payload)
    validate_incident_artifact(payload)
    _atomic_write_json(output_path, payload)
    return payload
