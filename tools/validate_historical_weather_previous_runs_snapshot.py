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

from aggie_analytics.temporal.weather_previous_runs_snapshot import (  # noqa: E402
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
    data_root = args.data_root.resolve()
    repo_root = args.repo_root.resolve()
    rebuild_root = args.rebuild_root.resolve()
    identity = args.dataset_identity
    manifest_path = (
        data_root
        / "manifests"
        / "historical_nominal_lead"
        / "sha256"
        / identity
        / "historical_weather_previous_runs_snapshot_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(
        (repo_root / "configs" / "historical_weather_previous_runs_snapshot_contract.json").read_text(
            encoding="utf-8"
        )
    )
    expected = contract["acceptance"]
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-194")
    check("jira_key", manifest["jira_key"] == "BAT-551")
    check("classification", manifest["classification"] == contract["classification"])
    inputs = manifest["input_identities"]
    source = contract["source_contract"]
    check("candidate_identity", inputs["candidate_dataset"] == source["candidate_dataset_identity"])
    check("candidate_manifest", inputs["candidate_manifest_sha256"] == source["candidate_manifest_sha256"])
    check("candidate_payload_count", len(inputs["candidate_payload_sha256"]) == expected["expected_source_files"])
    population = manifest["population"]
    scalar_expectations = {
        "source_cells": "expected_source_cells",
        "source_games": "expected_source_games",
        "source_requests": "expected_source_requests",
        "source_captures": "expected_source_captures",
        "variables": "expected_variables",
        "leads": "expected_leads",
        "candidate_cells": "expected_candidate_cells",
        "candidate_games": "expected_candidate_games",
        "nonadmitted_cells": "expected_nonadmitted_cells",
        "nonadmitted_games": "expected_nonadmitted_games",
        "dome_context_cells": "expected_dome_context_cells",
        "candidate_dome_context_cells": "expected_candidate_dome_context_cells",
        "missing_source_value_cells": "expected_missing_source_value_cells",
        "missing_game_id_cells": "expected_missing_game_id_cells",
        "missing_venue_id_cells": "expected_missing_venue_id_cells",
        "missing_coordinate_cells": "expected_missing_coordinate_cells",
        "source_evidence_gap_games": "expected_source_evidence_gap_games",
        "technical_route_gap_games": "expected_technical_route_gap_games",
    }
    for field, expected_key in scalar_expectations.items():
        check(f"population_{field}", int(population[field]) == int(expected[expected_key]), population[field])
    profile_expectations = {
        "candidate_by_season": "expected_candidate_by_season",
        "nonadmitted_by_season": "expected_nonadmitted_by_season",
        "source_cells_by_season": "expected_source_cells_by_season",
        "source_games_by_season": "expected_source_games_by_season",
        "lead_hours": "expected_lead_hours",
        "kickoff_offset_minutes": "expected_kickoff_offset_minutes",
    }
    for field, expected_key in profile_expectations.items():
        check(f"population_{field}", population[field] == expected[expected_key], population[field])
    check("physical_schema_hashes", len(population["physical_schema_hashes"]) == expected["expected_physical_schema_hashes"])
    capture = manifest["capture_profile"]
    check("capture_manifest_count", capture["capture_manifests"] == expected["expected_capture_manifests"])
    check("capture_known_at_range", capture["minimum_capture_known_at_utc"] <= capture["maximum_capture_known_at_utc"])
    chronology = manifest["chronology"]
    check("historical_known_at_unknown", chronology["historical_known_at_state"] == source["historical_known_at_state"])
    check("nominal_lead_semantics", chronology["nominal_lead_semantics_verified"] is True)
    check("exact_run_initialization_unproved", chronology["exact_model_run_initialization_proved"] is False)
    check("historical_api_availability_unproved", chronology["historical_api_availability_proved"] is False)
    check("venue_effective_time_unproved", chronology["venue_coordinate_effective_time_proved"] is False)
    check("pre_capture_backcast_closed", chronology["pre_capture_backcast"] is False)
    for key, value in contract["authority"].items():
        check(f"authority_{key}", manifest["authority"][key] is value)
    check("scientific_nonclaims_closed", not any(manifest["scientific_nonclaims"].values()))

    payload_root = data_root / "quarantine" / "historical_nominal_lead" / "sha256" / identity
    frames: dict[str, Any] = {}
    for payload in manifest["payloads"]:
        path = payload_root / payload["name"]
        check(f"payload_exists_{payload['role']}", path.is_file())
        check(f"payload_hash_{payload['role']}", sha256_file(path) == payload["sha256"])
        frame = pl.read_parquet(path)
        check(f"payload_rows_{payload['role']}", frame.height == int(payload["rows"]), frame.height)
        frames[payload["role"]] = frame
    candidate = frames["NOMINAL_LEAD_WEATHER_CANDIDATE_CELLS"]
    nonadmitted = frames["ARCHIVE_VARIABLE_UNAVAILABLE_WEATHER_CELLS"]
    forbidden = set(contract["disposition"]["forbidden_snapshot_fields"])
    check("forbidden_fields_absent", not forbidden.intersection(candidate.columns))
    check("candidate_nominal_reference_only", candidate["nominal_lead_reference_only"].all())
    check("candidate_exact_run_time_absent", candidate["historical_model_run_initialization_at_utc"].null_count() == candidate.height)
    check("candidate_api_availability_absent", candidate["historical_api_available_at_utc"].null_count() == candidate.height)
    check("candidate_historical_pit_closed", not candidate["historical_pit_eligible"].any())
    check("candidate_preliminary_replay_closed", not candidate["preliminary_replay_eligible"].any())
    check("candidate_protected_closed", not candidate["protected_eligible"].any())
    check("unavailable_values_preserved_null", nonadmitted["source_value"].null_count() == nonadmitted.height)
    check(
        "unavailable_reason_preserved",
        nonadmitted.filter(
            pl.col("nonadmission_reason") == "ARCHIVE_VARIABLE_NOT_AVAILABLE_NO_VALUE_FABRICATED"
        ).height
        == expected["expected_nonadmitted_cells"],
    )

    original_payload_hashes = {item["name"]: item["sha256"] for item in manifest["payloads"]}
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("rebuild_dataset_identity", rebuilt["dataset_identity"] == identity)
    rebuilt_payload_hashes = {item["name"]: item["sha256"] for item in rebuilt["manifest"]["payloads"]}
    check("byte_identical_payload_rebuild", rebuilt_payload_hashes == original_payload_hashes, rebuilt_payload_hashes)

    candidates, _, _, _ = _load_candidates(data_root, contract)
    mutation_controls = []
    opened = json.loads(json.dumps(contract))
    opened["authority"]["historical_pit_admission"] = True
    mutation_controls.append(expect_rejection("opened_historical_pit_authority", lambda: _validate_contract_authority(opened)))
    wrong_manifest = json.loads(json.dumps(contract))
    wrong_manifest["source_contract"]["candidate_manifest_sha256"] = "0" * 64
    mutation_controls.append(expect_rejection("candidate_manifest_hash_drift", lambda: _load_candidates(data_root, wrong_manifest)))
    wrong_population = json.loads(json.dumps(contract))
    wrong_population["acceptance"]["expected_candidate_cells"] += 1
    mutation_controls.append(expect_rejection("candidate_population_drift", lambda: _disposition(candidates, wrong_population)))
    wrong_missing = json.loads(json.dumps(contract))
    wrong_missing["acceptance"]["expected_nonadmitted_cells"] -= 1
    mutation_controls.append(expect_rejection("unavailable_population_drift", lambda: _disposition(candidates, wrong_missing)))
    forbidden_contract = json.loads(json.dumps(contract))
    forbidden_contract["disposition"]["snapshot_fields"].append("home_points")
    mutation_controls.append(expect_rejection("outcome_field_opened", lambda: _disposition(candidates, forbidden_contract)))
    duplicate = pl.concat([candidates, candidates.head(1)], how="vertical_relaxed")
    duplicate_contract = json.loads(json.dumps(contract))
    duplicate_contract["acceptance"]["expected_source_cells"] += 1
    duplicate_contract["acceptance"]["expected_candidate_cells"] += 1
    mutation_controls.append(expect_rejection("duplicate_observation_identity", lambda: _disposition(duplicate, duplicate_contract)))
    fabricated_run = candidates.with_columns(pl.lit("2021-01-01T00:00:00Z").alias("historical_model_run_initialization_at_utc"))
    mutation_controls.append(expect_rejection("fabricated_run_initialization", lambda: _disposition(fabricated_run, contract)))
    wrong_lead = candidates.with_columns(
        pl.when(pl.col("observation_id") == candidates["observation_id"][0])
        .then(pl.col("nominal_lead_hours") + 1)
        .otherwise(pl.col("nominal_lead_hours"))
        .alias("nominal_lead_hours")
    )
    mutation_controls.append(expect_rejection("nominal_lead_semantics_drift", lambda: _disposition(wrong_lead, contract)))

    report = {
        "schema_version": "1.0.0",
        "decision_unit": "POST-SUBTASK-194",
        "jira_key": "BAT-551",
        "result": "PASS",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "checks": checks,
        "check_count": len(checks),
        "mutation_controls": mutation_controls,
        "mutation_control_count": len(mutation_controls),
        "rebuild_dataset_identity": rebuilt["dataset_identity"],
        "byte_identical_payloads": sorted(original_payload_hashes),
        "rebuild_cleanup": "REMOVED_AFTER_SUCCESS",
    }
    report_root = data_root / "validation" / "POST-SUBTASK-194" / identity
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / f"historical_weather_previous_runs_snapshot_validation_{rebuild_root.name}.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(rebuild_root)
    print(
        json.dumps(
            {
                "result": "PASS",
                "report_path": str(report_path),
                "report_sha256": sha256_file(report_path),
                "check_count": len(checks),
                "mutation_control_count": len(mutation_controls),
                "rebuild_removed": not rebuild_root.exists(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
