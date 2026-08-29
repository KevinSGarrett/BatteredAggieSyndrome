"""Expanding chronological national development walk-forward for 2018 through 2023.

Each evaluation season is predicted by candidates refit on strictly preceding seasons only.
The candidate definitions and every fitting primitive are imported verbatim from the Cycle #20
baseline module, so this phase extends the chronology without redefining the models.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from aggie_analytics.modeling.national_expectation_baselines import (
    ALL_NUMERIC,
    FEATURE_SCOPES,
    ROUND_DIGITS,
    bootstrap_interval,
    build_design,
    conference_levels,
    elo_probability,
    elo_ratings,
    fit_logistic_l2,
    fit_ridge,
    predict_logistic,
    score_predictions,
)

SCHEMA_VERSION = "aggie.models.national_multi_year_walk_forward.v1"
CONTRACT_ID = "BAT-668-NATIONAL-MULTI-YEAR-WALK-FORWARD-V1"
CLASSIFICATION = "EXPANDING_CHRONOLOGICAL_NATIONAL_DEVELOPMENT_WALK_FORWARD_2018_THROUGH_2023"
LANE = "NATIONAL_DEVELOPMENT_EVALUATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-668"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-MULTI-YEAR-NATIONAL-WALK-FORWARD-001"
PRODUCER = "tools/build_national_multi_year_walk_forward.py"

CONTRACT_RELATIVE = "configs/national_multi_year_walk_forward_contract.json"
GATE_RELATIVE = "artifacts/experimentation/national_multi_year_walk_forward_gate.json"
EVIDENCE_RELATIVE = "artifacts/experimentation/national_multi_year_walk_forward_replay.json"
MATRIX_GATE_RELATIVE = "artifacts/pit/national_chronological_development_matrix_gate.json"
AUTHORITY_GATE_RELATIVE = "artifacts/data_lake/historical_known_at_authority_gate.json"
PAYLOAD_NAME = "national_multi_year_walk_forward_predictions.jsonl"

PASS_RESULT = "PASS_NATIONAL_MULTI_YEAR_WALK_FORWARD_DEVELOPMENT_ONLY_NO_CHAMPION"

PIT_ELIGIBLE_LABEL = "PIT_ELIGIBLE_DOMAINS_ONLY"
PROXY_LABEL = "DEVELOPMENT_CHRONOLOGY_PROXY_ONLY"

BLOCKED_FEATURE_PREFIXES = ("ap_poll", "coaches_poll", "opponent_ap_poll", "venue_", "rankings")
NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


class WalkForwardViolation(RuntimeError):
    """Raised when the walk-forward input or artifact is not admissible."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), ROUND_DIGITS)


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise WalkForwardViolation(f"the walk-forward contract is missing at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise WalkForwardViolation("the walk-forward contract identifier does not match")
    return contract


def load_candidates(repo_root: Path, contract: Mapping[str, Any]) -> tuple[list[dict], str]:
    """Load the Cycle #20 candidate list verbatim and hash it so preservation is provable."""

    source = contract["candidate_source"]
    path = Path(repo_root) / source["contract_relative_path"]
    if not path.exists():
        raise WalkForwardViolation("the Cycle #20 candidate contract is missing")
    predecessor = read_json(path)
    if predecessor.get("contract_id") != source["contract_id"]:
        raise WalkForwardViolation("the Cycle #20 candidate contract identifier does not match")
    candidates = list(predecessor["candidates"])
    observed = sorted(candidate["candidate_id"] for candidate in candidates)
    if observed != sorted(source["expected_candidate_ids"]):
        raise WalkForwardViolation(
            "the candidate set drifted from the frozen Cycle #20 list, so it was not preserved"
        )
    return candidates, sha256_of(candidates)


def candidate_features(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    """The exact feature columns a candidate's declared scope consumes."""

    scope = candidate["feature_scope"]
    if scope not in FEATURE_SCOPES:
        raise WalkForwardViolation(f"candidate {candidate['candidate_id']} declares scope {scope}")
    numeric, boolean, _ = FEATURE_SCOPES[scope]
    return tuple(numeric) + tuple(boolean)


def candidate_authority(candidate: Mapping[str, Any]) -> str:
    """Label a candidate by whether every feature it consumes has audited known-at authority."""

    for feature in candidate_features(candidate):
        if feature.startswith(BLOCKED_FEATURE_PREFIXES):
            return PROXY_LABEL
    return PIT_ELIGIBLE_LABEL


def fold_transforms(training: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reproduce the Cycle #20 fold-local standardization recipe exactly."""

    transforms: dict[str, Any] = {}
    for feature in ALL_NUMERIC:
        values = [float(row[feature]) for row in training if row.get(feature) is not None]
        if len(values) < 2:
            transforms[feature] = {"mean": None, "observed": len(values), "stdev": None}
            continue
        stdev = statistics.pstdev(values)
        transforms[feature] = {
            "mean": round(statistics.fmean(values), 9),
            "observed": len(values),
            "stdev": round(stdev, 9) if stdev > 0 else None,
        }
    return transforms


def indicator_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({key for row in rows for key in row if key.endswith("_missing")})


def build_season_folds(
    matrix: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """One expanding fold per evaluation season, training strictly on preceding seasons."""

    evaluation = contract["evaluation"]
    forbidden = set(evaluation["forbidden_seasons"])
    minimum = int(evaluation["minimum_training_rows"])
    folds: list[dict[str, Any]] = []
    for season in evaluation["evaluation_seasons"]:
        season = int(season)
        if season in forbidden:
            raise WalkForwardViolation(f"season {season} is forbidden and cannot be evaluated")
        training = [row for row in matrix if int(row["season"]) < season]
        holdout = [row for row in matrix if int(row["season"]) == season]
        if not holdout:
            raise WalkForwardViolation(f"evaluation season {season} has no rows")
        if len(training) < minimum:
            raise WalkForwardViolation(f"evaluation season {season} has too little training data")
        if any(int(row["season"]) >= season for row in training):
            raise WalkForwardViolation(f"fold {season} trained on its own season or later")
        folds.append(
            {
                "evaluation_rows": len(holdout),
                "evaluation_season": season,
                "fold_id": f"SEASON-{season}",
                "training_rows": len(training),
                "training_seasons": [
                    min(int(row["season"]) for row in training),
                    max(int(row["season"]) for row in training),
                ],
                "transform_scope": "FITTED_ON_THIS_FOLD_TRAINING_PARTITION_ONLY",
            }
        )
    return folds


def _target(label: Mapping[str, Any], tie_value: float) -> float:
    if label["label_tie"]:
        return float(tie_value)
    return 1.0 if label["label_win"] else 0.0


def _predict(
    candidate: Mapping[str, Any],
    training: Sequence[Mapping[str, Any]],
    holdout: Sequence[Mapping[str, Any]],
    *,
    label_index: Mapping[tuple[str, str], Mapping[str, Any]],
    transforms: Mapping[str, Any],
    levels: Sequence[str],
    indicators: Sequence[str],
    training_target: np.ndarray,
    training_margin: np.ndarray,
) -> np.ndarray:
    family = candidate["family"]
    scope = candidate["feature_scope"]
    hyperparameters = candidate["hyperparameters"]

    if family == "UNFITTED_REFERENCE":
        return np.full(len(holdout), float(np.mean(training_target)), dtype=np.float64)
    if family == "ELO":
        ratings = elo_ratings(training, label_index, hyperparameters=hyperparameters)
        return np.array(
            [elo_probability(row, ratings, hyperparameters=hyperparameters) for row in holdout],
            dtype=np.float64,
        )

    design, _ = build_design(
        training, scope=scope, transforms=transforms, levels=levels, indicators=indicators
    )
    holdout_design, _ = build_design(
        holdout, scope=scope, transforms=transforms, levels=levels, indicators=indicators
    )
    if family == "REGULARIZED_LOGISTIC":
        beta = fit_logistic_l2(
            design,
            training_target,
            l2_lambda=float(hyperparameters["l2_lambda"]),
            iterations=int(hyperparameters["newton_iterations"]),
            tolerance=float(hyperparameters["tolerance"]),
        )
        return predict_logistic(holdout_design, beta)
    if family == "RIDGE_MARGIN":
        beta = fit_ridge(design, training_margin, l2_lambda=float(hyperparameters["l2_lambda"]))
        spread = float(np.std(training_margin - design @ beta))
        divisor = float(hyperparameters["logistic_link_scale_divisor"])
        link_scale = max(spread / divisor, 1e-6)
        predicted = holdout_design @ beta
        return 1.0 / (1.0 + np.exp(-np.clip(predicted / link_scale, -30.0, 30.0)))
    raise WalkForwardViolation(f"unknown candidate family: {family}")


def run_walk_forward(
    *,
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Refit every preserved candidate per evaluation season and predict that season alone."""

    evaluation = contract["evaluation"]
    tie_value = float(evaluation["tie_target_value"])
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    indicators = indicator_names(matrix)
    folds = build_season_folds(matrix, contract)

    predictions: list[dict[str, Any]] = []
    for fold in folds:
        season = fold["evaluation_season"]
        training = [row for row in matrix if int(row["season"]) < season]
        holdout = [row for row in matrix if int(row["season"]) == season]
        transforms = fold_transforms(training)
        levels = conference_levels(training)
        training_target = np.array(
            [
                _target(label_index[(r["canonical_game_id"], r["canonical_team_id"])], tie_value)
                for r in training
            ],
            dtype=np.float64,
        )
        training_margin = np.array(
            [
                float(
                    label_index[(r["canonical_game_id"], r["canonical_team_id"])]["label_margin"]
                )
                for r in training
            ],
            dtype=np.float64,
        )

        for candidate in candidates:
            probabilities = _predict(
                candidate,
                training,
                holdout,
                label_index=label_index,
                transforms=transforms,
                levels=levels,
                indicators=indicators,
                training_target=training_target,
                training_margin=training_margin,
            )
            for position, row in enumerate(holdout):
                key = (row["canonical_game_id"], row["canonical_team_id"])
                predictions.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "canonical_game_id": row["canonical_game_id"],
                        "canonical_team_id": row["canonical_team_id"],
                        "evaluation_season": season,
                        "observed_win": bool(label_index[key]["label_win"]),
                        "predicted_win_probability": _round(float(probabilities[position])),
                        "target": _round(_target(label_index[key], tie_value)),
                    }
                )

    predictions.sort(
        key=lambda row: (
            row["candidate_id"],
            row["evaluation_season"],
            row["canonical_game_id"],
            row["canonical_team_id"],
        )
    )
    return predictions, folds


def summarize_candidates(
    predictions: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Report by-year and aggregate metrics for every candidate, negatives included."""

    evaluation = contract["evaluation"]
    clip = evaluation["probability_clip"]
    bins = int(evaluation["calibration_bin_count"])
    bootstrap = evaluation["bootstrap"]

    by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for row in predictions:
        by_candidate.setdefault(row["candidate_id"], []).append(row)

    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        rows = by_candidate.get(candidate_id, [])
        if not rows:
            raise WalkForwardViolation(f"candidate {candidate_id} produced no predictions")

        per_season = []
        for season in evaluation["evaluation_seasons"]:
            season_rows = [row for row in rows if row["evaluation_season"] == int(season)]
            if not season_rows:
                continue
            scored = score_predictions(
                np.array([r["predicted_win_probability"] for r in season_rows]),
                np.array([r["target"] for r in season_rows]),
                clip=clip,
                bin_count=bins,
            )
            per_season.append(
                {
                    "accuracy": scored["accuracy"],
                    "brier": scored["brier"],
                    "calibration_intercept": scored.get("calibration_intercept"),
                    "calibration_slope": scored.get("calibration_slope"),
                    "evaluation_season": int(season),
                    "log_loss": scored["log_loss"],
                    "mean_predicted": scored["mean_predicted"],
                    "observed_rate": scored["observed_rate"],
                    "rows": scored["rows"],
                }
            )

        probabilities = np.array([r["predicted_win_probability"] for r in rows])
        outcomes = np.array([r["target"] for r in rows])
        aggregate = score_predictions(probabilities, outcomes, clip=clip, bin_count=bins)
        low = max(float(clip[0]), 1e-15)
        high = min(float(clip[1]), 1.0 - 1e-15)
        squared = (np.clip(probabilities, low, high) - outcomes) ** 2
        summaries.append(
            {
                "abstained_rows": 0,
                "aggregate": {
                    "accuracy": aggregate["accuracy"],
                    "brier": aggregate["brier"],
                    "calibration_bins": aggregate["calibration_bins"],
                    "calibration_intercept": aggregate.get("calibration_intercept"),
                    "calibration_slope": aggregate.get("calibration_slope"),
                    "log_loss": aggregate["log_loss"],
                    "mean_predicted": aggregate["mean_predicted"],
                    "observed_rate": aggregate["observed_rate"],
                    "rows": aggregate["rows"],
                },
                "authority": candidate_authority(candidate),
                "brier_bootstrap": bootstrap_interval(
                    squared,
                    [r["canonical_game_id"] for r in rows],
                    resamples=int(bootstrap["resamples"]),
                    seed=int(bootstrap["seed"]),
                ),
                "candidate_id": candidate_id,
                "family": candidate["family"],
                "feature_scope": candidate["feature_scope"],
                "per_season": per_season,
                "seasons_evaluated": len(per_season),
            }
        )
    summaries.sort(key=lambda row: row["candidate_id"])
    return summaries


def stability_report(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Report whether the candidate ordering is stable across seasons, without selecting one."""

    seasons = sorted({row["evaluation_season"] for s in summaries for row in s["per_season"]})
    best_by_season: dict[str, str] = {}
    for season in seasons:
        ranked = sorted(
            (
                (entry["brier"], summary["candidate_id"])
                for summary in summaries
                for entry in summary["per_season"]
                if entry["evaluation_season"] == season
            )
        )
        best_by_season[str(season)] = ranked[0][1]
    counts = Counter(best_by_season.values())
    aggregate_ranked = sorted(
        (summary["aggregate"]["brier"], summary["candidate_id"]) for summary in summaries
    )
    return {
        "aggregate_brier_ranking": [candidate for _, candidate in aggregate_ranked],
        "distinct_seasonal_leaders": sorted(counts),
        "interpretation": (
            "The lowest-Brier candidate per season is reported to show whether the ordering is"
            " stable across years. This is a stability observation, not a selection: no candidate"
            " is promoted, tuned or declared a champion by this phase."
        ),
        "lowest_brier_candidate_by_season": best_by_season,
        "ordering_is_stable_across_every_season": len(counts) == 1,
        "seasons_evaluated": seasons,
    }


def pit_versus_proxy_separation(
    predictions: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Test whether the leading candidate actually beats the best point-in-time eligible one.

    The two leading candidates consume rankings and venue features, which have no known-at
    authority. If their advantage over the best authorized candidate is not separable, then no
    conclusion may rest on the unauthorized domains.
    """

    ranked = sorted((s["aggregate"]["brier"], s["candidate_id"]) for s in summaries)
    leader = ranked[0][1]
    eligible = sorted(
        (s["aggregate"]["brier"], s["candidate_id"])
        for s in summaries
        if s["authority"] == PIT_ELIGIBLE_LABEL and s["family"] != "UNFITTED_REFERENCE"
    )
    if not eligible:
        raise WalkForwardViolation("no point-in-time eligible candidate was evaluated")
    challenger = eligible[0][1]

    clip = contract["evaluation"]["probability_clip"]
    low = max(float(clip[0]), 1e-15)
    high = min(float(clip[1]), 1.0 - 1e-15)

    def losses(candidate_id: str) -> dict[tuple[str, str], float]:
        return {
            (row["canonical_game_id"], row["canonical_team_id"]): (
                min(max(row["predicted_win_probability"], low), high) - row["target"]
            )
            ** 2
            for row in predictions
            if row["candidate_id"] == candidate_id
        }

    leader_loss, challenger_loss = losses(leader), losses(challenger)
    keys = sorted(set(leader_loss) & set(challenger_loss))
    paired = np.array([leader_loss[key] - challenger_loss[key] for key in keys])
    bootstrap = contract["evaluation"]["bootstrap"]
    interval = bootstrap_interval(
        paired,
        [key[0] for key in keys],
        resamples=int(bootstrap["resamples"]),
        seed=int(bootstrap["seed"]),
    )
    separated = interval["percentile_97_5"] < 0.0

    return {
        "best_point_in_time_eligible_candidate": challenger,
        "interpretation": (
            "The leading candidate consumes rankings and venue features, which the BAT-666 audit"
            " found to have retrieval-time authority only. A negative interval excluding zero"
            " would mean the unauthorized domains buy a separable improvement."
            if separated
            else "The leading candidate's advantage over the best point-in-time eligible"
            " candidate is not separable from zero, so nothing in this walk-forward justifies"
            " relying on the domains that lack known-at authority."
        ),
        "leading_candidate": leader,
        "leading_candidate_authority": next(
            s["authority"] for s in summaries if s["candidate_id"] == leader
        ),
        "mean_paired_brier_difference": _round(float(np.mean(paired))),
        "paired_bootstrap": interval,
        "paired_rows": len(keys),
        "the_leader_is_separably_better": bool(separated),
    }


def build_gate(
    *,
    summaries: Sequence[Mapping[str, Any]],
    folds: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    candidate_sha256: str,
    predecessor_identities: Mapping[str, Any],
    producer: str = PRODUCER,
) -> dict[str, Any]:
    forbidden = set(contract["evaluation"]["forbidden_seasons"])
    seasons = {row["evaluation_season"] for row in predictions}
    if forbidden & seasons:
        raise WalkForwardViolation("a forbidden season was scored")

    proxy = [s["candidate_id"] for s in summaries if s["authority"] == PROXY_LABEL]
    bundle = {
        "artifact_type": "NATIONAL_MULTI_YEAR_WALK_FORWARD_GATE",
        "authority": {
            "champion_or_production_promotion": False,
            "hyperparameter_search_on_any_evaluation_season": False,
            "national_multi_year_development_evaluation": True,
            "protected_evaluation_admission": False,
            "protected_training_admission": False,
        },
        "bound_predecessor_identities": dict(sorted(predecessor_identities.items())),
        "candidate_metrics": list(summaries),
        "candidate_set_sha256": candidate_sha256,
        "candidates_requiring_a_chronology_proxy_label": sorted(proxy),
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "decision_unit": LOCAL_ISSUE_ID,
        "evaluation_seasons": sorted(seasons),
        "folds": list(folds),
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "leakage_checks": {
            "any_fold_trained_on_its_own_season": False,
            "calibration_fitted_outside_the_training_fold": False,
            "candidate_set_changed_after_reading_a_result": False,
            "forbidden_season_scored": False,
            "transforms_reused_across_folds": False,
        },
        "local_issue_id": LOCAL_ISSUE_ID,
        "parent_jira_key": PARENT_JIRA_KEY,
        "known_at_authority_separation": pit_versus_proxy_separation(
            predictions, summaries, contract
        ),
        "payload": {
            "name": PAYLOAD_NAME,
            "rows": len(predictions),
            "sha256": hashlib.sha256(
                b"".join(canonical_json_bytes(row) + b"\n" for row in predictions)
            ).hexdigest(),
        },
        "precommitment": contract["precommitment"],
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract["scientific_nonclaims"],
        "stability": stability_report(summaries),
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check the committed walk-forward for internal consistency and forbidden shortcuts."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    if gate is None:
        gate_path = repo_root / GATE_RELATIVE
        if not gate_path.exists():
            raise WalkForwardViolation("the walk-forward gate has not been materialized")
        gate = read_json(gate_path)

    if gate.get("schema_version") != SCHEMA_VERSION:
        raise WalkForwardViolation("the committed gate schema version does not match")
    if gate.get("contract_sha256") != sha256_of(contract):
        raise WalkForwardViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(gate) != gate.get("gate_identity"):
        raise WalkForwardViolation("the committed gate identity does not cover its content")

    _, expected_sha = load_candidates(repo_root, contract)
    if gate.get("candidate_set_sha256") != expected_sha:
        raise WalkForwardViolation(
            "the committed candidate set does not match the frozen Cycle #20 list"
        )

    observed = sorted(row["candidate_id"] for row in gate.get("candidate_metrics", []))
    if observed != sorted(contract["candidate_source"]["expected_candidate_ids"]):
        raise WalkForwardViolation("a candidate was dropped or added from the reported metrics")

    forbidden = set(contract["evaluation"]["forbidden_seasons"])
    if forbidden.intersection(gate.get("evaluation_seasons", [])):
        raise WalkForwardViolation("a forbidden season appears in the evaluation set")
    if sorted(gate.get("evaluation_seasons", [])) != sorted(
        int(season) for season in contract["evaluation"]["evaluation_seasons"]
    ):
        raise WalkForwardViolation("the evaluated seasons do not match the contract")

    for fold in gate.get("folds", []):
        if fold["training_seasons"][1] >= fold["evaluation_season"]:
            raise WalkForwardViolation(
                f"fold {fold['fold_id']} trained on its own evaluation season or later"
            )

    for summary in gate.get("candidate_metrics", []):
        if summary["authority"] not in contract["candidate_authority_labels"]:
            raise WalkForwardViolation("a candidate carries an undeclared authority label")
        if summary["seasons_evaluated"] != len(contract["evaluation"]["evaluation_seasons"]):
            raise WalkForwardViolation(
                f"candidate {summary['candidate_id']} was not evaluated on every season"
            )

    if gate.get("authority", {}).get("champion_or_production_promotion"):
        raise WalkForwardViolation("the walk-forward claims a champion promotion")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise WalkForwardViolation("the walk-forward does not retain the blocked protected lane")
    if any(gate.get("leakage_checks", {}).values()):
        raise WalkForwardViolation("a leakage check is reported as triggered")

    separation = gate.get("known_at_authority_separation", {})
    if separation.get("the_leader_is_separably_better") and separation.get(
        "leading_candidate_authority"
    ) == PROXY_LABEL:
        interval = separation["paired_bootstrap"]
        if interval["percentile_97_5"] >= 0.0:
            raise WalkForwardViolation(
                "the gate claims a separable advantage that its own interval does not support"
            )

    return {
        "aggregate_brier_ranking": gate["stability"]["aggregate_brier_ranking"],
        "known_at_authority_separation": {
            "best_point_in_time_eligible_candidate": separation.get(
                "best_point_in_time_eligible_candidate"
            ),
            "leading_candidate": separation.get("leading_candidate"),
            "the_leader_is_separably_better": separation.get("the_leader_is_separably_better"),
        },
        "candidates": [
            {
                "aggregate_brier": row["aggregate"]["brier"],
                "authority": row["authority"],
                "candidate_id": row["candidate_id"],
            }
            for row in gate["candidate_metrics"]
        ],
        "evaluation_seasons": gate["evaluation_seasons"],
        "gate_identity": gate["gate_identity"],
        "ordering_is_stable_across_every_season": gate["stability"][
            "ordering_is_stable_across_every_season"
        ],
        "result": gate["result"],
    }
