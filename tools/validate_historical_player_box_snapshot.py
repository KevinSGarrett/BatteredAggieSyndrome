from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.player_box_snapshot import (  # noqa: E402
    _disposition,
    _load_candidates,
    _validate_contract_authority,
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
    manifest_path = data_root / "manifests" / "historical_capture_time" / "sha256" / identity / "historical_player_box_snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_player_box_snapshot_contract.json").read_text(encoding="utf-8"))
    expected, checks = contract["acceptance"], []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-193")
    check("jira_key", manifest["jira_key"] == "BAT-550")
    check("classification", manifest["classification"] == contract["classification"])
    inputs = manifest["input_identities"]
    check("candidate_identity", inputs["candidate_dataset"] == contract["source_contract"]["candidate_dataset_identity"])
    check("candidate_manifest", inputs["candidate_manifest_sha256"] == contract["source_contract"]["candidate_manifest_sha256"])
    check("team_box_snapshot_identity", inputs["team_box_snapshot_dataset"] == contract["source_contract"]["team_box_snapshot_dataset_identity"])
    check("player_event_candidate_identity", inputs["player_event_candidate"] == contract["source_contract"]["player_event_candidate_identity"])
    population = manifest["population"]
    scalar_expectations = {
        "source_cells": "expected_source_cells", "source_games": "expected_source_games", "source_team_rows": "expected_source_team_rows", "source_player_ids": "expected_source_player_ids",
        "exact_cells": "expected_exact_cells", "exact_games": "expected_exact_games", "exact_player_ids": "expected_exact_player_ids",
        "nonadmitted_cells": "expected_nonadmitted_cells", "nonadmitted_games": "expected_nonadmitted_games", "categories": "expected_categories", "stat_types": "expected_stat_types",
        "missing_player_id_cells": "expected_missing_player_id_cells", "missing_player_name_cells": "expected_missing_player_name_cells", "missing_stat_value_cells": "expected_missing_stat_value_cells",
        "player_label_whitespace_drift_cells": "expected_player_label_whitespace_drift_cells", "games_with_two_team_rows": "expected_games_with_two_team_rows",
        "games_without_two_team_rows": "expected_games_without_two_team_rows", "missing_team_rows": "expected_missing_team_rows", "team_box_link_cells": "expected_team_box_link_cells",
        "player_event_link_cells": "expected_player_event_link_cells", "exact_value_incomplete_identity_cells": "expected_exact_value_incomplete_identity_cells",
    }
    for field, expected_key in scalar_expectations.items():
        check(f"population_{field}", int(population[field]) == int(expected[expected_key]), population[field])
    for field, expected_key in (("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season"), ("disposition_counts", "expected_disposition_counts")):
        check(f"population_{field}", population[field] == expected[expected_key])
    check("physical_schema_hashes", len(population["physical_schema_hashes"]) == expected["expected_physical_schema_hashes"])
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
    exact = frames["EXACT_RECONCILED_CAPTURE_TIME_PLAYER_BOX_STAT_CELLS"]
    nonadmitted = frames["NONADMITTED_PLAYER_BOX_STAT_CELLS"]
    check("forbidden_fields_absent", not set(contract["disposition"]["forbidden_snapshot_fields"]).intersection(exact.columns))
    check("exact_candidate_only", exact["capture_time_candidate_only"].all())
    check("exact_historical_pit_closed", not exact["historical_pit_eligible"].any())
    check("exact_preliminary_replay_closed", not exact["preliminary_replay_eligible"].any())
    check("exact_protected_closed", not exact["protected_eligible"].any())
    check("incomplete_identity_quarantine_preserved", nonadmitted.filter(pl.col("nonadmission_reason") == "EXACT_VALUE_EVIDENCE_WITHOUT_COMPLETE_CANONICAL_GAME_TEAM_PLAYER_IDENTITY").height == expected["expected_exact_value_incomplete_identity_cells"])
    check("conflict_quarantine_preserved", nonadmitted.filter(pl.col("nonadmission_reason") == "PLAY_DERIVED_METRIC_VALUE_CONFLICT").height == expected["expected_disposition_counts"]["QUARANTINE_PLAY_DERIVED_METRIC_VALUE_CONFLICT"])
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
    wrong_population = json.loads(json.dumps(contract)); wrong_population["acceptance"]["expected_exact_cells"] += 1
    mutation_controls.append(expect_rejection("exact_population_drift", lambda: _disposition(candidates, wrong_population)))
    wrong_incomplete = json.loads(json.dumps(contract)); wrong_incomplete["acceptance"]["expected_exact_value_incomplete_identity_cells"] -= 1
    mutation_controls.append(expect_rejection("incomplete_identity_population_drift", lambda: _disposition(candidates, wrong_incomplete)))
    forbidden = json.loads(json.dumps(contract)); forbidden["disposition"]["snapshot_fields"].append("source_team_points")
    mutation_controls.append(expect_rejection("outcome_field_opened", lambda: _disposition(candidates, forbidden)))
    duplicate = pl.concat([candidates, candidates.head(1)], how="vertical_relaxed")
    duplicate_contract = json.loads(json.dumps(contract)); duplicate_contract["acceptance"]["expected_source_cells"] += 1; duplicate_contract["acceptance"]["expected_nonadmitted_cells"] += 1
    mutation_controls.append(expect_rejection("duplicate_observation_identity", lambda: _disposition(duplicate, duplicate_contract)))
    report = {
        "schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-193", "jira_key": "BAT-550", "result": "PASS",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path), "checks": checks, "check_count": len(checks),
        "mutation_controls": mutation_controls, "mutation_control_count": len(mutation_controls),
        "rebuild_dataset_identity": rebuilt["dataset_identity"], "byte_identical_payloads": sorted(original_payload_hashes),
        "rebuild_cleanup": "REMOVED_AFTER_SUCCESS",
    }
    report_root = data_root / "validation" / "POST-SUBTASK-193" / identity
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "historical_player_box_snapshot_validation.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(rebuild_root)
    print(json.dumps({"result": "PASS", "report_path": str(report_path), "report_sha256": sha256_file(report_path), "check_count": len(checks), "mutation_control_count": len(mutation_controls), "rebuild_removed": not rebuild_root.exists()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
