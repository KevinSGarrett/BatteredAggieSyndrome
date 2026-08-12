"""Run bounded uncertainty-aware Elo challengers on exposed development data."""

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
REFERENCE_FAMILY = "elo_bounded_margin_2_calibrated_homoskedastic"
SUPPORT_FAMILY = "elo_bounded_margin_2_support_conditioned_variance"
BOOTSTRAP_FAMILY = "elo_bounded_margin_2_bootstrap_trajectory"
MEMBERS = 64
BASE_SEED = 423000
Z_80 = 1.2815515655446004
TAMU_TEAM_ID = scalar.TAMU_TEAM_ID


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def poisson_one(seed: int, member: int, game_id: str) -> int:
    identity = hashlib.sha256(f"{seed}|{member}|{game_id}".encode()).digest()
    rng = random.Random(int.from_bytes(identity[:8], "big"))
    limit = math.exp(-1.0)
    product, count = 1.0, 0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def support_value(row: dict[str, Any]) -> float:
    return 1.0 / math.sqrt(1.0 + int(row["home_prior_games"])) + 1.0 / math.sqrt(
        1.0 + int(row["away_prior_games"])
    )


def replay_weighted(
    rows: list[dict[str, Any]], *, member: int, seed: int, margin_cap: float = 2.0
) -> list[dict[str, Any]]:
    ratings: dict[str, float] = {}
    predictions: list[dict[str, Any]] = []
    groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(scalar.batch_key(row), []).append(row)
    for key in sorted(groups):
        group = sorted(
            groups[key], key=lambda row: (row["start_utc"], row["target_game_id"])
        )
        snapshot = dict(ratings)
        deltas: Counter[str] = Counter()
        for row in group:
            home, away = str(row["home_team_id"]), str(row["away_team_id"])
            rating_diff = (
                snapshot.get(home, 1500.0)
                + (0.0 if bool(row["neutral_site"]) else 55.0)
                - snapshot.get(away, 1500.0)
            )
            probability = scalar.sigmoid(scalar.ELO_LOGIT_SLOPE * rating_diff)
            raw_multiplier = (
                1.0 + math.log1p(max(0.0, abs(float(row["margin"])) - 1.0)) / 4.0
            )
            multiplier = min(margin_cap, raw_multiplier)
            weight = poisson_one(seed, member, str(row["target_game_id"]))
            change = (
                weight
                * scalar.K_FACTOR
                * multiplier
                * (float(row["home_win"]) - probability)
            )
            deltas[home] += change
            deltas[away] -= change
            predictions.append(
                {**row, "rating_diff": rating_diff, "resample_weight": weight}
            )
        for team in {
            str(row[field])
            for row in group
            for field in ("home_team_id", "away_team_id")
        }:
            ratings[team] = snapshot.get(team, 1500.0) + float(deltas[team])
    return predictions


def fit_margin_scale(rows: list[dict[str, Any]]) -> float:
    denominator = sum(float(row["rating_diff"]) ** 2 for row in rows)
    if denominator <= 0.0:
        raise ValueError("margin scale has no rating variation")
    return (
        sum(float(row["rating_diff"]) * float(row["margin"]) for row in rows)
        / denominator
    )


def fit_support_variance(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    xs = [support_value(row) for row in rows]
    ys = [math.log(float(row["margin_residual"]) ** 2 + 1e-6) for row in rows]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = (
        sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
        if denominator
        else 0.0
    )
    intercept = mean_y - slope * mean_x
    raw = [math.exp(intercept + slope * x) for x in xs]
    squared = [float(row["margin_residual"]) ** 2 for row in rows]
    smearing_scale = sum(squared) / sum(raw)
    return {
        "fit_rows": len(rows),
        "intercept": intercept,
        "slope_per_support_unit": slope,
        "smearing_scale": smearing_scale,
        "minimum_fit_variance": min(value * smearing_scale for value in raw),
        "maximum_fit_variance": max(value * smearing_scale for value in raw),
    }


def normal_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    alpha = 0.2
    brier = scalar.brier(rows)
    log_loss = scalar.log_loss(rows)
    ece = scalar.ece(rows)
    errors = [float(row["predicted_margin"]) - float(row["margin"]) for row in rows]
    nll, covered, widths, scores = [], [], [], []
    for row in rows:
        variance = float(row["margin_variance"])
        if not math.isfinite(variance) or variance <= 0.0:
            raise ValueError("margin variance must be finite and positive")
        error = float(row["margin"]) - float(row["predicted_margin"])
        sigma = math.sqrt(variance)
        lower = float(row["predicted_margin"]) - Z_80 * sigma
        upper = float(row["predicted_margin"]) + Z_80 * sigma
        outcome = float(row["margin"])
        interval_score = upper - lower
        if outcome < lower:
            interval_score += 2.0 / alpha * (lower - outcome)
        elif outcome > upper:
            interval_score += 2.0 / alpha * (outcome - upper)
        nll.append(
            0.5 * (math.log(2.0 * math.pi * variance) + error * error / variance)
        )
        covered.append(lower <= outcome <= upper)
        widths.append(upper - lower)
        scores.append(interval_score)
    return {
        "rows": len(rows),
        "brier": brier,
        "log_loss": log_loss,
        "ece_10": ece,
        "margin_mae": sum(abs(error) for error in errors) / len(errors),
        "margin_rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "normal_margin_nll": sum(nll) / len(nll),
        "interval_80_coverage": sum(covered) / len(covered),
        "interval_80_coverage_absolute_error": abs(sum(covered) / len(covered) - 0.8),
        "interval_80_mean_width": sum(widths) / len(widths),
        "interval_80_score": sum(scores) / len(scores),
    }


def slices(rows: list[dict[str, Any]], season: int) -> dict[str, list[dict[str, Any]]]:
    selected = [row for row in rows if int(row["season"]) == season]
    return {
        "ALL": selected,
        "NEUTRAL": [row for row in selected if bool(row["neutral_site"])],
        "NONNEUTRAL": [row for row in selected if not bool(row["neutral_site"])],
        "COLD_START": [row for row in selected if bool(row["cold_start"])],
        "TEXAS_AM_INVOLVED": [
            row
            for row in selected
            if TAMU_TEAM_ID in {str(row["home_team_id"]), str(row["away_team_id"])}
        ],
    }


def load_inputs(
    repo_root: Path, data_root: Path
) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
    import polars as pl

    contract_path = repo_root / "configs/elo_uncertainty_challenger_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    dataset_path = (
        data_root
        / "training/preliminary_event_chronology/sha256"
        / DATASET_IDENTITY
        / "training_matrix.parquet"
    )
    rows = (
        pl.read_parquet(dataset_path)
        .sort(["season", "season_type", "week", "start_utc", "target_game_id"])
        .to_dicts()
    )
    return contract, dataset_path, rows


def compute(
    repo_root: Path, data_root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract, dataset_path, rows = load_inputs(repo_root, data_root)
    raw_reference = scalar.replay(rows, offseason_retention=1.0, margin_cap=2.0)
    fit_raw = [row for row in raw_reference if int(row["season"]) in FIT_SEASONS]
    probability_fit = scalar.fit_logistic_calibration(fit_raw)
    margin_scale = fit_margin_scale(fit_raw)
    calibrated_reference = scalar.apply_logistic_calibration(
        raw_reference,
        float(probability_fit["intercept"]),
        float(probability_fit["slope_per_400_rating_points"]),
    )
    calibrated_reference = [
        {
            **row,
            "predicted_margin": margin_scale * float(row["rating_diff"]),
            "margin_residual": float(row["margin"])
            - margin_scale * float(row["rating_diff"]),
        }
        for row in calibrated_reference
    ]
    fit_reference = [
        row for row in calibrated_reference if int(row["season"]) in FIT_SEASONS
    ]
    global_variance = sum(
        float(row["margin_residual"]) ** 2 for row in fit_reference
    ) / len(fit_reference)
    support_fit = fit_support_variance(fit_reference)
    reference = [
        {
            **row,
            "margin_variance": global_variance,
            "uncertainty_support": support_value(row),
        }
        for row in calibrated_reference
    ]
    support_candidate = [
        {
            **row,
            "margin_variance": math.exp(
                float(support_fit["intercept"])
                + float(support_fit["slope_per_support_unit"]) * support_value(row)
            )
            * float(support_fit["smearing_scale"]),
            "uncertainty_support": support_value(row),
        }
        for row in calibrated_reference
    ]

    member_predictions: list[dict[str, dict[str, Any]]] = []
    member_fits: list[dict[str, Any]] = []
    for member in range(MEMBERS):
        raw_member = replay_weighted(rows, member=member, seed=BASE_SEED)
        member_fit_rows = [
            row for row in raw_member if int(row["season"]) in FIT_SEASONS
        ]
        member_probability_fit = scalar.fit_logistic_calibration(member_fit_rows)
        member_margin_scale = fit_margin_scale(member_fit_rows)
        calibrated = scalar.apply_logistic_calibration(
            raw_member,
            float(member_probability_fit["intercept"]),
            float(member_probability_fit["slope_per_400_rating_points"]),
        )
        member_predictions.append(
            {
                str(row["target_game_id"]): {
                    "probability": float(row["home_win_probability"]),
                    "margin": member_margin_scale * float(row["rating_diff"]),
                }
                for row in calibrated
                if int(row["season"]) in REPORT_SEASONS
            }
        )
        member_fits.append(
            {
                "member": member,
                "seed": BASE_SEED,
                "fit_rows": len(member_fit_rows),
                "probability_calibration": member_probability_fit,
                "margin_scale": member_margin_scale,
            }
        )
    bootstrap_candidate: list[dict[str, Any]] = []
    for row in reference:
        if int(row["season"]) not in REPORT_SEASONS:
            continue
        values = [member[str(row["target_game_id"])] for member in member_predictions]
        probability = sum(value["probability"] for value in values) / MEMBERS
        margin = sum(value["margin"] for value in values) / MEMBERS
        epistemic_variance = sum(
            (value["margin"] - margin) ** 2 for value in values
        ) / (MEMBERS - 1)
        bootstrap_candidate.append(
            {
                **row,
                "home_win_probability": probability,
                "predicted_margin": margin,
                "margin_variance": global_variance + epistemic_variance,
                "epistemic_margin_variance": epistemic_variance,
            }
        )

    families = {
        REFERENCE_FAMILY: reference,
        SUPPORT_FAMILY: support_candidate,
        BOOTSTRAP_FAMILY: bootstrap_candidate,
    }
    metrics: dict[str, Any] = {}
    output_rows: list[dict[str, Any]] = []
    run_basis = {
        "schema_version": "1.0.0",
        "classification": CLASSIFICATION,
        "dataset_identity": DATASET_IDENTITY,
        "dataset_sha256": sha256_file(dataset_path),
        "contract_sha256": sha256_file(
            repo_root / "configs/elo_uncertainty_challenger_contract.json"
        ),
        "code_sha256": sha256_file(
            repo_root / "tools/run_preliminary_elo_uncertainty.py"
        ),
        "fit_seasons": list(FIT_SEASONS),
        "report_only_exposed_seasons": list(REPORT_SEASONS),
    }
    run_identity = hashlib.sha256(canonical_json(run_basis)).hexdigest()
    model_identities: dict[str, str] = {}
    for family, family_rows in families.items():
        configuration = {
            "family": family,
            "probability_fit": probability_fit,
            "margin_scale": margin_scale,
            "global_variance": global_variance,
            "support_fit": support_fit if family == SUPPORT_FAMILY else None,
            "members": member_fits if family == BOOTSTRAP_FAMILY else None,
        }
        model_identities[family] = hashlib.sha256(
            canonical_json({"run": run_basis, **configuration})
        ).hexdigest()
        metrics[family] = {"by_season_slice": {}}
        for season in REPORT_SEASONS:
            for slice_name, subset in slices(family_rows, season).items():
                if subset:
                    metrics[family]["by_season_slice"][f"{season}_{slice_name}"] = (
                        normal_metrics(subset)
                    )
        for row in family_rows:
            if int(row["season"]) not in REPORT_SEASONS:
                continue
            output_rows.append(
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
                    "home_prior_games": row["home_prior_games"],
                    "away_prior_games": row["away_prior_games"],
                    "home_win": row["home_win"],
                    "margin": row["margin"],
                    "home_win_probability": row["home_win_probability"],
                    "predicted_margin": row["predicted_margin"],
                    "margin_variance": row["margin_variance"],
                    "margin_standard_deviation": math.sqrt(
                        float(row["margin_variance"])
                    ),
                    "uncertainty_support": row["uncertainty_support"],
                    "epistemic_margin_variance": row.get("epistemic_margin_variance"),
                }
            )
    effects: dict[str, Any] = {}
    reference_metrics = metrics[REFERENCE_FAMILY]["by_season_slice"]
    for family in (SUPPORT_FAMILY, BOOTSTRAP_FAMILY):
        effects[family] = {}
        for slice_id, values in metrics[family]["by_season_slice"].items():
            effects[family][slice_id] = {
                f"{metric}_delta": values[metric] - reference_metrics[slice_id][metric]
                for metric in (
                    "brier",
                    "log_loss",
                    "ece_10",
                    "margin_mae",
                    "margin_rmse",
                    "normal_margin_nll",
                    "interval_80_coverage",
                    "interval_80_coverage_absolute_error",
                    "interval_80_mean_width",
                    "interval_80_score",
                )
            }
    support_stable = all(
        effects[SUPPORT_FAMILY][f"{season}_ALL"][f"{metric}_delta"] < 0.0
        for season in REPORT_SEASONS
        for metric in ("normal_margin_nll", "interval_80_score")
    )
    bootstrap_distribution_stable = all(
        effects[BOOTSTRAP_FAMILY][f"{season}_ALL"][f"{metric}_delta"] < 0.0
        for season in REPORT_SEASONS
        for metric in ("normal_margin_nll", "interval_80_score")
    )
    bootstrap_probability_stable = all(
        effects[BOOTSTRAP_FAMILY][f"{season}_ALL"][f"{metric}_delta"] <= 0.0
        for season in REPORT_SEASONS
        for metric in ("brier", "log_loss")
    )
    if support_stable or (
        bootstrap_distribution_stable and bootstrap_probability_stable
    ):
        disposition = "PROMISING_REQUIRES_UNTOUCHED_PROTECTED_REPLICATION"
    else:
        disposition = "REJECT_OR_RETAIN_DIAGNOSTIC_ONLY_UNSTABLE"
    negative_findings = {
        family: {
            metric: sorted(
                slice_id
                for slice_id, values in family_effects.items()
                if values[f"{metric}_delta"] > 0.0
            )
            for metric in (
                "brier",
                "log_loss",
                "ece_10",
                "margin_mae",
                "margin_rmse",
                "normal_margin_nll",
                "interval_80_coverage_absolute_error",
                "interval_80_score",
            )
        }
        for family, family_effects in effects.items()
    }
    bootstrap_epistemic = [
        float(row["epistemic_margin_variance"]) for row in bootstrap_candidate
    ]
    manifest = {
        **run_basis,
        "artifact_type": "PRELIMINARY_ELO_UNCERTAINTY_CHALLENGER",
        "run_identity": run_identity,
        "feature_identity": "ELO_SUPPORT_AND_BOOTSTRAP_UNCERTAINTY_V1",
        "target_identity": "HOME_WIN_AND_HOME_MARGIN_FROM_8BEB354A_V1",
        "split_identity": "FIT_2010_2022_REPORT_2023_2025_EXPOSURE_AWARE_UNCERTAINTY_V1",
        "families": [REFERENCE_FAMILY, SUPPORT_FAMILY, BOOTSTRAP_FAMILY],
        "model_identities": model_identities,
        "probability_fit": probability_fit,
        "margin_scale": margin_scale,
        "global_aleatoric_margin_variance": global_variance,
        "support_variance_fit": support_fit,
        "bootstrap_members": MEMBERS,
        "bootstrap_base_seed": BASE_SEED,
        "bootstrap_member_fits": member_fits,
        "metrics": metrics,
        "effects_vs_reference": effects,
        "negative_findings_by_candidate": negative_findings,
        "bootstrap_epistemic_variance_summary": {
            "minimum": min(bootstrap_epistemic),
            "mean": sum(bootstrap_epistemic) / len(bootstrap_epistemic),
            "maximum": max(bootstrap_epistemic),
            "zero_variance_rows": sum(value == 0.0 for value in bootstrap_epistemic),
        },
        "support_distribution_stable": support_stable,
        "bootstrap_distribution_stable": bootstrap_distribution_stable,
        "bootstrap_probability_stable": bootstrap_probability_stable,
        "disposition": disposition,
        "fit_rows": len(fit_reference),
        "development_game_count": len(
            [row for row in rows if int(row["season"]) in REPORT_SEASONS]
        ),
        "prediction_rows": len(output_rows),
        "parameter_selection_uses_report_seasons": False,
        "target_game_outcome_used_before_prediction": False,
        "uncertainty_surfaces_combined": False,
        "eligibility": "DEVELOPMENT_UNPROTECTED_EXPOSED_CANDIDATE_ONLY",
        "promotion_authority": False,
        "protected_performance_claimed": False,
        "a_and_m_lift_claimed": False,
        "bas_or_aggie_excess_claimed": False,
    }
    return manifest, output_rows


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    manifest, rows = compute(repo_root, data_root)
    run_identity = manifest["run_identity"]
    prediction_path = (
        data_root
        / "forecast_snapshots/preliminary_elo_uncertainty/sha256"
        / run_identity
        / "predictions.parquet"
    )
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows, infer_schema_length=None).sort(
        ["family", "season", "season_type", "week", "start_utc", "target_game_id"]
    ).write_parquet(prediction_path, compression="zstd")
    manifest = {
        **manifest,
        "prediction_path": str(prediction_path),
        "prediction_sha256": sha256_file(prediction_path),
    }
    manifest_path = (
        data_root
        / "manifests/preliminary_elo_uncertainty/sha256"
        / run_identity
        / "run_manifest.json"
    )
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
                "disposition": manifest["disposition"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
