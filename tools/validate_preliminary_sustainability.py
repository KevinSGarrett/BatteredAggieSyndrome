from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.features.sustainability import materialize  # noqa: E402
from aggie_analytics.temporal.play_drive_pit import (  # noqa: E402
    canonical_json_bytes,
    parse_utc,
    sha256_file,
)


def _check(
    checks: list[dict[str, object]], name: str, passed: bool, detail: object
) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def _safe_remove_validation_rebuild(path: Path, validation_root: Path) -> None:
    resolved = path.resolve()
    allowed = validation_root.resolve()
    if allowed not in resolved.parents or "rebuild" not in resolved.name:
        raise ValueError(f"refusing to clean unverified rebuild path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _all_between(frame, columns: list[str], low: float, high: float) -> bool:
    import polars as pl

    return all(
        frame.filter(
            pl.col(column).is_not_null()
            & ((pl.col(column) < low) | (pl.col(column) > high))
        ).is_empty()
        for column in columns
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"
            )
        ),
    )
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--validated-at-utc", required=True)
    args = parser.parse_args()
    parse_utc(args.validated_at_utc)
    data_root = args.data_root.resolve()
    manifest_path = (
        data_root
        / "manifests"
        / "preliminary_sustainability"
        / "sha256"
        / args.dataset_identity
        / "run_manifest.json"
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    import polars as pl

    feature_path = (
        data_root
        / "features"
        / "preliminary_sustainability"
        / "sha256"
        / args.dataset_identity
        / "target_game_team_sustainability_features.parquet"
    )
    profile_path = (
        data_root
        / "pit_state"
        / "preliminary_sustainability"
        / "sha256"
        / args.dataset_identity
        / "team_sustainability_profiles.parquet"
    )
    features = pl.read_parquet(feature_path)
    profiles = pl.read_parquet(profile_path)
    checks: list[dict[str, object]] = []
    population = manifest["population"]
    _check(
        checks,
        "identity_matches_path",
        manifest["dataset_identity"] == args.dataset_identity,
        manifest["dataset_identity"],
    )
    _check(
        checks,
        "classification_is_preliminary_unprotected",
        manifest["classification"] == "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE",
        manifest["classification"],
    )
    _check(
        checks,
        "source_game_population",
        population["source_games"] == 10593,
        population["source_games"],
    )
    _check(
        checks,
        "source_games_unique",
        population["source_team_game_rows"] == population["source_games"] * 2,
        population["source_team_game_rows"],
    )
    _check(
        checks,
        "two_rows_per_target_game",
        features.height == population["target_games"] * 2,
        features.height,
    )
    _check(
        checks,
        "unique_target_game_team_rows",
        features.select(pl.struct("game_id", "team_id").n_unique()).item()
        == features.height,
        features.height,
    )
    _check(
        checks,
        "target_game_overlap_absent",
        population["target_game_overlap"] == 0,
        population["target_game_overlap"],
    )
    temporal = manifest["temporal_validation"]
    _check(
        checks,
        "source_known_at_precedes_targets",
        parse_utc(temporal["maximum_source_known_at_utc"])
        < parse_utc(temporal["minimum_target_cutoff_utc"]),
        temporal,
    )
    _check(
        checks,
        "source_seasons_precede_targets",
        temporal["source_season_precedes_target_season"],
        temporal,
    )
    _check(
        checks,
        "all_rows_unprotected",
        features.filter(pl.col("protected_eligible") != False).is_empty(),  # noqa: E712
        features["protected_eligible"].unique().to_list(),
    )
    _check(
        checks,
        "all_rows_retrospective_not_original_pit",
        features.filter(pl.col("historical_original_pit_eligible") != False).is_empty(),  # noqa: E712
        features["historical_original_pit_eligible"].unique().to_list(),
    )
    forbidden = {
        "home_win",
        "home_points",
        "away_points",
        "margin",
        "winner",
        "outcome",
        "target_score",
    }
    _check(
        checks,
        "target_and_future_outcome_fields_absent",
        not (forbidden & set(features.columns)),
        sorted(forbidden & set(features.columns)),
    )
    unsupported = set(manifest["unsupported_fields"])
    _check(
        checks,
        "unsupported_metric_columns_absent",
        not (unsupported & set(features.columns)),
        sorted(unsupported & set(features.columns)),
    )
    residual_columns = [
        name
        for name in features.columns
        if name.endswith("_minus_score_share")
        or name.endswith("_minus_overall")
        or name.endswith("_tail_imbalance")
    ]
    rate_columns = [
        name
        for name in features.columns
        if (name.endswith("_share") or name.endswith("_rate"))
        and name not in residual_columns
    ]
    _check(
        checks,
        "rates_bounded",
        _all_between(features, rate_columns, 0.0, 1.0),
        rate_columns,
    )
    _check(
        checks,
        "residuals_bounded",
        _all_between(features, residual_columns, -1.0, 1.0),
        residual_columns,
    )
    _check(
        checks,
        "close_residual_missingness_semantic",
        profiles.filter(
            (pl.col("all_close_game_share") == 0)
            & pl.col("all_close_win_share_minus_overall").is_not_null()
        ).is_empty(),
        manifest["feature_missingness"]["all_close_win_share_minus_overall"],
    )
    _check(
        checks,
        "sparse_team_season_finding_preserved",
        population["minimum_team_season_games"] == 1,
        {
            "min": population["minimum_team_season_games"],
            "median": population["median_team_season_games"],
            "max": population["maximum_team_season_games"],
        },
    )
    _check(
        checks,
        "pandemic_composition_exposed",
        "pandemic_2020_game_share" in features.columns,
        "pandemic_2020_game_share",
    )
    _check(
        checks,
        "no_protected_or_promotion_authority",
        not any(
            manifest["authority"][name]
            for name in [
                "protected_training_admission",
                "protected_evaluation_admission",
                "champion_or_production_promotion",
                "forecast_publication_authority",
                "bas_or_aggie_excess_authority",
            ]
        ),
        manifest["authority"],
    )
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["path"]
        _check(
            checks,
            f"payload_exists:{payload['role']}",
            payload_path.is_file(),
            str(payload_path),
        )
        _check(
            checks,
            f"payload_hash:{payload['role']}",
            payload_path.is_file() and sha256_file(payload_path) == payload["sha256"],
            payload["sha256"],
        )

    validation_root = data_root / "validation" / "POST-SUBTASK-055"
    rebuild_root = (
        validation_root / f"sustainability-rebuild-{args.dataset_identity[:12]}"
    )
    _safe_remove_validation_rebuild(rebuild_root, validation_root)
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=ROOT,
        issued_at_utc=manifest["issued_at_utc"],
    )
    _check(
        checks,
        "independent_rebuild_identity",
        rebuilt["dataset_identity"] == args.dataset_identity,
        rebuilt["dataset_identity"],
    )
    _check(
        checks,
        "independent_rebuild_manifest_byte_identical",
        sha256_file(Path(rebuilt["manifest_path"])) == sha256_file(manifest_path),
        sha256_file(Path(rebuilt["manifest_path"])),
    )
    rebuilt_payloads = {
        item["role"]: item["sha256"] for item in rebuilt["manifest"]["payloads"]
    }
    original_payloads = {item["role"]: item["sha256"] for item in manifest["payloads"]}
    _check(
        checks,
        "independent_rebuild_payloads_byte_identical",
        rebuilt_payloads == original_payloads,
        rebuilt_payloads,
    )
    _safe_remove_validation_rebuild(rebuild_root, validation_root)
    _check(
        checks,
        "reconstructible_rebuild_cleaned",
        not rebuild_root.exists(),
        str(rebuild_root),
    )

    report = {
        "schema_version": "1.0.0",
        "validation_id": f"BAT405-SUSTAINABILITY-{args.dataset_identity[:16]}",
        "validated_at_utc": args.validated_at_utc,
        "dataset_identity": args.dataset_identity,
        "classification": manifest["classification"],
        "checks": checks,
        "summary": {
            "passed": sum(1 for item in checks if item["passed"]),
            "failed": sum(1 for item in checks if not item["passed"]),
            "total": len(checks),
        },
        "disposition": "PASS_PRELIMINARY_CANDIDATE_ONLY"
        if all(item["passed"] for item in checks)
        else "FAIL_QUARANTINE",
        "scientific_nonclaims": manifest["scientific_nonclaims"],
    }
    validation_root.mkdir(parents=True, exist_ok=True)
    report_path = validation_root / "sustainability_candidate_validation.json"
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "report_sha256": sha256_file(report_path),
                "summary": report["summary"],
                "disposition": report["disposition"],
            },
            indent=2,
        )
    )
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
