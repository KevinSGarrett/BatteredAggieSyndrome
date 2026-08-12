from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.features.possession_pace import materialize  # noqa: E402
from aggie_analytics.temporal.play_drive_pit import canonical_json_bytes, parse_utc, sha256_file  # noqa: E402


def _check(checks: list[dict[str, object]], name: str, passed: bool, detail: object) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def _safe_remove_validation_rebuild(path: Path, validation_root: Path) -> None:
    resolved = path.resolve()
    allowed = validation_root.resolve()
    if allowed not in resolved.parents or "rebuild" not in resolved.name:
        raise ValueError(f"refusing to clean unverified rebuild path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")))
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--validated-at-utc", required=True)
    args = parser.parse_args()
    parse_utc(args.validated_at_utc)
    data_root = args.data_root.resolve()
    manifest_path = data_root / "manifests" / "preliminary_possession_pace" / "sha256" / args.dataset_identity / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    import polars as pl

    feature_path = data_root / "features" / "preliminary_possession_pace" / "sha256" / args.dataset_identity / "target_game_team_possession_pace_features.parquet"
    profile_path = data_root / "pit_state" / "preliminary_possession_pace" / "sha256" / args.dataset_identity / "team_possession_pace_profiles.parquet"
    features = pl.read_parquet(feature_path)
    profiles = pl.read_parquet(profile_path)
    checks: list[dict[str, object]] = []
    population = manifest["population"]
    _check(checks, "identity_matches_path", manifest["dataset_identity"] == args.dataset_identity, manifest["dataset_identity"])
    _check(checks, "classification_is_preliminary_unprotected", manifest["classification"] == "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE", manifest["classification"])
    _check(checks, "two_rows_per_target_game", features.height == population["target_games"] * 2, features.height)
    _check(checks, "unique_target_game_team_rows", features.select(pl.struct("game_id", "team_id").n_unique()).item() == features.height, features.height)
    _check(checks, "no_target_game_overlap", manifest["temporal_validation"]["target_game_overlap"] == 0, manifest["temporal_validation"])
    _check(checks, "known_at_precedes_target_cutoff", parse_utc(manifest["temporal_validation"]["maximum_source_known_at_utc"]) < parse_utc(manifest["temporal_validation"]["minimum_target_cutoff_utc"]), manifest["temporal_validation"])
    _check(checks, "all_rows_unprotected", features.filter(pl.col("protected_eligible") != False).is_empty(), features["protected_eligible"].unique().to_list())  # noqa: E712
    _check(checks, "all_targets_have_rule_era_mismatch", features.filter(pl.col("rule_era_transfer_mismatch") != True).is_empty(), features["rule_era_transfer_mismatch"].unique().to_list())  # noqa: E712
    forbidden = {"home_win", "home_points", "away_points", "margin", "winner", "outcome"}
    _check(checks, "target_and_outcome_fields_absent", not (forbidden & set(features.columns)), sorted(forbidden & set(features.columns)))
    unsupported = set(manifest["unsupported_fields"])
    _check(checks, "unsupported_metric_columns_absent", not (unsupported & set(features.columns)), sorted(unsupported & set(features.columns)))
    _check(checks, "negative_drive_spans_absent", profiles.filter(pl.col("regulation_drive_span_seconds_mean") < 0).is_empty(), 0)
    _check(checks, "source_order_anomaly_preserved", population["source_endpoint_reversed_rows"] > 0, population["source_endpoint_reversed_rows"])
    _check(checks, "ineligible_clock_rows_preserved", population["invalid_or_ineligible_clock_rows"] > 0, population["invalid_or_ineligible_clock_rows"])
    _check(checks, "cold_start_missingness_explicit", all(value == population["cold_start_rows"] for name, value in manifest["feature_missingness"].items() if name != "rule_era_transfer_mismatch"), manifest["feature_missingness"])
    _check(checks, "profile_population_matches", profiles.height == population["profile_teams"], profiles.height)
    _check(checks, "no_protected_or_promotion_authority", not any(manifest["authority"][name] for name in ["protected_training_admission", "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication_authority"]), manifest["authority"])
    _check(checks, "pinned_source_manifests_verified", len(manifest["verified_source_manifests"]) == 4, manifest["verified_source_manifests"])
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["path"]
        _check(checks, f"payload_exists:{payload['role']}", payload_path.is_file(), str(payload_path))
        _check(checks, f"payload_hash:{payload['role']}", payload_path.is_file() and sha256_file(payload_path) == payload["sha256"], payload["sha256"])

    validation_root = data_root / "validation" / "POST-SUBTASK-055"
    rebuild_root = validation_root / f"possession-pace-rebuild-{args.dataset_identity[:12]}"
    _safe_remove_validation_rebuild(rebuild_root, validation_root)
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=ROOT, issued_at_utc=manifest["issued_at_utc"])
    _check(checks, "independent_rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity, rebuilt["dataset_identity"])
    _check(checks, "independent_rebuild_manifest_byte_identical", sha256_file(Path(rebuilt["manifest_path"])) == sha256_file(manifest_path), sha256_file(Path(rebuilt["manifest_path"])))
    rebuilt_payloads = {item["role"]: item["sha256"] for item in rebuilt["manifest"]["payloads"]}
    original_payloads = {item["role"]: item["sha256"] for item in manifest["payloads"]}
    _check(checks, "independent_rebuild_payloads_byte_identical", rebuilt_payloads == original_payloads, rebuilt_payloads)
    _safe_remove_validation_rebuild(rebuild_root, validation_root)
    _check(checks, "reconstructible_rebuild_cleaned", not rebuild_root.exists(), str(rebuild_root))

    report = {
        "schema_version": "1.0.0",
        "validation_id": f"BAT405-POSSESSION-PACE-{args.dataset_identity[:16]}",
        "validated_at_utc": args.validated_at_utc,
        "dataset_identity": args.dataset_identity,
        "classification": manifest["classification"],
        "checks": checks,
        "summary": {"passed": sum(1 for item in checks if item["passed"]), "failed": sum(1 for item in checks if not item["passed"]), "total": len(checks)},
        "disposition": "PASS_PRELIMINARY_CANDIDATE_ONLY" if all(item["passed"] for item in checks) else "FAIL_QUARANTINE",
        "scientific_nonclaims": manifest["scientific_nonclaims"],
    }
    validation_root.mkdir(parents=True, exist_ok=True)
    report_path = validation_root / "possession_pace_candidate_validation.json"
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report_path": str(report_path), "report_sha256": sha256_file(report_path), "summary": report["summary"], "disposition": report["disposition"]}, indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
