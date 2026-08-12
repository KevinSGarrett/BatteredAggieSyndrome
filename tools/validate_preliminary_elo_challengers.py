from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import polars as pl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.validation.evaluation_exposure import canonical_json, sha256_file

    manifest_path = data_root / "manifests/preliminary_elo_challengers/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prediction_path = Path(manifest["prediction_path"])
    predictions = pl.read_parquet(prediction_path)
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("manifest_classification", manifest["classification"] == "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE")
    check("prediction_hash", sha256_file(prediction_path) == manifest["prediction_sha256"])
    check("prediction_rows", predictions.height == manifest["prediction_rows"] == 11052)
    check("unique_family_game", predictions.select("family", "target_game_id").unique().height == predictions.height)
    check("four_families", predictions["family"].n_unique() == 4)
    check("seasons", sorted(predictions["season"].unique().to_list()) == [2023, 2024, 2025])
    check("classification", predictions["classification"].unique().to_list() == ["PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"])
    check("probability_bounds", predictions.filter((pl.col("home_win_probability") < 0) | (pl.col("home_win_probability") > 1)).height == 0)
    check("finite_margin", predictions.filter(pl.col("predicted_margin").is_nan() | pl.col("predicted_margin").is_infinite()).height == 0)
    check("exposure_eligibility", manifest["eligibility"] == "DEVELOPMENT_UNPROTECTED_EXPOSED")
    check("no_promotion", manifest["promotion_authority"] is False and manifest["protected_performance_claimed"] is False)
    check("no_a_and_m_or_bas_claim", manifest["a_and_m_lift_claimed"] is False and manifest["bas_or_aggie_excess_claimed"] is False)
    check("negative_findings_preserved", manifest["negative_findings_preserved"] is True)
    check("reference_parameters", manifest["families"][0] == {"family": "elo_rating_week_batched_reference", "offseason_retention": 1.0, "margin_cap": None, "hypothesis": "UNCHANGED_REFERENCE"})
    for family in predictions["family"].unique().to_list():
        for season in (2023, 2024, 2025):
            frame = predictions.filter((pl.col("family") == family) & (pl.col("season") == season))
            actual = frame.select(((pl.col("home_win_probability") - pl.col("home_win")) ** 2).mean()).item()
            expected = manifest["metrics"][family]["by_season_slice"][f"{season}_ALL"]["brier"]
            check(f"brier_replay:{family}:{season}", abs(actual - expected) < 1e-12)
    mutation_controls = {
        "protected_claim_rejected": manifest["protected_performance_claimed"] is False,
        "promotion_rejected": manifest["promotion_authority"] is False,
        "identity_drift_rejected": manifest["run_identity"] == args.run_identity,
        "duplicate_prediction_rejected": predictions.select("family", "target_game_id").unique().height == predictions.height,
        "out_of_range_probability_rejected": predictions.filter((pl.col("home_win_probability") < 0) | (pl.col("home_win_probability") > 1)).height == 0,
    }
    check("mutation_controls", all(mutation_controls.values()), mutation_controls)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_ELO_CHALLENGER_VALIDATION",
        "classification": "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE",
        "run_identity": args.run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "prediction_sha256": sha256_file(prediction_path),
        "checks_passed": sum(row["result"] == "PASS" for row in checks),
        "checks_failed": len(failures),
        "checks": checks,
        "mutation_controls": mutation_controls,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_path": str(args.report_path.resolve()), "report_sha256": sha256_file(args.report_path)}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
