"""Cycle #27 semantic pin successor for the R26-22 bound-authority disposition.

The Cycle #26 disposition pins ``0070c1...`` while the referenced pair-audit
artifact reconstructs to ``e77195d...``. This successor does not edit that
disposition in place and does not accept a mismatched hash. It binds only an
independently reconstructed identity of the referenced audit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (
    CONSERVATIVE_BOUND,
    OBSERVED_EFFECTIVE,
    OBSERVED_PUBLICATION,
    canonical_json_bytes,
    operational_pit_admission_allowed,
    sha256_bytes,
)
from aggie_analytics.data.week1_2026_fitted_path_temporal_authority import (
    FittedPathTemporalAuthorityError,
    assess_fitted_path_temporal_authority,
)

SCHEMA_VERSION = "aggie.data.cycle27_r26_22_bound_authority_disposition.v1"
CONTRACT_ID = "CYCLE27-R26-22-BOUND-AUTHORITY-DISPOSITION-V1"
JIRA_KEY = "BAT-690"
LOCAL_ISSUE_ID = "POST-TASK-CYCLE27-R26-22-PIN-SUCCESSOR-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "CONDITIONAL_CHRONOLOGY_PROXY_NOT_UNIVERSAL_GUARANTEE"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
BLOCKED_STATUS = "BLOCKED"
FINDING_ID = "R26-22"
ARTIFACT_TYPE = "CYCLE27_R26_22_BOUND_AUTHORITY_DISPOSITION"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_R26_22_BOUND_AUTHORITY_DISPOSITION.json"
)
PREDECESSOR_DISPOSITION_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_R26_22_BOUND_AUTHORITY_DISPOSITION.json"
)
PAIR_AUDIT_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT.json"
)
MISMATCHED_PREDECESSOR_PIN = (
    "0070c1e33b5fdc2c23c6453cfa3c50e95cbc1c0adf9a8f6ce0e0e41141f6f548"
)
C26_WEEK1_GATE_IDENTITY = (
    "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43"
)
C26_WEEK1_DATASET_IDENTITY = (
    "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
)


class R2622PinSuccessorError(ValueError):
    """Raised when the R26-22 pin cannot be resolved semantically."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def reconstruct_gate_identity(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "gate_identity"}
    return sha256_bytes(canonical_json_bytes(body))


def resolve_referenced_audit_identity(
    audit: Mapping[str, Any],
    *,
    claimed_identity: str | None = None,
    accept_mismatched_hash: bool = False,
) -> dict[str, Any]:
    """Bind the referenced audit only when declared and reconstructed identities agree."""

    if accept_mismatched_hash:
        raise R2622PinSuccessorError(
            "manual mismatched-hash acceptance is forbidden; resolve semantically"
        )
    reconstructed = reconstruct_gate_identity(audit)
    declared = audit.get("gate_identity")
    if not isinstance(declared, str) or not declared:
        raise R2622PinSuccessorError("referenced audit is missing gate_identity")
    if declared != reconstructed:
        raise R2622PinSuccessorError(
            "referenced audit declared gate_identity does not reconstruct: "
            f"declared={declared} reconstructed={reconstructed}"
        )
    if claimed_identity is not None and claimed_identity != reconstructed:
        raise R2622PinSuccessorError(
            "claimed pair_audit_gate_identity does not resolve the referenced audit: "
            f"claimed={claimed_identity} reconstructed={reconstructed}"
        )
    return {
        "declared_gate_identity": declared,
        "reconstructed_gate_identity": reconstructed,
        "resolved_identity": reconstructed,
        "resolution": "SEMANTICALLY_RESOLVED",
        "manual_mismatched_hash_acceptance": False,
    }


def assess_clean_slice(
    *,
    proven_pit_training_row_count: int,
    proven_pit_domains: int,
    training_row_count: int,
    global_domain_flag_promotion: bool = False,
    fabricated_whistle_timestamps: bool = False,
) -> dict[str, Any]:
    """A domain flag or invented whistle clock cannot mint a proven-PIT slice."""

    if fabricated_whistle_timestamps:
        raise R2622PinSuccessorError(
            "fabricated whistle timestamps cannot create a proven-PIT slice"
        )
    if global_domain_flag_promotion:
        raise R2622PinSuccessorError(
            "a global domain flag must not promote training rows to proven-PIT"
        )
    if proven_pit_domains <= 0 and proven_pit_training_row_count != 0:
        raise R2622PinSuccessorError(
            "zero proven-PIT domains cannot yield proven-PIT training rows"
        )
    if proven_pit_training_row_count == training_row_count and proven_pit_domains <= 0:
        raise R2622PinSuccessorError(
            "training_row_count cannot be treated as proven-PIT without row authority"
        )
    clean = proven_pit_training_row_count > 0 and proven_pit_domains > 0
    return {
        "clean_slice_established": clean,
        "r26_22_status": "UNTRUSTED_SHADOW" if clean else BLOCKED_STATUS,
        "publication_label": SHADOW_CLASSIFICATION,
        "proven_pit_training_row_count": proven_pit_training_row_count,
        "proven_pit_domains": proven_pit_domains,
        "training_row_count": training_row_count,
        "global_domain_flag_promotion": False,
        "fabricated_whistle_timestamps": False,
    }


def _int_count(mapping: Mapping[str, Any], key: str) -> int:
    value = mapping.get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise R2622PinSuccessorError(f"count is not an integer: {key}") from exc


def build_successor_disposition(
    *,
    predecessor_disposition: Mapping[str, Any],
    pair_audit: Mapping[str, Any],
    authority_counts: Mapping[str, Any],
    training_row_count: int,
    week1_trust: Mapping[str, Any],
    issued_at_utc: str,
    accept_mismatched_hash: bool = False,
    global_domain_flag_promotion: bool = False,
    fabricated_whistle_timestamps: bool = False,
) -> dict[str, Any]:
    resolved = resolve_referenced_audit_identity(
        pair_audit,
        claimed_identity=None,
        accept_mismatched_hash=accept_mismatched_hash,
    )
    predecessor_pin = predecessor_disposition.get("pair_audit_gate_identity")
    try:
        assessment = assess_fitted_path_temporal_authority(
            authority_counts=authority_counts,
            training_row_count=training_row_count,
            week1_trust=week1_trust,
            predecessor_pit_boolean=True,
        )
    except FittedPathTemporalAuthorityError as exc:
        raise R2622PinSuccessorError(str(exc)) from exc
    if operational_pit_admission_allowed(
        CONSERVATIVE_BOUND, predecessor_sufficient=True
    ):
        raise R2622PinSuccessorError(
            "conservative precommitted bounds must not satisfy proven-PIT admission"
        )
    proven_domains = _int_count(authority_counts, OBSERVED_PUBLICATION) + _int_count(
        authority_counts, OBSERVED_EFFECTIVE
    )
    slice_state = assess_clean_slice(
        proven_pit_training_row_count=int(assessment["proven_pit_training_row_count"]),
        proven_pit_domains=proven_domains,
        training_row_count=training_row_count,
        global_domain_flag_promotion=global_domain_flag_promotion,
        fabricated_whistle_timestamps=fabricated_whistle_timestamps,
    )
    census = pair_audit.get("census") or {}
    disposition = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "finding": FINDING_ID,
        "disposition": "CONFIRMED_CONTAINED_NOT_FIXED",
        "r26_22_status": slice_state["r26_22_status"],
        "pin_resolution": resolved["resolution"],
        "pair_audit_relative_path": PAIR_AUDIT_RELATIVE,
        "pair_audit_gate_identity": resolved["resolved_identity"],
        "pair_audit_declared_gate_identity": resolved["declared_gate_identity"],
        "pair_audit_reconstructed_gate_identity": resolved["reconstructed_gate_identity"],
        "predecessor_disposition_relative_path": PREDECESSOR_DISPOSITION_RELATIVE,
        "predecessor_claimed_pair_audit_gate_identity": predecessor_pin,
        "predecessor_pin_matched_referenced_audit": (
            predecessor_pin == resolved["resolved_identity"]
        ),
        "predecessor_disposition_preserved_in_place": True,
        "manual_mismatched_hash_acceptance": False,
        "counts_agreeing_does_not_repair_unresolved_binding": True,
        "admitted_proxy_pairs": census.get("admitted_proxy_pairs"),
        "near_bound_pairs": census.get("near_bound_pairs"),
        "bound_epistemic_status": pair_audit.get("bound_epistemic_status")
        or CLASSIFICATION,
        "census_source": pair_audit.get("census_source"),
        "training_row_count": training_row_count,
        "proven_pit_training_row_count": slice_state["proven_pit_training_row_count"],
        "proven_pit_domains": slice_state["proven_pit_domains"],
        "clean_slice_established": slice_state["clean_slice_established"],
        "global_domain_flag_promotion": False,
        "fabricated_whistle_timestamps": False,
        "refit_without_proxy_pairs_possible": False,
        "reduced_feature_refit_performed": False,
        "active_week1_path_imports_pit_bound": bool(
            pair_audit.get("active_week1_path_imports_pit_bound")
        ),
        "publication_label": SHADOW_CLASSIFICATION,
        "leakage_declared": False,
        "proxy_model_if_any": SHADOW_CLASSIFICATION,
        "c26_week1_gate_identity_preserved": C26_WEEK1_GATE_IDENTITY,
        "c26_week1_dataset_identity_preserved": C26_WEEK1_DATASET_IDENTITY,
        "c26_week1_gate_or_dataset_overwritten": False,
        "operational_rule": (
            "Where proven PIT authority is required and only a precommitted "
            "proxy is available, fitted issuance must abstain or remain "
            "explicitly UNTRUSTED_SHADOW. R26-22 stays BLOCKED until a genuine "
            "row-level clean slice exists."
        ),
        "scientific_nonclaims": [
            "Does not rewrite the Cycle #26 disposition or pair-audit artifacts.",
            "Does not accept the mismatched 0070c1 pin by manual override.",
            "Does not promote 90198 training rows with a global domain flag.",
            "Does not fabricate whistle timestamps or invent a clean slice.",
            "Does not overwrite C26 gate aa4ff84b... or dataset 770d2544....",
            "Does not open the all-cycle trust gate or operator hold.",
        ],
        "result": "PASS_CYCLE27_R26_22_PIN_SUCCESSOR_BLOCKED",
    }
    disposition["disposition_identity"] = sha256_bytes(
        canonical_json_bytes(
            {
                key: value
                for key, value in disposition.items()
                if key != "disposition_identity"
            }
        )
    )
    return disposition


def build_from_repo(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    predecessor = read_json(repo_root / PREDECESSOR_DISPOSITION_RELATIVE)
    pair_audit = read_json(repo_root / PAIR_AUDIT_RELATIVE)
    authority = read_json(
        repo_root / "artifacts/data_lake/historical_known_at_authority_gate.json"
    )
    suite = read_json(
        repo_root / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
    )
    week1 = read_json(
        repo_root
        / "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
    )
    if week1.get("gate_identity") != C26_WEEK1_GATE_IDENTITY:
        raise R2622PinSuccessorError("C26 week1 gate identity drift")
    if week1.get("dataset_identity") != C26_WEEK1_DATASET_IDENTITY:
        raise R2622PinSuccessorError("C26 week1 dataset identity drift")
    return build_successor_disposition(
        predecessor_disposition=predecessor,
        pair_audit=pair_audit,
        authority_counts=authority.get("authority_class_counts") or {},
        training_row_count=int(
            (suite.get("deployment_fit") or {}).get("training_row_count") or 0
        ),
        week1_trust=week1.get("trust") or {},
        issued_at_utc=issued_at_utc,
    )


def materialize(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    disposition = build_from_repo(repo_root=repo_root, issued_at_utc=issued_at_utc)
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(disposition, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return disposition
