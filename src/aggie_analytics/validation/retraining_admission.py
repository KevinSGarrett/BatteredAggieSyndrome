from __future__ import annotations

import hashlib
import json
from typing import Any


MATERIAL_KINDS = {
    "ADDITIONAL_ELIGIBLE_SEASONS_OR_GAMES",
    "MATERIAL_DOMAIN_COVERAGE_INCREASE",
    "MEANINGFUL_MISSINGNESS_REDUCTION",
    "TRAINING_POPULATION_SCHEMA_CHANGE",
    "TRAINING_POPULATION_RECONCILIATION_CHANGE",
    "NEW_PIT_SAFE_FEATURE_FAMILY",
    "CONSEQUENTIAL_DATA_DEFECT_CORRECTION",
    "PREDECLARED_SCIENTIFIC_COMPARISON",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def decide(request: dict[str, Any]) -> dict[str, Any]:
    required = {
        "old_dataset_identity",
        "new_dataset_identity",
        "training_eligible",
        "observed_deltas",
        "material_changes",
    }
    missing = sorted(required - set(request))
    invalid: list[str] = [f"missing:{item}" for item in missing]
    changes = request.get("material_changes", [])
    for index, change in enumerate(changes):
        if change.get("kind") not in MATERIAL_KINDS:
            invalid.append(f"material_changes[{index}]:kind")
        if change.get("material") is True and not change.get("evidence_identity"):
            invalid.append(f"material_changes[{index}]:evidence_identity")
        if change.get("material") is True and not str(change.get("rationale", "")).strip():
            invalid.append(f"material_changes[{index}]:rationale")
    if invalid:
        action = "REJECT_INVALID_EVIDENCE"
    elif request["training_eligible"] and any(change.get("material") is True for change in changes):
        action = "FULL_LADDER_RETRAINING_ADMITTED"
    else:
        action = "FOCUSED_INTEGRATION_REPLAY_ONLY"
    decision = {
        "schema_version": "1.0.0",
        "artifact_type": "RETRAINING_ADMISSION_DECISION",
        "policy_id": "evidence-based-retraining-admission-v1",
        "request": request,
        "action": action,
        "invalid_findings": invalid,
        "full_ladder_required": action == "FULL_LADDER_RETRAINING_ADMITTED",
        "classification": "PRELIMINARY_UNPROTECTED",
        "protected_promotion_authority": False,
    }
    decision["decision_identity"] = hashlib.sha256(canonical_json(decision)).hexdigest()
    return decision


def validate_decision(decision: dict[str, Any]) -> list[str]:
    body = dict(decision)
    identity = body.pop("decision_identity", None)
    failures: list[str] = []
    if identity != hashlib.sha256(canonical_json(body)).hexdigest():
        failures.append("decision_identity")
    replay = decide(decision.get("request", {}))
    if replay.get("action") != decision.get("action"):
        failures.append("deterministic_action")
    if decision.get("protected_promotion_authority") is not False:
        failures.append("protected_promotion_authority")
    return failures
