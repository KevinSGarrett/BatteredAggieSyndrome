from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_official_outcome_crosscheck import (  # noqa: E402
    build_crosscheck,
    canonical_json_bytes,
    sha256_file,
    stable_hash,
)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ncaa_official_outcome_crosscheck_contract.json")
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    rebuild_root = args.rebuild_root.resolve()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract.resolve()
    identity = args.dataset_identity
    manifest_path = data_root / "manifests/ncaa_official_outcome_crosscheck/sha256" / identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity == stable_hash(manifest["identity_core"]))
    check("classification", manifest["classification"] == "CANDIDATE_ONLY_OFFICIAL_POSTGAME_OUTCOME_CROSSCHECK")
    payloads = {payload["name"]: payload for payload in manifest["payloads"]}
    check("payload_set", set(payloads) == {"comparisons.jsonl", "exceptions.jsonl"})
    loaded: dict[str, list[dict[str, object]]] = {}
    for name, payload in payloads.items():
        path = data_root / payload["relative_path"]
        check(f"{name}_exists", path.is_file())
        check(f"{name}_hash", sha256_file(path) == payload["sha256"])
        check(f"{name}_bytes", path.stat().st_size == payload["bytes"])
        loaded[name] = _read_jsonl(path)
        check(f"{name}_rows", len(loaded[name]) == payload["rows"])
    comparisons = loaded["comparisons.jsonl"]
    exceptions = loaded["exceptions.jsonl"]
    check("mapping_population", len(comparisons) == manifest["population"]["mapping_rows"] == 1536)
    check("unique_contests", len({(row["season"], row["ncaa_contest_id"]) for row in comparisons}) == len(comparisons))
    status_counts = dict(sorted(Counter(str(row["status"]) for row in comparisons).items()))
    check("status_partition", status_counts == manifest["population"]["status_counts"])
    check("exceptions_partition", exceptions == [row for row in comparisons if row["status"] != "AGREEMENT"])
    check("comparison_record_hash", hashlib.sha256((data_root / payloads["comparisons.jsonl"]["relative_path"]).read_bytes()).hexdigest() == manifest["identity_core"]["comparison_record_sha256"])
    check("exception_record_hash", hashlib.sha256((data_root / payloads["exceptions.jsonl"]["relative_path"]).read_bytes()).hexdigest() == manifest["identity_core"]["exception_record_sha256"])
    check("agreement_semantics", all(
        row["official_home_points"] == row["canonical_home_points"]
        and row["official_away_points"] == row["canonical_away_points"]
        for row in comparisons if row["status"] == "AGREEMENT"
    ))
    check("conflict_semantics", all(
        (row["official_home_points"], row["official_away_points"])
        != (row["canonical_home_points"], row["canonical_away_points"])
        for row in comparisons if row["status"] == "CONFLICT_FINAL_SCORE"
    ))
    check("missing_semantics", all(
        row["official_home_points"] is None and row["official_away_points"] is None
        for row in comparisons if row["status"] in {"MISSING_OFFICIAL_LINESCORE", "INVALID_OFFICIAL_LINESCORE"}
    ))
    check("no_name_only_promotion", all(row["name_only_promotion"] is False for row in comparisons))
    for field in ("historical_pit_eligible", "training_eligible", "protected_evaluation_eligible", "production_eligible"):
        check(f"{field}_closed", all(row[field] is False for row in comparisons))
    for key, value in manifest["authority"].items():
        check(f"authority_{key}", value is (key == "official_postgame_crosscheck_candidate"))
    check("scientific_nonclaims", all(value is False for value in manifest["nonclaims"].values()))

    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = build_crosscheck(
        data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        contract_path=contract_path,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("byte_identical_identity", rebuilt["dataset_identity"] == identity)
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    for name, payload in payloads.items():
        rebuilt_path = rebuild_root / payload["relative_path"]
        check(f"byte_identical_{name}", rebuilt_path.read_bytes() == (data_root / payload["relative_path"]).read_bytes())

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    mutations = [
        ("authority_expansion", lambda value: value["authority"].__setitem__("training_admission", True)),
        ("rollup_identity_drift", lambda value: value["source_seasons"][0].__setitem__("expected_acquisition_rollup_identity", "0" * 64)),
        ("mapping_method_drift", lambda value: value["identity"].__setitem__("required_mapping_method", "NAME_ONLY")),
    ]
    for name, mutate in mutations:
        changed = json.loads(json.dumps(contract))
        mutate(changed)
        mutation_path = rebuild_root / "mutations" / f"{name}.json"
        mutation_path.parent.mkdir(parents=True, exist_ok=True)
        mutation_path.write_bytes(canonical_json_bytes(changed) + b"\n")
        try:
            build_crosscheck(
                data_root=data_root,
                output_data_root=rebuild_root / "mutation-output" / name,
                repo_root=repo_root,
                contract_path=mutation_path,
                issued_at_utc=manifest["issued_at_utc"],
            )
        except ValueError as exc:
            checks.append({"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__})
        else:
            raise AssertionError(f"mutation did not fail closed: {name}")

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_OFFICIAL_OUTCOME_CROSSCHECK_VALIDATION",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS",
        "check_count": len(checks),
        "mutation_control_count": len(mutations),
        "checks": checks,
    }
    report_core = {key: value for key, value in report.items() if key != "validation_identity"}
    report["validation_identity"] = stable_hash(report_core)
    report_path = data_root / "validation/POST-SUBTASK-197/ncaa-official-outcome-crosscheck" / identity / "runs" / report["validation_identity"] / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_bytes = canonical_json_bytes(report) + b"\n"
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise ValueError("immutable cross-check validation report collision")
    report_path.write_bytes(report_bytes)
    print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": len(mutations), "report_path": str(report_path), "report_sha256": sha256_file(report_path), "validation_identity": report["validation_identity"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
