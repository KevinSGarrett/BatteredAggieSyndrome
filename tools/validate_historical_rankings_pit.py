from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import polars as pl


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_helpers(repo_root: Path) -> Any:
    path = repo_root / "src/aggie_analytics/temporal/rankings_pit.py"
    spec = importlib.util.spec_from_file_location("rankings_pit_validation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rankings PIT helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate(repo_root: Path, data_root: Path, run_identity: str) -> dict[str, Any]:
    helpers = load_helpers(repo_root)
    manifest_path = (
        data_root
        / "manifests/historical_rankings_pit/sha256"
        / run_identity
        / "rankings_pit_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("run_identity", manifest.get("run_identity") == run_identity)
    check("classification", manifest.get("classification") == helpers.CLASSIFICATION)
    check("publication_timestamp_not_claimed", manifest["temporal_policy"].get("publication_timestamp_claimed") is False)
    check("protected_evaluation_closed", manifest["eligibility"].get("protected_evaluation") is False)
    check("production_promotion_closed", manifest["eligibility"].get("production_promotion") is False)
    check("nonclaims", not any(manifest["protected_nonclaims"].values()))

    roots = {
        "state": data_root / manifest["external_locations"]["state"] / "rankings_pit_state.parquet",
        "targets": data_root / manifest["external_locations"]["features"] / "target_game_cutoffs.parquet",
        "features": data_root / manifest["external_locations"]["features"] / "rankings_pit_features.parquet",
        "quarantine": data_root / manifest["external_locations"]["quarantine"] / "rankings_pit_quarantine.parquet",
    }
    frames: dict[str, pl.DataFrame] = {}
    for name, path in roots.items():
        info = manifest["payloads"][name]
        check(f"exists:{name}", path.is_file())
        if path.is_file():
            frames[name] = pl.read_parquet(path)
            check(f"hash:{name}", sha256_file(path) == info["sha256"])
            check(f"rows:{name}", frames[name].height == info["rows"])
            check(
                f"classification:{name}",
                frames[name].filter(pl.col("classification") != helpers.CLASSIFICATION).height == 0,
            )

    state = frames["state"]
    targets = frames["targets"]
    features = frames["features"]
    quarantine = frames["quarantine"]
    check("state_unique_observations", state["observation_id"].n_unique() == state.height)
    check(
        "state_unique_poll_team",
        state.select(["season", "poll_id", "canonical_team_id"]).unique().height == state.height,
    )
    check("state_seasons", state["season"].min() == 2010 and state["season"].max() == 2025)
    check("state_exact_eligibility", state["admission_disposition"].n_unique() == 1)
    check("state_date_only_unknown_exact_time", state["publication_time_state"].n_unique() == 1)
    check(
        "state_upper_bound_after_interval_start",
        state.filter(pl.col("publication_interval_end_exclusive_utc") <= pl.col("publication_interval_start_utc")).height == 0,
    )
    check("state_rank_range", state.filter(pl.col("rank").is_not_null() & (pl.col("rank") <= 0)).height == 0)
    check("targets_unique", targets["game_id"].n_unique() == targets.height)
    check("targets_seasons", targets["season"].min() == 2010 and targets["season"].max() == 2025)
    check("two_feature_rows_per_game", features.height == targets.height * 2)
    check("feature_unique_game_side", features.select(["target_game_id", "team_side"]).unique().height == features.height)
    check("feature_sides", set(features["team_side"].unique().to_list()) == {"HOME", "AWAY"})
    check(
        "no_future_poll",
        features.filter(
            pl.col("poll_first_eligible_at_utc").is_not_null()
            & (pl.col("poll_first_eligible_at_utc") > pl.col("cutoff_utc"))
        ).height
        == 0,
    )
    check(
        "no_rank_without_source_row",
        features.filter(pl.col("rank").is_not_null() & ~pl.col("team_listed_in_poll")).height == 0,
    )
    check(
        "missing_rank_explicit",
        features.filter(pl.col("rank").is_null() & pl.col("missingness_disposition").is_null()).height == 0,
    )
    check("quarantine_nonempty", quarantine.height > 0)
    quarantine_reasons = set(quarantine["quarantine_reason"].unique().to_list())
    check("quarantine_undated", "UNDATED_PRESEASON_OR_FINAL" in quarantine_reasons)
    check("quarantine_conflicts", "DATED_POLL_NOT_EXACT_HIGH_COVERAGE_UNIQUE" in quarantine_reasons)
    check("quarantine_identity", "TEAM_IDENTITY_NOT_EXACT_VERIFIED" in quarantine_reasons)

    lower, upper = helpers.conservative_date_interval("2023-09-10")
    mutation_controls = {
        "date_interval_not_exact_timestamp": lower == "2023-09-09T00:00:00Z" and upper == "2023-09-12T00:00:00Z",
        "preseason_rejected": helpers.poll_admission_reason({"cpa_poll_phase": "PRESEASON", "cpa_poll_date": None, "alignment_state": "EXACT_HIGH_COVERAGE_UNIQUE"}) == "UNDATED_PRESEASON_OR_FINAL",
        "conflicted_poll_rejected": helpers.poll_admission_reason({"cpa_poll_phase": "DATED_WEEKLY", "cpa_poll_date": "2023-09-10", "alignment_state": "HIGH_COVERAGE_UNIQUE_WITH_CONFLICTS"}) == "DATED_POLL_NOT_EXACT_HIGH_COVERAGE_UNIQUE",
        "name_only_team_rejected": helpers.team_row_admission_reason({"identity_resolution_state": "AMBIGUOUS", "candidate_canonical_team_id": "team_x"}) == "TEAM_IDENTITY_NOT_EXACT_VERIFIED",
        "future_poll_not_selected": helpers.RankingsIndex([
            {
                "season": 2023,
                "poll_id": 1,
                "poll_date": "2023-09-10",
                "first_eligible_at_utc": "2023-09-12T00:00:00Z",
                "canonical_team_id": "team_x",
            }
        ]).latest(2023, "2023-09-11T23:59:59Z") is None,
    }
    check("mutation_controls", all(mutation_controls.values()), mutation_controls)
    failures = [item for item in checks if item["result"] == "FAIL"]
    return {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_AP_RANKINGS_PIT_VALIDATION",
        "classification": helpers.CLASSIFICATION,
        "run_identity": run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "checks": checks,
        "mutation_controls": mutation_controls,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.repo_root.resolve(), args.data_root.resolve(), args.run_identity)
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(payload, encoding="utf-8")
    print(json.dumps({"result": result["result"], "checks_passed": result["checks_passed"], "checks_failed": result["checks_failed"], "report_sha256": sha256_file(args.report_path), "report_path": str(args.report_path)}, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
