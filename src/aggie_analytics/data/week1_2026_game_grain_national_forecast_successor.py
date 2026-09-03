"""National game-grain forecast successor with joint Normal residual semantics.

Cycle #24 early-forecast rows remain immutable predecessors. Ridge probability,
expected margin, and predictive interval are jointly derived from the same
fitted Normal residual. Logistic / prior-only emit complementary probabilities
only. Outputs remain UNTRUSTED_SHADOW while the scientific-trust gate is closed.
Historical C20/C21/C25 payloads are never rewritten or cosmetically renormalized.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.week1_2026_game_grain_distribution_successor import (
    SHADOW_CLASSIFICATION,
    game_grain_forecast,
    oriented_rows_from_game,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_game_grain_national_forecast_successor.v1"
CONTRACT_ID = "CYCLE26-WEEK1-2026-GAME-GRAIN-NATIONAL-FORECAST-SUCCESSOR-V1"
JIRA_KEY = "BAT-693"
LOCAL_ISSUE_ID = (
    "POST-TASK-ACTIVE-NATIONAL-FORECAST-SCIENTIFIC-CORRECTNESS-RECOVERY-001"
)
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_GAME_GRAIN_NATIONAL_FORECAST_SUCCESSOR"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_GAME_GRAIN_NATIONAL_FORECAST_SUCCESSOR"
GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
PAYLOAD_SLUG = "week1_2026_game_grain_national_forecast_successor"
FORECAST_PAYLOAD_NAME = "week1_2026_game_grain_forecast_rows.jsonl"
ORIENTED_PAYLOAD_NAME = "week1_2026_game_grain_oriented_rows.jsonl"
COVERAGE_PAYLOAD_NAME = "week1_2026_game_grain_coverage_table.jsonl"
FOCUS_PAYLOAD_NAME = "week1_2026_game_grain_focus_contest_packet.jsonl"

DEPRECATE_PREDECESSORS = (
    "week1_2026_early_forecast_adequacy",
    "week1_2026_ridge_distribution_coherence",
    "week1_2026_forecast_input_binding_successor",
)
MARGIN_CAPABLE = "national_margin_ridge"
PROBABILITY_ONLY = frozenset(
    {"national_base_rate", "national_elo", "prior_only", "national_logistic_l2"}
)
CONTROL_ONLY = frozenset({"national_base_rate"})
TAMU_TEAM_MARKERS = ("texas a&m", "tamu", "texas aggie")
TAMU_NCAA_CONTEST_ID = "6607349"
TAMU_CANONICAL_TEAM_IDS = frozenset({"SRC-002:TEAM:245"})


class GameGrainNationalViolation(ValueError):
    """Raised when the game-grain national successor cannot be built honestly."""


def normalize_pair_probabilities(p_a_raw: float, p_b_raw: float) -> dict[str, float]:
    """Fail-closed pair renormalization without importing numpy-backed suites."""
    try:
        p_a = float(p_a_raw)
        p_b = float(p_b_raw)
    except (TypeError, ValueError) as exc:
        raise GameGrainNationalViolation("raw pair probability is not numeric") from exc
    if not math.isfinite(p_a) or not math.isfinite(p_b):
        raise GameGrainNationalViolation("raw pair probability is NaN or infinite")
    if p_a < 0.0 or p_b < 0.0 or p_a == 0.0 or p_b == 0.0:
        raise GameGrainNationalViolation("raw pair probability domain is invalid")
    raw_sum = p_a + p_b
    if raw_sum == 0.0:
        raise GameGrainNationalViolation("raw pair probability sum is zero")
    p_a_game = p_a / raw_sum
    p_b_game = 1.0 - p_a_game
    if abs((p_a_game + p_b_game) - 1.0) > 1e-12:
        raise GameGrainNationalViolation("normalized pair is not complementary")
    return {"p_a_game": p_a_game, "p_b_game": p_b_game, "raw_sum": raw_sum}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    )


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    lines = [
        json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for row in rows
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _is_tamu(row: Mapping[str, Any]) -> bool:
    if str(row.get("ncaa_contest_id") or "") == TAMU_NCAA_CONTEST_ID:
        return True
    for key in ("home_canonical_team_id", "away_canonical_team_id"):
        if str(row.get(key) or "") in TAMU_CANONICAL_TEAM_IDS:
            return True
    blob = " ".join(
        str(row.get(key) or "")
        for key in (
            "home_canonical_team_id",
            "away_canonical_team_id",
            "home_source_team_id",
            "away_source_team_id",
            "contest_identity",
        )
    ).casefold()
    return any(marker in blob for marker in TAMU_TEAM_MARKERS)


def _residual_stdev(
    suite_gate: Mapping[str, Any], parameter_rows: Sequence[Mapping[str, Any]]
) -> float:
    for row in parameter_rows:
        parameter_id = row.get("parameter_set_id") or row.get("parameter_id")
        if parameter_id == "NATIONAL_MARGIN_RIDGE_BETA":
            for key in (
                "ridge_training_residual_stdev",
                "training_residual_stdev",
                "residual_stdev",
            ):
                if key in row and row[key] is not None:
                    value = float(row[key])
                    if math.isfinite(value) and value > 0:
                        return value
    value = float(
        suite_gate.get("deployment_fit", {}).get("ridge_training_residual_stdev") or 0.0
    )
    if not math.isfinite(value) or value <= 0:
        raise GameGrainNationalViolation(
            "ridge residual_stdev unavailable or non-positive"
        )
    return value


def _early_forecast_rows(
    data_root: Path, gate: Mapping[str, Any]
) -> list[dict[str, Any]]:
    name = "week1_2026_early_forecast_rows.jsonl"
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if sha256_bytes(payload) != entry["sha256"]:
        raise GameGrainNationalViolation(f"early forecast payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def _rewrite_ridge_row(
    row: Mapping[str, Any],
    *,
    residual_stdev: float,
    interval_probability: float,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    expected_margin = row.get("expected_margin_home")
    if expected_margin is None or not math.isfinite(float(expected_margin)):
        raise GameGrainNationalViolation(
            f"ridge row missing finite expected_margin_home: {row.get('forecast_row_identity')}"
        )
    game = game_grain_forecast(
        contest_id=str(row["contest_identity"]),
        home_team_key=str(
            row.get("home_canonical_team_id") or row["home_source_team_id"]
        ),
        away_team_key=str(
            row.get("away_canonical_team_id") or row["away_source_team_id"]
        ),
        expected_margin_home=float(expected_margin),
        residual_stdev=residual_stdev,
        interval_probability=interval_probability,
        trust_gate_open=False,
        fold_local=True,
    )
    game["forecast_identity"] = row.get("forecast_row_identity")
    game["checkpoint"] = row.get("checkpoint_id")
    game["candidate_id"] = MARGIN_CAPABLE
    successor = dict(row)
    successor.update(
        {
            "probability_home": round(float(game["home_win_probability"]), 10),
            "probability_away": round(float(game["away_win_probability"]), 10),
            "raw_probability_home": round(float(game["home_win_probability"]), 10),
            "raw_probability_away": round(float(game["away_win_probability"]), 10),
            "expected_margin_home": round(float(game["expected_margin_home"]), 10),
            "expected_margin_away": round(float(game["expected_margin_away"]), 10),
            "margin_interval_home": [
                round(float(game["interval_lower"]), 10),
                round(float(game["interval_upper"]), 10),
            ],
            "margin_interval_away": [
                round(float(-game["interval_upper"]), 10),
                round(float(-game["interval_lower"]), 10),
            ],
            "margin_support": "SUPPORTED_BY_MODEL_FAMILY",
            "uncertainty_state": "FITTED_NORMAL_RESIDUAL_INTERVAL",
            "distribution_family": "NORMAL_RESIDUAL",
            "probability_link": "NORMAL_CDF_FROM_SAME_DISTRIBUTION",
            "grain": "GAME",
            "joint_coherence": bool(game["joint"]["coherent"]),
            "pair_coherence": bool(game["pair"]["coherent"]),
            "trust_classification": SHADOW_CLASSIFICATION,
            "row_state": game["row_state"]
            if row.get("row_state") == "FORECAST_FROZEN"
            else row.get("row_state"),
            "deprecated_predecessors": list(DEPRECATE_PREDECESSORS),
            "successor_contract_id": CONTRACT_ID,
            "control_only": False,
        }
    )
    if not (game["pair"]["coherent"] and game["joint"]["coherent"]):
        successor["probability_home"] = None
        successor["probability_away"] = None
        successor["expected_margin_home"] = None
        successor["expected_margin_away"] = None
        successor["margin_interval_home"] = None
        successor["margin_interval_away"] = None
        successor["row_state"] = "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        successor["abstention_reasons"] = sorted(
            set(successor.get("abstention_reasons") or [])
            | {"ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"}
        )
    oriented = oriented_rows_from_game(game)
    for item in oriented:
        item["trust_classification"] = SHADOW_CLASSIFICATION
        item["successor_contract_id"] = CONTRACT_ID
    return successor, game, oriented


def _rewrite_probability_only_row(row: Mapping[str, Any]) -> dict[str, Any]:
    successor = dict(row)
    candidate = row["candidate_id"]
    successor["grain"] = "GAME"
    successor["distribution_family"] = "NOT_APPLICABLE_PROBABILITY_ONLY"
    successor["probability_link"] = (
        "PAIR_NORMALIZED" if candidate != "national_base_rate" else "FIXED_CONTROL"
    )
    successor["margin_support"] = "NOT_SUPPORTED_BY_MODEL_FAMILY"
    successor["expected_margin_home"] = None
    successor["expected_margin_away"] = None
    successor["margin_interval_home"] = None
    successor["margin_interval_away"] = None
    successor["uncertainty_state"] = "NOT_SUPPORTED_BY_MODEL_FAMILY"
    successor["trust_classification"] = SHADOW_CLASSIFICATION
    successor["deprecated_predecessors"] = list(DEPRECATE_PREDECESSORS)
    successor["successor_contract_id"] = CONTRACT_ID
    successor["control_only"] = candidate in CONTROL_ONLY
    if row.get("row_state") != "FORECAST_FROZEN":
        return successor
    home = row.get("raw_probability_home")
    away = row.get("raw_probability_away")
    if home is None or away is None:
        home = row.get("probability_home")
        away = row.get("probability_away")
    if home is None or away is None:
        successor["row_state"] = "ABSTAIN_MISSING_REQUIRED_FEATURES"
        successor["probability_home"] = None
        successor["probability_away"] = None
        return successor
    if candidate == "national_base_rate":
        successor["probability_home"] = 0.5
        successor["probability_away"] = 0.5
        successor["pair_coherence"] = True
        successor["joint_coherence"] = False
        return successor
    if candidate == "national_elo":
        # Elo already emits a single complementary game probability in the predecessor.
        p_home = float(home)
        successor["probability_home"] = round(p_home, 10)
        successor["probability_away"] = round(1.0 - p_home, 10)
        successor["pair_coherence"] = abs(p_home + (1.0 - p_home) - 1.0) <= 1e-12
        successor["joint_coherence"] = False
        return successor
    normalized = normalize_pair_probabilities(float(home), float(away))
    successor["probability_home"] = round(float(normalized["p_a_game"]), 10)
    successor["probability_away"] = round(float(normalized["p_b_game"]), 10)
    successor["pair_coherence"] = (
        abs(successor["probability_home"] + successor["probability_away"] - 1.0)
        <= 1e-12
    )
    successor["joint_coherence"] = False
    if not successor["pair_coherence"]:
        successor["probability_home"] = None
        successor["probability_away"] = None
        successor["row_state"] = "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        successor["abstention_reasons"] = sorted(
            set(successor.get("abstention_reasons") or [])
            | {"ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"}
        )
    return successor


def build_successor_rows(
    *,
    predecessor_rows: Sequence[Mapping[str, Any]],
    residual_stdev: float,
    interval_probability: float = 0.8,
) -> dict[str, Any]:
    forecast_rows: list[dict[str, Any]] = []
    oriented_rows: list[dict[str, Any]] = []
    game_rows: list[dict[str, Any]] = []
    failing_pairs = 0
    ridge_emitted = 0
    for row in predecessor_rows:
        candidate = row["candidate_id"]
        if candidate == MARGIN_CAPABLE:
            if row.get("row_state") == "FORECAST_FROZEN":
                successor, game, oriented = _rewrite_ridge_row(
                    row,
                    residual_stdev=residual_stdev,
                    interval_probability=interval_probability,
                )
                forecast_rows.append(successor)
                oriented_rows.extend(oriented)
                game_rows.append(game)
                ridge_emitted += 1
                if successor.get("probability_home") is None:
                    failing_pairs += 1
            else:
                successor = dict(row)
                successor.update(
                    {
                        "grain": "GAME",
                        "distribution_family": "NORMAL_RESIDUAL",
                        "probability_link": "NORMAL_CDF_FROM_SAME_DISTRIBUTION",
                        "margin_support": "SUPPORTED_BY_MODEL_FAMILY",
                        "probability_home": None,
                        "probability_away": None,
                        "expected_margin_home": None,
                        "expected_margin_away": None,
                        "margin_interval_home": None,
                        "margin_interval_away": None,
                        "trust_classification": SHADOW_CLASSIFICATION,
                        "deprecated_predecessors": list(DEPRECATE_PREDECESSORS),
                        "successor_contract_id": CONTRACT_ID,
                        "control_only": False,
                        "pair_coherence": False,
                        "joint_coherence": False,
                    }
                )
                forecast_rows.append(successor)
        elif candidate in PROBABILITY_ONLY:
            successor = _rewrite_probability_only_row(row)
            forecast_rows.append(successor)
            if (
                successor.get("row_state") == "FORECAST_FROZEN"
                and successor.get("probability_home") is not None
                and abs(
                    float(successor["probability_home"])
                    + float(successor["probability_away"])
                    - 1.0
                )
                > 1e-12
            ):
                failing_pairs += 1
        else:
            raise GameGrainNationalViolation(f"unknown candidate: {candidate}")

    focus_rows = [row for row in forecast_rows if _is_tamu(row)]
    coverage: dict[str, dict[str, int]] = {}
    for row in forecast_rows:
        bucket = coverage.setdefault(
            row["candidate_id"],
            {
                "opportunity": 0,
                "frozen_with_probability": 0,
                "abstained": 0,
                "control_only": 0,
            },
        )
        bucket["opportunity"] += 1
        if row.get("control_only"):
            bucket["control_only"] += 1
        if row.get("probability_home") is not None:
            bucket["frozen_with_probability"] += 1
        else:
            bucket["abstained"] += 1

    return {
        "forecast_rows": forecast_rows,
        "oriented_rows": oriented_rows,
        "game_rows": game_rows,
        "focus_rows": focus_rows,
        "coverage": coverage,
        "failing_pairs": failing_pairs,
        "ridge_emitted": ridge_emitted,
    }


def build_gate(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    predecessor_gate: Mapping[str, Any],
    suite_gate: Mapping[str, Any],
    built: Mapping[str, Any],
    residual_stdev: float,
) -> dict[str, Any]:
    forecast_payload = jsonl_bytes(built["forecast_rows"])
    oriented_payload = jsonl_bytes(built["oriented_rows"])
    coverage_rows = [
        {"candidate_id": key, **value}
        for key, value in sorted(built["coverage"].items())
    ]
    coverage_payload = jsonl_bytes(coverage_rows)
    focus_payload = jsonl_bytes(built["focus_rows"])
    payloads = {
        "forecast_rows": {
            "relative_path": f"canonical/{PAYLOAD_SLUG}/sha256/{{dataset_identity}}/{FORECAST_PAYLOAD_NAME}",
            "sha256": sha256_bytes(forecast_payload),
            "bytes": len(forecast_payload),
            "row_count": len(built["forecast_rows"]),
        },
        "oriented_rows": {
            "relative_path": f"canonical/{PAYLOAD_SLUG}/sha256/{{dataset_identity}}/{ORIENTED_PAYLOAD_NAME}",
            "sha256": sha256_bytes(oriented_payload),
            "bytes": len(oriented_payload),
            "row_count": len(built["oriented_rows"]),
        },
        "coverage_rows": {
            "relative_path": f"canonical/{PAYLOAD_SLUG}/sha256/{{dataset_identity}}/{COVERAGE_PAYLOAD_NAME}",
            "sha256": sha256_bytes(coverage_payload),
            "bytes": len(coverage_payload),
            "row_count": len(coverage_rows),
        },
        "focus_packet": {
            "relative_path": f"canonical/{PAYLOAD_SLUG}/sha256/{{dataset_identity}}/{FOCUS_PAYLOAD_NAME}",
            "sha256": sha256_bytes(focus_payload),
            "bytes": len(focus_payload),
            "row_count": len(built["focus_rows"]),
        },
    }
    dataset_identity = stable_hash(
        {
            "payloads": {
                key: {
                    "sha256": value["sha256"],
                    "bytes": value["bytes"],
                    "row_count": value["row_count"],
                }
                for key, value in payloads.items()
            },
            "predecessor_gate_identity": predecessor_gate.get("gate_identity")
            or predecessor_gate.get("binding_identity"),
            "suite_gate_identity": suite_gate.get("gate_identity")
            or suite_gate.get("binding_identity"),
            "issued_at_utc": issued_at_utc,
            "residual_stdev": residual_stdev,
            "contract_id": CONTRACT_ID,
        }
    )
    for value in payloads.values():
        value["relative_path"] = value["relative_path"].format(
            dataset_identity=dataset_identity
        )
    ridge_coverage = built["coverage"].get(MARGIN_CAPABLE, {})
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_GAME_GRAIN_NATIONAL_FORECAST_SUCCESSOR_GATE",
        "contract_id": CONTRACT_ID,
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "season": 2026,
        "week_label": "WEEK_1",
        "checkpoint_id": predecessor_gate.get("checkpoint_id", "EARLY_WEEK1"),
        "issued_at_utc": issued_at_utc,
        "dataset_identity": dataset_identity,
        "gate_identity": None,
        "payloads": payloads,
        "bound_predecessors": {
            "early_forecast_gate_identity": predecessor_gate.get("gate_identity")
            or predecessor_gate.get("binding_identity"),
            "national_forecast_suite_gate_identity": suite_gate.get("gate_identity")
            or suite_gate.get("binding_identity"),
            "predecessor_artifacts_rewritten_in_place": False,
            "deprecated_predecessors": list(DEPRECATE_PREDECESSORS),
            "historical_c20_c21_c25_payloads_preserved": True,
        },
        "summary": {
            "national_row_count": len(built["forecast_rows"]),
            "oriented_row_count": len(built["oriented_rows"]),
            "ridge_emitted": built["ridge_emitted"],
            "failing_pairs": built["failing_pairs"],
            "focus_row_count": len(built["focus_rows"]),
            "ridge_frozen_with_probability": ridge_coverage.get(
                "frozen_with_probability", 0
            ),
            "residual_stdev": residual_stdev,
        },
        "coverage": {"by_candidate": coverage_rows},
        "pair_coherence": {
            "failing_pairs": built["failing_pairs"],
            "holds": built["failing_pairs"] == 0,
        },
        "joint_distribution": {
            "margin_capable_candidate": MARGIN_CAPABLE,
            "probability_link": "NORMAL_CDF_FROM_SAME_DISTRIBUTION",
            "interval_from_same_distribution": True,
            "interval_probability": 0.8,
        },
        "trust": {
            "scientific_trust_gate_open": False,
            "publication_label": SHADOW_CLASSIFICATION,
            "recommended": False,
            "control_only_candidates": sorted(CONTROL_ONLY),
            "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
        },
        "scientific_nonclaims": [
            "Does not release the operator hold or all-cycle trust gate.",
            "Does not certify predictive skill or BAS/Aggie Excess conclusions.",
            "Does not rewrite historical C20/C21/C25 saved payloads.",
            "UNTRUSTED_SHADOW only; not production-ready.",
        ],
        "result": PASS_RESULT
        if built["failing_pairs"] == 0 and built["ridge_emitted"] > 0
        else "FAIL_GAME_GRAIN_NATIONAL_FORECAST_SUCCESSOR",
        "_payload_bytes": {
            "forecast_rows": forecast_payload,
            "oriented_rows": oriented_payload,
            "coverage_rows": coverage_payload,
            "focus_packet": focus_payload,
        },
    }
    gate["gate_identity"] = stable_hash(
        {key: value for key, value in gate.items() if not str(key).startswith("_")}
    )
    gate["record_hashes"] = {
        "forecast_rows": payloads["forecast_rows"]["sha256"],
        "oriented_rows": payloads["oriented_rows"]["sha256"],
        "coverage_rows": payloads["coverage_rows"]["sha256"],
        "focus_packet": payloads["focus_packet"]["sha256"],
        "core_module": sha256_file(
            repo_root
            / "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py"
        ),
    }
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    early_gate_path: Path | None = None,
) -> dict[str, Any]:
    # Lazy import keeps unit-test discovery free of numpy-backed forecast-suite deps.
    from aggie_analytics.data import week1_2026_national_forecast_suite as suite

    early_gate_path = early_gate_path or (
        repo_root / "artifacts/forecast/week1_2026_early_forecast_adequacy_gate.json"
    )
    suite_gate_path = (
        repo_root / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
    )
    predecessor_gate = read_json(early_gate_path)
    suite_gate = read_json(suite_gate_path)
    predecessor_rows = _early_forecast_rows(data_root, predecessor_gate)
    parameter_rows = suite.payload_rows(
        data_root, suite_gate, "week1_2026_forecast_fitted_parameter_rows.jsonl"
    )
    residual_stdev = _residual_stdev(suite_gate, parameter_rows)
    built = build_successor_rows(
        predecessor_rows=predecessor_rows,
        residual_stdev=residual_stdev,
        interval_probability=0.8,
    )
    gate = build_gate(
        repo_root=repo_root,
        data_root=data_root,
        issued_at_utc=issued_at_utc,
        predecessor_gate=predecessor_gate,
        suite_gate=suite_gate,
        built=built,
        residual_stdev=residual_stdev,
    )
    dataset_identity = gate["dataset_identity"]
    canonical_dir = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / dataset_identity
    manifest_dir = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / dataset_identity
    canonical_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    payload_bytes = gate.pop("_payload_bytes")
    name_map = {
        "forecast_rows": FORECAST_PAYLOAD_NAME,
        "oriented_rows": ORIENTED_PAYLOAD_NAME,
        "coverage_rows": COVERAGE_PAYLOAD_NAME,
        "focus_packet": FOCUS_PAYLOAD_NAME,
    }
    for key, filename in name_map.items():
        (canonical_dir / filename).write_bytes(payload_bytes[key])
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    public_gate = {
        key: value for key, value in gate.items() if not str(key).startswith("_")
    }
    gate_path.write_text(
        json.dumps(public_gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "artifact_type": "WEEK1_2026_GAME_GRAIN_NATIONAL_FORECAST_SUCCESSOR_MANIFEST",
        "dataset_identity": dataset_identity,
        "gate_identity": public_gate["gate_identity"],
        "issued_at_utc": issued_at_utc,
        "payloads": public_gate["payloads"],
        "result": public_gate["result"],
    }
    (manifest_dir / f"{PAYLOAD_SLUG}_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return public_gate
