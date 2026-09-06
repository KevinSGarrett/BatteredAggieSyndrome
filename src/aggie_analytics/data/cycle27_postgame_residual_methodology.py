"""Predeclared postgame residual methodology. Not a scored result and not BAS."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aggie.data.cycle27_postgame_residual_methodology.v1"
CONTRACT_ID = "CYCLE27-POSTGAME-RESIDUAL-METHODOLOGY-V1"
JIRA_KEY = "BAT-690"
PARENT_JIRA_KEY = "BAT-523"
ARTIFACT_TYPE = "CYCLE27_POSTGAME_RESIDUAL_METHODOLOGY"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_POSTGAME_RESIDUAL_METHODOLOGY.json"
)
C26_SCORING_GATE = "b5f20df45d939d71e0b72b31ee558d87e0b696608816b1e56806c1ac09d4c27c"
C27_SCORING_GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING.json"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def load_cycle27_scoring_gate_identity(repo_root: Path) -> str | None:
    path = repo_root / C27_SCORING_GATE_RELATIVE
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    identity = str(payload.get("gate_identity") or "").strip()
    return identity or None


def build_methodology(
    *, issued_at_utc: str, cycle27_scoring_gate: str | None
) -> dict[str, Any]:
    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "issued_at_utc": issued_at_utc,
        "hold": "ACTIVE",
        "scientific_done_unauthorized": True,
        "prediction_error": "predicted - actual",
        "result_residual": "actual - predicted",
        "expected_margin_residual": "actual_margin_home - expected_margin_home",
        "probability_residual": "observed_home_win - probability_home",
        "independent_predicted_score": None,
        "independent_predicted_score_blocker": (
            "MARGIN_ALONE_CANNOT_IDENTIFY_BOTH_TEAM_SCORES"
        ),
        "do_not_populate_actual_score_before_official_final": True,
        "score_each_legitimately_frozen_checkpoint_separately": True,
        "repeated_checkpoints_are_not_independent_games": True,
        "one_game_residual_is_observation_not_bas": True,
        "tiny_sample_limitations": (
            "n<30 cannot establish skill, calibrate tails, or select a champion"
        ),
        "p_equals_half_is_no_direction": True,
        "national_peer_comparators_not_selected_from_this_game_outcome": True,
        "preserved_scoring_gates": {
            "cycle26_predecessor": C26_SCORING_GATE,
            "cycle27_successor": cycle27_scoring_gate,
        },
        "upset_severity": {
            "supported": False,
            "reason": "NO_PREDECLARED_UPSET_SEVERITY_CANDIDATE_IN_ACTIVE_SUITE",
        },
        "publication_label": "UNTRUSTED_SHADOW",
        "primary_trust_recovery": "PRIMARY_TRUST_RECOVERY_INCOMPLETE",
    }
    payload["methodology_identity"] = sha256_bytes(
        canonical_json_bytes(
            {
                key: value
                for key, value in payload.items()
                if key != "methodology_identity"
            }
        )
    )
    return payload


def materialize(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    payload = build_methodology(
        issued_at_utc=issued_at_utc,
        cycle27_scoring_gate=load_cycle27_scoring_gate_identity(repo_root),
    )
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
