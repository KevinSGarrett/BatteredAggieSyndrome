from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# Predeclared national expectation baselines, a rule-derived peer cohort, and a
# development-only Texas A&M residual pipeline test.
#
# The candidate set is frozen in the contract before the 2023 partition is ever
# scored. Every candidate is refitted inside each expanding fold on that fold's
# training partition alone, so no evaluation row ever informs its own prediction.

SCHEMA_VERSION = "aggie.models.national_expectation_baselines_and_peers.v1"
CONTRACT_RELATIVE = "configs/national_expectation_baselines_and_peers_contract.json"
CONTRACT_ID = "BAT-655-NATIONAL-EXPECTATION-BASELINES-AND-PEERS-V1"
GATE_RELATIVE = "artifacts/experimentation/national_expectation_baselines_and_peers_gate.json"
PASS_RESULT = "PASS_NATIONAL_EXPECTATION_BASELINES_DEVELOPMENT_ONLY_NO_CHAMPION"
CLASSIFICATION = "NATIONAL_EXPECTATION_BASELINES_PEER_COHORT_AND_DEVELOPMENT_RESIDUAL_TEST"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

TAMU_TEAM_ID = "SRC-002:TEAM:245"

# Reported floats are rounded before they enter any identity so that a rebuild on
# another BLAS implementation cannot drift the gate identity in the last bits.
ROUND_DIGITS = 8

PRIOR_DOMAIN_NUMERIC = (
    "prior_games_played",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
    "prior_margin_mean",
    "prior_season_win_rate",
    "season_to_date_games",
    "season_to_date_win_rate",
    "opponent_prior_games_played",
    "opponent_prior_win_rate",
    "opponent_prior_margin_mean",
    "opponent_prior_season_win_rate",
    "prior_win_rate_differential",
)

PRIOR_DOMAIN_BOOLEAN = ("is_home", "is_neutral_site")

ALL_NUMERIC = PRIOR_DOMAIN_NUMERIC + (
    "ap_poll_rank",
    "coaches_poll_rank",
    "opponent_ap_poll_rank",
    "venue_elevation_m",
    "venue_latitude",
    "venue_longitude",
)

ALL_BOOLEAN = PRIOR_DOMAIN_BOOLEAN + (
    "rankings_source_available",
    "venue_dome",
    "venue_grass",
    "team_is_fbs",
)

FEATURE_SCOPES = {
    "NONE": ((), (), False),
    "PRIOR_OUTCOME_DOMAIN_AND_SITE": (PRIOR_DOMAIN_NUMERIC, PRIOR_DOMAIN_BOOLEAN, False),
    "OUTCOME_SEQUENCE_AND_SITE": ((), PRIOR_DOMAIN_BOOLEAN, False),
    "ALL_ADMITTED_FEATURES": (ALL_NUMERIC, ALL_BOOLEAN, True),
}

# A conference level must be common enough inside a fold's own training partition
# before it earns a column; everything rarer collapses into one bucket.
MIN_CONFERENCE_TRAINING_ROWS = 50

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "calibration",
    "candidates",
    "classification",
    "cohort",
    "contract_id",
    "contract_sha256",
    "dataset_identity",
    "decision_unit",
    "jira_key",
    "leakage_checks",
    "manifest",
    "parent_jira_key",
    "payloads",
    "peer_cohort",
    "precommitment",
    "preserved_predecessor_result",
    "protected_lane",
    "residual_test",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "slices",
    "source_identities",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _require_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned input: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"pinned input SHA-256 drift: {path}")


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return round(float(value), ROUND_DIGITS)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return _round(numerator / denominator)


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("national baseline contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("national baseline schema drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("protected lane must remain blocked")

    precommitment = contract["precommitment"]
    if precommitment.get("candidate_set_frozen_before_evaluation") is not True:
        raise ValueError("the candidate set is not declared as frozen")
    for key in (
        "post_hoc_candidate_insertion",
        "post_hoc_feature_shopping",
        "hyperparameter_search_on_the_evaluation_season",
        "boosting_neural_sequence_or_graph_models",
        "champion_promotion",
    ):
        if precommitment.get(key) is not False:
            raise ValueError(f"precommitment is violated: {key}")

    authority = contract["authority"]
    if authority.get("national_baseline_development_evaluation") is not True:
        raise ValueError("baseline evaluation authority is not enabled")
    for key in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"baseline authority is open: {key}")

    residual = contract["residual_test"]
    for key in (
        "claims_bas_or_aggie_excess",
        "claims_tamu_lift_or_specialization_benefit",
        "claims_statistical_persistence",
    ):
        if residual.get(key) is not False:
            raise ValueError(f"the residual test asserts a forbidden claim: {key}")
    if residual.get("baseline_is_unchanged_by_the_residual_test") is not True:
        raise ValueError("the residual test must not alter the national baseline")

    preserved = contract["preserved_predecessor_result"]
    if preserved.get("predecessor_is_preserved_not_superseded") is not True:
        raise ValueError("the predecessor candidate ledger must be preserved")

    declared = [candidate["candidate_id"] for candidate in contract["candidates"]]
    if len(declared) != len(set(declared)):
        raise ValueError("duplicate candidate identifiers")
    for candidate in contract["candidates"]:
        if candidate["feature_scope"] not in FEATURE_SCOPES:
            raise ValueError(f"unknown feature scope: {candidate['feature_scope']}")
    if residual["reference_candidate"] not in declared:
        raise ValueError("the residual reference candidate is not predeclared")
    return contract


def _load_payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = _read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ValueError(f"source payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# design matrices
# ---------------------------------------------------------------------------


def conference_levels(training: Sequence[Mapping[str, Any]]) -> list[str]:
    counts: defaultdict[str, int] = defaultdict(int)
    for row in training:
        conference = row.get("team_conference")
        if conference:
            counts[str(conference)] += 1
    return sorted(name for name, count in counts.items() if count >= MIN_CONFERENCE_TRAINING_ROWS)


def _indicator_names(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    if not rows:
        return ()
    return tuple(sorted(key for key in rows[0] if key.endswith("_missing")))


def build_design(
    rows: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    transforms: Mapping[str, Any],
    levels: Sequence[str],
    indicators: Sequence[str],
) -> tuple[np.ndarray, list[str]]:
    """Encode rows into a fold-local standardized design matrix with an intercept."""
    numeric, boolean, use_conference = FEATURE_SCOPES[scope]
    columns = list(numeric)
    columns.extend(f"{feature}_missing" for feature in numeric if f"{feature}_missing" in indicators)
    columns.extend(boolean)
    columns.extend(f"{feature}_missing" for feature in boolean if f"{feature}_missing" in indicators)
    level_list = list(levels)
    if use_conference:
        columns.extend(f"team_conference={level}" for level in level_list)
        columns.append("team_conference=OTHER_OR_MISSING")

    matrix = np.zeros((len(rows), len(columns) + 1), dtype=np.float64)
    matrix[:, 0] = 1.0
    index = {name: position + 1 for position, name in enumerate(columns)}

    for position, row in enumerate(rows):
        for feature in numeric:
            value = row.get(feature)
            if value is None:
                continue
            stats = transforms.get(feature) or {}
            mean = stats.get("mean")
            stdev = stats.get("stdev")
            if mean is None:
                continue
            scaled = float(value) - float(mean)
            if stdev:
                scaled /= float(stdev)
            matrix[position, index[feature]] = scaled
        for feature in numeric:
            name = f"{feature}_missing"
            if name in index and row.get(name):
                matrix[position, index[name]] = 1.0
        for feature in boolean:
            value = row.get(feature)
            if value:
                matrix[position, index[feature]] = 1.0
            name = f"{feature}_missing"
            if name in index and row.get(name):
                matrix[position, index[name]] = 1.0
        if use_conference:
            conference = row.get("team_conference")
            key = f"team_conference={conference}"
            if conference and key in index:
                matrix[position, index[key]] = 1.0
            else:
                matrix[position, index["team_conference=OTHER_OR_MISSING"]] = 1.0
    return matrix, columns


# ---------------------------------------------------------------------------
# estimators
# ---------------------------------------------------------------------------


def fit_logistic_l2(
    design: np.ndarray, target: np.ndarray, *, l2_lambda: float, iterations: int, tolerance: float
) -> np.ndarray:
    """Newton-Raphson logistic regression with a ridge penalty that spares the intercept."""
    beta = np.zeros(design.shape[1], dtype=np.float64)
    penalty = np.full(design.shape[1], float(l2_lambda), dtype=np.float64)
    penalty[0] = 0.0
    for _ in range(int(iterations)):
        eta = design @ beta
        probability = 1.0 / (1.0 + np.exp(-np.clip(eta, -30.0, 30.0)))
        weight = np.clip(probability * (1.0 - probability), 1e-9, None)
        gradient = design.T @ (target - probability) - penalty * beta
        hessian = (design.T * weight) @ design + np.diag(penalty)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hessian, gradient, rcond=None)[0]
        beta = beta + step
        if float(np.max(np.abs(step))) < tolerance:
            break
    return beta


def predict_logistic(design: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30.0, 30.0)))


def fit_ridge(design: np.ndarray, target: np.ndarray, *, l2_lambda: float) -> np.ndarray:
    penalty = np.full(design.shape[1], float(l2_lambda), dtype=np.float64)
    penalty[0] = 0.0
    left = design.T @ design + np.diag(penalty)
    right = design.T @ target
    try:
        return np.linalg.solve(left, right)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(left, right, rcond=None)[0]


def elo_ratings(
    training: Sequence[Mapping[str, Any]],
    labels: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    hyperparameters: Mapping[str, Any],
) -> dict[str, float]:
    """Replay Elo chronologically across the fold training partition only."""
    initial = float(hyperparameters["initial_rating"])
    k_factor = float(hyperparameters["k_factor"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    regression = float(hyperparameters["between_season_regression"])

    ratings: dict[str, float] = {}
    by_game: dict[str, list[Mapping[str, Any]]] = {}
    order: list[str] = []
    for row in training:
        game_id = row["canonical_game_id"]
        if game_id not in by_game:
            by_game[game_id] = []
            order.append(game_id)
        by_game[game_id].append(row)

    current_season: int | None = None
    for game_id in order:
        rows = by_game[game_id]
        if len(rows) != 2:
            continue
        season = int(rows[0]["season"])
        if current_season is not None and season != current_season:
            for team in list(ratings):
                ratings[team] = initial + (ratings[team] - initial) * (1.0 - regression)
        current_season = season

        first, second = sorted(rows, key=lambda row: row["canonical_team_id"])
        left = first["canonical_team_id"]
        right = second["canonical_team_id"]
        left_rating = ratings.get(left, initial)
        right_rating = ratings.get(right, initial)

        left_bonus = 0.0
        if not first.get("is_neutral_site"):
            if first.get("is_home"):
                left_bonus = advantage
            elif second.get("is_home"):
                left_bonus = -advantage
        expected = 1.0 / (1.0 + 10.0 ** (-(left_rating + left_bonus - right_rating) / scale))

        label = labels.get((game_id, left))
        if label is None:
            continue
        if label["label_tie"]:
            observed = 0.5
        else:
            observed = 1.0 if label["label_win"] else 0.0
        delta = k_factor * (observed - expected)
        ratings[left] = left_rating + delta
        ratings[right] = right_rating - delta
    return ratings


def elo_probability(
    row: Mapping[str, Any], ratings: Mapping[str, float], *, hyperparameters: Mapping[str, Any]
) -> float:
    initial = float(hyperparameters["initial_rating"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    own = ratings.get(row["canonical_team_id"], initial)
    other = ratings.get(row["opponent_canonical_team_id"], initial)
    bonus = 0.0
    if not row.get("is_neutral_site"):
        bonus = advantage if row.get("is_home") else -advantage
    return 1.0 / (1.0 + 10.0 ** (-(own + bonus - other) / scale))


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------


def _target(label: Mapping[str, Any], tie_value: float) -> float:
    if label["label_tie"]:
        return float(tie_value)
    return 1.0 if label["label_win"] else 0.0


def score_predictions(
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    *,
    clip: Sequence[float],
    bin_count: int,
) -> dict[str, Any]:
    # The clip keeps a confident forecast away from an infinite log loss.
    low = max(float(clip[0]), 1e-15)
    high = min(float(clip[1]), 1.0 - 1e-15)
    clipped = np.clip(probabilities, low, high)
    brier = float(np.mean((clipped - outcomes) ** 2))
    log_loss = float(
        -np.mean(outcomes * np.log(clipped) + (1.0 - outcomes) * np.log(1.0 - clipped))
    )
    decided = np.where(clipped > 0.5, 1.0, np.where(clipped < 0.5, 0.0, 0.5))
    accuracy = float(np.mean(1.0 - np.abs(decided - outcomes)))
    return {
        "rows": int(len(outcomes)),
        "brier": _round(brier),
        "log_loss": _round(log_loss),
        "accuracy": _round(accuracy),
        "mean_predicted": _round(float(np.mean(clipped))),
        "observed_rate": _round(float(np.mean(outcomes))),
        "calibration_bins": calibration_bins(clipped, outcomes, bin_count=bin_count),
        **calibration_fit(clipped, outcomes),
    }


def calibration_bins(
    probabilities: np.ndarray, outcomes: np.ndarray, *, bin_count: int
) -> list[dict[str, Any]]:
    edges = np.linspace(0.0, 1.0, int(bin_count) + 1)
    bins: list[dict[str, Any]] = []
    for index in range(int(bin_count)):
        lower, upper = edges[index], edges[index + 1]
        if index == int(bin_count) - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        count = int(np.count_nonzero(mask))
        bins.append(
            {
                "bin_index": index,
                "lower": _round(float(lower)),
                "upper": _round(float(upper)),
                "rows": count,
                "mean_predicted": _round(float(np.mean(probabilities[mask]))) if count else None,
                "observed_rate": _round(float(np.mean(outcomes[mask]))) if count else None,
            }
        )
    return bins


def calibration_fit(probabilities: np.ndarray, outcomes: np.ndarray) -> dict[str, Any]:
    """Logistic recalibration of the outcome on the predicted logit."""
    if len(np.unique(np.round(probabilities, 12))) < 2 or len(np.unique(outcomes)) < 2:
        return {
            "calibration_slope": None,
            "calibration_intercept": None,
            "calibration_supported": False,
        }
    logit = np.log(probabilities / (1.0 - probabilities))
    design = np.column_stack([np.ones_like(logit), logit])
    beta = fit_logistic_l2(design, outcomes, l2_lambda=0.0, iterations=50, tolerance=1e-12)
    return {
        "calibration_slope": _round(float(beta[1])),
        "calibration_intercept": _round(float(beta[0])),
        "calibration_supported": True,
    }


def bootstrap_interval(
    values: np.ndarray, groups: Sequence[str], *, resamples: int, seed: int
) -> dict[str, Any]:
    """Percentile bootstrap resampling whole games so paired team rows travel together."""
    unique = sorted(set(groups))
    index_of: dict[str, list[int]] = {name: [] for name in unique}
    for position, name in enumerate(groups):
        index_of[name].append(position)
    generator = np.random.default_rng(int(seed))
    draws = np.empty(int(resamples), dtype=np.float64)
    keys = np.array(unique)
    for draw in range(int(resamples)):
        chosen = generator.integers(0, len(keys), size=len(keys))
        positions: list[int] = []
        for pick in chosen:
            positions.extend(index_of[keys[pick]])
        draws[draw] = float(np.mean(values[positions]))
    return {
        "point_estimate": _round(float(np.mean(values))),
        "resamples": int(resamples),
        "bootstrap_unit": "GAME",
        "percentile_2_5": _round(float(np.percentile(draws, 2.5))),
        "percentile_97_5": _round(float(np.percentile(draws, 97.5))),
    }


# ---------------------------------------------------------------------------
# fold evaluation
# ---------------------------------------------------------------------------


def evaluate_candidates(
    *,
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    folds: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[tuple[str, str], float]],
    dict[str, dict[tuple[str, str], float]],
]:
    """Refit every predeclared candidate inside every fold and predict that fold alone."""
    evaluation = contract["evaluation"]
    tie_value = float(evaluation["tie_target_value"])
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    row_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in matrix
    }
    indicators = _indicator_names(matrix)

    predictions: list[dict[str, Any]] = []
    margins: dict[str, dict[tuple[str, str], float]] = {}
    probability_index: dict[str, dict[tuple[str, str], float]] = {
        candidate["candidate_id"]: {} for candidate in contract["candidates"]
    }

    for fold in folds:
        boundary = int(fold["training_max_ordinal_exclusive"])
        fold_ordinals = set(fold["evaluation_ordinals"])
        training = [row for row in matrix if row["chronological_ordinal"] < boundary]
        holdout = [row for row in matrix if row["chronological_ordinal"] in fold_ordinals]
        if not training or not holdout:
            raise ValueError(f"fold {fold['fold_id']} has an empty partition")
        if fold_ordinals & {row["chronological_ordinal"] for row in training}:
            raise ValueError(f"fold {fold['fold_id']} trained on its own evaluation rows")

        transforms = fold["fold_local_transforms"]
        levels = conference_levels(training)
        training_target = np.array(
            [
                _target(label_index[(row["canonical_game_id"], row["canonical_team_id"])], tie_value)
                for row in training
            ],
            dtype=np.float64,
        )
        training_margin = np.array(
            [
                float(label_index[(row["canonical_game_id"], row["canonical_team_id"])]["label_margin"])
                for row in training
            ],
            dtype=np.float64,
        )

        for candidate in contract["candidates"]:
            candidate_id = candidate["candidate_id"]
            scope = candidate["feature_scope"]
            family = candidate["family"]
            hyperparameters = candidate["hyperparameters"]

            if family == "UNFITTED_REFERENCE":
                rate = float(np.mean(training_target))
                probabilities = np.full(len(holdout), rate, dtype=np.float64)
                predicted_margin = None
            elif family == "ELO":
                ratings = elo_ratings(
                    training, label_index, hyperparameters=hyperparameters
                )
                probabilities = np.array(
                    [
                        elo_probability(row, ratings, hyperparameters=hyperparameters)
                        for row in holdout
                    ],
                    dtype=np.float64,
                )
                predicted_margin = None
            elif family == "REGULARIZED_LOGISTIC":
                design, _ = build_design(
                    training,
                    scope=scope,
                    transforms=transforms,
                    levels=levels,
                    indicators=indicators,
                )
                beta = fit_logistic_l2(
                    design,
                    training_target,
                    l2_lambda=float(hyperparameters["l2_lambda"]),
                    iterations=int(hyperparameters["newton_iterations"]),
                    tolerance=float(hyperparameters["tolerance"]),
                )
                holdout_design, _ = build_design(
                    holdout,
                    scope=scope,
                    transforms=transforms,
                    levels=levels,
                    indicators=indicators,
                )
                probabilities = predict_logistic(holdout_design, beta)
                predicted_margin = None
            elif family == "RIDGE_MARGIN":
                design, _ = build_design(
                    training,
                    scope=scope,
                    transforms=transforms,
                    levels=levels,
                    indicators=indicators,
                )
                beta = fit_ridge(
                    design, training_margin, l2_lambda=float(hyperparameters["l2_lambda"])
                )
                residual = training_margin - design @ beta
                spread = float(np.std(residual))
                divisor = float(hyperparameters["logistic_link_scale_divisor"])
                link_scale = max(spread / divisor, 1e-6)
                holdout_design, _ = build_design(
                    holdout,
                    scope=scope,
                    transforms=transforms,
                    levels=levels,
                    indicators=indicators,
                )
                predicted_margin = holdout_design @ beta
                probabilities = 1.0 / (
                    1.0 + np.exp(-np.clip(predicted_margin / link_scale, -30.0, 30.0))
                )
            else:
                raise ValueError(f"unknown candidate family: {family}")

            for position, row in enumerate(holdout):
                key = (row["canonical_game_id"], row["canonical_team_id"])
                probability_index[candidate_id][key] = float(probabilities[position])
                if predicted_margin is not None:
                    margins.setdefault(candidate_id, {})[key] = float(predicted_margin[position])
                predictions.append(
                    {
                        "candidate_id": candidate_id,
                        "fold_id": fold["fold_id"],
                        "canonical_game_id": row["canonical_game_id"],
                        "canonical_team_id": row["canonical_team_id"],
                        "chronological_ordinal": row["chronological_ordinal"],
                        "predicted_win_probability": _round(float(probabilities[position])),
                        "predicted_margin": _round(float(predicted_margin[position]))
                        if predicted_margin is not None
                        else None,
                        "observed_win": bool(label_index[key]["label_win"]),
                        "observed_margin": int(label_index[key]["label_margin"]),
                    }
                )

    expected_rows = int(contract["evaluation"]["expected_evaluation_rows"])
    for candidate_id, values in probability_index.items():
        if len(values) != expected_rows:
            raise ValueError(
                f"candidate {candidate_id} produced {len(values)} predictions, expected {expected_rows}"
            )
        for key in values:
            if row_index[key]["partition"] != "EVALUATION":
                raise ValueError(f"candidate {candidate_id} scored a training row")

    predictions.sort(
        key=lambda row: (row["candidate_id"], row["chronological_ordinal"], row["canonical_game_id"], row["canonical_team_id"])
    )
    return predictions, probability_index, margins


def summarize_candidates(
    *,
    contract: Mapping[str, Any],
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    probability_index: Mapping[str, Mapping[tuple[str, str], float]],
    margins: Mapping[str, Mapping[tuple[str, str], float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evaluation = contract["evaluation"]
    clip = evaluation["probability_clip"]
    bin_count = int(evaluation["calibration_bin_count"])
    tie_value = float(evaluation["tie_target_value"])
    minimum_rows = int(evaluation["minimum_slice_rows_for_reported_metric"])

    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    holdout = [row for row in matrix if row["partition"] == "EVALUATION"]
    holdout.sort(key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"], row["canonical_team_id"]))
    keys = [(row["canonical_game_id"], row["canonical_team_id"]) for row in holdout]
    outcomes = np.array([_target(label_index[key], tie_value) for key in keys], dtype=np.float64)
    observed_margin = np.array(
        [float(label_index[key]["label_margin"]) for key in keys], dtype=np.float64
    )
    games = [key[0] for key in keys]

    dimensions = {
        "national": lambda row: "ALL",
        "conference": lambda row: row["team_conference"] or "UNRESOLVED",
        "site": lambda row: row["site"],
        "ranking_state": lambda row: row["ranking_state"],
        "favorite_state": lambda row: row["favorite_state"],
        "data_coverage": lambda row: row["data_coverage_class"],
    }

    summaries: list[dict[str, Any]] = []
    calibration: list[dict[str, Any]] = []
    slices: list[dict[str, Any]] = []

    reference_id = contract["residual_test"]["reference_candidate"]
    reference_brier: float | None = None

    for candidate in contract["candidates"]:
        candidate_id = candidate["candidate_id"]
        probabilities = np.array(
            [probability_index[candidate_id][key] for key in keys], dtype=np.float64
        )
        scored = score_predictions(
            probabilities, outcomes, clip=clip, bin_count=bin_count
        )
        bins = scored.pop("calibration_bins")
        for entry in bins:
            calibration.append({"candidate_id": candidate_id, **entry})

        clipped = np.clip(probabilities, float(clip[0]), float(clip[1]))
        squared = (clipped - outcomes) ** 2
        interval = bootstrap_interval(
            squared,
            games,
            resamples=int(evaluation["bootstrap_resamples"]),
            seed=int(evaluation["bootstrap_seed"]),
        )

        margin_metrics: dict[str, Any] = {"margin_mae": None, "margin_rmse": None}
        if candidate.get("emits_margin"):
            predicted = np.array(
                [margins[candidate_id][key] for key in keys], dtype=np.float64
            )
            margin_metrics = {
                "margin_mae": _round(float(np.mean(np.abs(predicted - observed_margin)))),
                "margin_rmse": _round(
                    float(np.sqrt(np.mean((predicted - observed_margin) ** 2)))
                ),
            }

        if candidate_id == reference_id:
            reference_brier = scored["brier"]

        summaries.append(
            {
                "candidate_id": candidate_id,
                "family": candidate["family"],
                "feature_scope": candidate["feature_scope"],
                "hyperparameters": candidate["hyperparameters"],
                "evaluated_folds": int(evaluation["expected_folds"]),
                "abstained_rows": 0,
                **scored,
                **margin_metrics,
                "brier_bootstrap": interval,
                "promoted": False,
                "authority": "DEVELOPMENT_ONLY_UNPROTECTED_CANDIDATE",
            }
        )

        for dimension, key_of in dimensions.items():
            buckets: defaultdict[str, list[int]] = defaultdict(list)
            for position, row in enumerate(holdout):
                buckets[str(key_of(row))].append(position)
            for name in sorted(buckets):
                positions = buckets[name]
                reported = len(positions) >= minimum_rows
                slices.append(
                    {
                        "candidate_id": candidate_id,
                        "dimension": dimension,
                        "slice": name,
                        "rows": len(positions),
                        "observed_rate": _round(float(np.mean(outcomes[positions]))),
                        "brier": _round(float(np.mean(squared[positions]))) if reported else None,
                        "accuracy": _round(
                            float(
                                np.mean(
                                    1.0
                                    - np.abs(
                                        np.where(
                                            clipped[positions] > 0.5,
                                            1.0,
                                            np.where(clipped[positions] < 0.5, 0.0, 0.5),
                                        )
                                        - outcomes[positions]
                                    )
                                )
                            )
                        )
                        if reported
                        else None,
                        "metric_suppressed_for_small_sample": not reported,
                    }
                )

    for summary in summaries:
        summary["brier_delta_vs_prior_only"] = (
            _round(summary["brier"] - reference_brier) if reference_brier is not None else None
        )

    summaries.sort(key=lambda row: row["candidate_id"])
    calibration.sort(key=lambda row: (row["candidate_id"], row["bin_index"]))
    slices.sort(key=lambda row: (row["candidate_id"], row["dimension"], row["slice"]))
    return summaries, calibration, slices


# ---------------------------------------------------------------------------
# peer cohort
# ---------------------------------------------------------------------------


def build_peer_cohort(
    *,
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive peers from a declared measurable profile, never from reputation."""
    rule = contract["peer_cohort_rule"]
    window = rule["reference_window_seasons"]
    low, high = int(window[0]), int(window[1])
    power = set(rule["power_conferences"])
    reference = rule["reference_team"]
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }

    profiles: dict[str, dict[str, float]] = {}
    for row in matrix:
        if row["partition"] != "TRAINING":
            continue
        season = int(row["season"])
        if season < low or season > high:
            continue
        team = row["canonical_team_id"]
        profile = profiles.setdefault(
            team,
            {
                "rows": 0.0,
                "wins": 0.0,
                "ranked_rows": 0.0,
                "schedule_sum": 0.0,
                "schedule_rows": 0.0,
                "power_rows": 0.0,
            },
        )
        label = label_index[(row["canonical_game_id"], team)]
        profile["rows"] += 1.0
        profile["wins"] += 0.5 if label["label_tie"] else (1.0 if label["label_win"] else 0.0)
        if row["ap_poll_rank"] is not None:
            profile["ranked_rows"] += 1.0
        if row["opponent_prior_win_rate"] is not None:
            profile["schedule_sum"] += float(row["opponent_prior_win_rate"])
            profile["schedule_rows"] += 1.0
        if row["team_conference"] in power:
            profile["power_rows"] += 1.0

    minimum = int(rule["minimum_reference_window_games"])
    eligible: dict[str, dict[str, float]] = {}
    for team, profile in profiles.items():
        if profile["rows"] < minimum:
            continue
        eligible[team] = {
            "long_run_win_expectation": profile["wins"] / profile["rows"],
            "historical_ranking_exposure": profile["ranked_rows"] / profile["rows"],
            "schedule_strength": (profile["schedule_sum"] / profile["schedule_rows"])
            if profile["schedule_rows"]
            else 0.0,
            "power_conference_share": profile["power_rows"] / profile["rows"],
            "reference_window_rows": profile["rows"],
        }

    if reference not in eligible:
        raise ValueError("the reference program does not satisfy its own eligibility rule")

    criteria = [item["criterion_id"] for item in rule["criteria"]]
    standardization: dict[str, dict[str, float]] = {}
    for criterion in criteria:
        values = np.array([eligible[team][criterion] for team in sorted(eligible)], dtype=np.float64)
        mean = float(np.mean(values))
        stdev = float(np.std(values))
        standardization[criterion] = {"mean": mean, "stdev": stdev if stdev > 0 else 1.0}

    def vector(team: str) -> np.ndarray:
        return np.array(
            [
                (eligible[team][criterion] - standardization[criterion]["mean"])
                / standardization[criterion]["stdev"]
                for criterion in criteria
            ],
            dtype=np.float64,
        )

    anchor = vector(reference)
    scored: list[tuple[float, str]] = []
    for team in sorted(eligible):
        if team == reference:
            continue
        scored.append((round(float(np.linalg.norm(vector(team) - anchor)), ROUND_DIGITS), team))
    scored.sort(key=lambda item: (item[0], item[1]))
    members = scored[: int(rule["cohort_size"])]

    return {
        "rule_id": rule["rule_id"],
        "reference_team": reference,
        "reference_window_seasons": [low, high],
        "criteria": criteria,
        "unavailable_criteria": rule["unavailable_criteria"],
        "eligible_programs": len(eligible),
        "minimum_reference_window_games": minimum,
        "cohort_size": len(members),
        "seeded_from_famous_programs": False,
        "reference_profile": {
            criterion: _round(eligible[reference][criterion]) for criterion in criteria
        },
        "standardization": {
            criterion: {
                "mean": _round(standardization[criterion]["mean"]),
                "stdev": _round(standardization[criterion]["stdev"]),
            }
            for criterion in criteria
        },
        "members": [
            {
                "canonical_team_id": team,
                "rank": position,
                "distance": distance,
                "reference_window_rows": int(eligible[team]["reference_window_rows"]),
                **{criterion: _round(eligible[team][criterion]) for criterion in criteria},
            }
            for position, (distance, team) in enumerate(members, start=1)
        ],
    }


# ---------------------------------------------------------------------------
# residual pipeline test
# ---------------------------------------------------------------------------


def build_residual_test(
    *,
    contract: Mapping[str, Any],
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    probability_index: Mapping[str, Mapping[tuple[str, str], float]],
    peer_cohort: Mapping[str, Any],
) -> dict[str, Any]:
    """A development-only residual read-out. It proves the pipeline runs, nothing more."""
    residual_contract = contract["residual_test"]
    evaluation = contract["evaluation"]
    reference = residual_contract["reference_candidate"]
    tie_value = float(evaluation["tie_target_value"])
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    peers = {member["canonical_team_id"] for member in peer_cohort["members"]}

    holdout = [row for row in matrix if row["partition"] == "EVALUATION"]
    holdout.sort(key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"], row["canonical_team_id"]))

    groups: dict[str, list[int]] = {"NATIONAL": [], "PEER_COHORT": [], "TEXAS_AM": []}
    residuals = np.zeros(len(holdout), dtype=np.float64)
    games: list[str] = []
    for position, row in enumerate(holdout):
        key = (row["canonical_game_id"], row["canonical_team_id"])
        residuals[position] = _target(label_index[key], tie_value) - probability_index[reference][key]
        games.append(row["canonical_game_id"])
        groups["NATIONAL"].append(position)
        if row["canonical_team_id"] in peers:
            groups["PEER_COHORT"].append(position)
        if row["canonical_team_id"] == TAMU_TEAM_ID:
            groups["TEXAS_AM"].append(position)

    summaries: list[dict[str, Any]] = []
    for name in residual_contract["comparison_groups"]:
        positions = groups[name]
        if not positions:
            summaries.append(
                {
                    "group": name,
                    "rows": 0,
                    "mean_residual": None,
                    "mean_absolute_residual": None,
                    "brier": None,
                    "residual_bootstrap": None,
                    "sample_is_too_small_for_inference": True,
                }
            )
            continue
        values = residuals[positions]
        summaries.append(
            {
                "group": name,
                "rows": len(positions),
                "mean_residual": _round(float(np.mean(values))),
                "mean_absolute_residual": _round(float(np.mean(np.abs(values)))),
                "brier": _round(float(np.mean(values**2))),
                "residual_bootstrap": bootstrap_interval(
                    values,
                    [games[position] for position in positions],
                    resamples=int(evaluation["bootstrap_resamples"]),
                    seed=int(evaluation["bootstrap_seed"]),
                ),
                "sample_is_too_small_for_inference": len(positions) < 30,
            }
        )

    return {
        "test_id": residual_contract["test_id"],
        "reference_candidate": reference,
        "residual_definition": residual_contract["residual_definition"],
        "groups": summaries,
        "baseline_refit_for_this_test": False,
        "interpretation": "PIPELINE_EXECUTION_EVIDENCE_ONLY",
        "claims": {
            "bas_or_aggie_excess": False,
            "tamu_lift_or_specialization_benefit": False,
            "statistical_persistence": False,
            "tamu_result_is_unusual": False,
        },
    }


# ---------------------------------------------------------------------------
# artifact assembly
# ---------------------------------------------------------------------------


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    contract_bytes = (repo_root / CONTRACT_RELATIVE).read_bytes()
    source = contract["source_contract"]

    matrix_gate_path = repo_root / source["matrix_gate_relative_path"]
    _require_file(matrix_gate_path, source["matrix_gate_sha256"])
    matrix_gate = _read_json(matrix_gate_path)
    if matrix_gate["dataset_identity"] != source["matrix_dataset_identity"]:
        raise ValueError("development matrix dataset identity drift")

    preserved = contract["preserved_predecessor_result"]
    ledger_path = repo_root / preserved["ledger_relative_path"]
    _require_file(ledger_path, preserved["ledger_sha256"])
    ledger = _read_json(ledger_path)
    if ledger["ledger_identity"] != preserved["ledger_identity"]:
        raise ValueError("preserved predecessor ledger identity drift")

    matrix = _load_payload_rows(
        data_root, matrix_gate, "national_development_matrix_features.jsonl"
    )
    labels = _load_payload_rows(
        data_root, matrix_gate, "national_development_matrix_labels.jsonl"
    )
    folds = _load_payload_rows(data_root, matrix_gate, "national_development_matrix_folds.jsonl")

    evaluation = contract["evaluation"]
    holdout = [row for row in matrix if row["partition"] == "EVALUATION"]
    if len(holdout) != int(evaluation["expected_evaluation_rows"]):
        raise ValueError(f"evaluation row drift: {len(holdout)}")
    if len({row["canonical_game_id"] for row in holdout}) != int(
        evaluation["expected_evaluation_games"]
    ):
        raise ValueError("evaluation game drift")
    if len(folds) != int(evaluation["expected_folds"]):
        raise ValueError(f"fold count drift: {len(folds)}")

    predictions, probability_index, margins = evaluate_candidates(
        matrix=matrix, labels=labels, folds=folds, contract=contract
    )
    summaries, calibration, slices = summarize_candidates(
        contract=contract,
        matrix=matrix,
        labels=labels,
        probability_index=probability_index,
        margins=margins,
    )
    peer_cohort = build_peer_cohort(matrix=matrix, labels=labels, contract=contract)
    residual_test = build_residual_test(
        contract=contract,
        matrix=matrix,
        labels=labels,
        probability_index=probability_index,
        peer_cohort=peer_cohort,
    )

    cohort = {
        "season": int(matrix_gate["chronology"]["development_evaluation_season"]),
        "team_rows": len(holdout),
        "unique_games": len({row["canonical_game_id"] for row in holdout}),
        "folds": len(folds),
        "observed_win_rate": _ratio(
            sum(
                1
                for row in labels
                if row["partition"] == "EVALUATION" and row["label_win"]
            ),
            len(holdout),
        ),
        "tamu_rows": sum(1 for row in holdout if row["canonical_team_id"] == TAMU_TEAM_ID),
        "protected_seasons_excluded": matrix_gate["chronology"]["excluded_protected_seasons"],
        "prospective_seasons_excluded": matrix_gate["chronology"]["excluded_prospective_seasons"],
    }

    record_hashes = {
        "predictions": stable_hash(predictions),
        "candidates": stable_hash(summaries),
        "calibration": stable_hash(calibration),
        "slices": stable_hash(slices),
        "peer_cohort": stable_hash(peer_cohort),
        "residual_test": stable_hash(residual_test),
    }
    module_path = Path(__file__).resolve()
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "builder_sha256": sha256_file(module_path),
            "matrix_dataset_identity": source["matrix_dataset_identity"],
            "record_hashes": record_hashes,
            "classification": CLASSIFICATION,
        }
    )
    return {
        "contract": contract,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identity": sha256_file(module_path),
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "cohort": cohort,
        "predictions": predictions,
        "candidates": summaries,
        "calibration": calibration,
        "slices": slices,
        "peer_cohort": peer_cohort,
        "residual_test": residual_test,
    }


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = expected["contract"]
    peer_cohort = dict(expected["peer_cohort"])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_EXPECTATION_BASELINES_AND_PEERS_GATE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": payloads,
        "cohort": expected["cohort"],
        "precommitment": contract["precommitment"],
        "candidates": expected["candidates"],
        "calibration": expected["calibration"],
        "slices": expected["slices"],
        "peer_cohort": peer_cohort,
        "residual_test": expected["residual_test"],
        "preserved_predecessor_result": contract["preserved_predecessor_result"],
        "leakage_checks": {
            "candidates_refit_inside_each_fold": True,
            "evaluation_rows_influenced_their_own_fit": False,
            "fold_transforms_reused_across_folds": False,
            "protected_season_row_scored": False,
            "prospective_season_row_scored": False,
            "peer_cohort_used_evaluation_season_rows": False,
            "peer_cohort_hardcoded_program_names": False,
            "residual_test_refit_the_baseline": False,
        },
        "source_identities": {
            "matrix_gate_sha256": contract["source_contract"]["matrix_gate_sha256"],
            "matrix_dataset_identity": contract["source_contract"]["matrix_dataset_identity"],
            "preserved_ledger_sha256": contract["preserved_predecessor_result"]["ledger_sha256"],
            "preserved_ledger_identity": contract["preserved_predecessor_result"][
                "ledger_identity"
            ],
        },
        "authority": contract["authority"],
        "scientific_nonclaims": {
            "champion_promoted": False,
            "production_model_declared": False,
            "protected_evaluation_opened": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
            "tamu_residual_persistence_claimed": False,
            "forecast_published": False,
            "gap_004_resolved": False,
            "gap_005_resolved": False,
            "gap_006_resolved": False,
            "gap_007_resolved": False,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = expected["dataset_identity"]
    canonical_root = (
        data_root / "canonical" / "national_expectation_baselines_and_peers" / "sha256" / identity
    )
    manifest_root = (
        data_root / "manifests" / "national_expectation_baselines_and_peers" / "sha256" / identity
    )

    written = [
        (
            "national_baseline_predictions.jsonl",
            "NATIONAL_BASELINE_FOLD_PREDICTIONS",
            expected["predictions"],
        ),
        (
            "national_baseline_candidate_metrics.jsonl",
            "NATIONAL_BASELINE_CANDIDATE_METRICS",
            expected["candidates"],
        ),
        (
            "national_baseline_calibration_bins.jsonl",
            "NATIONAL_BASELINE_CALIBRATION_BINS",
            expected["calibration"],
        ),
        ("national_baseline_slices.jsonl", "NATIONAL_BASELINE_SLICES", expected["slices"]),
        (
            "national_peer_cohort_members.jsonl",
            "NATIONAL_PEER_COHORT_MEMBERS",
            expected["peer_cohort"]["members"],
        ),
        (
            "national_tamu_residual_groups.jsonl",
            "DEVELOPMENT_ONLY_TAMU_RESIDUAL_GROUPS",
            expected["residual_test"]["groups"],
        ),
    ]
    payloads: list[dict[str, Any]] = []
    for name, role, rows in written:
        payload_bytes = _jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_EXPECTATION_BASELINES_AND_PEERS_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "classification": CLASSIFICATION,
        "cohort": expected["cohort"],
        "record_hashes": expected["record_hashes"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": expected["code_identity"],
            "contract_sha256": expected["contract_sha256"],
        },
    }
    manifest_path = manifest_root / "national_expectation_baselines_and_peers_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate_payloads = [
        {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")} for item in payloads
    ]
    gate = build_gate(expected=expected, manifest_entry=manifest_entry, payloads=gate_payloads)
    _write_bytes(repo_root / GATE_RELATIVE, canonical_json_bytes(gate) + b"\n")
    return {"gate": gate, "manifest": manifest, "expected": expected}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate if gate is not None else _read_json(repo_root / GATE_RELATIVE))
    if gate.get("result") != PASS_RESULT:
        raise ValueError(f"baseline gate is not passing: {gate.get('result')}")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("baseline gate opened the protected lane")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value is not False:
            raise ValueError(f"baseline gate asserted a forbidden claim: {key}")
    for key, value in gate.get("authority", {}).items():
        if key in {
            "national_baseline_development_evaluation",
            "peer_cohort_reference_use",
            "shadow_forecast_candidate_source",
        }:
            continue
        if value is not False:
            raise ValueError(f"baseline authority is open: {key}")

    checks = gate.get("leakage_checks", {})
    if checks.get("candidates_refit_inside_each_fold") is not True:
        raise ValueError("candidates were not refitted inside each fold")
    for key in (
        "evaluation_rows_influenced_their_own_fit",
        "fold_transforms_reused_across_folds",
        "protected_season_row_scored",
        "prospective_season_row_scored",
        "peer_cohort_used_evaluation_season_rows",
        "peer_cohort_hardcoded_program_names",
        "residual_test_refit_the_baseline",
    ):
        if checks.get(key) is not False:
            raise ValueError(f"forbidden baseline behaviour is enabled: {key}")

    precommitment = gate.get("precommitment", {})
    if precommitment.get("candidate_set_frozen_before_evaluation") is not True:
        raise ValueError("the gate does not record a frozen candidate set")
    for key in ("post_hoc_candidate_insertion", "post_hoc_feature_shopping", "champion_promotion"):
        if precommitment.get(key) is not False:
            raise ValueError(f"precommitment is violated in the gate: {key}")

    for candidate in gate.get("candidates", []):
        if candidate.get("promoted") is not False:
            raise ValueError(f"candidate {candidate['candidate_id']} was promoted")
        if candidate.get("authority") != "DEVELOPMENT_ONLY_UNPROTECTED_CANDIDATE":
            raise ValueError(f"candidate {candidate['candidate_id']} escaped development authority")

    residual = gate.get("residual_test", {})
    for key, value in residual.get("claims", {}).items():
        if value is not False:
            raise ValueError(f"the residual test asserted a forbidden claim: {key}")
    if residual.get("baseline_refit_for_this_test") is not False:
        raise ValueError("the residual test refitted the national baseline")

    peer_cohort = gate.get("peer_cohort", {})
    if peer_cohort.get("seeded_from_famous_programs") is not False:
        raise ValueError("the peer cohort was seeded from reputation")
    if not peer_cohort.get("members"):
        raise ValueError("the peer cohort is empty")
    if any(
        member["canonical_team_id"] == peer_cohort.get("reference_team")
        for member in peer_cohort["members"]
    ):
        raise ValueError("the reference program is inside its own peer cohort")

    if not require_rebuild:
        return {"result": "PASS", "mode": "SCHEMA_ONLY", "gate_identity": gate.get("gate_identity")}

    if expected is None:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    manifest_path = data_root / gate["manifest"]["relative_path"]
    manifest = dict(manifest if manifest is not None else _read_json(manifest_path))

    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("cohort", gate["cohort"], expected["cohort"], errors)
    _compare("candidates", gate["candidates"], expected["candidates"], errors)
    _compare("calibration", gate["calibration"], expected["calibration"], errors)
    _compare("slices", gate["slices"], expected["slices"], errors)
    _compare("peer_cohort", gate["peer_cohort"], expected["peer_cohort"], errors)
    _compare("residual_test", gate["residual_test"], expected["residual_test"], errors)
    _compare(
        "manifest.record_hashes", manifest.get("record_hashes"), expected["record_hashes"], errors
    )
    if manifest_authoritative_sha256(manifest) != gate["manifest"].get("authoritative_sha256"):
        errors.append("manifest authoritative content drift")

    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest.get("payloads", []) if item["name"] == payload["name"]), None
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    if compute_gate_identity(gate) != gate.get("gate_identity"):
        errors.append("gate identity does not match its own identity-bearing fields")
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        errors.append("cross-surface binding identity drift")

    if errors:
        raise ValueError("independent baseline validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
    }
