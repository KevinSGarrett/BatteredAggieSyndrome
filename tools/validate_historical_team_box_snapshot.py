from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.team_box_snapshot import (  # noqa: E402
    _disposition,
    _load_candidates,
    _validate_contract_authority,
    _validate_source_stats,
    canonical_json_bytes,
    dataframe_record_sha256,
    materialize,
    sha256_file,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    data_root, repo_root, rebuild_root = args.data_root.resolve(), args.repo_root.resolve(), args.rebuild_root.resolve()
    identity = args.dataset_identity
    manifest_path = data_root / "manifests" / "historical_capture_time" / "sha256" / identity / "historical_team_box_snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_team_box_snapshot_contract.json").read_text(encoding="utf-8"))
    expected = contract["acceptance"]
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-191")
    check("jira_key", manifest["jira_key"] == "BAT-548")
    check("classification", manifest["classification"] == contract["classification"])
    check("candidate_identity", manifest["input_identities"]["candidate_dataset"] == contract["source_contract"]["candidate_dataset_identity"])
    check("candidate_manifest", manifest["input_identities"]["candidate_manifest_sha256"] == contract["source_contract"]["candidate_manifest_sha256"])
    check("accepted_outcome_identity", manifest["input_identities"]["accepted_outcome_dataset"] == contract["source_contract"]["accepted_outcome_dataset_identity"])
    population = manifest["population"]
    scalar_expectations = {
        "source_rows": "expected_source_rows", "source_games": "expected_source_games", "source_stat_cells": "expected_source_stat_cells",
        "exact_rows": "expected_exact_rows", "exact_games": "expected_exact_games", "exact_teams": "expected_exact_teams",
        "exact_stat_cells": "expected_exact_stat_cells", "nonadmitted_rows": "expected_nonadmitted_rows",
        "nonadmitted_games": "expected_nonadmitted_games", "nonadmitted_stat_cells": "expected_nonadmitted_stat_cells",
        "distinct_stat_categories": "expected_distinct_stat_categories", "side_swap_rows": "expected_side_swap_rows",
        "side_swap_games": "expected_side_swap_games", "outcome_overlap_rows": "expected_outcome_overlap_rows",
    }
    for field, expected_key in scalar_expectations.items():
        check(f"population_{field}", int(population[field]) == int(expected[expected_key]), population[field])
    for field, expected_key in (("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season"), ("disposition_counts", "expected_disposition_counts"), ("category_counts_by_season", "expected_category_counts_by_season")):
        check(f"population_{field}", population[field] == expected[expected_key])
    check("physical_schema_hashes", len(population["physical_schema_hashes"]) == expected["expected_physical_schema_hashes"])
    chronology = manifest["chronology"]
    check("historical_known_at_unknown", chronology["historical_known_at_state"] == contract["source_contract"]["historical_known_at_state"])
    check("capture_minimum", chronology["minimum_capture_known_at_utc"] == contract["source_contract"]["minimum_capture_known_at_utc"])
    check("capture_maximum", chronology["maximum_capture_known_at_utc"] == contract["source_contract"]["maximum_capture_known_at_utc"])
    check("historical_publication_unproved", chronology["historical_publication_time_proved"] is False)
    check("no_pre_capture_backcast", chronology["pre_capture_backcast"] is False)
    _validate_contract_authority(contract)
    authority = manifest["authority"]
    check("candidate_snapshot_enabled", authority["candidate_snapshot_materialization"] is True)
    for key in (
        "immutable_raw_capture_mutation", "canonical_entity_mutation", "historical_pit_admission",
        "preliminary_chronological_replay_admission", "protected_training_admission", "protected_evaluation_admission",
        "champion_or_production_promotion", "forecast_publication",
    ):
        check(f"authority_closed_{key}", authority[key] is False)
    for key, value in manifest["scientific_nonclaims"].items():
        check(f"scientific_nonclaim_{key}", value is False)
    payload_root = data_root / "quarantine" / "historical_capture_time" / "sha256" / identity
    frames: dict[str, Any] = {}
    for payload in manifest["payloads"]:
        path = payload_root / payload["name"]
        check(f"payload_exists_{payload['role']}", path.is_file())
        check(f"payload_bytes_{payload['role']}", path.stat().st_size == payload["bytes"])
        check(f"payload_sha256_{payload['role']}", sha256_file(path) == payload["sha256"])
        frame = pl.read_parquet(path)
        frames[payload["role"]] = frame
        check(f"payload_rows_{payload['role']}", frame.height == payload["rows"])
        check(f"record_sha256_{payload['role']}", dataframe_record_sha256(frame) == payload["record_sha256"])
    snapshot = frames["EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_ROWS"]
    cells = frames["EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_STAT_CELLS"]
    nonadmitted = frames["SOURCE_ONLY_NONADMITTED_TEAM_BOX_ROWS"]
    check("snapshot_forbidden_fields", not (set(contract["disposition"]["forbidden_snapshot_fields"]) & set(snapshot.columns)))
    check("snapshot_candidate_only", snapshot["capture_time_candidate_only"].all())
    check("snapshot_no_historical_pit", snapshot["historical_pit_eligible"].sum() == 0)
    check("snapshot_no_preliminary_replay", snapshot["preliminary_replay_eligible"].sum() == 0)
    check("snapshot_no_protected", snapshot["protected_eligible"].sum() == 0)
    check("cell_identity_unique", cells["stat_cell_id"].n_unique() == cells.height)
    check("cell_natural_key_unique", cells.group_by(["observation_id", "stat_category"]).len().filter(pl.col("len") > 1).height == 0)
    check("cell_raw_parse_state", cells["stat_value_parse_state"].unique().to_list() == ["RAW_SOURCE_TEXT_NOT_PARSED"])
    check("cell_no_historical_pit", cells["historical_pit_eligible"].sum() == 0)
    check("cell_no_protected", cells["protected_eligible"].sum() == 0)
    check("nonadmitted_disposition", nonadmitted["reconciliation_disposition"].unique().to_list() == [contract["disposition"]["nonadmitted_reconciliation_disposition"]])
    check("nonadmission_reason", nonadmitted["nonadmission_reason"].n_unique() == 1)
    check("nonadmitted_no_historical_pit", nonadmitted["historical_pit_eligible"].sum() == 0)
    check("stat_cell_conservation", cells.height + expected["expected_nonadmitted_stat_cells"] == expected["expected_source_stat_cells"])
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"])
    check("byte_identical_identity", rebuilt["dataset_identity"] == identity)
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    for result_key, role in (("snapshot_path", "EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_ROWS"), ("cells_path", "EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_STAT_CELLS"), ("nonadmitted_path", "SOURCE_ONLY_NONADMITTED_TEAM_BOX_ROWS")):
        original = payload_root / next(item["name"] for item in manifest["payloads"] if item["role"] == role)
        check(f"byte_identical_{role}", Path(rebuilt[result_key]).read_bytes() == original.read_bytes())
    candidates, _, _ = _load_candidates(data_root, contract)
    first = candidates["observation_id"][0]
    source_rows = candidates.filter(pl.col("reconciliation_disposition") == contract["disposition"]["nonadmitted_reconciliation_disposition"])
    stats = json.loads(candidates["stats_json"][0]); duplicated = stats + [stats[0]]; duplicated_json = json.dumps(duplicated, separators=(",", ":"))
    mutated_stats = candidates.with_columns(
        pl.when(pl.col("observation_id") == first).then(pl.lit(duplicated_json)).otherwise(pl.col("stats_json")).alias("stats_json"),
        pl.when(pl.col("observation_id") == first).then(pl.lit(hashlib.sha256(duplicated_json.encode()).hexdigest())).otherwise(pl.col("stats_sha256")).alias("stats_sha256"),
        pl.when(pl.col("observation_id") == first).then(pl.lit(len(duplicated))).otherwise(pl.col("stats_category_count")).alias("stats_category_count"),
    )
    mutations = [
        expect_rejection("duplicate_natural_key", lambda: _disposition(pl.concat([candidates, candidates.head(1)]), contract)),
        expect_rejection("eligible_missing_canonical_team", lambda: _disposition(candidates.with_columns(pl.when(pl.col("observation_id") == first).then(pl.lit(None, dtype=pl.String)).otherwise(pl.col("canonical_team_id_candidate")).alias("canonical_team_id_candidate")), contract)),
        expect_rejection("source_only_silently_promoted", lambda: _disposition(candidates.with_columns(pl.when(pl.col("observation_id") == source_rows["observation_id"][0]).then(pl.lit(contract["disposition"]["eligible_reconciliation_dispositions"][0])).otherwise(pl.col("reconciliation_disposition")).alias("reconciliation_disposition")), contract)),
        expect_rejection("stat_hash_drift", lambda: _validate_source_stats(candidates.with_columns(pl.when(pl.col("observation_id") == first).then(pl.lit("[]")).otherwise(pl.col("stats_json")).alias("stats_json")))),
        expect_rejection("duplicate_stat_category", lambda: _validate_source_stats(mutated_stats)),
        expect_rejection("historical_pit_authority_open", lambda: _validate_contract_authority({**contract, "authority": {**contract["authority"], "historical_pit_admission": True}})),
    ]
    checks.extend(mutations)
    report = {
        "schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-191", "jira_key": "BAT-548",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "dataset_identity": identity,
        "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "rebuild_root": str(rebuild_root),
        "result": "PASS", "check_count": len(checks), "mutation_control_count": len(mutations), "checks": checks,
    }
    report_root = data_root / "validation" / "POST-SUBTASK-191"
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "historical_team_box_snapshot_validation.json"
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": len(mutations), "report_path": str(report_path), "report_sha256": sha256_file(report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
