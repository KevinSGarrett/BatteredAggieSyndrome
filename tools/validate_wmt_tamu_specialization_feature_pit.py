from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.wmt_tamu_specialization_feature_pit import (  # noqa: E402
    _assert_output_boundary,
    _record_is_tamu,
    canonical_json_bytes,
    materialize,
    parse_utc,
    remove_rebuild_root,
    sha256_file,
)


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
    manifest_path = (
        data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / identity
        / "wmt_tamu_specialization_feature_pit_manifest.json"
    )
    state_root = data_root / "pit_state" / "historical_known_at" / "sha256" / identity
    feature_root = data_root / "features" / "historical_known_at" / "sha256" / identity
    record_path = state_root / "wmt_tamu_feature_source_records.parquet"
    source_game_path = state_root / "wmt_tamu_source_game_features.parquet"
    target_path = feature_root / "wmt_tamu_target_cutoff_features.parquet"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(
        (repo_root / "configs" / "wmt_tamu_specialization_feature_pit_contract.json").read_text(encoding="utf-8")
    )
    records = pl.read_parquet(record_path)
    source_games = pl.read_parquet(source_game_path)
    targets = pl.read_parquet(target_path)
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(records.height == manifest["population"]["attributed_records"], "record_rows", checks)
    check(source_games.height == contract["acceptance"]["expected_identity_games"], "source_game_rows", checks)
    check(targets.height == contract["acceptance"]["expected_tamu_target_games"], "target_rows", checks)
    check(records.select(pl.struct(["domain", "record_id"]).n_unique()).item() == records.height, "unique_domain_record", checks)
    check(source_games["wmt_game_id"].n_unique() == source_games.height, "unique_source_game", checks)
    check(targets["game_id"].n_unique() == targets.height, "unique_target_game", checks)
    check(
        dict(sorted(Counter(records["domain"].to_list()).items()))
        == dict(sorted(contract["acceptance"]["expected_attributed_records_by_domain"].items())),
        "exact_attributed_domain_population",
        checks,
    )
    check(set(records["domain"].unique().to_list()) == set(contract["acceptance"]["required_feature_domains"]), "required_domains", checks)
    check(records["provider_known_at_utc"].null_count() == 0, "known_at_nonnull", checks)
    check(records["effective_at_utc"].null_count() == 0, "effective_nonnull", checks)
    check(records["available_at_utc"].null_count() == 0, "availability_nonnull", checks)
    check(not records["protected_eligible"].any(), "record_protected_closed", checks)
    check(not source_games["protected_eligible"].any(), "source_game_protected_closed", checks)
    check(not targets["protected_eligible"].any(), "target_protected_closed", checks)
    check(not source_games["name_only_merge"].any(), "name_only_merge_absent", checks)
    check(not source_games["score_assisted_merge"].any(), "score_assisted_merge_absent", checks)
    check(source_games["wmt_tamu_school_id"].unique().to_list() == [contract["source_contract"]["wmt_tamu_school_id"]], "official_school_identity", checks)
    check(source_games["canonical_tamu_team_id"].unique().to_list() == [contract["source_contract"]["canonical_tamu_team_id"]], "canonical_tamu_identity", checks)
    check(targets["canonical_tamu_team_id"].unique().to_list() == [contract["source_contract"]["canonical_tamu_team_id"]], "target_canonical_tamu_identity", checks)
    check(sorted(targets["season"].unique().to_list()) == contract["source_contract"]["target_seasons"], "target_seasons", checks)
    check(not targets["cold_start"].any(), "target_cold_start_absent", checks)
    check(targets["source_record_count"].is_sorted(), "target_record_coverage_monotonic", checks)
    check(
        all(
            row["latest_source_available_at_utc"] is None
            or parse_utc(row["latest_source_available_at_utc"]) < parse_utc(row["cutoff_utc"])
            for row in targets.iter_rows(named=True)
        ),
        "strict_available_at_before_cutoff",
        checks,
    )
    check(
        all(
            row["latest_source_effective_at_utc"] is None
            or parse_utc(row["latest_source_effective_at_utc"]) < parse_utc(row["cutoff_utc"])
            for row in targets.iter_rows(named=True)
        ),
        "strict_effective_at_before_cutoff",
        checks,
    )
    _assert_output_boundary((records, source_games, targets), contract)
    checks.append("forbidden_output_columns_absent")
    pit_path = (
        data_root
        / "pit_state"
        / "historical_known_at"
        / "sha256"
        / contract["source_contract"]["provider_record_pit_identity"]
        / "wmt_provider_timestamp_records.parquet"
    )
    provider_records = pl.read_parquet(pit_path).select("domain", "record_id", "source_record_sha256")
    membership = records.select("domain", "record_id", "source_record_sha256").join(
        provider_records,
        on=["domain", "record_id", "source_record_sha256"],
        how="inner",
    )
    check(membership.height == records.height, "exact_provider_record_pit_membership", checks)
    for payload, path in zip(manifest["payloads"], [record_path, source_game_path, target_path], strict=True):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
        check(payload["rows"] == pl.read_parquet(path).height, f"payload_rows_{payload['role']}", checks)

    mutations: list[str] = []
    mapping = {"wmt_tamu_competitor_id": "11", "wmt_tamu_team_id": "22"}
    if not _record_is_tamu("actions", {"competitor_id": "12"}, mapping):
        mutations.append("WRONG_COMPETITOR_ID_REJECTED")
    if not _record_is_tamu("drives", {"competitor_id": "11", "team_id": "23"}, mapping):
        mutations.append("DRIVE_TEAM_ID_MISMATCH_REJECTED")
    if not _record_is_tamu("players", {"team_id": "23"}, mapping):
        mutations.append("PLAYER_TEAM_ID_MISMATCH_REJECTED")
    try:
        _assert_output_boundary((pl.DataFrame({"winner": [True]}),), contract)
    except ValueError:
        mutations.append("FORBIDDEN_WINNER_FIELD_REJECTED")
    else:
        raise AssertionError("FORBIDDEN_WINNER_FIELD_REJECTED")

    rebuild_root = (
        args.rebuild_root
        or data_root / "validation" / "POST-SUBTASK-179" / "deterministic-rebuild"
    ).resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    check(manifest_path.read_bytes() == Path(rebuilt["manifest_path"]).read_bytes(), "manifest_byte_identical", checks)
    check(record_path.read_bytes() == Path(rebuilt["record_path"]).read_bytes(), "record_lineage_byte_identical", checks)
    check(source_game_path.read_bytes() == Path(rebuilt["source_game_path"]).read_bytes(), "source_game_byte_identical", checks)
    check(target_path.read_bytes() == Path(rebuilt["target_path"]).read_bytes(), "target_feature_byte_identical", checks)
    remove_rebuild_root(rebuild_root)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "WMT_TAMU_SPECIALIZATION_FEATURE_PIT_VALIDATION",
        "decision_unit": "POST-SUBTASK-179",
        "jira_key": "BAT-536",
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
    report_path = data_root / "validation" / "POST-SUBTASK-179" / "wmt_tamu_specialization_feature_pit_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
