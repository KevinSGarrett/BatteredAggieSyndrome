from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.roster_membership_pit import (  # noqa: E402
    _disposition,
    _load_candidates,
    _minimum_target_cutoff,
    canonical_json_bytes,
    dataframe_record_sha256,
    materialize,
    parse_utc,
    sha256_file,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rebuild-root", type=Path, required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    repo_root = args.repo_root.resolve()
    rebuild_root = args.rebuild_root.resolve()
    identity = args.dataset_identity
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "historical_roster_membership_pit_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_roster_membership_pit_contract.json").read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity, identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-189")
    check("jira_key", manifest["jira_key"] == "BAT-546")
    check("classification", manifest["classification"] == contract["classification"])
    population = manifest["population"]
    acceptance = contract["acceptance"]
    for key, expected in {
        "source_files": acceptance["expected_source_files"],
        "source_rows": acceptance["expected_source_rows"],
        "admitted_rows": acceptance["expected_admitted_rows"],
        "nonadmitted_rows": acceptance["expected_nonadmitted_rows"],
        "distinct_players": acceptance["expected_distinct_players"],
        "distinct_teams": acceptance["expected_distinct_teams"],
        "multi_team_player_seasons": acceptance["expected_multi_team_player_seasons"],
        "duplicate_observation_ids": 0,
        "duplicate_natural_keys": 0,
    }.items():
        check(f"population_{key}", int(population[key]) == expected, population[key])
    check("per_season_population", population["admitted_by_season"] == acceptance["expected_admitted_by_season"])
    check("nonadmitted_dispositions", population["nonadmitted_dispositions"] == acceptance["expected_nonadmitted_dispositions"])
    check("admitted_missingness", manifest["field_missingness_in_admitted_state"] == acceptance["expected_admitted_missingness"])
    check("semantic_schema_hashes", manifest["semantic_source_schema_hashes"] == acceptance["expected_source_schema_hashes"])
    check("physical_null_type_drift", manifest["physical_schema_variants"] >= 2, manifest["physical_schema_variants"])
    chronology = manifest["chronology"]
    check("minimum_target_cutoff", chronology["minimum_target_cutoff_utc"] == acceptance["expected_minimum_target_cutoff_utc"])
    check("known_at_before_target_cutoff", parse_utc(chronology["source_known_at_utc"]) < parse_utc(chronology["minimum_target_cutoff_utc"]))
    check("no_backcast", chronology["backcast_before_source_known_at"] is False)
    authority = manifest["authority"]
    check("pit_state_admission", authority["pit_state_admission"] is True)
    check("season_membership_only", authority["season_membership_only"] is True)
    for key in ("backcast_before_source_known_at", "effective_day_inferred", "transfer_order_inferred", "depth_or_starter_inferred", "participation_or_usage_inferred", "availability_or_injury_inferred", "eligibility_inferred", "protected_training_admission", "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication"):
        check(f"authority_closed_{key}", authority[key] is False)
    for key, value in manifest["scientific_nonclaims"].items():
        check(f"scientific_nonclaim_{key}", value is False)
    payload_roots = {
        "DEVELOPMENT_ONLY_ROSTER_MEMBERSHIPS": data_root / "pit_state" / "historical_known_at" / "sha256" / identity,
        "NONADMITTED_ROSTER_EVIDENCE": data_root / "quarantine" / "historical_known_at" / "sha256" / identity,
    }
    original_payloads: dict[str, Path] = {}
    for item in manifest["payloads"]:
        path = payload_roots[item["role"]] / item["name"]
        check(f"payload_exists_{item['role']}", path.is_file())
        check(f"payload_bytes_{item['role']}", path.stat().st_size == item["bytes"], path.stat().st_size)
        check(f"payload_sha256_{item['role']}", sha256_file(path) == item["sha256"], item["sha256"])
        frame = pl.read_parquet(path)
        check(f"payload_rows_{item['role']}", frame.height == item["rows"], frame.height)
        check(f"payload_record_sha256_{item['role']}", dataframe_record_sha256(frame) == item["record_sha256"], item["record_sha256"])
        original_payloads[item["role"]] = path
    state = pl.read_parquet(original_payloads["DEVELOPMENT_ONLY_ROSTER_MEMBERSHIPS"])
    nonadmitted = pl.read_parquet(original_payloads["NONADMITTED_ROSTER_EVIDENCE"])
    forbidden = set(contract["forbidden_admitted_fields"]) & set(state.columns)
    check("forbidden_admitted_fields", not forbidden, sorted(forbidden))
    check("season_grain_only", state["membership_effective_grain"].unique().to_list() == ["SEASON"])
    check("no_effective_day_fabricated", state["membership_effective_day_utc"].null_count() == state.height)
    check("no_availability_inference", state["game_time_availability"].sum() == 0)
    check("no_depth_or_starter_inference", state["depth_or_starter_status"].sum() == 0)
    check("no_protected_eligibility", state["protected_eligible"].sum() == 0)
    check("nonadmitted_rows_preserved", nonadmitted.height == acceptance["expected_nonadmitted_rows"])
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"])
    check("byte_identical_dataset_identity", rebuilt["dataset_identity"] == identity, rebuilt["dataset_identity"])
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    rebuilt_paths = {
        "DEVELOPMENT_ONLY_ROSTER_MEMBERSHIPS": Path(rebuilt["state_path"]),
        "NONADMITTED_ROSTER_EVIDENCE": Path(rebuilt["quarantine_path"]),
    }
    for role, original in original_payloads.items():
        check(f"byte_identical_{role}", rebuilt_paths[role].read_bytes() == original.read_bytes(), sha256_file(original))
    candidates, _, _ = _load_candidates(data_root, contract)
    first_exact = candidates.filter(pl.col("reconciliation_disposition") == contract["admission"]["eligible_disposition"]).head(1)
    first_exact_observation = first_exact["observation_id"][0]
    mutation_controls = [
        expect_rejection("duplicate_exact_membership", lambda: _disposition(pl.concat([candidates, first_exact], how="diagonal_relaxed"), contract)),
        expect_rejection("nonverified_eligible_identity", lambda: _disposition(candidates.with_columns(pl.when(pl.col("observation_id") == first_exact_observation).then(pl.lit("UNVERIFIED")).otherwise(pl.col("canonical_membership_resolution_state")).alias("canonical_membership_resolution_state")), contract)),
        expect_rejection("historical_team_label_conflict", lambda: _disposition(candidates.with_columns(pl.when(pl.col("observation_id") == first_exact_observation).then(pl.lit("NOT THE HISTORICAL TEAM")).otherwise(pl.col("team")).alias("team")), contract)),
        expect_rejection("admission_count_drift", lambda: _disposition(candidates, {**contract, "acceptance": {**acceptance, "expected_admitted_rows": acceptance["expected_admitted_rows"] + 1}})),
        expect_rejection("target_payload_hash_drift", lambda: _minimum_target_cutoff(data_root, {**contract, "source_contract": {**contract["source_contract"], "target_cutoff_sha256": "0" * 64}})),
    ]
    checks.extend(mutation_controls)
    report = {
        "schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-189", "jira_key": "BAT-546",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "rebuild_root": str(rebuild_root), "result": "PASS", "check_count": len(checks),
        "mutation_control_count": len(mutation_controls), "checks": checks,
    }
    report_root = data_root / "validation" / "POST-SUBTASK-189"
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "historical_roster_membership_pit_validation.json"
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": len(mutation_controls), "report_path": str(report_path), "report_sha256": sha256_file(report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
