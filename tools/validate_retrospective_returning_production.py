from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.features.returning_production import (  # noqa: E402
    BOUNDED_COUNT_PAIRS,
    PAIR_FIELDS,
    materialize,
    sha256_file,
)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("validation requires the optional data-engineering environment") from exc
    return polars


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = json.loads(
        (repo_root / "configs/retrospective_returning_production_contract.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_path = (
        data_root
        / "manifests"
        / "returning_production_research"
        / "sha256"
        / args.dataset_identity
        / "run_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append(
            {"check": name, "result": "PASS" if condition else "FAIL", "detail": detail}
        )

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("decision_unit", manifest["decision_unit"] == contract["decision_unit"])
    check("authority", manifest["authority"] == contract["authority"])
    check("protected_nonclaims", not any(manifest["protected_nonclaims"].values()))
    check("shared_snap_unsupported", "shared_snap_continuity" in manifest["unsupported_fields"])
    pl = _polars()
    frames: dict[str, Any] = {}
    for payload in manifest["payloads"]:
        path = data_root / payload["path"]
        check(f"payload_exists:{payload['role']}", path.is_file())
        if path.is_file():
            frame = pl.read_parquet(path)
            frames[payload["role"]] = frame
            check(f"payload_hash:{payload['role']}", sha256_file(path) == payload["sha256"])
            check(f"payload_rows:{payload['role']}", frame.height == payload["rows"])
    features = frames.get("TEAM_TRANSITION_FEATURE_RESEARCH", pl.DataFrame())
    components = frames.get("RETURNING_PRODUCTION_COMPONENTS", pl.DataFrame())
    coverage = frames.get("TRANSITION_COVERAGE", pl.DataFrame())
    if features.height:
        check("feature_rows", features.height == manifest["population"]["feature_rows"])
        check(
            "feature_natural_key_unique",
            features.select("target_season", "canonical_team_id").unique().height
            == features.height,
        )
        check("transition_seasons", set(features["target_season"]) == set(range(2015, 2023)))
        check("classification_feature", set(features["classification"]) == {contract["classification"]})
        check("protected_feature_false", features.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
        check("target_feature_false", features.filter(pl.col("target_game_feature_eligible") != False).height == 0)  # noqa: E712
        check("original_pit_false", features.filter(pl.col("original_transition_time_pit_eligible") != False).height == 0)  # noqa: E712
        bounded_share_columns = [
            "roster_retention_rate",
            "roster_arrival_rate",
            "roster_jaccard",
            *(PAIR_FIELDS[pair] for pair in sorted(BOUNDED_COUNT_PAIRS)),
        ]
        invalid = sum(
            features.filter(
                pl.col(name).is_not_null()
                & ((pl.col(name) < 0.0) | (pl.col(name) > 1.0))
            ).height
            for name in bounded_share_columns
        )
        check("bounded_share_bounds", invalid == 0, invalid)
        unsupported = set(contract["feature_contract"]["unsupported_fields"])
        check("unsupported_columns_absent", not unsupported.intersection(features.columns))
    if components.height:
        check("component_rows", components.height == manifest["population"]["component_rows"])
        check("component_identity_unique", components["component_identity"].n_unique() == components.height)
        check("component_denominators_positive", components.filter(pl.col("prior_total") <= 0).height == 0)
        bounded_components = components.filter(
            pl.col("ratio_semantics") == "BOUNDED_NONNEGATIVE_COUNT_SHARE"
        )
        check(
            "bounded_component_share_bounds",
            bounded_components.filter(
                (pl.col("returning_share") < 0.0)
                | (pl.col("returning_share") > 1.0)
            ).height
            == 0,
        )
        signed_anomalies = components.filter(
            (pl.col("ratio_semantics") == "SIGNED_EVENT_SUM_RATIO")
            & pl.col("outside_unit_interval")
        ).height
        check(
            "signed_yardage_ratio_diagnostic",
            signed_anomalies
            == contract["acceptance"][
                "expected_signed_yardage_ratios_outside_zero_one"
            ]
            == manifest["population"][
                "signed_yardage_ratios_outside_zero_one"
            ],
            signed_anomalies,
        )
        pairs = {
            (str(row["category"]), str(row["stat_type"]))
            for row in components.select("category", "stat_type").unique().to_dicts()
        }
        check("category_stat_pairs", pairs == set(PAIR_FIELDS))
    if coverage.height:
        check("coverage_rows", coverage.height == 8)
        check("coverage_floor", coverage["common_support_teams"].min() >= 121)
        check(
            "coverage_signed_diagnostic",
            coverage["signed_ratios_outside_unit_interval"].sum()
            == contract["acceptance"][
                "expected_signed_yardage_ratios_outside_zero_one"
            ],
        )
        partial = coverage.filter(pl.col("partial_prior_metric_season"))
        check(
            "partial_2020_preserved",
            partial.height == 1 and partial.row(0, named=True)["prior_season"] == 2020,
        )

    validation_root = data_root / "validation"
    validation_root.mkdir(parents=True, exist_ok=True)
    rebuild_root = Path(
        tempfile.mkdtemp(
            prefix="bat415-returning-production-rebuild-",
            dir=validation_root,
        )
    )
    deterministic_files = 0
    try:
        rebuilt = materialize(
            input_data_root=data_root,
            output_data_root=rebuild_root,
            repo_root=repo_root,
            issued_at_utc=manifest["issued_at_utc"],
        )
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        relative_paths = [payload["path"] for payload in manifest["payloads"]]
        relative_paths.append(
            f"manifests/returning_production_research/sha256/{args.dataset_identity}/run_manifest.json"
        )
        for relative in relative_paths:
            original = data_root / relative
            rebuilt_path = rebuild_root / relative
            deterministic_files += 1
            check(
                f"byte_identical:{relative}",
                rebuilt_path.is_file()
                and sha256_file(original) == sha256_file(rebuilt_path),
            )
    finally:
        shutil.rmtree(rebuild_root, ignore_errors=False)

    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "RETROSPECTIVE_RETURNING_PRODUCTION_VALIDATION",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "dataset_identity": args.dataset_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "deterministic_files_compared": deterministic_files,
        "checks": checks,
        "failures": failures,
        "cleanup": {"rebuild_removed": not rebuild_root.exists()},
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks_passed": report["checks_passed"],
                "checks_failed": report["checks_failed"],
                "report_sha256": sha256_file(args.report_path),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
