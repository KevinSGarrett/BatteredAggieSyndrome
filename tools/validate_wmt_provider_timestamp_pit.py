from __future__ import annotations

import argparse
import bisect
import json
import sys
from pathlib import Path

import polars as pl

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.wmt_provider_timestamp_pit import (  # noqa: E402
    canonical_json_bytes,
    materialize,
    nested_record,
    parse_utc,
    provider_known_at,
    remove_rebuild_root,
    sha256_file,
)


FORBIDDEN_COLUMNS = {"home_score", "away_score", "winner", "margin", "label", "target_value", "game_outcome"}


def check(condition: bool, name: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rebuild-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    repo_root = args.repo_root.resolve()
    identity = args.dataset_identity
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "wmt_provider_timestamp_pit_manifest.json"
    state_path = data_root / "pit_state" / "historical_known_at" / "sha256" / identity / "wmt_provider_timestamp_records.parquet"
    feature_path = data_root / "features" / "historical_known_at" / "sha256" / identity / "target_cutoff_wmt_domain_features.parquet"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "wmt_provider_timestamp_pit_contract.json").read_text(encoding="utf-8"))
    records = pl.read_parquet(state_path)
    coverage = pl.read_parquet(feature_path)
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(records.height == manifest["population"]["admitted_records"], "record_rows", checks)
    check(coverage.height == manifest["population"]["target_cutoff_rows"], "coverage_rows", checks)
    check(records.select(pl.struct(["domain", "record_id"]).n_unique()).item() == records.height, "unique_domain_record", checks)
    check(set(records["domain"].unique().to_list()) == set(contract["acceptance"]["required_domains"]), "required_domains", checks)
    check(records["provider_known_at_utc"].null_count() == 0, "known_at_nonnull", checks)
    check(records["effective_at_utc"].null_count() == 0, "effective_nonnull", checks)
    check(all(parse_utc(row["provider_known_at_utc"]) <= parse_utc(row["available_at_utc"]) for row in records.iter_rows(named=True)), "known_at_not_after_availability", checks)
    check(all(parse_utc(row["effective_at_utc"]) <= parse_utc(row["available_at_utc"]) for row in records.iter_rows(named=True)), "effective_not_after_availability", checks)
    check(not records["protected_eligible"].any(), "record_protected_closed", checks)
    check(not coverage["protected_eligible"].any(), "coverage_protected_closed", checks)
    check(coverage["coverage_diagnostic_only"].all(), "coverage_diagnostic_only", checks)
    check(not (FORBIDDEN_COLUMNS & set(records.columns)), "no_record_target_columns", checks)
    check(not (FORBIDDEN_COLUMNS & set(coverage.columns)), "no_coverage_target_columns", checks)
    check(sorted(coverage["season"].unique().to_list()) == contract["source_contract"]["target_seasons"], "target_seasons", checks)
    count_columns = [name for name in coverage.columns if name.endswith("_record_count")]
    check(all(coverage[name].is_sorted() for name in count_columns), "coverage_monotonic_by_sorted_cutoff", checks)
    sorted_availability = sorted(parse_utc(value) for value in records["available_at_utc"].to_list())
    coverage_exact = True
    for row in coverage.iter_rows(named=True):
        cutoff = parse_utc(row["cutoff_utc"])
        expected = bisect.bisect_left(sorted_availability, cutoff)
        coverage_exact = coverage_exact and row["total_record_count"] == expected
    check(coverage_exact, "coverage_exact_for_every_target_cutoff", checks)
    for payload, path in zip(manifest["payloads"], [state_path, feature_path], strict=True):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
    # Explicit mutation controls exercise the exact timestamp authority boundary.
    mutations: list[str] = []
    for candidate, name in [({}, "MISSING_PROVIDER_TIMESTAMP_REJECTED"), ({"created_at": "not-a-time"}, "INVALID_PROVIDER_TIMESTAMP_REJECTED"), ({"created_at": "2021-01-01T00:00:00"}, "TIMEZONELESS_PROVIDER_TIMESTAMP_REJECTED")]:
        try:
            provider_known_at(candidate, ["created_at", "updated_at"])
        except ValueError:
            mutations.append(name)
        else:
            raise AssertionError(name)
    check(nested_record({"action": {"created_at": "2021-01-01T00:00:00Z"}}, ["action"])["created_at"].endswith("Z"), "nested_exact_record_selected", checks)
    check(nested_record({"action": None}, ["action"]) == {}, "missing_nested_record_isolated", checks)
    rebuild_root = (args.rebuild_root or data_root / "validation" / "POST-SUBTASK-178" / "deterministic-rebuild").resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"])
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    check(manifest_path.read_bytes() == Path(rebuilt["manifest_path"]).read_bytes(), "manifest_byte_identical", checks)
    check(state_path.read_bytes() == Path(rebuilt["state_path"]).read_bytes(), "state_byte_identical", checks)
    check(feature_path.read_bytes() == Path(rebuilt["feature_path"]).read_bytes(), "coverage_byte_identical", checks)
    remove_rebuild_root(rebuild_root)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "WMT_PROVIDER_TIMESTAMP_PIT_VALIDATION",
        "decision_unit": "POST-SUBTASK-178",
        "jira_key": "BAT-535",
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "mutation_controls_passed": len(mutations),
        "mutation_controls": mutations,
        "byte_identical_rebuild": True,
        "rebuild_root_removed": not rebuild_root.exists(),
        "authority": contract["authority"],
        "negative_findings": manifest["negative_findings"],
    }
    report_path = data_root / "validation" / "POST-SUBTASK-178" / "wmt_provider_timestamp_pit_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
