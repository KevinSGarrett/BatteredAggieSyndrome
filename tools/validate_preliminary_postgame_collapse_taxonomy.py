from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.features.postgame_collapse_taxonomy import materialize  # noqa: E402
from aggie_analytics.temporal.play_drive_pit import canonical_json_bytes, sha256_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--dataset-identity", required=True)
    args = parser.parse_args()

    import polars as pl

    manifest_path = args.data_root / "manifests" / "postgame_collapse_taxonomy" / "sha256" / args.dataset_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_root = args.data_root / "features" / "postgame_collapse_taxonomy" / "sha256" / args.dataset_identity
    games = pl.read_parquet(feature_root / "game_postgame_taxonomy.parquet")
    teams = pl.read_parquet(feature_root / "team_game_postgame_taxonomy.parquet")
    coverage = pl.read_parquet(feature_root / "season_domain_coverage.parquet")
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == "PRELIMINARY_UNPROTECTED_POSTGAME_DESCRIPTIVE_ONLY")
    check("capture_count", manifest["capture_count"] == 50, manifest["capture_count"])
    check("source_play_rows", manifest["population"]["source_play_rows"] == 487_982, manifest["population"]["source_play_rows"])
    check("all_play_games_reconciled_before_score_gate", manifest["population"]["joined_games_before_final_score_gate"] == 2_763)
    check("partial_scoreboard_failures_preserved", manifest["population"]["final_score_mismatch_games"] > 0, manifest["population"]["final_score_mismatch_games"])
    check("admitted_game_population", games.height == manifest["population"]["admitted_games"])
    check("team_rows_twice_games", teams.height == 2 * games.height)
    check("unique_game_rows", games["canonical_game_id"].n_unique() == games.height)
    check("two_team_rows_per_game", teams.group_by("canonical_game_id").len()["len"].min() == 2 and teams.group_by("canonical_game_id").len()["len"].max() == 2)
    check("team_identity_nonempty", teams["team_id"].null_count() == 0)
    check("reference_identity_exact", teams["reference_model_identity"].n_unique() == 1 and teams["reference_model_identity"][0] == "3aedd0dce933bf9c87550c46eae2eef525c766165db9ddb36188eeea473b9fd7")
    check("reference_margin_complete", teams["national_expected_margin"].null_count() == 0)
    check("residual_complete", teams["national_expected_margin_residual"].null_count() == 0)
    check("pregame_ineligible", not teams["pregame_feature_eligible"].any())
    check("original_pit_ineligible", not teams["historical_original_pit_eligible"].any())
    check("protected_ineligible", not teams["protected_eligible"].any())
    check("coverage_has_all_season_types", coverage.height == 6)
    check("partial_coverage_visible", coverage["admitted_outcome_coverage"].min() < 1.0)
    check("lead_surrender_requires_loss", teams.filter(pl.any_horizontal([pl.col(name) for name in ("lead_surrendered_7", "lead_surrendered_14", "lead_surrendered_21")]) & (pl.col("actual_margin") >= 0)).height == 0)
    check("fourth_quarter_surrender_requires_loss", teams.filter(pl.col("fourth_quarter_lead_surrendered") & (pl.col("actual_margin") >= 0)).height == 0)
    orientation = teams.group_by("canonical_game_id").agg(
        pl.col("actual_margin").sum().alias("actual_sum"),
        pl.col("national_expected_margin").sum().alias("expected_sum"),
        pl.col("national_expected_margin_residual").sum().alias("residual_sum"),
    )
    check("actual_margin_antisymmetry", orientation["actual_sum"].abs().max() == 0)
    check("expected_margin_antisymmetry", orientation["expected_sum"].abs().max() < 1e-10)
    check("residual_antisymmetry", orientation["residual_sum"].abs().max() < 1e-10)
    for payload in manifest["payloads"]:
        path = feature_root / payload["name"]
        check(f"payload_hash_{payload['name']}", sha256_file(path) == payload["sha256"])
        check(f"payload_bytes_{payload['name']}", path.stat().st_size == payload["bytes"])
    rebuilt = materialize(input_data_root=args.data_root, output_data_root=args.rebuild_root, repo_root=args.repo_root, issued_at_utc=manifest["issued_at_utc"])
    check("byte_identical_dataset_identity", rebuilt["dataset_identity"] == args.dataset_identity)
    check("byte_identical_manifest", rebuilt["manifest_sha256"] == sha256_file(manifest_path))
    rebuild_feature_root = args.rebuild_root / "features" / "postgame_collapse_taxonomy" / "sha256" / args.dataset_identity
    for payload in manifest["payloads"]:
        check(f"byte_identical_{payload['name']}", sha256_file(rebuild_feature_root / payload["name"]) == payload["sha256"])
    failed = [row for row in checks if not row["passed"]]
    report = {
        "schema_version": "1.0.0", "artifact_type": "POSTGAME_COLLAPSE_TAXONOMY_VALIDATION",
        "dataset_identity": args.dataset_identity, "manifest_sha256": sha256_file(manifest_path),
        "checks": checks, "check_count": len(checks), "failure_count": len(failed),
        "disposition": "PASS" if not failed else "FAIL", "failures": failed,
    }
    report_path = args.data_root / "validation" / "TASK-107" / "postgame_collapse_taxonomy_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report_path": str(report_path), "report_sha256": sha256_file(report_path), "check_count": len(checks), "failure_count": len(failed)}, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
