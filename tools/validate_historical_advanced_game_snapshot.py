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

from aggie_analytics.temporal.advanced_game_snapshot import (  # noqa: E402
    _disposition,
    _load_candidates,
    _validate_contract_authority,
    _validate_source_values,
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
    manifest_path = data_root / "manifests" / "historical_capture_time" / "sha256" / identity / "historical_advanced_game_snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_advanced_game_snapshot_contract.json").read_text(encoding="utf-8"))
    expected, checks = contract["acceptance"], []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-192")
    check("jira_key", manifest["jira_key"] == "BAT-549")
    check("classification", manifest["classification"] == contract["classification"])
    check("candidate_identity", manifest["input_identities"]["candidate_dataset"] == contract["source_contract"]["candidate_dataset_identity"])
    check("candidate_manifest", manifest["input_identities"]["candidate_manifest_sha256"] == contract["source_contract"]["candidate_manifest_sha256"])
    check("team_box_snapshot_identity", manifest["input_identities"]["team_box_snapshot_dataset"] == contract["source_contract"]["team_box_snapshot_dataset_identity"])
    population = manifest["population"]
    scalar_expectations = {
        "source_rows": "expected_source_rows", "source_games": "expected_source_games", "source_leaf_cells": "expected_source_leaf_cells",
        "exact_rows": "expected_exact_rows", "exact_games": "expected_exact_games", "exact_teams": "expected_exact_teams", "exact_leaf_cells": "expected_exact_leaf_cells",
        "nonadmitted_rows": "expected_nonadmitted_rows", "nonadmitted_games": "expected_nonadmitted_games", "nonadmitted_leaf_cells": "expected_nonadmitted_leaf_cells",
        "field_path_count": "expected_field_path_count", "leaf_path_count": "expected_leaf_path_count", "missing_leaf_cells": "expected_missing_leaf_cells",
        "reciprocal_games": "expected_reciprocal_games", "team_box_link_rows": "expected_team_box_link_rows", "team_box_outcome_match_rows": "expected_team_box_outcome_match_rows",
        "team_box_only_collision_rows": "expected_team_box_only_collision_rows", "team_box_only_collision_games": "expected_team_box_only_collision_games",
    }
    for field, expected_key in scalar_expectations.items():
        check(f"population_{field}", int(population[field]) == int(expected[expected_key]), population[field])
    for field, expected_key in (("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season"), ("disposition_counts", "expected_disposition_counts")):
        check(f"population_{field}", population[field] == expected[expected_key])
    check("physical_schema_hashes", len(population["physical_schema_hashes"]) == expected["expected_physical_schema_hashes"])
    check("field_paths_unique", len(population["field_paths"]) == len(set(population["field_paths"])))
    check("leaf_paths_unique", len(population["leaf_paths"]) == len(set(population["leaf_paths"])))
    chronology = manifest["chronology"]
    check("historical_known_at_unknown", chronology["historical_known_at_state"] == contract["source_contract"]["historical_known_at_state"])
    check("historical_publication_unproved", chronology["historical_publication_time_proved"] is False)
    check("pre_capture_backcast_closed", chronology["pre_capture_backcast"] is False)
    for key, value in contract["authority"].items():
        check(f"authority_{key}", manifest["authority"][key] is value)
    check("scientific_nonclaims_closed", not any(manifest["scientific_nonclaims"].values()))
    payload_root = data_root / "quarantine" / "historical_capture_time" / "sha256" / identity
    frames = {}
    for payload in manifest["payloads"]:
        path = payload_root / payload["name"]
        check(f"payload_exists_{payload['role']}", path.is_file())
        check(f"payload_hash_{payload['role']}", sha256_file(path) == payload["sha256"])
        frame = pl.read_parquet(path)
        check(f"payload_rows_{payload['role']}", frame.height == int(payload["rows"]), frame.height)
        frames[payload["role"]] = frame
    exact = frames["EXACT_RECONCILED_CAPTURE_TIME_ADVANCED_GAME_ROWS"]
    nonadmitted = frames["NONADMITTED_ADVANCED_GAME_ROWS"]
    forbidden = set(contract["disposition"]["forbidden_snapshot_fields"])
    check("forbidden_fields_absent", not forbidden.intersection(exact.columns))
    check("exact_candidate_only", exact["capture_time_candidate_only"].all())
    check("exact_historical_pit_closed", not exact["historical_pit_eligible"].any())
    check("exact_preliminary_replay_closed", not exact["preliminary_replay_eligible"].any())
    check("exact_protected_closed", not exact["protected_eligible"].any())
    check("collision_quarantine_preserved", nonadmitted.filter(pl.col("nonadmission_reason") == "TEAM_BOX_ONLY_LINK_WITH_DUPLICATE_CANONICAL_GAME_TEAM_COLLISION").height == expected["expected_team_box_only_collision_rows"])
    original_payload_hashes = {item["name"]: item["sha256"] for item in manifest["payloads"]}
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"])
    check("rebuild_dataset_identity", rebuilt["dataset_identity"] == identity)
    rebuilt_payload_hashes = {item["name"]: item["sha256"] for item in rebuilt["manifest"]["payloads"]}
    check("byte_identical_payload_rebuild", rebuilt_payload_hashes == original_payload_hashes, rebuilt_payload_hashes)
    candidates, _, _ = _load_candidates(data_root, contract)
    mutation_controls = []
    opened = json.loads(json.dumps(contract)); opened["authority"]["historical_pit_admission"] = True
    mutation_controls.append(expect_rejection("opened_historical_pit_authority", lambda: _validate_contract_authority(opened)))
    wrong_manifest = json.loads(json.dumps(contract)); wrong_manifest["source_contract"]["candidate_manifest_sha256"] = "0" * 64
    mutation_controls.append(expect_rejection("candidate_manifest_hash_drift", lambda: _load_candidates(data_root, wrong_manifest)))
    wrong_population = json.loads(json.dumps(contract)); wrong_population["acceptance"]["expected_exact_rows"] += 1
    mutation_controls.append(expect_rejection("exact_population_drift", lambda: _disposition(candidates, wrong_population)))
    duplicate = pl.concat([candidates, candidates.head(1)], how="vertical_relaxed")
    duplicate_contract = json.loads(json.dumps(contract)); duplicate_contract["acceptance"]["expected_source_rows"] += 1; duplicate_contract["acceptance"]["expected_nonadmitted_rows"] += 1
    mutation_controls.append(expect_rejection("duplicate_observation_identity", lambda: _disposition(duplicate, duplicate_contract)))
    bad_hash = candidates.with_row_index("_i").with_columns(pl.when(pl.col("_i") == 0).then(pl.lit("0" * 64)).otherwise(pl.col("offense_sha256")).alias("offense_sha256")).drop("_i")
    mutation_controls.append(expect_rejection("nested_value_hash_drift", lambda: _validate_source_values(bad_hash, contract)))
    wrong_collision = json.loads(json.dumps(contract)); wrong_collision["acceptance"]["expected_team_box_only_collision_rows"] -= 1
    mutation_controls.append(expect_rejection("collision_population_drift", lambda: _disposition(candidates, wrong_collision)))
    report = {
        "schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-192", "jira_key": "BAT-549", "result": "PASS",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path), "checks": checks, "check_count": len(checks),
        "mutation_controls": mutation_controls, "mutation_control_count": len(mutation_controls),
        "rebuild_dataset_identity": rebuilt["dataset_identity"], "byte_identical_payloads": sorted(original_payload_hashes),
    }
    report_root = data_root / "validation" / "POST-SUBTASK-192" / identity
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "historical_advanced_game_snapshot_validation.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "report_path": str(report_path), "report_sha256": sha256_file(report_path), "check_count": len(checks), "mutation_control_count": len(mutation_controls)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
