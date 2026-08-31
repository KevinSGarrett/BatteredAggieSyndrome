"""Immutable EARLY_WEEK1 national forecast snapshot and A&M readout.

This unit consumes the executable Cycle #24 forecast-suite binding and freezes
one contest-candidate row for every Week 1 2026 contest and every one of the
exactly five frozen candidates. Each row either carries a pair-coherent
probability with its supported margin and uncertainty, or names the exact
evidence it lacks. The unit never executes the A&M T-24H or T-90M checkpoints,
never reads a Week 1 outcome, never promotes a candidate, and never presents
the historical fifty-percent control or the historical Elo row as current.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from aggie_analytics.data import week1_2026_frozen_strength_prior as prior_module
from aggie_analytics.data import week1_2026_national_forecast_suite as suite
from aggie_analytics.data.national_foundation_reconciliation import binding_identity
from aggie_analytics.experimentation.development_2023_labeled_replay import (
    normalize_pair_probabilities,
)
from aggie_analytics.modeling import national_expectation_baselines as baselines

SCHEMA_VERSION = "aggie.shadow.week1_2026_early_forecast_adequacy.v1"
CONTRACT_ID = "CYCLE24-WEEK1-2026-EARLY-FORECAST-ADEQUACY-V1"
JIRA_KEY = "BAT-681"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-EARLY-FORECAST-ADEQUACY-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_EARLY_FORECAST_ADEQUACY_SNAPSHOT"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_EARLY_FORECAST_ADEQUACY"
CONTRACT_RELATIVE = "configs/week1_2026_early_forecast_adequacy_contract.json"
GATE_RELATIVE = "artifacts/forecast/week1_2026_early_forecast_adequacy_gate.json"
PAYLOAD_SLUG = "week1_2026_early_forecast_adequacy"
FORECAST_PAYLOAD_NAME = "week1_2026_early_forecast_rows.jsonl"
FOCUS_PAYLOAD_NAME = "week1_2026_early_focus_contest_packet.jsonl"
COVERAGE_PAYLOAD_NAME = "week1_2026_early_coverage_table.jsonl"

FORECAST_FROZEN = "FORECAST_FROZEN"
ABSTAIN_FEATURES = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"
QUARANTINED = "QUARANTINED_CONFLICT"
MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
READY = "FORECAST_READY_ALL_REQUIRED_FEATURES_ADMITTED"
LIMITED = "LIMITED_STALE_INPUT_SHADOW_ONLY"
ADEQUATE = "ADEQUATE_FOR_SHADOW_OBSERVATION"
NOT_SUPPORTED = "NOT_SUPPORTED_BY_MODEL_FAMILY"
UNCERTAINTY_NOT_ESTABLISHED = "UNCERTAINTY_NOT_ESTABLISHED"
NO_DIRECTION = "NO_DIRECTION"

GATE_IDENTITY_FIELDS = (
    "schema_version",
    "contract_id",
    "decision_unit",
    "local_issue_id",
    "jira_key",
    "parent_jira_key",
    "classification",
    "lane",
    "protected_lane",
    "season",
    "week_label",
    "checkpoint_id",
    "issued_at_utc",
    "contract_sha256",
    "dataset_identity",
    "record_hashes",
    "payloads",
    "manifest",
    "bound_predecessors",
    "summary",
    "pair_coherence",
    "coverage",
    "focus_contest_report",
    "checkpoints",
    "historical_predecessor_comparison",
    "uncertainty",
    "adequacy",
    "tamu_policy",
    "scientific_nonclaims",
    "result",
)


class EarlyForecastViolation(ValueError):
    """Raised when the early forecast snapshot cannot be built honestly."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = read_json(repo_root / CONTRACT_RELATIVE)
    return load_contract_mapping(contract)


def load_contract_mapping(contract: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "checkpoint_id": "EARLY_WEEK1",
    }
    for key, value in required.items():
        if contract.get(key) != value:
            raise EarlyForecastViolation(
                f"contract field {key} drifted: {contract.get(key)}"
            )
    if list(contract["candidates"]) != [
        "national_base_rate",
        "prior_only",
        "national_elo",
        "national_logistic_l2",
        "national_margin_ridge",
    ]:
        raise EarlyForecastViolation(
            "the early snapshot must bind exactly the five frozen candidates"
        )
    checkpoint = contract["checkpoint"]
    if checkpoint["tamu_t_minus_24h_may_execute_in_this_unit"]:
        raise EarlyForecastViolation("T-24H may not execute inside the early snapshot")
    if checkpoint["tamu_t_minus_90m_may_execute_in_this_unit"]:
        raise EarlyForecastViolation("T-90M may not execute inside the early snapshot")
    if checkpoint["backfill_allowed"]:
        raise EarlyForecastViolation("missed-cutoff backfill is forbidden")
    if contract["uncertainty"]["probability_interval_established"]:
        raise EarlyForecastViolation("a probability interval is not established")
    if contract["adequacy_rule"]["partial_model_input_may_emit_a_forecast"]:
        raise EarlyForecastViolation("partial input may not emit a forecast")
    if contract["focus_contest"]["custom_correction_applied"]:
        raise EarlyForecastViolation("a custom A&M correction is forbidden")
    if contract["focus_contest"]["tamu_specific_adjustment_applied"]:
        raise EarlyForecastViolation("a TAMU-specific adjustment is forbidden")
    if contract["forbidden"]["week1_outcome_access"]:
        raise EarlyForecastViolation("Week 1 outcome access is forbidden")
    return dict(contract)


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    sources = contract["sources"]

    suite_gate = read_json(
        repo_root / sources["national_forecast_suite"]["gate_relative_path"]
    )
    if (
        suite_gate.get("gate_identity")
        != sources["national_forecast_suite"]["gate_identity"]
    ):
        raise EarlyForecastViolation("national forecast suite gate identity drift")
    prior_gate = read_json(
        repo_root / sources["frozen_strength_prior"]["gate_relative_path"]
    )
    if (
        prior_gate.get("gate_identity")
        != sources["frozen_strength_prior"]["gate_identity"]
    ):
        raise EarlyForecastViolation("frozen strength prior gate identity drift")
    for name in (
        "spine_semantic_successor",
        "authority_enrichment",
        "frozen_candidates",
    ):
        gate = read_json(repo_root / sources[name]["gate_relative_path"])
        if gate.get("gate_identity") != sources[name]["gate_identity"]:
            raise EarlyForecastViolation(f"predecessor gate identity drift for {name}")
    rehearsal = read_json(
        repo_root / sources["historical_predecessor_rows"]["gate_relative_path"]
    )
    if (
        rehearsal.get("gate_identity")
        != sources["historical_predecessor_rows"]["gate_identity"]
    ):
        raise EarlyForecastViolation("historical predecessor gate identity drift")

    feature_rows = suite.payload_rows(
        data_root,
        suite_gate,
        sources["national_forecast_suite"]["feature_payload_name"],
    )
    adequacy_rows = suite.payload_rows(
        data_root,
        suite_gate,
        sources["national_forecast_suite"]["adequacy_payload_name"],
    )
    model_rows = suite.payload_rows(
        data_root, suite_gate, sources["national_forecast_suite"]["model_payload_name"]
    )
    parameter_rows = suite.payload_rows(
        data_root,
        suite_gate,
        sources["national_forecast_suite"]["parameter_payload_name"],
    )
    prior_rows = prior_module._payload_rows(
        data_root, prior_gate, sources["frozen_strength_prior"]["prior_payload_name"]
    )
    return {
        "contract": contract,
        "suite_gate": suite_gate,
        "prior_gate": prior_gate,
        "rehearsal_gate": rehearsal,
        "feature_rows": feature_rows,
        "adequacy_rows": adequacy_rows,
        "model_rows": model_rows,
        "parameter_rows": parameter_rows,
        "prior_rows": prior_rows,
    }


def _parameter_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["parameter_set_id"]: dict(row) for row in rows}


def _model_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["candidate_id"]: dict(row) for row in rows}


def _design_row(feature_row: Mapping[str, Any]) -> dict[str, Any]:
    values = dict(feature_row["feature_values"])
    values["canonical_team_id"] = feature_row.get("canonical_team_id")
    values["opponent_canonical_team_id"] = feature_row.get("opponent_canonical_team_id")
    return values


def _score_logistic(
    feature_row: Mapping[str, Any],
    *,
    beta: Sequence[float],
    scope: str,
    transforms: Mapping[str, Any],
    levels: Sequence[str],
    indicators: Sequence[str],
) -> float:
    design, _ = baselines.build_design(
        [_design_row(feature_row)],
        scope=scope,
        transforms=transforms,
        levels=levels,
        indicators=indicators,
    )
    return float(
        baselines.predict_logistic(design, np.asarray(beta, dtype=np.float64))[0]
    )


def _score_margin(
    feature_row: Mapping[str, Any],
    *,
    beta: Sequence[float],
    transforms: Mapping[str, Any],
    levels: Sequence[str],
    indicators: Sequence[str],
) -> float:
    design, _ = baselines.build_design(
        [_design_row(feature_row)],
        scope="ALL_ADMITTED_FEATURES",
        transforms=transforms,
        levels=levels,
        indicators=indicators,
    )
    return float((design @ np.asarray(beta, dtype=np.float64))[0])


def _elo_probability(
    feature_row: Mapping[str, Any], hyperparameters: Mapping[str, Any]
) -> float:
    own = float(feature_row["opening_rating"])
    other = float(feature_row["opponent_opening_rating"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    bonus = 0.0
    if not feature_row["feature_values"].get("is_neutral_site"):
        bonus = (
            advantage if feature_row["feature_values"].get("is_home") else -advantage
        )
    return 1.0 / (1.0 + 10.0 ** (-(own + bonus - other) / scale))


def _direction(probability: float | None, margin: float | None) -> str:
    if probability is None and margin is None:
        return NO_DIRECTION
    if probability is not None and abs(probability - 0.5) <= 1e-12:
        return NO_DIRECTION
    if probability is not None:
        return "HOME" if probability > 0.5 else "AWAY"
    assert margin is not None
    if abs(margin) <= 1e-12:
        return NO_DIRECTION
    return "HOME" if margin > 0.0 else "AWAY"


def _verdict_for_frozen(
    *,
    candidate_id: str,
    home: Mapping[str, Any],
    away: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> str:
    if candidate_id == "national_base_rate":
        return LIMITED
    stale_classes = set(contract["adequacy_rule"]["stale_prior_uncertainty_classes"])
    home_class = home.get("prior_uncertainty_class")
    away_class = away.get("prior_uncertainty_class")
    if home_class in stale_classes or away_class in stale_classes:
        return LIMITED
    return ADEQUATE


def build_forecast_rows(
    *,
    contract: Mapping[str, Any],
    suite_gate: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    adequacy_rows: Sequence[Mapping[str, Any]],
    model_rows: Sequence[Mapping[str, Any]],
    parameter_rows: Sequence[Mapping[str, Any]],
    issued_at_utc: str,
) -> list[dict[str, Any]]:
    parameters = _parameter_index(parameter_rows)
    models = _model_index(model_rows)
    design = parameters["WEEK1_2026_DEPLOYMENT_DESIGN"]
    transforms = design["transforms"]
    levels = design["conference_levels"]
    indicators = design["indicators"]
    logistic_beta = parameters["NATIONAL_LOGISTIC_L2_BETA"]["coefficients"]
    prior_only_beta = parameters["PRIOR_ONLY_BETA"]["coefficients"]
    ridge_beta = parameters["NATIONAL_MARGIN_RIDGE_BETA"]["coefficients"]
    residual_stdev = float(
        suite_gate["deployment_fit"].get("ridge_training_residual_stdev") or 0.0
    )
    # Prefer the residual stdev recorded on the parameter surface when present.
    for key in (
        "ridge_training_residual_stdev",
        "training_residual_stdev",
        "residual_stdev",
    ):
        if key in parameters["NATIONAL_MARGIN_RIDGE_BETA"]:
            residual_stdev = float(parameters["NATIONAL_MARGIN_RIDGE_BETA"][key])
            break
    else:
        residual_stdev = float(
            suite_gate.get("deployment_fit", {}).get("ridge_training_residual_stdev")
            or math.nan
        )
    link_scale = float(
        models["national_margin_ridge"]["hyperparameters"][
            "logistic_link_scale_divisor"
        ]
    )
    elo_hyperparameters = models["national_elo"]["hyperparameters"]
    quantile = float(contract["uncertainty"]["normal_quantile"])

    by_contest: dict[str, list[dict[str, Any]]] = {}
    for row in feature_rows:
        by_contest.setdefault(row["contest_identity"], []).append(dict(row))
    adequacy_index = {
        (row["candidate_id"], row["contest_identity"], row["source_team_id"]): dict(row)
        for row in adequacy_rows
    }

    rows: list[dict[str, Any]] = []
    for contest_identity, oriented in sorted(by_contest.items()):
        if len(oriented) != 2:
            raise EarlyForecastViolation(
                f"contest {contest_identity} does not carry exactly two orientations"
            )
        home = next(
            (row for row in oriented if row["site_orientation"] == "HOME"), None
        )
        away = next(
            (row for row in oriented if row["site_orientation"] == "AWAY"), None
        )
        if home is None or away is None:
            # Neutral contests still carry two oriented rows; pick lexicographic roles.
            ordered = sorted(oriented, key=lambda row: row["source_team_id"])
            home, away = ordered[0], ordered[1]
            orientation_mode = "NEUTRAL_OR_UNKNOWN_ORDERED_BY_SOURCE_TEAM_ID"
        else:
            orientation_mode = "HOME_AWAY"

        kickoff = home["kickoff_bound_utc"]
        if kickoff and issued_at_utc >= kickoff:
            missed = True
        else:
            missed = False

        for candidate_id in contract["candidates"]:
            home_ready = adequacy_index[
                (candidate_id, contest_identity, home["source_team_id"])
            ]
            away_ready = adequacy_index[
                (candidate_id, contest_identity, away["source_team_id"])
            ]
            states = {home_ready["readiness_state"], away_ready["readiness_state"]}
            reasons = sorted(
                set(home_ready.get("abstention_reasons") or [])
                | set(away_ready.get("abstention_reasons") or [])
            )

            if missed:
                state = MISSED_CUTOFF
                verdict = MISSED_CUTOFF
            elif QUARANTINED in states:
                state = QUARANTINED
                verdict = QUARANTINED
            elif ABSTAIN_ENTITY in states:
                state = ABSTAIN_ENTITY
                verdict = ABSTAIN_ENTITY
            elif states != {READY}:
                state = ABSTAIN_FEATURES
                verdict = ABSTAIN_FEATURES
            else:
                state = FORECAST_FROZEN
                verdict = _verdict_for_frozen(
                    candidate_id=candidate_id, home=home, away=away, contract=contract
                )

            probability_home = None
            probability_away = None
            raw_probability_home = None
            raw_probability_away = None
            expected_margin_home = None
            expected_margin_away = None
            raw_margin_home = None
            raw_margin_away = None
            margin_interval_home = None
            margin_interval_away = None
            uncertainty_state = UNCERTAINTY_NOT_ESTABLISHED
            margin_support = NOT_SUPPORTED
            probability_direction = NO_DIRECTION
            margin_direction = NO_DIRECTION

            if state == FORECAST_FROZEN:
                if candidate_id == "national_base_rate":
                    probability_home = 0.5
                    probability_away = 0.5
                    raw_probability_home = 0.5
                    raw_probability_away = 0.5
                elif candidate_id == "national_elo":
                    raw_probability_home = _elo_probability(home, elo_hyperparameters)
                    raw_probability_away = _elo_probability(away, elo_hyperparameters)
                    probability_home = raw_probability_home
                    probability_away = 1.0 - probability_home
                elif candidate_id == "prior_only":
                    raw_probability_home = _score_logistic(
                        home,
                        beta=prior_only_beta,
                        scope="PRIOR_OUTCOME_DOMAIN_AND_SITE",
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    raw_probability_away = _score_logistic(
                        away,
                        beta=prior_only_beta,
                        scope="PRIOR_OUTCOME_DOMAIN_AND_SITE",
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    normalized = normalize_pair_probabilities(
                        raw_probability_home, raw_probability_away
                    )
                    probability_home = float(normalized["p_a_game"])
                    probability_away = float(normalized["p_b_game"])
                elif candidate_id == "national_logistic_l2":
                    raw_probability_home = _score_logistic(
                        home,
                        beta=logistic_beta,
                        scope="ALL_ADMITTED_FEATURES",
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    raw_probability_away = _score_logistic(
                        away,
                        beta=logistic_beta,
                        scope="ALL_ADMITTED_FEATURES",
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    normalized = normalize_pair_probabilities(
                        raw_probability_home, raw_probability_away
                    )
                    probability_home = float(normalized["p_a_game"])
                    probability_away = float(normalized["p_b_game"])
                elif candidate_id == "national_margin_ridge":
                    raw_margin_home = _score_margin(
                        home,
                        beta=ridge_beta,
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    raw_margin_away = _score_margin(
                        away,
                        beta=ridge_beta,
                        transforms=transforms,
                        levels=levels,
                        indicators=indicators,
                    )
                    expected_margin_home = 0.5 * (raw_margin_home - raw_margin_away)
                    expected_margin_away = -expected_margin_home
                    probability_home = float(
                        1.0
                        / (
                            1.0
                            + math.exp(
                                -max(
                                    min(expected_margin_home / link_scale, 30.0), -30.0
                                )
                            )
                        )
                    )
                    probability_away = 1.0 - probability_home
                    raw_probability_home = probability_home
                    raw_probability_away = probability_away
                    margin_support = "SUPPORTED_BY_MODEL_FAMILY"
                    if math.isfinite(residual_stdev) and residual_stdev > 0.0:
                        half = quantile * residual_stdev
                        margin_interval_home = [
                            round(expected_margin_home - half, 10),
                            round(expected_margin_home + half, 10),
                        ]
                        margin_interval_away = [
                            round(expected_margin_away - half, 10),
                            round(expected_margin_away + half, 10),
                        ]
                        uncertainty_state = "DEVELOPMENT_FITTED_RESIDUAL_INTERVAL"
                    else:
                        uncertainty_state = UNCERTAINTY_NOT_ESTABLISHED
                else:
                    raise EarlyForecastViolation(f"unknown candidate: {candidate_id}")

                probability_direction = _direction(probability_home, None)
                margin_direction = _direction(None, expected_margin_home)
                if (
                    expected_margin_home is not None
                    and probability_direction != NO_DIRECTION
                    and margin_direction != NO_DIRECTION
                    and probability_direction != margin_direction
                ):
                    raise EarlyForecastViolation(
                        f"probability and margin directions disagree for {contest_identity}/{candidate_id}"
                    )

            row = {
                "forecast_row_identity": None,
                "checkpoint_id": "EARLY_WEEK1",
                "snapshot_timestamp_utc": issued_at_utc,
                "candidate_id": candidate_id,
                "family": models[candidate_id]["family"],
                "contest_identity": contest_identity,
                "ncaa_contest_id": home["ncaa_contest_id"],
                "orientation_mode": orientation_mode,
                "home_source_team_id": home["source_team_id"],
                "away_source_team_id": away["source_team_id"],
                "home_canonical_team_id": home["canonical_team_id"],
                "away_canonical_team_id": away["canonical_team_id"],
                "home_site_orientation": home["site_orientation"],
                "away_site_orientation": away["site_orientation"],
                "kickoff_bound_utc": kickoff,
                "kickoff_confirmation_state": home["kickoff_confirmation_state"],
                "feature_spine_successor_gate_identity": suite_gate[
                    "bound_predecessors"
                ]["spine_semantic_successor_gate_identity"],
                "prior_gate_identity": suite_gate["bound_predecessors"][
                    "frozen_strength_prior_gate_identity"
                ],
                "forecast_suite_gate_identity": suite_gate["gate_identity"],
                "training_partition": suite_gate["deployment_fit"][
                    "training_partition"
                ],
                "training_season_max": suite_gate["deployment_fit"][
                    "training_season_max"
                ],
                "row_state": state,
                "adequacy_verdict": verdict,
                "abstention_reasons": reasons if state != FORECAST_FROZEN else [],
                "probability_home": None
                if probability_home is None
                else round(float(probability_home), 10),
                "probability_away": None
                if probability_away is None
                else round(float(probability_away), 10),
                "raw_probability_home": None
                if raw_probability_home is None
                else round(float(raw_probability_home), 10),
                "raw_probability_away": None
                if raw_probability_away is None
                else round(float(raw_probability_away), 10),
                "expected_margin_home": None
                if expected_margin_home is None
                else round(float(expected_margin_home), 10),
                "expected_margin_away": None
                if expected_margin_away is None
                else round(float(expected_margin_away), 10),
                "raw_margin_home": None
                if raw_margin_home is None
                else round(float(raw_margin_home), 10),
                "raw_margin_away": None
                if raw_margin_away is None
                else round(float(raw_margin_away), 10),
                "margin_support": margin_support
                if state == FORECAST_FROZEN
                else NOT_SUPPORTED,
                "uncertainty_state": uncertainty_state
                if state == FORECAST_FROZEN
                else UNCERTAINTY_NOT_ESTABLISHED,
                "margin_interval_home": margin_interval_home,
                "margin_interval_away": margin_interval_away,
                "nominal_interval_level": contract["uncertainty"][
                    "nominal_interval_level"
                ]
                if margin_interval_home is not None
                else None,
                "probability_direction": probability_direction
                if state == FORECAST_FROZEN
                else NO_DIRECTION,
                "margin_direction": margin_direction
                if state == FORECAST_FROZEN
                else NO_DIRECTION,
                "home_prior_disposition": home["prior_disposition"],
                "away_prior_disposition": away["prior_disposition"],
                "home_prior_uncertainty_class": home["prior_uncertainty_class"],
                "away_prior_uncertainty_class": away["prior_uncertainty_class"],
                "home_prior_age_seasons": home["prior_age_seasons"],
                "away_prior_age_seasons": away["prior_age_seasons"],
                "home_ranking_state": home["ranking_state"],
                "away_ranking_state": away["ranking_state"],
                "never_recommended": bool(
                    models[candidate_id].get("never_recommended")
                ),
                "recommended": False,
                "promoted": False,
                "custom_correction_applied": False,
                "tamu_specific_adjustment_applied": False,
                "staleness_state": LIMITED
                if verdict == LIMITED
                else ("CURRENT_SUPPORT" if verdict == ADEQUATE else "NOT_APPLICABLE"),
            }
            row["forecast_row_identity"] = stable_hash(
                {
                    key: value
                    for key, value in row.items()
                    if key != "forecast_row_identity"
                }
            )
            rows.append(row)
    rows.sort(key=lambda item: (item["contest_identity"], item["candidate_id"]))
    return rows


def build_coverage_rows(
    forecast_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for row in forecast_rows:
        by_candidate.setdefault(row["candidate_id"], []).append(row)
    for candidate_id, items in sorted(by_candidate.items()):
        counts = Counter(item["row_state"] for item in items)
        verdict_counts = Counter(item["adequacy_verdict"] for item in items)
        rows.append(
            {
                "candidate_id": candidate_id,
                "contest_count": len(items),
                "row_state_counts": dict(sorted(counts.items())),
                "adequacy_verdict_counts": dict(sorted(verdict_counts.items())),
                "frozen_count": counts.get(FORECAST_FROZEN, 0),
                "abstention_count": len(items) - counts.get(FORECAST_FROZEN, 0),
            }
        )
    return rows


def build_focus_packet(
    *,
    contract: Mapping[str, Any],
    suite_gate: Mapping[str, Any],
    forecast_rows: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    prior_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    focus_id = suite_gate["focus_contest_report"]["contest_identity"]
    focus_forecasts = [
        row for row in forecast_rows if row["contest_identity"] == focus_id
    ]
    if len(focus_forecasts) != 5:
        raise EarlyForecastViolation(
            "the focus contest does not carry exactly five candidate rows"
        )
    features = [row for row in feature_rows if row["contest_identity"] == focus_id]
    if len(features) != 2:
        raise EarlyForecastViolation(
            "the focus contest does not carry exactly two feature rows"
        )
    home = next(row for row in features if row["site_orientation"] == "HOME")
    away = next(row for row in features if row["site_orientation"] == "AWAY")
    prior_by_source = {
        row["source_team_id"]: row for row in prior_rows if "source_team_id" in row
    }
    # Fall back to canonical identity when the prior payload is keyed that way.
    if home["source_team_id"] not in prior_by_source:
        prior_by_source = {
            row.get("source_team_id") or row.get("canonical_team_id"): row
            for row in prior_rows
        }
    historical = contract["sources"]["historical_predecessor_rows"]
    disagreement = sorted(
        {
            (
                row["candidate_id"],
                row["probability_home"],
                row["row_state"],
                row["adequacy_verdict"],
            )
            for row in focus_forecasts
        }
    )
    packet = {
        "packet_identity": None,
        "contest_identity": focus_id,
        "ncaa_contest_id": home["ncaa_contest_id"],
        "home_source_team_id": home["source_team_id"],
        "away_source_team_id": away["source_team_id"],
        "home_canonical_team_id": home["canonical_team_id"],
        "away_canonical_team_id": away["canonical_team_id"],
        "site_orientation_home": home["site_orientation"],
        "kickoff_bound_utc": home["kickoff_bound_utc"],
        "kickoff_confirmation_state": home["kickoff_confirmation_state"],
        "candidate_rows": [
            {
                "candidate_id": row["candidate_id"],
                "row_state": row["row_state"],
                "adequacy_verdict": row["adequacy_verdict"],
                "probability_home": row["probability_home"],
                "probability_away": row["probability_away"],
                "expected_margin_home": row["expected_margin_home"],
                "uncertainty_state": row["uncertainty_state"],
                "margin_interval_home": row["margin_interval_home"],
                "never_recommended": row["never_recommended"],
                "abstention_reasons": row["abstention_reasons"],
            }
            for row in sorted(focus_forecasts, key=lambda item: item["candidate_id"])
        ],
        "home_prior": {
            "disposition": home["prior_disposition"],
            "uncertainty_class": home["prior_uncertainty_class"],
            "age_seasons": home["prior_age_seasons"],
            "opening_rating": home["opening_rating"],
            "pre_week_zero_rating": home["pre_week_zero_rating"],
        },
        "away_prior": {
            "disposition": away["prior_disposition"],
            "uncertainty_class": away["prior_uncertainty_class"],
            "age_seasons": away["prior_age_seasons"],
            "opening_rating": away["opening_rating"],
            "pre_week_zero_rating": away["pre_week_zero_rating"],
        },
        "home_ranking_state": home["ranking_state"],
        "away_ranking_state": away["ranking_state"],
        "feature_coverage_home": {
            "admitted_feature_names": home["admitted_feature_names"],
            "features_missing_behind_a_learned_indicator": home[
                "features_missing_behind_a_learned_indicator"
            ],
            "features_neither_admitted_nor_indicator_covered": home[
                "features_neither_admitted_nor_indicator_covered"
            ],
        },
        "candidate_disagreement": [
            {
                "candidate_id": item[0],
                "probability_home": item[1],
                "row_state": item[2],
                "adequacy_verdict": item[3],
            }
            for item in disagreement
        ],
        "historical_predecessor_comparison": {
            "immutable_base_rate_probability": historical[
                "immutable_base_rate_probability"
            ],
            "immutable_elo_probability": historical["immutable_elo_probability"],
            "may_be_relabelled_as_current": False,
            "may_be_presented_as_recommended": False,
            "current_base_rate_is_the_same_control": True,
            "current_elo_is_a_separate_frozen_row": True,
        },
        "custom_correction_applied": False,
        "tamu_specific_adjustment_applied": False,
        "pregame_bas_score": None,
        "predeclared_result_residual": contract["focus_contest"][
            "predeclared_result_residual"
        ],
        "predeclared_margin_residual": contract["focus_contest"][
            "predeclared_margin_residual"
        ],
        "outcome_read": False,
        "hardcoded_participant_identities": [],
        "discovery_rule": contract["focus_contest"]["discovery_rule"],
    }
    packet["packet_identity"] = stable_hash(
        {key: value for key, value in packet.items() if key != "packet_identity"}
    )
    return [packet]


def _pair_coherence_report(
    forecast_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tolerance = 1e-09
    checked = 0
    max_probability_error = 0.0
    max_margin_error = 0.0
    direction_disagreements = 0
    for row in forecast_rows:
        if row["row_state"] != FORECAST_FROZEN:
            continue
        checked += 1
        error = abs(
            float(row["probability_home"]) + float(row["probability_away"]) - 1.0
        )
        max_probability_error = max(max_probability_error, error)
        if row["expected_margin_home"] is not None:
            margin_error = abs(
                float(row["expected_margin_home"]) + float(row["expected_margin_away"])
            )
            max_margin_error = max(max_margin_error, margin_error)
            if (
                row["probability_direction"] != NO_DIRECTION
                and row["margin_direction"] != NO_DIRECTION
                and row["probability_direction"] != row["margin_direction"]
            ):
                direction_disagreements += 1
    if max_probability_error > tolerance:
        raise EarlyForecastViolation(
            f"probability pairs are not coherent within tolerance: {max_probability_error}"
        )
    if max_margin_error > tolerance:
        raise EarlyForecastViolation(
            f"margin pairs are not coherent within tolerance: {max_margin_error}"
        )
    if direction_disagreements:
        raise EarlyForecastViolation("probability and margin directions disagree")
    return {
        "frozen_rows_checked": checked,
        "probability_tolerance": tolerance,
        "margin_tolerance": tolerance,
        "max_probability_complement_error": round(max_probability_error, 12),
        "max_margin_sum_error": round(max_margin_error, 12),
        "direction_disagreement_count": direction_disagreements,
        "pair_coherence_holds": True,
    }


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    loaded = load_inputs(repo_root, data_root)
    contract = loaded["contract"]
    forecast_rows = build_forecast_rows(
        contract=contract,
        suite_gate=loaded["suite_gate"],
        feature_rows=loaded["feature_rows"],
        adequacy_rows=loaded["adequacy_rows"],
        model_rows=loaded["model_rows"],
        parameter_rows=loaded["parameter_rows"],
        issued_at_utc=issued_at_utc,
    )
    coverage_rows = build_coverage_rows(forecast_rows)
    focus_packet = build_focus_packet(
        contract=contract,
        suite_gate=loaded["suite_gate"],
        forecast_rows=forecast_rows,
        feature_rows=loaded["feature_rows"],
        prior_rows=loaded["prior_rows"],
    )
    pair_coherence = _pair_coherence_report(forecast_rows)
    state_counts = Counter(row["row_state"] for row in forecast_rows)
    verdict_counts = Counter(row["adequacy_verdict"] for row in forecast_rows)
    return {
        "contract": contract,
        "loaded": loaded,
        "forecast_rows": forecast_rows,
        "coverage_rows": coverage_rows,
        "focus_packet": focus_packet,
        "pair_coherence": pair_coherence,
        "summary": {
            "candidate_count": 5,
            "contest_count": len({row["contest_identity"] for row in forecast_rows}),
            "forecast_row_count": len(forecast_rows),
            "row_state_counts": dict(sorted(state_counts.items())),
            "adequacy_verdict_counts": dict(sorted(verdict_counts.items())),
            "recommended_candidate": None,
            "promoted_candidate": None,
            "week1_outcome_access": False,
            "week_zero_used_to_tune_select_or_promote": False,
            "custom_correction_applied": False,
            "tamu_specific_adjustment_applied": False,
            "base_rate_presented_as_recommended": False,
        },
    }


def build_gate(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    built = expected or build_expected(
        repo_root=repo_root, data_root=data_root, issued_at_utc=issued_at_utc
    )
    contract = built["contract"]
    loaded = built["loaded"]
    forecast_payload = jsonl_bytes(built["forecast_rows"])
    coverage_payload = jsonl_bytes(built["coverage_rows"])
    focus_payload = jsonl_bytes(built["focus_packet"])
    payloads = [
        {
            "name": FORECAST_PAYLOAD_NAME,
            "role": "WEEK1_2026_EARLY_FORECAST_ROWS",
            "rows": len(built["forecast_rows"]),
            "bytes": len(forecast_payload),
            "sha256": sha256_bytes(forecast_payload),
        },
        {
            "name": COVERAGE_PAYLOAD_NAME,
            "role": "WEEK1_2026_EARLY_COVERAGE_TABLE",
            "rows": len(built["coverage_rows"]),
            "bytes": len(coverage_payload),
            "sha256": sha256_bytes(coverage_payload),
        },
        {
            "name": FOCUS_PAYLOAD_NAME,
            "role": "WEEK1_2026_EARLY_FOCUS_CONTEST_PACKET",
            "rows": len(built["focus_packet"]),
            "bytes": len(focus_payload),
            "sha256": sha256_bytes(focus_payload),
        },
    ]
    dataset_identity = stable_hash(
        {
            "payloads": payloads,
            "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
            "suite_gate_identity": loaded["suite_gate"]["gate_identity"],
            "issued_at_utc": issued_at_utc,
        }
    )
    record_hashes = {
        "forecast_rows": sha256_bytes(forecast_payload),
        "coverage_rows": sha256_bytes(coverage_payload),
        "focus_packet": sha256_bytes(focus_payload),
        "core_module": sha256_file(
            repo_root / "src/aggie_analytics/data/week1_2026_early_forecast_adequacy.py"
        ),
    }
    gate = {
        "schema_version": SCHEMA_VERSION,
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
        "checkpoint_id": "EARLY_WEEK1",
        "issued_at_utc": issued_at_utc,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "payloads": payloads,
        "manifest": {
            "relative_path": (
                f"manifests/{PAYLOAD_SLUG}/sha256/{dataset_identity}/"
                f"{PAYLOAD_SLUG}_manifest.json"
            ),
            "dataset_identity": dataset_identity,
            "authoritative_sha256": None,
        },
        "bound_predecessors": {
            "national_forecast_suite_gate_identity": loaded["suite_gate"][
                "gate_identity"
            ],
            "frozen_strength_prior_gate_identity": loaded["prior_gate"][
                "gate_identity"
            ],
            "spine_semantic_successor_gate_identity": contract["sources"][
                "spine_semantic_successor"
            ]["gate_identity"],
            "authority_enrichment_gate_identity": contract["sources"][
                "authority_enrichment"
            ]["gate_identity"],
            "frozen_candidate_gate_identity": contract["sources"]["frozen_candidates"][
                "gate_identity"
            ],
            "historical_rehearsal_gate_identity": loaded["rehearsal_gate"][
                "gate_identity"
            ],
            "predecessor_artifacts_rewritten_in_place": False,
            "preserved_predecessor_forecast_rows": [
                "THE_HISTORICAL_FIFTY_PERCENT_CONTROL_ROW",
                "THE_HISTORICAL_SIXTY_EIGHT_POINT_ONE_NINE_PERCENT_ELO_ROW",
            ],
        },
        "summary": built["summary"],
        "pair_coherence": built["pair_coherence"],
        "coverage": {
            "by_candidate": built["coverage_rows"],
            "national_row_count": len(built["forecast_rows"]),
        },
        "focus_contest_report": {
            "contest_identity": built["focus_packet"][0]["contest_identity"],
            "packet_identity": built["focus_packet"][0]["packet_identity"],
            "candidate_count": 5,
            "custom_correction_applied": False,
            "tamu_specific_adjustment_applied": False,
            "outcome_read": False,
            "hardcoded_participant_identities": [],
        },
        "checkpoints": {
            "checkpoint_id": "EARLY_WEEK1",
            "t_minus_24h_state": "OPEN",
            "t_minus_90m_state": "OPEN",
            "executed_early": False,
            "week1_outcome_access": False,
            "pregame_result_access": False,
            "backfill_allowed": False,
        },
        "historical_predecessor_comparison": built["focus_packet"][0][
            "historical_predecessor_comparison"
        ],
        "uncertainty": {
            "nominal_interval_level": contract["uncertainty"]["nominal_interval_level"],
            "probability_interval_established": False,
            "margin_interval_allowed_candidates": ["national_margin_ridge"],
            "aleatoric_and_epistemic_are_reported_separately": True,
        },
        "adequacy": {
            "verdicts": list(contract["adequacy_verdicts"]),
            "partial_model_input_may_emit_a_forecast": False,
            "credibility_may_rest_on_intuitive_plausibility": False,
            "verdict_counts": built["summary"]["adequacy_verdict_counts"],
        },
        "tamu_policy": {
            "custom_correction_applied": False,
            "tamu_specific_adjustment_applied": False,
        },
        "scientific_nonclaims": list(contract["scientific_nonclaims"]),
        "artifact_type": "WEEK1_2026_EARLY_FORECAST_ADEQUACY_GATE",
        "result": PASS_RESULT,
        "gate_identity": None,
        "binding_identity": None,
        "code_identity": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
    }
    manifest_body = {
        "dataset_identity": dataset_identity,
        "payloads": payloads,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": gate["contract_sha256"],
    }
    gate["manifest"]["authoritative_sha256"] = stable_hash(manifest_body)
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    gate["_payload_bytes"] = {
        FORECAST_PAYLOAD_NAME: forecast_payload,
        COVERAGE_PAYLOAD_NAME: coverage_payload,
        FOCUS_PAYLOAD_NAME: focus_payload,
    }
    gate["_manifest_body"] = manifest_body
    return gate


def enforce_invariants(gate: Mapping[str, Any]) -> None:
    if gate.get("result") != PASS_RESULT:
        raise EarlyForecastViolation(f"unexpected result: {gate.get('result')}")
    if gate.get("jira_key") != JIRA_KEY:
        raise EarlyForecastViolation("jira key drift")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise EarlyForecastViolation("protected lane drift")
    if gate["checkpoints"]["t_minus_24h_state"] != "OPEN":
        raise EarlyForecastViolation("T-24H is not OPEN")
    if gate["checkpoints"]["t_minus_90m_state"] != "OPEN":
        raise EarlyForecastViolation("T-90M is not OPEN")
    if gate["checkpoints"]["week1_outcome_access"]:
        raise EarlyForecastViolation("Week 1 outcome access leaked into the gate")
    if gate["summary"]["recommended_candidate"] is not None:
        raise EarlyForecastViolation("a recommended candidate was claimed")
    if gate["summary"]["base_rate_presented_as_recommended"]:
        raise EarlyForecastViolation(
            "the base-rate control was presented as recommended"
        )
    if gate["focus_contest_report"]["custom_correction_applied"]:
        raise EarlyForecastViolation("a custom A&M correction leaked into the gate")
    if gate["tamu_policy"]["tamu_specific_adjustment_applied"]:
        raise EarlyForecastViolation("a TAMU-specific adjustment leaked into the gate")
    if not gate["pair_coherence"]["pair_coherence_holds"]:
        raise EarlyForecastViolation("pair coherence failed")
    if compute_gate_identity(gate) != gate["gate_identity"]:
        raise EarlyForecastViolation("gate identity does not recompute")


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    gate = build_gate(
        repo_root=repo_root, data_root=data_root, issued_at_utc=issued_at_utc
    )
    payload_bytes = gate.pop("_payload_bytes")
    manifest_body = gate.pop("_manifest_body")
    identity = gate["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    manifest_root = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / identity

    manifest_payloads: list[dict[str, Any]] = []
    for entry in gate["payloads"]:
        name = entry["name"]
        path = canonical_root / name
        _write_bytes(path, payload_bytes[name])
        manifest_payloads.append({**entry, "relative_path": _relative(path, data_root)})
    on_disk_manifest = {
        **manifest_body,
        "payloads": manifest_payloads,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_EARLY_FORECAST_ADEQUACY_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
    }
    manifest_path = data_root / gate["manifest"]["relative_path"]
    assert manifest_path == manifest_root / f"{PAYLOAD_SLUG}_manifest.json"
    _write_bytes(
        manifest_path,
        json.dumps(on_disk_manifest, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    public_gate = {key: value for key, value in gate.items() if not key.startswith("_")}
    _write_bytes(
        repo_root / GATE_RELATIVE,
        json.dumps(public_gate, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    enforce_invariants(public_gate)
    return public_gate


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    gate = read_json(repo_root / GATE_RELATIVE)
    enforce_invariants(gate)
    if not require_rebuild:
        return {
            "result": "PASS",
            "mode": "SCHEMA_ONLY",
            "gate_identity": gate["gate_identity"],
        }
    rebuilt = build_gate(
        repo_root=repo_root,
        data_root=data_root,
        issued_at_utc=gate["issued_at_utc"],
    )
    rebuilt.pop("_payload_bytes", None)
    rebuilt.pop("_manifest_body", None)
    if rebuilt["gate_identity"] != gate["gate_identity"]:
        raise EarlyForecastViolation(
            "independent rebuild drifted from the committed gate"
        )
    if rebuilt["dataset_identity"] != gate["dataset_identity"]:
        raise EarlyForecastViolation(
            "dataset identity drifted under independent rebuild"
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "gate_identity": gate["gate_identity"],
        "dataset_identity": gate["dataset_identity"],
        "summary": gate["summary"],
        "pair_coherence": gate["pair_coherence"],
        "focus_contest_report": gate["focus_contest_report"],
    }
