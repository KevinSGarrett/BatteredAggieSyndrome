"""Bind the Week 1 fitted path to proven-PIT admission reality.

Observed publication and effective known-at counts are zero on the BAT-666
authority gate. The 90,198-row deployment fit therefore remains a chronology-proxy
experiment. This successor does not refit a reduced-feature candidate, does not
rewrite Week 1 forecast payloads, and does not upgrade conservative precommitted
bounds to proven historical known-at.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (
    CONSERVATIVE_BOUND,
    OBSERVED_EFFECTIVE,
    OBSERVED_PUBLICATION,
    operational_pit_admission_allowed,
)

SCHEMA_VERSION = "aggie.data.week1_2026_fitted_path_temporal_authority.v1"
CONTRACT_ID = "CYCLE26-WEEK1-2026-FITTED-PATH-TEMPORAL-AUTHORITY-V1"
JIRA_KEY = "BAT-690"
LOCAL_ISSUE_ID = (
    "POST-TASK-ACTIVE-NATIONAL-FORECAST-SCIENTIFIC-CORRECTNESS-RECOVERY-001"
)
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "FITTED_PATH_CHRONOLOGY_PROXY_NOT_PROVEN_PIT"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_FITTED_PATH_TEMPORAL_AUTHORITY_CONTAINED"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_FITTED_PATH_TEMPORAL_AUTHORITY.json"
)
AUTHORITY_GATE_RELATIVE = "artifacts/data_lake/historical_known_at_authority_gate.json"
SUITE_GATE_RELATIVE = "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
WEEK1_GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
PAIR_AUDIT_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT.json"
)
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
PRIMARY_INCOMPLETE = "PRIMARY_TRUST_RECOVERY_INCOMPLETE"


class FittedPathTemporalAuthorityError(ValueError):
    """Raised when the fitted path is mislabeled as proven-PIT."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _int_count(counts: Mapping[str, Any], key: str) -> int:
    value = counts.get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise FittedPathTemporalAuthorityError(
            f"authority class count is not an integer: {key}"
        ) from exc


def assess_fitted_path_temporal_authority(
    *,
    authority_counts: Mapping[str, Any],
    training_row_count: int,
    week1_trust: Mapping[str, Any],
    predecessor_pit_boolean: bool = True,
) -> dict[str, Any]:
    """Independently classify the live fitted path against proven-PIT rules."""

    if training_row_count < 0:
        raise FittedPathTemporalAuthorityError("training_row_count is negative")
    observed_publication = _int_count(authority_counts, OBSERVED_PUBLICATION)
    observed_effective = _int_count(authority_counts, OBSERVED_EFFECTIVE)
    conservative = _int_count(authority_counts, CONSERVATIVE_BOUND)
    proven_pit_domains = observed_publication + observed_effective
    operational_allowed = operational_pit_admission_allowed(
        CONSERVATIVE_BOUND, predecessor_sufficient=predecessor_pit_boolean
    )
    if operational_allowed:
        raise FittedPathTemporalAuthorityError(
            "conservative precommitted bounds must not satisfy proven-PIT admission"
        )
    if proven_pit_domains > 0 and conservative == 0:
        proven_pit_training_rows = training_row_count
    else:
        proven_pit_training_rows = 0
    if proven_pit_domains == 0 and proven_pit_training_rows != 0:
        raise FittedPathTemporalAuthorityError(
            "zero proven-PIT domains cannot yield proven-PIT training rows"
        )
    active_claim = week1_trust.get("ACTIVE_PATH_CORRECTNESS_CLAIM")
    if active_claim is True:
        raise FittedPathTemporalAuthorityError(
            "ACTIVE_PATH_CORRECTNESS_CLAIM is forbidden while proven-PIT training is empty"
        )
    publication = week1_trust.get("publication_label")
    if publication != SHADOW_CLASSIFICATION:
        raise FittedPathTemporalAuthorityError(
            "fitted path publication_label must remain UNTRUSTED_SHADOW"
        )
    if week1_trust.get("scientific_trust_gate_open") is True:
        raise FittedPathTemporalAuthorityError(
            "scientific trust gate must remain closed on this chronology-proxy path"
        )
    if week1_trust.get("recommended") is True:
        raise FittedPathTemporalAuthorityError(
            "chronology-proxy fitted outputs must not be recommended"
        )
    return {
        "observed_publication_domains": observed_publication,
        "observed_effective_domains": observed_effective,
        "conservative_bound_domains": conservative,
        "proven_pit_domains": proven_pit_domains,
        "training_row_count": training_row_count,
        "proven_pit_training_row_count": proven_pit_training_rows,
        "operational_pit_admission_allowed": False,
        "predecessor_pit_boolean_ignored": bool(predecessor_pit_boolean),
        "refit_without_proxy_pairs_possible": False,
        "reduced_feature_refit_performed": False,
        "week1_payloads_rewritten": False,
        "primary_trust_recovery": PRIMARY_INCOMPLETE,
        "primary_blocker": (
            "OBSERVED_PUBLICATION_TIMESTAMP=0 and OBSERVED_EFFECTIVE_TIMESTAMP=0; "
            "deployment fit remains a chronology-proxy experiment"
        ),
        "publication_label": SHADOW_CLASSIFICATION,
        "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
    }


def build_gate(
    *,
    repo_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    authority = read_json(repo_root / AUTHORITY_GATE_RELATIVE)
    suite = read_json(repo_root / SUITE_GATE_RELATIVE)
    week1 = read_json(repo_root / WEEK1_GATE_RELATIVE)
    pair_audit = read_json(repo_root / PAIR_AUDIT_RELATIVE)
    assessment = assess_fitted_path_temporal_authority(
        authority_counts=authority.get("authority_class_counts") or {},
        training_row_count=int(
            (suite.get("deployment_fit") or {}).get("training_row_count") or 0
        ),
        week1_trust=week1.get("trust") or {},
        predecessor_pit_boolean=True,
    )
    gate = {
        "artifact_type": "CYCLE26_FITTED_PATH_TEMPORAL_AUTHORITY",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "publication_label": SHADOW_CLASSIFICATION,
        "bound_predecessors": {
            "authority_gate_identity": authority.get("gate_identity")
            or authority.get("binding_identity"),
            "suite_gate_identity": suite.get("gate_identity")
            or suite.get("binding_identity"),
            "week1_successor_gate_identity": week1.get("gate_identity"),
            "pair_audit_gate_identity": pair_audit.get("gate_identity"),
            "predecessor_payloads_rewritten_in_place": False,
        },
        "assessment": assessment,
        "scientific_nonclaims": [
            "Does not rewrite BAT-666 or BAT-667 predecessor gates.",
            "Does not upgrade +12h/+2d proxies to proven historical known-at.",
            "Does not refit a reduced-feature candidate as the same ridge identity.",
            "Does not rewrite Week 1 forecast payloads.",
            "Does not open the all-cycle trust gate or operator hold.",
            "Does not establish ACTIVE_PATH_CORRECTNESS_VERIFIED.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in gate.items() if key != "gate_identity"}
        )
    )
    return gate


def materialize(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    gate = build_gate(repo_root=repo_root, issued_at_utc=issued_at_utc)
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(gate, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return gate
