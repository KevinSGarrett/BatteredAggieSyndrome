"""Run a bounded opponent-adjusted offense/defense Elo challenger."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_preliminary_elo_challengers as scalar  # noqa: E402


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
DATASET_IDENTITY = "8beb354a3d80fa2435c05fecf588d2be9cf803f6ba72d08c23d895712453c2e2"
FIT_SEASONS = tuple(range(2010, 2023))
REPORT_SEASONS = (2023, 2024, 2025)
TAMU_TEAM_ID = scalar.TAMU_TEAM_ID
REFERENCE_FAMILY = "elo_rating_week_batched_reference"
BOUNDED_MARGIN_FAMILY = "elo_bounded_margin_2"
CALIBRATED_SCALAR_FAMILY = "elo_probability_logistic_calibrated"
CANDIDATE_FAMILY = "elo_offense_defense_score_components_selected"
SUPERSEDED_PRE_REVIEW_RUN_IDENTITIES = [
    "45e9818ff933dd1fbab6aaa970d12504a98119675894ad566e34b5464e532660",
    "13c569008cab2989b31ed2c2d0828880d9252ebb1437df5cd50e13300cb5316e",
    "ae5330e05bfec2675ead268507fc1ae937b0c00226f2a1325f6d1b6733ae192f",
]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clip(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def replay_components(
    rows: list[dict[str, Any]],
    *,
    update_rate: float,
    offseason_retention: float,
    initial_score_mean: float = 24.0,
    home_score_edge: float = 2.5,
    residual_cap: float = 28.0,
) -> list[dict[str, Any]]:
    if update_rate <= 0.0:
        raise ValueError("update_rate must be positive")
    if not 0.0 <= offseason_retention <= 1.0:
        raise ValueError("offseason_retention must be in [0, 1]")
    if residual_cap <= 0.0:
        raise ValueError("residual_cap must be positive")
    offense: dict[str, float] = {}
    defense: dict[str, float] = {}
    games: Counter[str] = Counter()
    groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(scalar.batch_key(row), []).append(row)
    predictions: list[dict[str, Any]] = []
    prior_season: int | None = None
    for key in sorted(groups):
        season = key[0]
        if prior_season is not None and season != prior_season:
            offense = {team: value * offseason_retention for team, value in offense.items()}
            defense = {team: value * offseason_retention for team, value in defense.items()}
        prior_season = season
        group = sorted(groups[key], key=lambda item: (item["start_utc"], item["target_game_id"]))
        offense_snapshot = dict(offense)
        defense_snapshot = dict(defense)
        games_snapshot = Counter(games)
        offense_delta: Counter[str] = Counter()
        defense_delta: Counter[str] = Counter()
        game_delta: Counter[str] = Counter()
        for row in group:
            home, away = str(row["home_team_id"]), str(row["away_team_id"])
            home_offense = offense_snapshot.get(home, 0.0)
            away_offense = offense_snapshot.get(away, 0.0)
            home_defense = defense_snapshot.get(home, 0.0)
            away_defense = defense_snapshot.get(away, 0.0)
            site = 0.0 if bool(row["neutral_site"]) else home_score_edge
            predicted_home = initial_score_mean + home_offense - away_defense + site / 2.0
            predicted_away = initial_score_mean + away_offense - home_defense - site / 2.0
            raw_margin = predicted_home - predicted_away
            home_residual = clip(float(row["home_points"]) - predicted_home, residual_cap)
            away_residual = clip(float(row["away_points"]) - predicted_away, residual_cap)
            half_rate = update_rate / 2.0
            offense_delta[home] += half_rate * home_residual
            defense_delta[away] -= half_rate * home_residual
            offense_delta[away] += half_rate * away_residual
            defense_delta[home] -= half_rate * away_residual
            game_delta[home] += 1
            game_delta[away] += 1
            predictions.append(
                {
                    **row,
                    "raw_predicted_home_points": predicted_home,
                    "raw_predicted_away_points": predicted_away,
                    "raw_predicted_margin": raw_margin,
                    "home_offense_component": home_offense,
                    "home_defense_component": home_defense,
                    "away_offense_component": away_offense,
                    "away_defense_component": away_defense,
                    "home_component_games": int(games_snapshot[home]),
                    "away_component_games": int(games_snapshot[away]),
                    "home_information_scarcity": 1.0 / math.sqrt(1.0 + games_snapshot[home]),
                    "away_information_scarcity": 1.0 / math.sqrt(1.0 + games_snapshot[away]),
                }
            )
        teams = set(offense_delta) | set(defense_delta) | set(game_delta)
        for team in teams:
            offense[team] = offense_snapshot.get(team, 0.0) + float(offense_delta[team])
            defense[team] = defense_snapshot.get(team, 0.0) + float(defense_delta[team])
            games[team] = games_snapshot[team] + game_delta[team]
    return predictions


def fit_logistic(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    intercept, slope = 0.0, 0.15
    iterations = 0
    for iterations in range(1, 101):
        g0 = g1 = i00 = i01 = i11 = 0.0
        for row in rows:
            x = float(row["raw_predicted_margin"])
            probability = scalar.sigmoid(intercept + slope * x)
            residual = float(row["home_win"]) - probability
            weight = probability * (1.0 - probability)
            g0 += residual
            g1 += residual * x
            i00 += weight
            i01 += weight * x
            i11 += weight * x * x
        determinant = i00 * i11 - i01 * i01
        if determinant <= 1e-12:
            raise ValueError("offense/defense logistic calibration is singular")
        step0 = (g0 * i11 - g1 * i01) / determinant
        step1 = (g1 * i00 - g0 * i01) / determinant
        intercept += step0
        slope += step1
        if max(abs(step0), abs(step1)) < 1e-12:
            break
    return {"intercept": intercept, "slope_per_margin_point": slope, "iterations": iterations, "fit_rows": len(rows)}


def fit_margin(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    xs = [float(row["raw_predicted_margin"]) for row in rows]
    ys = [float(row["margin"]) for row in rows]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator if denominator else 0.0
    return {"intercept": mean_y - slope * mean_x, "slope": slope, "fit_rows": len(rows)}


def calibrate_components(
    rows: list[dict[str, Any]], logistic: dict[str, float | int], margin: dict[str, float | int]
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "home_win_probability": scalar.sigmoid(
                float(logistic["intercept"]) + float(logistic["slope_per_margin_point"]) * float(row["raw_predicted_margin"])
            ),
            "predicted_margin": float(margin["intercept"]) + float(margin["slope"]) * float(row["raw_predicted_margin"]),
            "raw_rating_diff": float(row["raw_predicted_margin"]),
            "rating_diff": float(row["raw_predicted_margin"]),
        }
        for row in rows
    ]


def metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    errors = [float(row["predicted_margin"]) - float(row["margin"]) for row in rows]
    return {
        "rows": len(rows),
        "brier": scalar.brier(rows),
        "log_loss": scalar.log_loss(rows),
        "ece_10": scalar.ece(rows),
        "margin_mae": sum(abs(value) for value in errors) / len(errors),
        "margin_rmse": math.sqrt(sum(value * value for value in errors) / len(errors)),
    }


def component_slices(rows: list[dict[str, Any]], season: int) -> dict[str, list[dict[str, Any]]]:
    selected = [row for row in rows if int(row["season"]) == season]
    return {
        "ALL": selected,
        "NONNEUTRAL": [row for row in selected if not bool(row["neutral_site"])],
        "NEUTRAL": [row for row in selected if bool(row["neutral_site"])],
        "COLD_START": [row for row in selected if bool(row["cold_start"])],
        "HOME_FAVORITE": [
            row for row in selected if float(row.get("raw_predicted_margin", row["rating_diff"])) >= 0.0
        ],
        "HOME_UNDERDOG": [
            row for row in selected if float(row.get("raw_predicted_margin", row["rating_diff"])) < 0.0
        ],
        "TEXAS_AM_INVOLVED": [row for row in selected if TAMU_TEAM_ID in {row["home_team_id"], row["away_team_id"]}],
    }


def paired_bootstrap_diagnostic(
    candidate_rows: list[dict[str, Any]],
    comparator_rows: list[dict[str, Any]],
    *,
    metric: str,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    comparator = {row["target_game_id"]: row for row in comparator_rows}
    pairs = [(row, comparator[row["target_game_id"]]) for row in candidate_rows]
    if not pairs or len(pairs) != len(comparator):
        raise ValueError("paired bootstrap requires identical nonempty common support")

    def loss(row: dict[str, Any]) -> float:
        if metric == "brier":
            return (float(row["home_win_probability"]) - float(row["home_win"])) ** 2
        if metric == "log_loss":
            probability = min(max(float(row["home_win_probability"]), 1e-12), 1.0 - 1e-12)
            outcome = float(row["home_win"])
            return -(outcome * math.log(probability) + (1.0 - outcome) * math.log(1.0 - probability))
        if metric == "margin_absolute_error":
            return abs(float(row["predicted_margin"]) - float(row["margin"]))
        raise ValueError(f"unsupported bootstrap metric: {metric}")

    deltas = [loss(left) - loss(right) for left, right in pairs]
    rng = random.Random(seed)
    means = []
    for _ in range(replicates):
        means.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    means.sort()
    lower_index = int(0.025 * (replicates - 1))
    upper_index = int(0.975 * (replicates - 1))
    return {
        "rows": len(deltas),
        "replicates": replicates,
        "seed": seed,
        "mean_delta": sum(deltas) / len(deltas),
        "percentile_95_lower": means[lower_index],
        "percentile_95_upper": means[upper_index],
    }


def load_inputs(repo_root: Path, data_root: Path) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
    import polars as pl

    contract_path = repo_root / "configs/elo_offense_defense_challenger_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    dataset_path = data_root / "training/preliminary_event_chronology/sha256" / DATASET_IDENTITY / "training_matrix.parquet"
    rows = pl.read_parquet(dataset_path).sort(["season", "season_type", "week", "start_utc", "target_game_id"]).to_dicts()
    return contract, dataset_path, rows


def compute(repo_root: Path, data_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract, dataset_path, rows = load_inputs(repo_root, data_root)
    grid = contract["parameter_grid"]
    trials: list[dict[str, Any]] = []
    trial_predictions: dict[tuple[float, float], list[dict[str, Any]]] = {}
    trial_fits: dict[tuple[float, float], tuple[dict[str, Any], dict[str, Any]]] = {}
    for update_rate in grid["update_rate"]:
        for retention in grid["offseason_retention"]:
            predictions = replay_components(rows, update_rate=float(update_rate), offseason_retention=float(retention))
            fit_rows = [row for row in predictions if int(row["season"]) in FIT_SEASONS]
            logistic_fit, margin_fit = fit_logistic(fit_rows), fit_margin(fit_rows)
            calibrated = calibrate_components(predictions, logistic_fit, margin_fit)
            fit_calibrated = [row for row in calibrated if int(row["season"]) in FIT_SEASONS]
            result = metrics(fit_calibrated)
            trials.append(
                {
                    "update_rate": float(update_rate),
                    "offseason_retention": float(retention),
                    "fit_rows": len(fit_rows),
                    "fit_log_loss": result["log_loss"],
                    "fit_brier": result["brier"],
                    "fit_margin_rmse": result["margin_rmse"],
                }
            )
            key = float(update_rate), float(retention)
            trial_predictions[key] = calibrated
            trial_fits[key] = logistic_fit, margin_fit
    selected = min(
        trials,
        key=lambda row: (
            row["fit_log_loss"], row["fit_brier"], row["fit_margin_rmse"], row["update_rate"], -row["offseason_retention"]
        ),
    )
    selected_key = float(selected["update_rate"]), float(selected["offseason_retention"])
    candidate = trial_predictions[selected_key]
    logistic_fit, margin_fit = trial_fits[selected_key]

    reference_raw = scalar.replay(rows, offseason_retention=1.0, margin_cap=None)
    reference_fit = [row for row in reference_raw if int(row["season"]) in FIT_SEASONS]
    reference_margin_scale = scalar.fit_margin_scale(reference_fit)
    reference = [
        {**row, "predicted_margin": reference_margin_scale * float(row["rating_diff"])} for row in reference_raw
    ]
    bounded_raw = scalar.replay(rows, offseason_retention=1.0, margin_cap=2.0)
    bounded_fit = [row for row in bounded_raw if int(row["season"]) in FIT_SEASONS]
    bounded_margin_scale = scalar.fit_margin_scale(bounded_fit)
    bounded = [{**row, "predicted_margin": bounded_margin_scale * float(row["rating_diff"])} for row in bounded_raw]
    scalar_calibration_fit = scalar.fit_logistic_calibration(reference_fit)
    calibrated_scalar = [
        {
            **row,
            "predicted_margin": reference_margin_scale * float(row["rating_diff"]),
        }
        for row in scalar.apply_logistic_calibration(
            reference_raw,
            float(scalar_calibration_fit["intercept"]),
            float(scalar_calibration_fit["slope_per_400_rating_points"]),
        )
    ]
    families = {
        REFERENCE_FAMILY: reference,
        BOUNDED_MARGIN_FAMILY: bounded,
        CALIBRATED_SCALAR_FAMILY: calibrated_scalar,
        CANDIDATE_FAMILY: candidate,
    }
    result_metrics: dict[str, Any] = {}
    report_rows: list[dict[str, Any]] = []
    run_basis = {
        "schema_version": "1.0.0",
        "classification": CLASSIFICATION,
        "dataset_identity": DATASET_IDENTITY,
        "dataset_sha256": sha256_file(dataset_path),
        "contract_sha256": sha256_file(repo_root / "configs/elo_offense_defense_challenger_contract.json"),
        "code_sha256": sha256_file(repo_root / "tools/run_preliminary_elo_offense_defense.py"),
        "fit_seasons": list(FIT_SEASONS),
        "report_only_exposed_seasons": list(REPORT_SEASONS),
    }
    run_identity = hashlib.sha256(canonical_json(run_basis)).hexdigest()
    model_identities: dict[str, str] = {}
    for family, predictions in families.items():
        if family == REFERENCE_FAMILY:
            configuration = {"offseason_retention": 1.0, "margin_cap": None, "margin_scale": reference_margin_scale}
        elif family == BOUNDED_MARGIN_FAMILY:
            configuration = {"offseason_retention": 1.0, "margin_cap": 2.0, "margin_scale": bounded_margin_scale}
        elif family == CALIBRATED_SCALAR_FAMILY:
            configuration = {
                "offseason_retention": 1.0,
                "margin_cap": None,
                "margin_scale": reference_margin_scale,
                "calibration": scalar_calibration_fit,
            }
        else:
            configuration = {"selected": selected, "logistic_fit": logistic_fit, "margin_fit": margin_fit}
        model_identities[family] = hashlib.sha256(canonical_json({"run": run_basis, "family": family, **configuration})).hexdigest()
        result_metrics[family] = {"by_season_slice": {}}
        for season in REPORT_SEASONS:
            for slice_name, subset in component_slices(predictions, season).items():
                if subset:
                    result_metrics[family]["by_season_slice"][f"{season}_{slice_name}"] = metrics(subset)
        for row in predictions:
            if int(row["season"]) not in REPORT_SEASONS:
                continue
            report_rows.append(
                {
                    "classification": CLASSIFICATION,
                    "run_identity": run_identity,
                    "model_identity": model_identities[family],
                    "family": family,
                    "target_game_id": row["target_game_id"],
                    "season": row["season"],
                    "season_type": row["season_type"],
                    "week": row["week"],
                    "start_utc": row["start_utc"],
                    "cutoff_utc": row["cutoff_utc"],
                    "home_team_id": row["home_team_id"],
                    "away_team_id": row["away_team_id"],
                    "neutral_site": row["neutral_site"],
                    "cold_start": row["cold_start"],
                    "home_win": row["home_win"],
                    "margin": row["margin"],
                    "home_win_probability": row["home_win_probability"],
                    "predicted_margin": row["predicted_margin"],
                    "raw_predicted_margin": row.get("raw_predicted_margin", row["rating_diff"]),
                    "home_offense_component": row.get("home_offense_component"),
                    "home_defense_component": row.get("home_defense_component"),
                    "away_offense_component": row.get("away_offense_component"),
                    "away_defense_component": row.get("away_defense_component"),
                    "home_component_games": row.get("home_component_games"),
                    "away_component_games": row.get("away_component_games"),
                    "home_information_scarcity": row.get("home_information_scarcity"),
                    "away_information_scarcity": row.get("away_information_scarcity"),
                }
            )
    candidate_metrics = result_metrics[CANDIDATE_FAMILY]["by_season_slice"]
    effects_by_comparator: dict[str, Any] = {}
    for comparator in (REFERENCE_FAMILY, BOUNDED_MARGIN_FAMILY, CALIBRATED_SCALAR_FAMILY):
        comparator_metrics = result_metrics[comparator]["by_season_slice"]
        effects_by_comparator[comparator] = {}
        for slice_id, values in candidate_metrics.items():
            base = comparator_metrics[slice_id]
            effects_by_comparator[comparator][slice_id] = {
                f"{metric}_delta": values[metric] - base[metric]
                for metric in ("brier", "log_loss", "ece_10", "margin_mae", "margin_rmse")
            }
    negative_findings_by_comparator = {
        comparator: {
            metric: sorted(
                slice_id
                for slice_id, values in effects.items()
                if values[f"{metric}_delta"] > 0.0
            )
            for metric in ("brier", "log_loss", "ece_10", "margin_mae", "margin_rmse")
        }
        for comparator, effects in effects_by_comparator.items()
    }
    effects = effects_by_comparator[REFERENCE_FAMILY]
    unstable = {
        metric: [season for season in REPORT_SEASONS if effects[f"{season}_ALL"][f"{metric}_delta"] > 0]
        for metric in ("brier", "log_loss", "ece_10", "margin_mae", "margin_rmse")
    }
    probability_vs_calibrated_stable = all(
        effects_by_comparator[CALIBRATED_SCALAR_FAMILY][f"{season}_ALL"][f"{metric}_delta"] <= 0
        for season in REPORT_SEASONS
        for metric in ("brier", "log_loss")
    )
    margin_vs_bounded_stable = all(
        effects_by_comparator[BOUNDED_MARGIN_FAMILY][f"{season}_ALL"][f"{metric}_delta"] <= 0
        for season in REPORT_SEASONS
        for metric in ("margin_mae", "margin_rmse")
    )
    directional_core_stable = (
        all(not unstable[metric] for metric in ("brier", "log_loss", "margin_mae", "margin_rmse"))
        and probability_vs_calibrated_stable
        and margin_vs_bounded_stable
    )
    bootstrap: dict[str, Any] = {}
    for season in REPORT_SEASONS:
        season_candidate = [row for row in candidate if int(row["season"]) == season]
        season_calibrated = [row for row in calibrated_scalar if int(row["season"]) == season]
        season_bounded = [row for row in bounded if int(row["season"]) == season]
        bootstrap[str(season)] = {
            "brier_vs_calibrated_scalar": paired_bootstrap_diagnostic(
                season_candidate, season_calibrated, metric="brier", replicates=2000, seed=423 + season * 10
            ),
            "log_loss_vs_calibrated_scalar": paired_bootstrap_diagnostic(
                season_candidate, season_calibrated, metric="log_loss", replicates=2000, seed=424 + season * 10
            ),
            "margin_mae_vs_bounded_scalar": paired_bootstrap_diagnostic(
                season_candidate,
                season_bounded,
                metric="margin_absolute_error",
                replicates=2000,
                seed=425 + season * 10,
            ),
        }
    bootstrap_supported = all(
        result[metric]["percentile_95_upper"] < 0.0
        for result in bootstrap.values()
        for metric in ("brier_vs_calibrated_scalar", "log_loss_vs_calibrated_scalar", "margin_mae_vs_bounded_scalar")
    )
    if directional_core_stable and bootstrap_supported:
        disposition = "PROMISING_POST_RESULT_BOOTSTRAP_SUPPORTED_REQUIRES_UNTOUCHED_PROTECTED_REPLICATION"
    elif directional_core_stable:
        disposition = "PROMISING_DIRECTIONALLY_STABLE_UNCERTAINTY_NOT_UNIFORMLY_SUPPORTED"
    else:
        disposition = "REJECT_DIRECTIONALLY_UNSTABLE_OR_NEGATIVE"
    manifest_core = {
        **run_basis,
        "artifact_type": "PRELIMINARY_ELO_OFFENSE_DEFENSE_CHALLENGER",
        "run_identity": run_identity,
        "feature_identity": "OPPONENT_ADJUSTED_OFFENSE_DEFENSE_SCORE_COMPONENTS_V1",
        "target_identity": "HOME_WIN_AND_HOME_MARGIN_FROM_8BEB354A_V1",
        "split_identity": "FIT_2010_2022_REPORT_2023_2025_EXPOSURE_AWARE_OD_V1",
        "families": [REFERENCE_FAMILY, BOUNDED_MARGIN_FAMILY, CALIBRATED_SCALAR_FAMILY, CANDIDATE_FAMILY],
        "model_identities": model_identities,
        "selection_trials": trials,
        "selected_parameters": selected,
        "selected_logistic_fit": logistic_fit,
        "selected_margin_fit": margin_fit,
        "reference_margin_scale": reference_margin_scale,
        "bounded_margin_scale": bounded_margin_scale,
        "scalar_calibration_fit": scalar_calibration_fit,
        "metrics": result_metrics,
        "effects_by_comparator": effects_by_comparator,
        "negative_findings": unstable,
        "negative_findings_by_comparator": negative_findings_by_comparator,
        "probability_vs_calibrated_scalar_stable": probability_vs_calibrated_stable,
        "margin_vs_bounded_scalar_stable": margin_vs_bounded_stable,
        "post_result_bootstrap_diagnostic": bootstrap,
        "bootstrap_all_core_95_upper_below_zero": bootstrap_supported,
        "bootstrap_added_after_first_result_inspection": True,
        "disposition": disposition,
        "superseded_pre_review_run_identities": SUPERSEDED_PRE_REVIEW_RUN_IDENTITIES,
        "development_game_count": len([row for row in rows if int(row["season"]) in REPORT_SEASONS]),
        "prediction_rows": len(report_rows),
        "family_count": 4,
        "common_support": "IDENTICAL_TARGET_GAME_IDS_WITHIN_EACH_REPORT_SEASON",
        "parameter_selection_uses_report_seasons": False,
        "target_game_outcome_used_before_prediction": False,
        "eligibility": "DEVELOPMENT_UNPROTECTED_EXPOSED_CANDIDATE_ONLY",
        "promotion_authority": False,
        "protected_performance_claimed": False,
        "a_and_m_lift_claimed": False,
        "bas_or_aggie_excess_claimed": False,
    }
    return manifest_core, report_rows


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    manifest, rows = compute(repo_root, data_root)
    run_identity = manifest["run_identity"]
    prediction_path = data_root / "forecast_snapshots/preliminary_elo_offense_defense/sha256" / run_identity / "predictions.parquet"
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows, infer_schema_length=None).sort(
        ["family", "season", "season_type", "week", "start_utc", "target_game_id"]
    ).write_parquet(
        prediction_path, compression="zstd"
    )
    manifest = {**manifest, "prediction_path": str(prediction_path), "prediction_sha256": sha256_file(prediction_path)}
    manifest_path = data_root / "manifests/preliminary_elo_offense_defense/sha256" / run_identity / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")
    print(
        json.dumps(
            {
                "result": "PASS",
                "run_identity": run_identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "prediction_sha256": manifest["prediction_sha256"],
                "prediction_rows": manifest["prediction_rows"],
                "selected_parameters": manifest["selected_parameters"],
                "disposition": manifest["disposition"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
