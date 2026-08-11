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

from aggie_analytics.temporal.team_membership_pit import (  # noqa: E402
    _admit, _load_candidates, _minimum_target_cutoff, canonical_json_bytes,
    dataframe_record_sha256, materialize, parse_utc, sha256_file,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    import polars as pl
    parser = argparse.ArgumentParser(); parser.add_argument("--data-root", type=Path, required=True); parser.add_argument("--dataset-identity", required=True); parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1]); parser.add_argument("--rebuild-root", type=Path, required=True); args = parser.parse_args()
    data_root, repo_root, rebuild_root, identity = args.data_root.resolve(), args.repo_root.resolve(), args.rebuild_root.resolve(), args.dataset_identity
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "historical_team_membership_pit_manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8")); contract = json.loads((repo_root / "configs" / "historical_team_membership_pit_contract.json").read_text(encoding="utf-8")); acceptance = contract["acceptance"]; checks = []
    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition: raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})
    check("dataset_identity", manifest["dataset_identity"] == identity); check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-190"); check("jira_key", manifest["jira_key"] == "BAT-547"); check("classification", manifest["classification"] == contract["classification"])
    population = manifest["population"]
    for key, expected in {"source_files": 20, "source_rows": 2462, "admitted_rows": 2462, "nonadmitted_rows": 0, "distinct_teams": 132, "duplicate_observation_ids": 0, "duplicate_natural_keys": 0, "conference_nulls": 0, "division_nulls": 993, "conference_or_division_transitions": 158}.items(): check(f"population_{key}", int(population[key]) == expected, population[key])
    check("per_season_population", population["admitted_by_season"] == acceptance["expected_admitted_by_season"]); check("source_schema_hashes", manifest["semantic_source_schema_hashes"] == 1)
    chronology = manifest["chronology"]; check("minimum_target_cutoff", chronology["minimum_target_cutoff_utc"] == acceptance["expected_minimum_target_cutoff_utc"]); check("chronology", parse_utc(chronology["source_known_at_utc"]) < parse_utc(chronology["minimum_target_cutoff_utc"])); check("no_backcast", chronology["backcast_before_source_known_at"] is False)
    authority = manifest["authority"]; check("pit_admission", authority["pit_state_admission"] is True); check("team_membership_only", authority["team_season_membership_only"] is True)
    for key in ("backcast_before_source_known_at", "effective_day_inferred", "conference_or_division_imputed", "venue_or_capacity_inferred", "branding_effective_time_inferred", "protected_training_admission", "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication"): check(f"authority_closed_{key}", authority[key] is False)
    for key, value in manifest["scientific_nonclaims"].items(): check(f"scientific_nonclaim_{key}", value is False)
    payload = manifest["payloads"][0]; state_path = data_root / "pit_state" / "historical_known_at" / "sha256" / identity / payload["name"]; check("payload_exists", state_path.is_file()); check("payload_bytes", state_path.stat().st_size == payload["bytes"]); check("payload_sha256", sha256_file(state_path) == payload["sha256"])
    state = pl.read_parquet(state_path); check("payload_rows", state.height == payload["rows"]); check("record_sha256", dataframe_record_sha256(state) == payload["record_sha256"]); check("forbidden_fields", not (set(contract["forbidden_admitted_fields"]) & set(state.columns))); check("season_grain", state["membership_effective_grain"].unique().to_list() == ["SEASON"]); check("no_effective_day", state["membership_effective_day_utc"].null_count() == state.height); check("no_venue_truth", state["venue_or_capacity_truth"].sum() == 0); check("no_branding_truth", state["branding_effective_truth"].sum() == 0); check("no_protected", state["protected_eligible"].sum() == 0)
    if rebuild_root.exists(): raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"]); check("byte_identical_identity", rebuilt["dataset_identity"] == identity); check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes()); check("byte_identical_payload", Path(rebuilt["state_path"]).read_bytes() == state_path.read_bytes())
    candidates, _, _ = _load_candidates(data_root, contract); first = candidates["observation_id"][0]
    mutations = [
        expect_rejection("duplicate_natural_key", lambda: _admit(pl.concat([candidates, candidates.head(1)]), contract)),
        expect_rejection("unverified_identity", lambda: _admit(candidates.with_columns(pl.when(pl.col("observation_id") == first).then(pl.lit("UNVERIFIED")).otherwise(pl.col("canonical_resolution_state")).alias("canonical_resolution_state")), contract)),
        expect_rejection("ambiguous_source_id", lambda: _admit(candidates.with_columns(pl.when(pl.col("observation_id") == first).then(pl.lit(2)).otherwise(pl.col("canonical_source_id_option_count")).alias("canonical_source_id_option_count")), contract)),
        expect_rejection("venue_field_present", lambda: _admit(candidates.with_columns(pl.when(pl.col("observation_id") == first).then(pl.lit(True)).otherwise(pl.col("venue_fields_present")).alias("venue_fields_present")), contract)),
        expect_rejection("target_hash_drift", lambda: _minimum_target_cutoff(data_root, {**contract, "source_contract": {**contract["source_contract"], "target_cutoff_sha256": "0" * 64}})),
    ]; checks.extend(mutations)
    report = {"schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-190", "jira_key": "BAT-547", "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "rebuild_root": str(rebuild_root), "result": "PASS", "check_count": len(checks), "mutation_control_count": len(mutations), "checks": checks}
    report_root = data_root / "validation" / "POST-SUBTASK-190"; report_root.mkdir(parents=True, exist_ok=True); report_path = report_root / "historical_team_membership_pit_validation.json"; report_path.write_bytes(canonical_json_bytes(report) + b"\n"); print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": len(mutations), "report_path": str(report_path), "report_sha256": sha256_file(report_path)}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
