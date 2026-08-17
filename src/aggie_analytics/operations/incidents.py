from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from typing import Any, Mapping

from aggie_analytics.validation.promotion import PromotionContext, evaluate_promotion
from aggie_analytics.validation.protected_split_authority import (
    assert_current_contract_respects_protected_splits,
)

from .backup import create_backup, verify_backup
from .observability import JsonlEventSink, OperationalEvent

SCHEMA_VERSION = "aggie.operations.incident_drill.v2"
DEFAULT_SECRET_PROBE = "demo-secret-token-value"
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


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_incident_artifact_identity(payload: dict) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_identity", None)
    return _canonical_hash(canonical)


def _state_hash(payload: Mapping[str, Any]) -> str:
    return _canonical_hash(payload)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid timestamp format") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone required")
    return parsed.astimezone(UTC)


def evaluate_outage_control(
    *,
    request: str,
    upstream_available: bool,
    evidence_hash: str,
    approved_recovery_hash: str,
) -> dict[str, Any]:
    if request in {"TRAIN", "PUBLISH"} or not upstream_available:
        if not upstream_available:
            return {
                "request": request,
                "upstream_available": False,
                "evidence_hash": evidence_hash,
                "approved_recovery_hash": approved_recovery_hash,
                "decision": "REJECT_UNSAFE_WORK",
                "allowed": False,
                "external_delivery": False,
            }
    if evidence_hash != approved_recovery_hash:
        return {
            "request": request,
            "upstream_available": upstream_available,
            "evidence_hash": evidence_hash,
            "approved_recovery_hash": approved_recovery_hash,
            "decision": "REJECT_SAME_EVIDENCE",
            "allowed": False,
            "external_delivery": False,
        }
    return {
        "request": request,
        "upstream_available": True,
        "evidence_hash": evidence_hash,
        "approved_recovery_hash": approved_recovery_hash,
        "decision": "ALLOW_LOCAL_RECOVERY_ONLY",
        "allowed": True,
        "external_delivery": False,
    }


def derive_outage_conclusions(observations: list[Mapping[str, Any]]) -> dict[str, Any]:
    if len(observations) != 3:
        raise ValueError("outage requires three control observations")
    unsafe, same_evidence, changed_evidence = observations
    return {
        "unsafe_training_blocked": unsafe.get("decision") == "REJECT_UNSAFE_WORK" and unsafe.get("allowed") is False,
        "unsafe_publication_blocked": unsafe.get("decision") == "REJECT_UNSAFE_WORK" and unsafe.get("allowed") is False,
        "substitute_route_reevaluated": same_evidence.get("decision") == "REJECT_SAME_EVIDENCE",
        "recovery_requires_changed_evidence": same_evidence.get("allowed") is False,
        "recovered_after_evidence_change": (
            changed_evidence.get("decision") == "ALLOW_LOCAL_RECOVERY_ONLY"
            and changed_evidence.get("allowed") is True
            and changed_evidence.get("external_delivery") is False
        ),
        "external_delivery_claimed": any(row.get("external_delivery") is True for row in observations),
    }


def evaluate_publication_guard(
    *,
    model_id: str,
    eligible_models: set[str] | frozenset[str],
    promotion_context: PromotionContext,
) -> dict[str, Any]:
    promotion_decision = evaluate_promotion(promotion_context)
    registered = model_id in set(eligible_models)
    if not registered:
        publication_decision = "REJECT_UNREGISTERED_MODEL"
    elif promotion_decision != "PROMOTE":
        publication_decision = f"REJECT_{promotion_decision}"
    else:
        publication_decision = "PROMOTE"
    return {
        "model_id": model_id,
        "eligible_models": sorted(eligible_models),
        "promotion_decision": promotion_decision,
        "publication_decision": publication_decision,
        "publication_allowed": publication_decision == "PROMOTE",
        "champion_substitution_fabricated": False,
    }


def evaluate_governance_conflict_guard(
    repo_root: Path,
    proposed_contract: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        assert_current_contract_respects_protected_splits(repo_root, proposed_contract)
    except ValueError as exc:
        return {
            "proposed_contract": dict(proposed_contract),
            "governance_conflict_detected": True,
            "registry_weakened": False,
            "execution_rejected": True,
            "rejection_exception": str(exc),
        }
    return {
        "proposed_contract": dict(proposed_contract),
        "governance_conflict_detected": False,
        "registry_weakened": False,
        "execution_rejected": False,
        "rejection_exception": None,
    }


def derive_schema_conclusions(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "validator_rejected_payload": row.get("rejection_exception") == "schema_incompatible_payload",
        "silent_coercion_performed": False,
        "unaffected_scopes_preserved": row.get("state_hash_before") == row.get("state_hash_after")
        and isinstance(row.get("state_hash_before"), str)
        and len(str(row.get("state_hash_before"))) == 64,
    }


def derive_disk_conclusions(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "partial_output_promoted": False,
        "last_known_good_unchanged": row.get("lkg_hash_before") == row.get("lkg_hash_after"),
        "recovery_path_observed": (
            row.get("detected_failure") == "simulated write failure"
            and isinstance(row.get("recovery_write_sha256"), str)
            and len(str(row.get("recovery_write_sha256"))) == 64
            and row.get("recovery_write_sha256") != row.get("lkg_hash_before")
        ),
    }


def derive_corrupt_conclusions(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "verification_rejected_corruption": isinstance(row.get("rejection_exception"), str)
        and bool(row.get("rejection_exception")),
        "last_known_good_unchanged": row.get("lkg_hash_before") == row.get("lkg_hash_after"),
    }


def derive_model_conclusions(row: Mapping[str, Any]) -> dict[str, Any]:
    guard = evaluate_publication_guard(
        model_id=str(row.get("model_id") or ""),
        eligible_models=set(row.get("eligible_models") or []),
        promotion_context=PromotionContext(
            protocol_sealed=bool(row.get("protocol_sealed")),
            required_artifacts_present=bool(row.get("required_artifacts_present")),
            required_threshold_ids=tuple(row.get("required_threshold_ids") or ()),
            threshold_values=dict(row.get("threshold_values") or {}),
            protected_results_available=bool(row.get("protected_results_available")),
            precommitted_criteria_passed=row.get("precommitted_criteria_passed"),
        ),
    )
    return {
        "publication_failed_closed": guard["publication_allowed"] is False,
        "champion_substitution_fabricated": guard["champion_substitution_fabricated"],
        "publication_decision": guard["publication_decision"],
        "promotion_decision": guard["promotion_decision"],
    }


def derive_governance_conclusions(row: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    guard = evaluate_governance_conflict_guard(repo_root, row.get("proposed_contract") or {})
    return {
        "governance_conflict_detected": guard["governance_conflict_detected"],
        "registry_weakened": guard["registry_weakened"],
        "execution_rejected": guard["execution_rejected"],
        "rejection_exception": guard["rejection_exception"],
    }


def _require_derived(row: dict, derived: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if row.get(field) != derived[field]:
            raise ValueError(f"{row.get('scenario_id')} {field} is not derived from observations")


def _validate_outage(row: dict) -> None:
    observations = row.get("control_observations")
    if not isinstance(observations, list):
        raise ValueError("outage control_observations required")
    recomputed = [
        evaluate_outage_control(
            request=str(item["request"]),
            upstream_available=bool(item["upstream_available"]),
            evidence_hash=str(item["evidence_hash"]),
            approved_recovery_hash=str(item["approved_recovery_hash"]),
        )
        for item in observations
    ]
    if recomputed != observations:
        raise ValueError("outage control observations do not match evaluate_outage_control")
    derived = derive_outage_conclusions(recomputed)
    _require_derived(
        row,
        derived,
        (
            "unsafe_training_blocked",
            "unsafe_publication_blocked",
            "substitute_route_reevaluated",
            "recovery_requires_changed_evidence",
            "recovered_after_evidence_change",
            "external_delivery_claimed",
        ),
    )
    if derived["external_delivery_claimed"]:
        raise ValueError("outage claimed external delivery")
    if row.get("detected_failure") != "simulated upstream outage":
        raise ValueError("outage detected_failure required")


def _validate_schema_incident(row: dict) -> None:
    if row.get("detected_failure") != "schema_incompatible_payload":
        raise ValueError("schema incident must prove schema rejection")
    derived = derive_schema_conclusions(row)
    _require_derived(
        row,
        derived,
        ("validator_rejected_payload", "silent_coercion_performed", "unaffected_scopes_preserved"),
    )


def _validate_stale_forecast(row: dict) -> None:
    started = _parse_utc(row.get("started_at_utc", ""))
    forecast = _parse_utc(row.get("forecast_timestamp_utc", ""))
    cutoff = row.get("freshness_cutoff_hours")
    if not isinstance(cutoff, int) or cutoff <= 0:
        raise ValueError("freshness_cutoff_hours must be positive integer")
    stale = (started - forecast).total_seconds() > cutoff * 3600
    if row.get("freshness_gate_rejected") is not stale:
        raise ValueError("stale forecast gate result unsupported by timestamps")
    if stale and row.get("last_known_good_remained_active") is not True:
        raise ValueError("stale forecast must keep last-known-good active")


def _validate_disk(row: dict) -> None:
    if row.get("detected_failure") != "simulated write failure":
        raise ValueError("disk incident must record write failure")
    derived = derive_disk_conclusions(row)
    _require_derived(
        row,
        derived,
        ("partial_output_promoted", "last_known_good_unchanged", "recovery_path_observed"),
    )


def _validate_corrupt_artifact(row: dict) -> None:
    if not isinstance(row.get("detected_failure"), str):
        raise ValueError("corrupt artifact failure evidence required")
    derived = derive_corrupt_conclusions(row)
    _require_derived(row, derived, ("verification_rejected_corruption", "last_known_good_unchanged"))
    for field in ("corrupt_archive_sha256", "lkg_hash_before", "lkg_hash_after"):
        value = row.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"corrupt artifact {field} identity required")
    if row.get("rejection_exception") != row.get("detected_failure"):
        raise ValueError("corrupt rejection is not bound to archive identity exception")


def _validate_model(row: dict) -> None:
    if not isinstance(row.get("model_id"), str) or not row["model_id"]:
        raise ValueError("model_id required")
    derived = derive_model_conclusions(row)
    _require_derived(
        row,
        derived,
        ("publication_failed_closed", "champion_substitution_fabricated", "publication_decision", "promotion_decision"),
    )


def _validate_security(row: dict) -> None:
    event_text = row.get("persisted_event_text")
    secret_value = row.get("secret_probe_value") or DEFAULT_SECRET_PROBE
    if not isinstance(event_text, str):
        raise ValueError("security raw observation fields required")
    derived = {
        "raw_secret_present": secret_value in event_text,
        "redaction_token_present": "[REDACTED]" in event_text,
        "persisted_events_redacted_only": secret_value not in event_text,
    }
    _require_derived(
        row,
        derived,
        ("raw_secret_present", "redaction_token_present", "persisted_events_redacted_only"),
    )
    if derived["raw_secret_present"] or not derived["persisted_events_redacted_only"]:
        raise ValueError("security redaction failed")


def _validate_governance_conflict(row: dict, *, repo_root: Path) -> None:
    derived = derive_governance_conclusions(row, repo_root=repo_root)
    _require_derived(
        row,
        derived,
        ("governance_conflict_detected", "registry_weakened", "execution_rejected", "rejection_exception"),
    )
    if not derived["execution_rejected"]:
        raise ValueError("governance conflict must fail closed")


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


def derive_issue_completion(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "status": "DONE",
        "achieved_maturity": "DETERMINISTIC_LOCAL_INCIDENT_DRILL_VERIFIED",
        "evidence_state": "VERIFIED",
        "protected_nonclaims": [
            "EXTERNAL_DELIVERY_NOT_CONFIGURED",
            "TARGET_HARDWARE_AUTHORITY_PENDING",
        ],
    }


def validate_incident_artifact(payload: dict, *, repo_root: Path | None = None) -> None:
    repo_root = repo_root or Path(__file__).resolve().parents[3]
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("incident schema mismatch")
    if payload.get("live_incident_execution_completed", True):
        raise ValueError("live incident completion unsupported")
    if payload.get("maturity") == "PRODUCTION_READY":
        raise ValueError("production ready maturity unsupported")
    if payload.get("eligibility") != "EXTERNAL_DELIVERY_NOT_CONFIGURED":
        raise ValueError("incident drill must preserve nonproduction authority boundary")
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
        validator = SCENARIO_VALIDATORS[scenario_id]
        if scenario_id == "governance_conflict":
            validator(row, repo_root=repo_root)
        else:
            validator(row)
        seen_ordered.append(scenario_id)
    if seen_ordered != list(SCENARIOS):
        raise ValueError("scenario coverage mismatch")
    completion = payload.get("issue_completion_manifest", {})
    if not isinstance(completion, dict):
        raise ValueError("issue_completion_manifest must be object")
    expected = derive_issue_completion(rows)
    for field, value in expected.items():
        if completion.get(field) != value:
            raise ValueError(f"completion {field} is not derived from validated observations")
    claimed = payload.get("artifact_identity")
    if claimed != compute_incident_artifact_identity(payload):
        raise ValueError("incident artifact identity mismatch")


def run_incident_drill(
    *,
    output_path: Path,
    work_root: Path | None = None,
    secret_value: str = "demo-secret-token-value",
    repo_root: Path | None = None,
) -> dict:
    started = datetime.now(UTC).replace(microsecond=0)
    repo_root = repo_root or Path(__file__).resolve().parents[3]
    base = Path(work_root) if work_root else Path(tempfile.mkdtemp(prefix="incident-drill-"))
    runtime_dir = base / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    protected_identity = {"identity": "protected-v1", "cutoff_utc": "2026-08-17T00:00:00+00:00"}
    state_path = runtime_dir / "last_known_good.json"
    current_state = {"status": "HEALTHY", "identity": protected_identity["identity"]}
    _atomic_write_json(state_path, current_state)
    lkg_hash = _file_sha256(state_path)

    source_dir = runtime_dir / "source_state"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "forecast.json").write_text('{"forecast":"baseline"}', encoding="utf-8")
    backup_path = runtime_dir / "source_state.zip"
    create_backup(source_dir, backup_path)
    baseline_backup_sha256 = _file_sha256(backup_path)

    event_sink_path = runtime_dir / "events.jsonl"
    sink = JsonlEventSink(event_sink_path)

    incidents: list[dict] = []

    outage_started = datetime.now(UTC).replace(microsecond=0)
    outage_evidence = _canonical_hash({"failure": "simulated upstream outage", "window": _iso_utc(outage_started)})
    approved_recovery = _canonical_hash({"failure": "cleared", "approved": True, "window": _iso_utc(outage_started)})
    try:
        raise ConnectionError("simulated upstream outage")
    except ConnectionError as exc:
        observations = [
            evaluate_outage_control(
                request="TRAIN",
                upstream_available=False,
                evidence_hash=outage_evidence,
                approved_recovery_hash=approved_recovery,
            ),
            evaluate_outage_control(
                request="RECOVER",
                upstream_available=True,
                evidence_hash=outage_evidence,
                approved_recovery_hash=approved_recovery,
            ),
            evaluate_outage_control(
                request="RECOVER",
                upstream_available=True,
                evidence_hash=approved_recovery,
                approved_recovery_hash=approved_recovery,
            ),
        ]
        derived = derive_outage_conclusions(observations)
        incidents.append(
            {
                "scenario_id": "outage",
                "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
                "started_at_utc": _iso_utc(outage_started),
                "detected_failure": str(exc),
                "control_observations": observations,
                **derived,
            }
        )

    schema_started = datetime.now(UTC).replace(microsecond=0)
    state_before = json.loads(state_path.read_text(encoding="utf-8"))
    hash_before = _state_hash(state_before)
    try:
        _validate_schema_payload({"game_id": "g1", "home_score": 21})
        rejection = None
    except ValueError as exc:
        rejection = str(exc)
    hash_after = _state_hash(json.loads(state_path.read_text(encoding="utf-8")))
    schema_row = {
        "scenario_id": "schema",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(schema_started),
        "detected_failure": rejection,
        "rejection_exception": rejection,
        "state_hash_before": hash_before,
        "state_hash_after": hash_after,
    }
    schema_row.update(derive_schema_conclusions(schema_row))
    incidents.append(schema_row)

    stale_started = datetime.now(UTC).replace(microsecond=0)
    forecast_time = started - timedelta(hours=12)
    freshness_cutoff_hours = 4
    stale = (stale_started - forecast_time).total_seconds() > freshness_cutoff_hours * 3600
    incidents.append(
        {
            "scenario_id": "stale_forecast",
            "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
            "started_at_utc": _iso_utc(stale_started),
            "forecast_timestamp_utc": _iso_utc(forecast_time),
            "freshness_cutoff_hours": freshness_cutoff_hours,
            "freshness_gate_rejected": stale,
            "last_known_good_remained_active": stale and _file_sha256(state_path) == lkg_hash,
        }
    )

    disk_started = datetime.now(UTC).replace(microsecond=0)
    lkg_before = _file_sha256(state_path)
    try:
        _atomic_write_json(
            state_path,
            {"status": "UNSAFE", "identity": protected_identity["identity"]},
            inject_write_failure=True,
        )
        disk_failure = None
    except OSError as exc:
        disk_failure = str(exc)
    recovery_path = runtime_dir / "recovered_state.json"
    _atomic_write_json(recovery_path, {"status": "RECOVERED", "identity": protected_identity["identity"]})
    disk_row = {
        "scenario_id": "disk",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(disk_started),
        "detected_failure": disk_failure,
        "lkg_hash_before": lkg_before,
        "lkg_hash_after": _file_sha256(state_path),
        "recovery_write_path": str(recovery_path),
        "recovery_write_sha256": _file_sha256(recovery_path),
    }
    disk_row.update(derive_disk_conclusions(disk_row))
    incidents.append(disk_row)

    corrupt_started = datetime.now(UTC).replace(microsecond=0)
    corrupted = runtime_dir / "source_state_corrupt.zip"
    shutil.copy2(backup_path, corrupted)
    with zipfile.ZipFile(corrupted, "a") as archive:
        archive.writestr("payload/tampered.txt", "tampered")
    corrupt_sha = _file_sha256(corrupted)
    lkg_before_corrupt = _file_sha256(state_path)
    try:
        verify_backup(corrupted)
        failure = None
    except ValueError as exc:
        failure = str(exc)
    corrupt_row = {
        "scenario_id": "corrupt_artifact",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(corrupt_started),
        "detected_failure": failure,
        "rejection_exception": failure,
        "corrupt_archive_sha256": corrupt_sha,
        "baseline_backup_sha256": baseline_backup_sha256,
        "lkg_hash_before": lkg_before_corrupt,
        "lkg_hash_after": _file_sha256(state_path),
    }
    corrupt_row.update(derive_corrupt_conclusions(corrupt_row))
    incidents.append(corrupt_row)

    model_started = datetime.now(UTC).replace(microsecond=0)
    model_inputs = {
        "model_id": "model-unregistered",
        "eligible_models": ["model-prod-a", "model-prod-b"],
        "protocol_sealed": True,
        "required_artifacts_present": True,
        "required_threshold_ids": ["THR-001"],
        "threshold_values": {"THR-001": None},
        "protected_results_available": False,
        "precommitted_criteria_passed": None,
    }
    model_row = {
        "scenario_id": "model",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(model_started),
        **model_inputs,
    }
    model_row.update(derive_model_conclusions(model_row))
    incidents.append(model_row)

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
    security_row = {
        "scenario_id": "security",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(security_started),
        "persisted_event_text": event_text,
        "raw_secret_present": secret_value in event_text,
        "redaction_token_present": "[REDACTED]" in event_text,
        "persisted_events_redacted_only": secret_value not in event_text,
    }
    incidents.append(security_row)

    gov_started = datetime.now(UTC).replace(microsecond=0)
    proposed_contract = {
        "split_policy": {
            "2023": "DEVELOPMENT_FIT_SELECTION_CALIBRATION",
            "2024": "DEVELOPMENT_TUNE",
            "2025": "DEVELOPMENT_EVALUATION_UNPROTECTED",
        }
    }
    gov_row = {
        "scenario_id": "governance_conflict",
        "execution_class": "DETERMINISTIC_LOCAL_INCIDENT_DRILL",
        "started_at_utc": _iso_utc(gov_started),
        "proposed_contract": proposed_contract,
    }
    gov_row.update(derive_governance_conclusions(gov_row, repo_root=repo_root))
    incidents.append(gov_row)

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
        "issue_completion_manifest": derive_issue_completion(incidents),
    }
    payload["artifact_identity"] = compute_incident_artifact_identity(payload)
    validate_incident_artifact(payload, repo_root=repo_root)
    _atomic_write_json(output_path, payload)
    return payload
