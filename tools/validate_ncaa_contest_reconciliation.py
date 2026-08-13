from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import reconcile, sha256_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ncaa_contest_reconciliation_contract.json")
    parser.add_argument("--dataset-identity", required=True)
    args = parser.parse_args()

    import polars as pl

    data_root = args.data_root.resolve()
    projected_rebuild_payload = (
        args.rebuild_root.resolve()
        / "canonical/ncaa_contest_reconciliation/sha256"
        / args.dataset_identity
        / "source_schedule_observations.parquet"
    )
    if len(str(projected_rebuild_payload)) >= 240:
        raise ValueError(
            "rebuild path is too long for reliable Windows filesystem behavior; "
            "use a short directory beneath the external validation root"
        )
    manifest_path = data_root / "manifests/ncaa_contest_reconciliation/sha256" / args.dataset_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_root = data_root / "canonical/ncaa_contest_reconciliation/sha256" / args.dataset_identity
    mappings = pl.read_parquet(artifact_root / "contest_mappings.parquet")
    team_mappings = pl.read_parquet(artifact_root / "team_season_mappings.parquet")
    unresolved = pl.read_parquet(artifact_root / "unresolved_contests.parquet")
    observations = pl.read_parquet(artifact_root / "source_schedule_observations.parquet")
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    population = manifest["identity_core"]["population"]
    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == "CANDIDATE_ONLY_DETERMINISTIC_TWO_SIDED_CONTEXT_RECONCILIATION")
    check("complete_partition", mappings.height + unresolved.height == population["discovered_contests"])
    check("mapping_population", mappings.height == population["reconciled_contests"])
    check("unresolved_population", unresolved.height == population["unresolved_contests"])
    check("observation_population", observations.height == population["scored_schedule_observations"])
    check("team_mapping_population", team_mappings.height == population["reconciled_team_seasons"])
    check("unique_ncaa_contest", mappings["ncaa_contest_id"].n_unique() == mappings.height)
    check("unique_canonical_game", mappings["canonical_game_id"].n_unique() == mappings.height)
    check("two_sided_observations", mappings["source_schedule_observation_count"].min() >= 2)
    check("two_distinct_source_pages", mappings["source_team_season_page_count"].min() >= 2)
    check("mapping_method", mappings["mapping_method"].unique().to_list() == ["TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT"])
    check("no_name_only_promotion", not mappings["name_only_promotion"].any() and not team_mappings["name_only_promotion"].any())
    check("historical_pit_closed", not mappings["historical_pit_eligible"].any())
    check("training_closed", not mappings["training_eligible"].any())
    check("protected_closed", not mappings["protected_eligible"].any())
    check("unresolved_reasons_nonempty", unresolved["reason"].null_count() == 0)
    check("unresolved_candidate_only", unresolved["classification"].unique().to_list() == ["CANDIDATE_ONLY_UNRESOLVED_PRESERVED"])
    check("canonical_registry_write_closed", manifest["authority"]["canonical_registry_write"] is False)
    check("production_closed", manifest["authority"]["production_eligible"] is False)
    for payload in manifest["payloads"]:
        path = artifact_root / payload["name"]
        check(f"payload_hash_{payload['name']}", sha256_file(path) == payload["sha256"])
        check(f"payload_bytes_{payload['name']}", path.stat().st_size == payload["bytes"])

    rebuilt = reconcile(
        input_data_root=data_root,
        output_data_root=args.rebuild_root.resolve(),
        repo_root=args.repo_root.resolve(),
        contract_path=args.contract.resolve(),
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("byte_identical_dataset_identity", rebuilt["dataset_identity"] == args.dataset_identity)
    check("byte_identical_manifest", rebuilt["manifest_sha256"] == sha256_file(manifest_path))
    rebuild_root = args.rebuild_root.resolve() / "canonical/ncaa_contest_reconciliation/sha256" / args.dataset_identity
    for payload in manifest["payloads"]:
        check(f"byte_identical_{payload['name']}", sha256_file(rebuild_root / payload["name"]) == payload["sha256"])

    failed = [row for row in checks if not row["passed"]]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_CONTEST_RECONCILIATION_VALIDATION",
        "dataset_identity": args.dataset_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "checks": checks,
        "check_count": len(checks),
        "failure_count": len(failed),
        "failures": failed,
        "disposition": "PASS" if not failed else "FAIL",
    }
    report_bytes = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()
    report_path = (
        data_root
        / "validation/POST-SUBTASK-197/ncaa-contest-reconciliation"
        / args.dataset_identity
        / "runs"
        / report_sha256
        / "report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise ValueError("immutable NCAA reconciliation validation report collision")
    report_path.write_bytes(report_bytes)
    print(json.dumps({
        "report_path": str(report_path),
        "report_sha256": report_sha256,
        "check_count": len(checks),
        "failure_count": len(failed),
    }, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
