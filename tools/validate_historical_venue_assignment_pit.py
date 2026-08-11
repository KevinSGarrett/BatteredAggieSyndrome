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

from aggie_analytics.temporal.venue_assignment_pit import (  # noqa: E402
    _load_outcomes_and_targets,
    _load_sources,
    _validate_and_join,
    canonical_json_bytes,
    materialize,
    normalize_numeric_identifier,
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
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "historical_venue_assignment_pit_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_venue_assignment_pit_contract.json").read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity, identity)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-188")
    check("classification", manifest["classification"] == contract["classification"])
    population = manifest["population"]
    acceptance = contract["acceptance"]
    for key, expected in {
        "source_rows": acceptance["expected_source_rows"],
        "accepted_outcome_rows": acceptance["expected_accepted_outcome_rows"],
        "exact_join_rows": acceptance["expected_exact_join_rows"],
        "admitted_rows": acceptance["expected_admitted_rows"],
        "not_present_or_quarantine_rows": acceptance["expected_not_present_rows"],
        "source_distinct_venue_ids": acceptance["expected_source_distinct_venue_ids"],
        "source_distinct_venue_names": acceptance["expected_source_distinct_venue_names"],
        "admitted_distinct_venue_ids": acceptance["expected_admitted_distinct_venue_ids"],
        "admitted_distinct_venue_names": acceptance["expected_admitted_distinct_venue_names"],
    }.items():
        check(f"population_{key}", int(population[key]) == expected, population[key])
    temporal = manifest["temporal_and_identity_validation"]
    check("exact_join_cardinality", temporal["exact_join_rows"] == acceptance["expected_exact_join_rows"])
    check("duplicate_source_keys", temporal["source_duplicate_keys"] == 0)
    check("duplicate_outcome_keys", temporal["outcome_duplicate_keys"] == 0)
    check("schema_variants", temporal["schema_variants"] == acceptance["expected_schema_variants"])
    check("venue_id_name_ambiguities", temporal["venue_id_name_ambiguities"] == 0)
    check("target_game_overlap", temporal["target_game_overlap"] == 0)
    check("minimum_target_cutoff", temporal["minimum_target_cutoff_utc"] == acceptance["earliest_target_cutoff_utc"])
    check("known_at_before_cutoff", temporal["maximum_source_known_at_utc"] < temporal["minimum_target_cutoff_utc"])
    check("not_present_disposition", manifest["quarantine_dispositions"] == {"NOT_PRESENT_VENUE_ID_AND_NAME": 179})
    check("capacity_placeholder_count", manifest["placeholder_normalization"]["nonpositive_capacity_rows"] == acceptance["expected_nonpositive_capacity_rows_in_admitted"])
    check("capacity_placeholder_disposition", manifest["placeholder_normalization"]["analytical_capacity_disposition"] == "NULL_RAW_VALUE_RETAINED")
    authority = manifest["authority"]
    check("record_time_authority", authority["record_time_venue_evidence"] is True)
    for key in (
        "timeless_canonical_venue_catalog", "current_catalog_historical_backfill", "protected_training_admission",
        "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
    ):
        check(f"authority_closed_{key}", authority[key] is False)
    for key, value in manifest["scientific_nonclaims"].items():
        check(f"scientific_nonclaim_{key}", value is False)
    payload_roots = {
        "DEVELOPMENT_ONLY_VENUE_ASSIGNMENTS": data_root / "pit_state" / "historical_known_at" / "sha256" / identity,
        "NOT_PRESENT_AND_PARTIAL_VENUE_EVIDENCE": data_root / "quarantine" / "historical_known_at" / "sha256" / identity,
    }
    original_payloads: dict[str, Path] = {}
    for item in manifest["payloads"]:
        path = payload_roots[item["role"]] / item["name"]
        check(f"payload_exists_{item['role']}", path.is_file())
        check(f"payload_bytes_{item['role']}", path.stat().st_size == item["bytes"], path.stat().st_size)
        check(f"payload_sha256_{item['role']}", sha256_file(path) == item["sha256"], item["sha256"])
        original_payloads[item["role"]] = path
    state = pl.read_parquet(original_payloads["DEVELOPMENT_ONLY_VENUE_ASSIGNMENTS"])
    forbidden = {"home_points", "away_points", "completed_known_by_utc", "label", "target", "outcome"}
    check("target_or_outcome_columns", not (set(state.columns) & forbidden), sorted(set(state.columns) & forbidden))
    capacity_placeholders = state.filter(pl.col("venue_capacity_source_raw") <= 0)
    check("raw_capacity_placeholder_retained", capacity_placeholders.height == acceptance["expected_nonpositive_capacity_rows_in_admitted"])
    check("analytical_capacity_placeholder_is_null", capacity_placeholders["venue_capacity"].null_count() == capacity_placeholders.height)
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize(
        input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("byte_identical_dataset_identity", rebuilt["dataset_identity"] == identity, rebuilt["dataset_identity"])
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    rebuilt_paths = {
        "DEVELOPMENT_ONLY_VENUE_ASSIGNMENTS": Path(rebuilt["state_path"]),
        "NOT_PRESENT_AND_PARTIAL_VENUE_EVIDENCE": Path(rebuilt["quarantine_path"]),
    }
    for role, original in original_payloads.items():
        check(f"byte_identical_{role}", rebuilt_paths[role].read_bytes() == original.read_bytes(), sha256_file(original))

    sources, _ = _load_sources(data_root, contract)
    outcomes, targets, _, _ = _load_outcomes_and_targets(data_root, contract)
    mutation_controls = [
        expect_rejection("fractional_game_id", lambda: normalize_numeric_identifier("312440275.5")),
        expect_rejection("absent_game_id", lambda: normalize_numeric_identifier(None)),
        expect_rejection("duplicate_source_key", lambda: _validate_and_join(sources.vstack(sources.head(1)), outcomes, targets, contract)),
        expect_rejection("unmatched_source_game", lambda: _validate_and_join(
            sources,
            outcomes.with_row_index("_row").with_columns(
                pl.when(pl.col("_row") == 0).then(pl.lit("999999999")).otherwise(pl.col("source_game_id")).alias("source_game_id")
            ).drop("_row"),
            targets, contract,
        )),
        expect_rejection("season_type_conflict", lambda: _validate_and_join(sources.with_columns((sources["source_season_type"] + 1).alias("source_season_type")), outcomes, targets, contract)),
        expect_rejection("outcome_disposition_conflict", lambda: _validate_and_join(
            sources, outcomes.with_columns(pl.lit("UNVERIFIED").alias("reconciliation_disposition")), targets, contract,
        )),
        expect_rejection("target_game_overlap", lambda: _validate_and_join(
            sources, outcomes,
            targets.with_row_index("_row").with_columns(
                pl.when(pl.col("_row") == 0).then(pl.lit(outcomes["canonical_game_id"][0])).otherwise(pl.col("game_id")).alias("game_id")
            ).drop("_row"),
            contract,
        )),
        expect_rejection("post_cutoff_source_known_at", lambda: _validate_and_join(
            sources.with_columns(pl.lit("2026-01-01T00:00:00Z").alias("venue_source_known_at_utc")), outcomes, targets, contract,
        )),
    ]
    checks.extend(mutation_controls)
    report = {
        "schema_version": "1.0.0", "decision_unit": "POST-SUBTASK-188", "jira_key": "BAT-545",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "rebuild_root": str(rebuild_root), "result": "PASS", "check_count": len(checks),
        "mutation_control_count": len(mutation_controls), "checks": checks,
    }
    report_root = data_root / "validation" / "POST-SUBTASK-188"
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "historical_venue_assignment_pit_validation.json"
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": len(mutation_controls), "report_path": str(report_path), "report_sha256": sha256_file(report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
