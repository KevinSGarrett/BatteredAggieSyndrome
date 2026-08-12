from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
DATASET_IDENTITY = "8beb354a3d80fa2435c05fecf588d2be9cf803f6ba72d08c23d895712453c2e2"
TAMU_TEAM_ID = "team_d0aff8aacd805801ab3d3d8293f3b298"
K_FACTOR = 40.0
HOME_ADVANTAGE = 55.0
ELO_LOGIT_SLOPE = math.log(10.0) / 400.0
TIME_DECAY_HALF_LIFE_GRID_DAYS = (365.0, 730.0, 1460.0, 2920.0)
FIT_SEASONS = tuple(range(2010, 2023))
REPORT_SEASONS = (2023, 2024, 2025)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    direct = math.exp(value)
    return direct / (1.0 + direct)


def batch_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return int(row["season"]), 0 if str(row["season_type"]).lower() == "regular" else 1, int(row["week"])


def replay(
    rows: list[dict[str, Any]],
    *,
    offseason_retention: float,
    margin_cap: float | None,
    rating_half_life_days: float | None = None,
    home_advantage: float = HOME_ADVANTAGE,
) -> list[dict[str, Any]]:
    if not 0.0 <= offseason_retention <= 1.0:
        raise ValueError("offseason_retention must be in [0, 1]")
    if rating_half_life_days is not None and rating_half_life_days <= 0:
        raise ValueError("rating_half_life_days must be positive")
    ratings: dict[str, float] = {}
    last_played: dict[str, datetime] = {}
    predictions: list[dict[str, Any]] = []
    groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(batch_key(row), []).append(row)
    prior_season: int | None = None
    for key in sorted(groups):
        season = key[0]
        if prior_season is not None and season != prior_season:
            ratings = {team: 1500.0 + offseason_retention * (rating - 1500.0) for team, rating in ratings.items()}
        prior_season = season
        group_rows = sorted(groups[key], key=lambda item: (item["start_utc"], item["target_game_id"]))
        teams = {
            str(row[field])
            for row in group_rows
            for field in ("home_team_id", "away_team_id")
        }
        group_time = min(parse_utc(row["start_utc"]) for row in group_rows)
        snapshot = dict(ratings)
        if rating_half_life_days is not None:
            for team_id in teams:
                rating = ratings.get(team_id, 1500.0)
                prior_time = last_played.get(team_id)
                if prior_time is not None:
                    elapsed_days = max(0.0, (group_time - prior_time).total_seconds() / 86400.0)
                    retention = 0.5 ** (elapsed_days / rating_half_life_days)
                    rating = 1500.0 + retention * (rating - 1500.0)
                snapshot[team_id] = rating
        deltas: Counter[str] = Counter()
        for row in group_rows:
            home_id, away_id = str(row["home_team_id"]), str(row["away_team_id"])
            home_rating = snapshot.get(home_id, 1500.0)
            away_rating = snapshot.get(away_id, 1500.0)
            site = 0.0 if bool(row["neutral_site"]) else home_advantage
            rating_diff = home_rating + site - away_rating
            probability = sigmoid(ELO_LOGIT_SLOPE * rating_diff)
            actual = float(row["home_win"])
            multiplier = 1.0
            if margin_cap is not None:
                raw = 1.0 + math.log1p(max(0.0, abs(float(row["margin"])) - 1.0)) / 4.0
                multiplier = min(margin_cap, raw)
            change = K_FACTOR * multiplier * (actual - probability)
            deltas[home_id] += change
            deltas[away_id] -= change
            predictions.append(
                {
                    **row,
                    "raw_rating_diff": float(rating_diff),
                    "rating_diff": float(rating_diff),
                    "home_win_probability": float(probability),
                    "update_multiplier": float(multiplier),
                }
            )
        for team_id in teams:
            ratings[team_id] = snapshot.get(team_id, 1500.0) + float(deltas[team_id])
            latest = max(
                parse_utc(row["start_utc"])
                for row in group_rows
                if team_id in {str(row["home_team_id"]), str(row["away_team_id"])}
            )
            last_played[team_id] = latest
    return predictions


def brier(rows: list[dict[str, Any]]) -> float:
    return sum((float(row["home_win_probability"]) - float(row["home_win"])) ** 2 for row in rows) / len(rows)


def log_loss(rows: list[dict[str, Any]]) -> float:
    result = 0.0
    for row in rows:
        probability = min(max(float(row["home_win_probability"]), 1e-12), 1 - 1e-12)
        actual = float(row["home_win"])
        result -= actual * math.log(probability) + (1 - actual) * math.log(1 - probability)
    return result / len(rows)


def ece(rows: list[dict[str, Any]], bins: int = 10) -> float:
    result = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        selected = [
            row
            for row in rows
            if low <= float(row["home_win_probability"]) < high
            or (index == bins - 1 and float(row["home_win_probability"]) == 1.0)
        ]
        if selected:
            observed = sum(float(row["home_win"]) for row in selected) / len(selected)
            predicted = sum(float(row["home_win_probability"]) for row in selected) / len(selected)
            result += len(selected) / len(rows) * abs(observed - predicted)
    return result


def fit_site_adjustment(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [row for row in rows if not bool(row["neutral_site"])]
    gamma = 0.0
    iterations = 0
    for iterations in range(1, 101):
        gradient = 0.0
        information = 0.0
        for row in selected:
            probability = sigmoid(ELO_LOGIT_SLOPE * float(row["rating_diff"]) + gamma)
            gradient += float(row["home_win"]) - probability
            information += probability * (1.0 - probability)
        if information <= 1e-12:
            raise ValueError("site adjustment fit has insufficient information")
        step = gradient / information
        gamma += step
        if abs(step) < 1e-12:
            break
    delta_rating = gamma / ELO_LOGIT_SLOPE
    return {
        "fit_rows": len(selected),
        "iterations": iterations,
        "logit_adjustment": gamma,
        "rating_point_adjustment": delta_rating,
        "effective_non_neutral_home_advantage": HOME_ADVANTAGE + delta_rating,
    }


def apply_site_adjustment(rows: list[dict[str, Any]], rating_point_adjustment: float) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        adjusted = float(row["rating_diff"])
        if not bool(row["neutral_site"]):
            adjusted += rating_point_adjustment
        output.append(
            {
                **row,
                "raw_rating_diff": float(row["rating_diff"]),
                "rating_diff": adjusted,
                "home_win_probability": sigmoid(ELO_LOGIT_SLOPE * adjusted),
            }
        )
    return output


def fit_logistic_calibration(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    intercept = 0.0
    slope = math.log(10.0)
    iterations = 0
    for iterations in range(1, 101):
        gradient_0 = gradient_1 = 0.0
        info_00 = info_01 = info_11 = 0.0
        for row in rows:
            scaled_diff = float(row["rating_diff"]) / 400.0
            probability = sigmoid(intercept + slope * scaled_diff)
            residual = float(row["home_win"]) - probability
            weight = probability * (1.0 - probability)
            gradient_0 += residual
            gradient_1 += residual * scaled_diff
            info_00 += weight
            info_01 += weight * scaled_diff
            info_11 += weight * scaled_diff * scaled_diff
        determinant = info_00 * info_11 - info_01 * info_01
        if determinant <= 1e-12:
            raise ValueError("logistic calibration fit is singular")
        step_0 = (gradient_0 * info_11 - gradient_1 * info_01) / determinant
        step_1 = (gradient_1 * info_00 - gradient_0 * info_01) / determinant
        intercept += step_0
        slope += step_1
        if max(abs(step_0), abs(step_1)) < 1e-12:
            break
    return {
        "fit_rows": len(rows),
        "iterations": iterations,
        "intercept": intercept,
        "slope_per_400_rating_points": slope,
    }


def apply_logistic_calibration(rows: list[dict[str, Any]], intercept: float, slope: float) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "home_win_probability": sigmoid(intercept + slope * float(row["rating_diff"]) / 400.0),
        }
        for row in rows
    ]


def fit_margin_scale(rows: list[dict[str, Any]]) -> float:
    numerator = sum(float(row["rating_diff"]) * float(row["margin"]) for row in rows)
    denominator = sum(float(row["rating_diff"]) ** 2 for row in rows)
    return numerator / denominator if denominator else 0.0


def metric_row(rows: list[dict[str, Any]], margin_scale: float) -> dict[str, Any]:
    errors = [margin_scale * float(row["rating_diff"]) - float(row["margin"]) for row in rows]
    return {
        "rows": len(rows),
        "brier": brier(rows),
        "log_loss": log_loss(rows),
        "ece_10": ece(rows),
        "margin_mae": sum(abs(value) for value in errors) / len(errors),
        "margin_rmse": math.sqrt(sum(value * value for value in errors) / len(errors)),
    }


def slices(rows: list[dict[str, Any]], season: int) -> dict[str, list[dict[str, Any]]]:
    selected = [row for row in rows if int(row["season"]) == season]
    return {
        "ALL": selected,
        "NONNEUTRAL": [row for row in selected if not bool(row["neutral_site"])],
        "NEUTRAL": [row for row in selected if bool(row["neutral_site"])],
        "COLD_START": [row for row in selected if bool(row["cold_start"])],
        "HOME_FAVORITE": [row for row in selected if float(row["raw_rating_diff"]) >= 0.0],
        "HOME_UNDERDOG": [row for row in selected if float(row["raw_rating_diff"]) < 0.0],
        "TEXAS_AM_INVOLVED": [row for row in selected if TAMU_TEAM_ID in {row["home_team_id"], row["away_team_id"]}],
    }


def select_time_decay(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, float]]]:
    trials: list[dict[str, float]] = []
    for half_life in TIME_DECAY_HALF_LIFE_GRID_DAYS:
        predictions = replay(
            rows,
            offseason_retention=1.0,
            margin_cap=None,
            rating_half_life_days=half_life,
        )
        fit_rows = [row for row in predictions if int(row["season"]) in FIT_SEASONS]
        trials.append(
            {
                "half_life_days": half_life,
                "fit_rows": float(len(fit_rows)),
                "fit_brier": brier(fit_rows),
                "fit_log_loss": log_loss(fit_rows),
            }
        )
    selected = min(trials, key=lambda row: (row["fit_log_loss"], row["fit_brier"], -row["half_life_days"]))
    return float(selected["half_life_days"]), trials


def main() -> int:
    # Keep pure replay/calibration functions importable without optional data dependencies.
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    contract_path = repo_root / "configs/elo_challenger_research_contract.json"
    dataset_path = data_root / "training/preliminary_event_chronology/sha256" / DATASET_IDENTITY / "training_matrix.parquet"
    rows = pl.read_parquet(dataset_path).sort(["season", "season_type", "week", "start_utc", "target_game_id"]).to_dicts()

    selected_half_life, time_decay_trials = select_time_decay(rows)
    replay_configs = [
        {"family": "elo_rating_week_batched_reference", "offseason_retention": 1.0, "margin_cap": None, "rating_half_life_days": None, "hypothesis": "UNCHANGED_REFERENCE"},
        {"family": "elo_offseason_regression_75", "offseason_retention": 0.75, "margin_cap": None, "rating_half_life_days": None, "hypothesis": "Unchanged offseason ratings overstate continuity."},
        {"family": "elo_bounded_margin_2", "offseason_retention": 1.0, "margin_cap": 2.0, "rating_half_life_days": None, "hypothesis": "Binary Elo updates discard bounded victory-margin evidence."},
        {"family": "elo_offseason_75_bounded_margin_2", "offseason_retention": 0.75, "margin_cap": 2.0, "rating_half_life_days": None, "hypothesis": "Offseason continuity and binary updates are jointly misspecified."},
        {"family": "elo_inactivity_time_decay_selected", "offseason_retention": 1.0, "margin_cap": None, "rating_half_life_days": selected_half_life, "hypothesis": "Inactive-team rating information decays across changing regimes."},
    ]
    predictions_by_family: dict[str, list[dict[str, Any]]] = {}
    for config in replay_configs:
        predictions_by_family[str(config["family"])] = replay(
            rows,
            offseason_retention=float(config["offseason_retention"]),
            margin_cap=config["margin_cap"],
            rating_half_life_days=config["rating_half_life_days"],
        )

    reference_predictions = predictions_by_family["elo_rating_week_batched_reference"]
    reference_fit = [row for row in reference_predictions if int(row["season"]) in FIT_SEASONS]
    site_fit = fit_site_adjustment(reference_fit)
    calibration_fit = fit_logistic_calibration(reference_fit)
    predictions_by_family["elo_non_neutral_site_effect_fitted"] = apply_site_adjustment(
        reference_predictions,
        float(site_fit["rating_point_adjustment"]),
    )
    predictions_by_family["elo_probability_logistic_calibrated"] = apply_logistic_calibration(
        reference_predictions,
        float(calibration_fit["intercept"]),
        float(calibration_fit["slope_per_400_rating_points"]),
    )
    families = replay_configs + [
        {"family": "elo_non_neutral_site_effect_fitted", "base_family": "elo_rating_week_batched_reference", "fit": site_fit, "hypothesis": "A fixed 55-point home edge may misstate non-neutral development outcomes."},
        {"family": "elo_probability_logistic_calibrated", "base_family": "elo_rating_week_batched_reference", "fit": calibration_fit, "hypothesis": "Raw rating differences may be probability-miscalibrated."},
    ]
    run_basis = {
        "schema_version": "1.1.0",
        "classification": CLASSIFICATION,
        "dataset_identity": DATASET_IDENTITY,
        "dataset_sha256": sha256_file(dataset_path),
        "contract_sha256": sha256_file(contract_path),
        "code_sha256": sha256_file(Path(__file__)),
        "families": families,
        "time_decay_selection": {
            "fit_seasons": list(FIT_SEASONS),
            "selection_metric": "FIT_LOG_LOSS_THEN_BRIER_THEN_SIMPLER_LONGER_HALF_LIFE",
            "grid_days": list(TIME_DECAY_HALF_LIFE_GRID_DAYS),
            "trials": time_decay_trials,
            "selected_half_life_days": selected_half_life,
            "report_seasons_excluded_from_selection": list(REPORT_SEASONS),
        },
        "fit_seasons": list(FIT_SEASONS),
        "development_report_seasons": list(REPORT_SEASONS),
    }
    run_identity = hashlib.sha256(canonical_json(run_basis)).hexdigest()
    all_predictions: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    model_identities: dict[str, str] = {}
    config_by_family = {str(config["family"]): config for config in families}
    for family, predictions in predictions_by_family.items():
        fit_rows = [row for row in predictions if int(row["season"]) in FIT_SEASONS]
        margin_scale = fit_margin_scale(fit_rows)
        model_identities[family] = hashlib.sha256(
            canonical_json({"run": run_basis, "family": config_by_family[family], "margin_scale": margin_scale})
        ).hexdigest()
        metrics[family] = {
            "margin_scale_fit_2010_2022": margin_scale,
            "fit_2010_2022": metric_row(fit_rows, margin_scale),
            "by_season_slice": {},
        }
        for season in REPORT_SEASONS:
            for slice_name, subset in slices(predictions, season).items():
                if subset:
                    metrics[family]["by_season_slice"][f"{season}_{slice_name}"] = metric_row(subset, margin_scale)
        for row in predictions:
            if int(row["season"]) in REPORT_SEASONS:
                all_predictions.append(
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
                        "home_team_id": row["home_team_id"],
                        "away_team_id": row["away_team_id"],
                        "neutral_site": row["neutral_site"],
                        "cold_start": row["cold_start"],
                        "home_win": row["home_win"],
                        "margin": row["margin"],
                        "home_win_probability": row["home_win_probability"],
                        "raw_rating_diff": row["raw_rating_diff"],
                        "rating_diff": row["rating_diff"],
                        "predicted_margin": margin_scale * float(row["rating_diff"]),
                        "update_multiplier": row["update_multiplier"],
                    }
                )

    prediction_root = data_root / "forecast_snapshots/preliminary_elo_challengers/sha256" / run_identity
    prediction_root.mkdir(parents=True, exist_ok=True)
    prediction_path = prediction_root / "predictions.parquet"
    pl.DataFrame(all_predictions).sort(["family", "season", "season_type", "week", "start_utc", "target_game_id"]).write_parquet(
        prediction_path, compression="zstd"
    )
    reference = metrics["elo_rating_week_batched_reference"]["by_season_slice"]
    effects: dict[str, Any] = {}
    negative_findings: list[dict[str, Any]] = []
    for family, result in metrics.items():
        if family == "elo_rating_week_batched_reference":
            continue
        effects[family] = {}
        for slice_id, values in result["by_season_slice"].items():
            base = reference[slice_id]
            effects[family][slice_id] = {
                "brier_delta_vs_reference": values["brier"] - base["brier"],
                "log_loss_delta_vs_reference": values["log_loss"] - base["log_loss"],
                "ece_10_delta_vs_reference": values["ece_10"] - base["ece_10"],
                "margin_mae_delta_vs_reference": values["margin_mae"] - base["margin_mae"],
                "margin_rmse_delta_vs_reference": values["margin_rmse"] - base["margin_rmse"],
            }
        for metric in ("brier", "log_loss", "ece_10", "margin_mae", "margin_rmse"):
            worse = [
                season
                for season in REPORT_SEASONS
                if effects[family][f"{season}_ALL"][f"{metric}_delta_vs_reference"] > 0.0
            ]
            if worse:
                negative_findings.append({"family": family, "metric": metric, "worse_all_game_seasons": worse})

    report_games = len([row for row in reference_predictions if int(row["season"]) in REPORT_SEASONS])
    manifest = {
        **run_basis,
        "artifact_type": "PRELIMINARY_ELO_CHALLENGER_RESEARCH",
        "run_identity": run_identity,
        "feature_identity": "ELO_RATING_TIME_DECAY_SITE_CALIBRATION_AND_BOUNDED_MARGIN_V2",
        "target_identity": "HOME_WIN_AND_HOME_MARGIN_FROM_8BEB354A_V1",
        "split_identity": "FIT_2010_2022_REPORT_2023_2025_EXPOSURE_AWARE_V2",
        "model_identities": model_identities,
        "metrics": metrics,
        "effects_vs_unchanged_reference": effects,
        "negative_findings": negative_findings,
        "prediction_path": str(prediction_path),
        "prediction_sha256": sha256_file(prediction_path),
        "prediction_rows": len(all_predictions),
        "development_game_count": report_games,
        "family_count": len(families),
        "common_support": "IDENTICAL_TARGET_GAME_IDS_WITHIN_EACH_REPORT_SEASON",
        "parameter_selection_uses_report_seasons": False,
        "eligibility": "DEVELOPMENT_UNPROTECTED_EXPOSED",
        "negative_findings_preserved": True,
        "promotion_authority": False,
        "protected_performance_claimed": False,
        "a_and_m_lift_claimed": False,
        "bas_or_aggie_excess_claimed": False,
    }
    manifest_root = data_root / "manifests/preliminary_elo_challengers/sha256" / run_identity
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / "run_manifest.json"
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")
    print(
        json.dumps(
            {
                "result": "PASS",
                "run_identity": run_identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "prediction_rows": len(all_predictions),
                "family_count": len(families),
                "selected_time_decay_half_life_days": selected_half_life,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
