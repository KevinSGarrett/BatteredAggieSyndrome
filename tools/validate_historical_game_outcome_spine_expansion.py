from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.historical_game_outcome_spine import (  # noqa: E402
    _load_cfbd,
    _load_registry,
    _validate_contract_authority,
    canonical_json_bytes,
    dataframe_record_sha256,
    sha256_file,
)
from aggie_analytics.data.historical_game_outcome_spine_expansion import (  # noqa: E402
    materialize_expansion,
    resolve_expansion_contract,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(exc).__name__,
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "configs/historical_game_outcome_spine_expansion_contract.json",
    )
    parser.add_argument("--rebuild-root", type=Path, required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract.resolve()
    rebuild_root = args.rebuild_root.resolve()
    identity = args.dataset_identity
    manifest_path = (
        data_root
        / "manifests/historical_game_outcome_spine/sha256"
        / identity
        / "historical_game_outcome_spine_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract, contract_sources = resolve_expansion_contract(
        repo_root=repo_root, contract_path=contract_path
    )
    acceptance = contract["acceptance"]
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("artifact_type", manifest["artifact_type"] == "HISTORICAL_GAME_OUTCOME_REFERENCE_SPINE_EXPANSION")
    check("decision_unit", manifest["decision_unit"] == contract["decision_unit"])
    check("jira_key", manifest["jira_key"] == contract["jira_key"])
    check("classification", manifest["classification"] == contract["classification"])
    check("contract_sources", manifest["contract_sources"] == contract_sources)
    population = manifest["population"]
    for actual, expected in {
        "cfbd_rows": "expected_cfbd_rows",
        "cfbd_unique_games": "expected_cfbd_unique_games",
        "sportsdataverse_rows": "expected_sportsdataverse_rows",
        "sportsdataverse_unique_source_games": "expected_sportsdataverse_unique_source_games",
        "sportsdataverse_unique_canonical_games": "expected_sportsdataverse_unique_canonical_games",
        "canonical_schedule_games": "expected_canonical_schedule_games",
        "completed_outcomes": "expected_completed_outcomes",
        "schedule_only_nonoutcomes": "expected_schedule_only_nonoutcomes",
        "ties": "expected_ties",
        "canonical_cross_source_overlap": "expected_canonical_cross_source_overlap",
        "cfbd_only_canonical_games": "expected_cfbd_only_canonical_games",
        "sportsdataverse_only_canonical_games": "expected_sportsdataverse_only_canonical_games",
        "alias_groups": "expected_alias_groups",
        "alias_rows": "expected_alias_rows",
        "duplicate_completed_game_ids": "expected_duplicate_completed_game_ids",
        "duplicate_schedule_only_game_ids": "expected_duplicate_schedule_only_game_ids",
        "unmapped_cfbd_rows": "expected_unmapped_cfbd_rows",
        "unmapped_sportsdataverse_rows": "expected_unmapped_sportsdataverse_rows",
    }.items():
        check(f"population_{actual}", int(population[actual]) == int(acceptance[expected]), population[actual])
    for actual, expected in {
        "reconciliation_dispositions": "expected_reconciliation_dispositions",
        "cfbd_by_season": "expected_cfbd_by_season",
        "schedule_by_season": "expected_schedule_by_season",
        "completed_by_season": "expected_completed_by_season",
        "alias_groups_by_season": "expected_alias_groups_by_season",
    }.items():
        check(f"population_{actual}", population[actual] == acceptance[expected])

    chronology = manifest["chronology"]
    check("historical_publication_unknown", chronology["historical_source_publication_time_proved"] is False)
    check("final_whistle_unknown", chronology["historical_final_whistle_time_proved"] is False)
    check("same_day_closed", chronology["same_day_chronology_admitted"] is False)
    check("target_game_feature_closed", chronology["target_game_feature_use_admitted"] is False)
    check("inspected_2024_2025_not_untouched", chronology["inspected_2024_2025_untouched_protected"] is False)
    authority = manifest["authority"]
    for key in (
        "candidate_snapshot_materialization",
        "schedule_reference_use",
        "outcome_reference_use",
        "preliminary_outcome_label_candidate",
    ):
        check(f"authority_open_{key}", authority[key] is True)
    for key in (
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
        "historical_pit_admission",
        "same_day_chronology_admission",
        "preliminary_feature_direct_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "forecast_publication",
    ):
        check(f"authority_closed_{key}", authority[key] is False)
    for key, value in manifest["scientific_nonclaims"].items():
        check(f"scientific_nonclaim_{key}", value is False)

    frames: dict[str, Any] = {}
    for payload in manifest["payloads"]:
        path = data_root / payload["relative_path"]
        check(f"payload_exists_{payload['role']}", path.is_file())
        check(f"payload_bytes_{payload['role']}", path.stat().st_size == payload["bytes"])
        check(f"payload_sha256_{payload['role']}", sha256_file(path) == payload["sha256"])
        frame = pl.read_parquet(path)
        frames[payload["role"]] = frame
        check(f"payload_rows_{payload['role']}", frame.height == payload["rows"])
        check(
            f"payload_record_sha256_{payload['role']}",
            dataframe_record_sha256(frame) == payload["record_sha256"],
        )
    completed = frames["COMPLETED_OUTCOME_REFERENCE_CANDIDATES"]
    schedule_only = frames["SCHEDULE_ONLY_NONOUTCOMES"]
    reconciliation = frames["SOURCE_ALIAS_AND_OUTCOME_RECONCILIATION"]
    forbidden = set(contract["fields"]["forbidden_output_fields"])
    check("forbidden_output_fields", not forbidden & (set(completed.columns) | set(schedule_only.columns) | set(reconciliation.columns)))
    check("completed_unique", completed["canonical_game_id"].n_unique() == completed.height)
    check("completed_scores_present", completed["home_points"].null_count() == 0 and completed["away_points"].null_count() == 0)
    check("completed_reference_only", completed["outcome_reference_eligible"].all())
    check("completed_no_pit", completed["historical_pit_eligible"].sum() == 0)
    check("completed_no_same_day", completed["same_day_chronology_eligible"].sum() == 0)
    check("completed_no_feature_direct", completed["preliminary_feature_direct_admission"].sum() == 0)
    check("completed_no_protected", completed["protected_eligible"].sum() == 0)
    check("schedule_only_unique", schedule_only["canonical_game_id"].n_unique() == schedule_only.height)
    check("schedule_only_scores_cleared", schedule_only["home_points"].null_count() == schedule_only.height and schedule_only["away_points"].null_count() == schedule_only.height)
    check("schedule_only_outcomes_cleared", schedule_only["outcome_result"].null_count() == schedule_only.height)
    check("schedule_only_no_outcome_authority", schedule_only["outcome_reference_eligible"].sum() == 0)

    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize_expansion(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        contract_path=contract_path,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("byte_identical_identity", rebuilt["dataset_identity"] == identity)
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    for key, role in (
        ("completed_path", "COMPLETED_OUTCOME_REFERENCE_CANDIDATES"),
        ("schedule_only_path", "SCHEDULE_ONLY_NONOUTCOMES"),
        ("reconciliation_path", "SOURCE_ALIAS_AND_OUTCOME_RECONCILIATION"),
    ):
        original = data_root / next(
            item["relative_path"] for item in manifest["payloads"] if item["role"] == role
        )
        check(f"byte_identical_{role}", Path(rebuilt[key]).read_bytes() == original.read_bytes())

    mutations = [
        expect_rejection(
            "base_contract_hash_drift",
            lambda: resolve_expansion_contract(
                repo_root=repo_root,
                contract_path=_mutated_overlay(contract_path, rebuild_root, base_sha256="0" * 64),
            ),
        ),
        expect_rejection(
            "authority_historical_pit_opened",
            lambda: _validate_contract_authority(
                {
                    **contract,
                    "authority": {**contract["authority"], "historical_pit_admission": True},
                }
            ),
        ),
        expect_rejection(
            "forbidden_output_field",
            lambda: _validate_contract_authority(
                {
                    **contract,
                    "fields": {
                        **contract["fields"],
                        "completed_outcome_fields": contract["fields"]["completed_outcome_fields"]
                        + ["homePostgameElo"],
                    },
                }
            ),
        ),
        expect_rejection(
            "cfbd_manifest_hash_drift",
            lambda: _load_cfbd(
                data_root,
                {
                    **contract,
                    "source_contract": {
                        **contract["source_contract"],
                        "cfbd_manifest_sha256": "0" * 64,
                    },
                },
            ),
        ),
        expect_rejection(
            "canonical_registry_hash_drift",
            lambda: _load_registry(
                data_root,
                {
                    **contract,
                    "source_contract": {
                        **contract["source_contract"],
                        "canonical_registry_sha256": "0" * 64,
                    },
                },
            ),
        ),
    ]
    checks.extend(mutations)
    report = {
        "schema_version": "2.0.0",
        "artifact_type": "HISTORICAL_GAME_OUTCOME_SPINE_EXPANSION_VALIDATION",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "rebuild_root": str(rebuild_root),
        "result": "PASS",
        "check_count": len(checks),
        "mutation_control_count": len(mutations),
        "checks": checks,
    }
    report_bytes = canonical_json_bytes(report) + b"\n"
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()
    report_path = (
        data_root
        / "validation/BAT-554/outcome-spine"
        / identity
        / "runs"
        / report_sha256
        / "report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise ValueError("immutable validation report collision")
    report_path.write_bytes(report_bytes)
    print(
        json.dumps(
            {
                "result": "PASS",
                "checks": len(checks),
                "mutation_controls": len(mutations),
                "report_path": str(report_path),
                "report_sha256": report_sha256,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _mutated_overlay(path: Path, root: Path, *, base_sha256: str) -> Path:
    mutated = json.loads(path.read_text(encoding="utf-8"))
    mutated["base_contract_sha256"] = base_sha256
    target = root / "mutations/base-contract-hash-drift.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(mutated, sort_keys=True) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    raise SystemExit(main())
