from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
DATASET_IDENTITY = "8beb354a3d80fa2435c05fecf588d2be9cf803f6ba72d08c23d895712453c2e2"
TAMU_TEAM_ID = "team_d0aff8aacd805801ab3d3d8293f3b298"
K_FACTOR = 40.0
HOME_ADVANTAGE = 55.0


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def batch_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return int(row["season"]), 0 if str(row["season_type"]).lower() == "regular" else 1, int(row["week"])


def replay(rows: list[dict[str, Any]], *, offseason_retention: float, margin_cap: float | None) -> list[dict[str, Any]]:
    ratings: dict[str, float] = {}
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
        snapshot = dict(ratings)
        deltas: Counter[str] = Counter()
        for row in sorted(groups[key], key=lambda item: (item["start_utc"], item["target_game_id"])):
            home_id, away_id = str(row["home_team_id"]), str(row["away_team_id"])
            home_rating = snapshot.get(home_id, 1500.0)
            away_rating = snapshot.get(away_id, 1500.0)
            site = 0.0 if bool(row["neutral_site"]) else HOME_ADVANTAGE
            rating_diff = home_rating + site - away_rating
            probability = 1.0 / (1.0 + 10.0 ** (-rating_diff / 400.0))
            actual = float(row["home_win"])
            multiplier = 1.0
            if margin_cap is not None:
                raw = 1.0 + math.log1p(max(0.0, abs(float(row["margin"])) - 1.0)) / 4.0
                multiplier = min(margin_cap, raw)
            change = K_FACTOR * multiplier * (actual - probability)
            deltas[home_id] += change
            deltas[away_id] -= change
            predictions.append({
                **row,
                "rating_diff": float(rating_diff),
                "home_win_probability": float(probability),
                "update_multiplier": float(multiplier),
            })
        for team_id, delta in deltas.items():
            ratings[team_id] = snapshot.get(team_id, 1500.0) + float(delta)
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
        selected = [row for row in rows if low <= float(row["home_win_probability"]) < high or (index == bins - 1 and float(row["home_win_probability"]) == 1.0)]
        if selected:
            observed = sum(float(row["home_win"]) for row in selected) / len(selected)
            predicted = sum(float(row["home_win_probability"]) for row in selected) / len(selected)
            result += len(selected) / len(rows) * abs(observed - predicted)
    return result


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
        "COLD_START": [row for row in selected if bool(row["cold_start"])],
        "TEXAS_AM_INVOLVED": [row for row in selected if TAMU_TEAM_ID in {row["home_team_id"], row["away_team_id"]}],
    }


def main() -> int:
    # Keep the pure chronological Elo replay importable in the core environment;
    # Parquet I/O remains an explicitly optional data-engineering dependency.
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    contract_path = repo_root / "configs/elo_challenger_research_contract.json"
    dataset_path = data_root / "training/preliminary_event_chronology/sha256" / DATASET_IDENTITY / "training_matrix.parquet"
    rows = pl.read_parquet(dataset_path).sort(["season", "season_type", "week", "start_utc", "target_game_id"]).to_dicts()
    families = [
        {"family": "elo_rating_week_batched_reference", "offseason_retention": 1.0, "margin_cap": None, "hypothesis": "UNCHANGED_REFERENCE"},
        {"family": "elo_offseason_regression_75", "offseason_retention": 0.75, "margin_cap": None, "hypothesis": "Unchanged offseason ratings overstate continuity."},
        {"family": "elo_bounded_margin_2", "offseason_retention": 1.0, "margin_cap": 2.0, "hypothesis": "Binary Elo updates discard bounded victory-margin evidence."},
        {"family": "elo_offseason_75_bounded_margin_2", "offseason_retention": 0.75, "margin_cap": 2.0, "hypothesis": "Offseason continuity and binary updates are jointly misspecified."},
    ]
    run_basis = {
        "schema_version": "1.0.0",
        "classification": CLASSIFICATION,
        "dataset_identity": DATASET_IDENTITY,
        "dataset_sha256": sha256_file(dataset_path),
        "contract_sha256": sha256_file(contract_path),
        "code_sha256": sha256_file(Path(__file__)),
        "families": families,
        "fit_seasons": list(range(2010, 2023)),
        "development_report_seasons": [2023, 2024, 2025],
    }
    run_identity = hashlib.sha256(canonical_json(run_basis)).hexdigest()
    all_predictions: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    model_identities: dict[str, str] = {}
    for config in families:
        family = str(config["family"])
        predictions = replay(rows, offseason_retention=float(config["offseason_retention"]), margin_cap=config["margin_cap"])
        fit_rows = [row for row in predictions if int(row["season"]) <= 2022]
        margin_scale = fit_margin_scale(fit_rows)
        model_identities[family] = hashlib.sha256(canonical_json({"run": run_basis, "family": config, "margin_scale": margin_scale})).hexdigest()
        metrics[family] = {"margin_scale_fit_2010_2022": margin_scale, "by_season_slice": {}}
        for season in (2023, 2024, 2025):
            for slice_name, subset in slices(predictions, season).items():
                if subset:
                    metrics[family]["by_season_slice"][f"{season}_{slice_name}"] = metric_row(subset, margin_scale)
        for row in predictions:
            if int(row["season"]) >= 2023:
                all_predictions.append({
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
                    "rating_diff": row["rating_diff"],
                    "predicted_margin": margin_scale * float(row["rating_diff"]),
                    "update_multiplier": row["update_multiplier"],
                })
    prediction_root = data_root / "forecast_snapshots/preliminary_elo_challengers/sha256" / run_identity
    prediction_root.mkdir(parents=True, exist_ok=True)
    prediction_path = prediction_root / "predictions.parquet"
    pl.DataFrame(all_predictions).sort(["family", "season", "season_type", "week", "start_utc", "target_game_id"]).write_parquet(prediction_path, compression="zstd")
    reference = metrics["elo_rating_week_batched_reference"]["by_season_slice"]
    effects: dict[str, Any] = {}
    for family, result in metrics.items():
        if family == "elo_rating_week_batched_reference":
            continue
        effects[family] = {}
        for slice_id, values in result["by_season_slice"].items():
            base = reference[slice_id]
            effects[family][slice_id] = {
                "brier_delta_vs_reference": values["brier"] - base["brier"],
                "log_loss_delta_vs_reference": values["log_loss"] - base["log_loss"],
                "margin_mae_delta_vs_reference": values["margin_mae"] - base["margin_mae"],
            }
    manifest = {
        **run_basis,
        "artifact_type": "PRELIMINARY_ELO_CHALLENGER_RESEARCH",
        "run_identity": run_identity,
        "feature_identity": "ELO_RATING_STATE_SITE_COLD_START_AND_BOUNDED_MARGIN_UPDATE_V1",
        "target_identity": "HOME_WIN_AND_HOME_MARGIN_FROM_8BEB354A_V1",
        "split_identity": "FIT_2010_2022_DEVELOPMENT_2023_2025_EXPOSURE_AWARE_V1",
        "model_identities": model_identities,
        "metrics": metrics,
        "effects_vs_unchanged_reference": effects,
        "prediction_path": str(prediction_path),
        "prediction_sha256": sha256_file(prediction_path),
        "prediction_rows": len(all_predictions),
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
    print(json.dumps({"result": "PASS", "run_identity": run_identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "prediction_rows": len(all_predictions)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
