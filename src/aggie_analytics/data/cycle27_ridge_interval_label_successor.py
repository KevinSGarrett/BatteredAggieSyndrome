"""Cycle #27 ridge interval-label successor.

Cycle #26 ridge rows emit 80% Normal predictive intervals while retaining
``nominal_interval_level=0.95``. This successor issues new candidate/version/row
identities with the Cycle #26 IDs as lineage. Interval endpoints and
probabilities are preserved; only the uncertainty label is corrected to the
reconstructed mass. The level is not chosen from A&M or market evidence.
Already-kicked-off games are retrospective diagnostics, not new prospective
freezes. Cycle #26 gate ``aa4ff84b...`` and dataset ``770d2544...`` stay frozen.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.shadow.cycle27_ridge_interval_label_successor.v1"
CONTRACT_ID = "CYCLE27-WEEK1-2026-RIDGE-INTERVAL-LABEL-SUCCESSOR-V1"
JIRA_KEY = "BAT-690"
LOCAL_ISSUE_ID = "POST-TASK-CYCLE27-RIDGE-INTERVAL-LABEL-SUCCESSOR-001"
PARENT_JIRA_KEY = "BAT-523"
CANDIDATE_ID = "national_margin_ridge_cycle27_interval_label"
CANDIDATE_VERSION = "CYCLE27_INTERVAL_LABEL_V1"
PREDECESSOR_CANDIDATE_ID = "national_margin_ridge"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_RIDGE_INTERVAL_LABEL_SUCCESSOR_GATE.json"
)
ROWS_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_RIDGE_INTERVAL_LABEL_SUCCESSOR_ROWS.jsonl"
)
C26_GATE_IDENTITY = "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43"
C26_DATASET_IDENTITY = "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
C26_GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
MASS_TOLERANCE = 1e-6
LEVEL_TOLERANCE = 1e-9
RETROSPECTIVE = "RETROSPECTIVE_DIAGNOSTIC"
PROSPECTIVE_SHADOW = "PROSPECTIVE_SHADOW_LABEL_CORRECTION"


class RidgeIntervalLabelSuccessorError(ValueError):
    """Raised when the interval-label successor cannot be issued honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def standard_normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def parse_instant(text: str) -> datetime:
    raw = (text or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    instant = datetime.fromisoformat(raw)
    if instant.tzinfo is None:
        raise RidgeIntervalLabelSuccessorError("timestamp must be timezone-aware")
    return instant.astimezone(timezone.utc)


def reconstructed_interval_mass(
    *,
    expected_margin: float,
    interval: Sequence[float],
    residual_stdev: float,
) -> float:
    if residual_stdev <= 0 or not math.isfinite(residual_stdev):
        raise RidgeIntervalLabelSuccessorError("residual_stdev must be positive and finite")
    if len(interval) != 2:
        raise RidgeIntervalLabelSuccessorError("interval must be a two-endpoint sequence")
    lower, upper = float(interval[0]), float(interval[1])
    mean = float(expected_margin)
    z_lo = (lower - mean) / residual_stdev
    z_hi = (upper - mean) / residual_stdev
    return standard_normal_cdf(z_hi) - standard_normal_cdf(z_lo)


def choose_interval_level(
    *,
    reconstructed_masses: Sequence[float],
    declared_gate_level: float,
    focus_game_level: float | None = None,
    market_level: float | None = None,
    week1_outcome_level: float | None = None,
) -> float:
    """Use the gate-declared predictive-interval mass; never A&M or market."""

    if focus_game_level is not None or market_level is not None or week1_outcome_level is not None:
        raise RidgeIntervalLabelSuccessorError(
            "interval level must not be chosen from A&M, market, or Week 1 outcomes"
        )
    if not reconstructed_masses:
        raise RidgeIntervalLabelSuccessorError("no reconstructed interval masses")
    if not 0.0 < declared_gate_level < 1.0:
        raise RidgeIntervalLabelSuccessorError("declared_gate_level must be in (0, 1)")
    for mass in reconstructed_masses:
        if abs(float(mass) - float(declared_gate_level)) > MASS_TOLERANCE:
            raise RidgeIntervalLabelSuccessorError(
                "reconstructed interval mass disagrees with declared gate level"
            )
    return float(declared_gate_level)


def issuance_class(*, kickoff_utc: str | None, as_of_utc: str) -> str:
    if not kickoff_utc:
        return PROSPECTIVE_SHADOW
    if parse_instant(kickoff_utc) <= parse_instant(as_of_utc):
        return RETROSPECTIVE
    return PROSPECTIVE_SHADOW


def successor_row_identity(payload: Mapping[str, Any]) -> str:
    return stable_hash({"kind": "CYCLE27_RIDGE_INTERVAL_LABEL_ROW", **dict(payload)})


def correct_ridge_interval_row(
    row: Mapping[str, Any],
    *,
    residual_stdev: float,
    declared_gate_level: float,
    as_of_utc: str,
    predecessor_gate_identity: str,
    predecessor_dataset_identity: str,
    focus_game_level: float | None = None,
    market_level: float | None = None,
) -> dict[str, Any]:
    if row.get("candidate_id") != PREDECESSOR_CANDIDATE_ID:
        raise RidgeIntervalLabelSuccessorError("row is not a ridge predecessor")
    probability = row.get("probability_home")
    interval = row.get("margin_interval_home")
    expected_margin = row.get("expected_margin_home")
    if probability is None or not interval or expected_margin is None:
        raise RidgeIntervalLabelSuccessorError("ridge row missing probability/interval/margin")
    mass = reconstructed_interval_mass(
        expected_margin=float(expected_margin),
        interval=interval,
        residual_stdev=residual_stdev,
    )
    level = choose_interval_level(
        reconstructed_masses=(mass,),
        declared_gate_level=declared_gate_level,
        focus_game_level=focus_game_level,
        market_level=market_level,
    )
    labeled = row.get("nominal_interval_level")
    if labeled is None:
        raise RidgeIntervalLabelSuccessorError("predecessor row missing nominal_interval_level")
    if abs(float(labeled) - level) <= LEVEL_TOLERANCE:
        raise RidgeIntervalLabelSuccessorError("no interval-label mismatch to correct")
    kickoff = row.get("kickoff_bound_utc") or row.get("kickoff_utc")
    class_label = issuance_class(kickoff_utc=kickoff, as_of_utc=as_of_utc)
    scientific = {
        "predecessor_forecast_row_identity": row.get("forecast_row_identity"),
        "predecessor_candidate_id": PREDECESSOR_CANDIDATE_ID,
        "predecessor_gate_identity": predecessor_gate_identity,
        "predecessor_dataset_identity": predecessor_dataset_identity,
        "candidate_id": CANDIDATE_ID,
        "candidate_version": CANDIDATE_VERSION,
        "contest_identity": row.get("contest_identity"),
        "ncaa_contest_id": row.get("ncaa_contest_id"),
        "probability_home": row.get("probability_home"),
        "probability_away": row.get("probability_away"),
        "expected_margin_home": row.get("expected_margin_home"),
        "margin_interval_home": list(interval),
        "predecessor_nominal_interval_level": float(labeled),
        "successor_nominal_interval_level": level,
        "reconstructed_interval_mass": round(mass, 12),
        "interval_kind": "PREDICTION_INTERVAL_NOT_CONFIDENCE_INTERVAL_FOR_THE_MEAN",
        "issuance_class": class_label,
        "new_prospective_freeze": False,
        "frozen_before_kickoff_claim": False,
        "original_as_issued_scoring_preserved": True,
        "trust_classification": SHADOW_CLASSIFICATION,
        "kickoff_bound_utc": kickoff,
        "as_of_utc": as_of_utc,
    }
    successor = dict(scientific)
    successor["forecast_row_identity"] = successor_row_identity(scientific)
    if successor["forecast_row_identity"] == row.get("forecast_row_identity"):
        raise RidgeIntervalLabelSuccessorError(
            "successor reused predecessor forecast_row_identity after uncertainty semantics changed"
        )
    if predecessor_gate_identity != C26_GATE_IDENTITY:
        raise RidgeIntervalLabelSuccessorError("C26 gate identity lineage drift")
    if predecessor_dataset_identity != C26_DATASET_IDENTITY:
        raise RidgeIntervalLabelSuccessorError("C26 dataset identity lineage drift")
    return successor


def build_successor(
    *,
    predecessor_rows: Sequence[Mapping[str, Any]],
    residual_stdev: float,
    declared_gate_level: float,
    as_of_utc: str,
    predecessor_gate_identity: str = C26_GATE_IDENTITY,
    predecessor_dataset_identity: str = C26_DATASET_IDENTITY,
    focus_game_level: float | None = None,
    market_level: float | None = None,
) -> dict[str, Any]:
    ridge = [
        row
        for row in predecessor_rows
        if row.get("candidate_id") == PREDECESSOR_CANDIDATE_ID
        and row.get("probability_home") is not None
        and row.get("margin_interval_home")
    ]
    if not ridge:
        raise RidgeIntervalLabelSuccessorError("no emitted ridge rows to correct")
    masses = [
        reconstructed_interval_mass(
            expected_margin=float(row["expected_margin_home"]),
            interval=row["margin_interval_home"],
            residual_stdev=residual_stdev,
        )
        for row in ridge
    ]
    level = choose_interval_level(
        reconstructed_masses=masses,
        declared_gate_level=declared_gate_level,
        focus_game_level=focus_game_level,
        market_level=market_level,
    )
    corrected = [
        correct_ridge_interval_row(
            row,
            residual_stdev=residual_stdev,
            declared_gate_level=level,
            as_of_utc=as_of_utc,
            predecessor_gate_identity=predecessor_gate_identity,
            predecessor_dataset_identity=predecessor_dataset_identity,
        )
        for row in ridge
    ]
    identities = [row["forecast_row_identity"] for row in corrected]
    if len(set(identities)) != len(identities):
        raise RidgeIntervalLabelSuccessorError("successor row identities are not unique")
    predecessor_ids = [row.get("forecast_row_identity") for row in ridge]
    if set(identities) & set(predecessor_ids):
        raise RidgeIntervalLabelSuccessorError("successor reused a predecessor row identity")
    retrospective = sum(1 for row in corrected if row["issuance_class"] == RETROSPECTIVE)
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "CYCLE27_RIDGE_INTERVAL_LABEL_SUCCESSOR_GATE",
        "contract_id": CONTRACT_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "candidate_id": CANDIDATE_ID,
        "candidate_version": CANDIDATE_VERSION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "issued_at_utc": as_of_utc,
        "publication_label": SHADOW_CLASSIFICATION,
        "scientific_trust_gate_open": False,
        "predecessor_candidate_id": PREDECESSOR_CANDIDATE_ID,
        "predecessor_gate_identity": predecessor_gate_identity,
        "predecessor_dataset_identity": predecessor_dataset_identity,
        "predecessor_gate_or_dataset_overwritten": False,
        "declared_interval_level": level,
        "interval_kind": "PREDICTION_INTERVAL_NOT_CONFIDENCE_INTERVAL_FOR_THE_MEAN",
        "level_chosen_from_a_and_m_or_market_or_week1_outcome": False,
        "ridge_row_count": len(corrected),
        "retrospective_diagnostic_count": retrospective,
        "prospective_shadow_label_correction_count": len(corrected) - retrospective,
        "new_prospective_freeze_count": 0,
        "original_as_issued_scoring_preserved": True,
        "probability_values_changed": False,
        "interval_endpoints_changed": False,
        "uncertainty_label_changed": True,
        "residual_stdev": residual_stdev,
        "scientific_nonclaims": [
            "Does not overwrite C26 gate aa4ff84b... or dataset 770d2544....",
            "Does not reuse predecessor row identities after uncertainty-label change.",
            "Does not choose 80%/95% from A&M or market.",
            "Does not claim a new pre-kickoff freeze for already started games.",
            "Does not change original-as-issued scoring.",
        ],
        "result": "PASS_CYCLE27_RIDGE_INTERVAL_LABEL_SUCCESSOR",
        "rows": corrected,
    }
    dataset_identity = stable_hash(
        {
            "row_identities": identities,
            "candidate_id": CANDIDATE_ID,
            "candidate_version": CANDIDATE_VERSION,
            "declared_interval_level": level,
            "predecessor_gate_identity": predecessor_gate_identity,
            "predecessor_dataset_identity": predecessor_dataset_identity,
        }
    )
    gate["dataset_identity"] = dataset_identity
    public_rows = [
        {key: value for key, value in row.items() if key != "rows"} for row in corrected
    ]
    gate["row_identities"] = identities
    gate["predecessor_row_identities"] = predecessor_ids
    body = {key: value for key, value in gate.items() if key not in {"gate_identity", "rows"}}
    gate["gate_identity"] = stable_hash(body)
    gate["rows"] = public_rows
    return gate


def _forecast_payload_path(data_root: Path, gate: Mapping[str, Any]) -> Path:
    payloads = gate.get("payloads") or {}
    forecast = payloads.get("forecast_rows") or {}
    relative = forecast.get("relative_path")
    if not relative:
        raise RidgeIntervalLabelSuccessorError("C26 gate missing forecast payload path")
    return data_root / relative


def build_from_repo(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    c26 = read_json(repo_root / C26_GATE_RELATIVE)
    if c26.get("gate_identity") != C26_GATE_IDENTITY:
        raise RidgeIntervalLabelSuccessorError("refusing to overwrite or rebind drifted C26 gate")
    if c26.get("dataset_identity") != C26_DATASET_IDENTITY:
        raise RidgeIntervalLabelSuccessorError(
            "refusing to overwrite or rebind drifted C26 dataset"
        )
    declared = float((c26.get("joint_distribution") or {}).get("interval_probability") or 0.0)
    residual = float((c26.get("summary") or {}).get("residual_stdev") or 0.0)
    payload = _forecast_payload_path(data_root, c26)
    rows = read_jsonl(payload)
    return build_successor(
        predecessor_rows=rows,
        residual_stdev=residual,
        declared_gate_level=declared,
        as_of_utc=issued_at_utc,
        predecessor_gate_identity=C26_GATE_IDENTITY,
        predecessor_dataset_identity=C26_DATASET_IDENTITY,
    )


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    gate = build_from_repo(
        repo_root=repo_root, data_root=data_root, issued_at_utc=issued_at_utc
    )
    gate_path = repo_root / GATE_RELATIVE
    rows_path = repo_root / ROWS_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    rows = gate["rows"]
    public_gate = {key: value for key, value in gate.items() if key != "rows"}
    public_gate["payloads"] = {
        "rows": {
            "relative_path": ROWS_RELATIVE.replace("\\", "/"),
            "row_count": len(rows),
            "sha256": sha256_bytes(
                (
                    "\n".join(
                        json.dumps(row, sort_keys=True, separators=(",", ":"))
                        for row in rows
                    )
                    + ("\n" if rows else "")
                ).encode("utf-8")
            ),
        }
    }
    public_gate["gate_identity"] = stable_hash(
        {key: value for key, value in public_gate.items() if key != "gate_identity"}
    )
    rows_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    gate_path.write_text(
        json.dumps(public_gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    public_gate["rows"] = rows
    return public_gate
