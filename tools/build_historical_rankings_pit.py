from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

import polars as pl


NORMALIZATION_ID = "acad9e20ba70ab7f371fa210431e4adc66243138154683f9a1b71961e0630220"
NORMALIZATION_MANIFEST_SHA = "5b92f53c17ad9a7a1a7e438bb0abb6466347f413fc9eea0493ad43c4f6a800f2"
RECONCILIATION_ID = "28668e9138f9267a0dbe00c60f7cedd8f1fc37b051e2b3c61dde4fd240fb3570"
RECONCILIATION_MANIFEST_SHA = "e9cafcc251a0888bdf3e2651f859d2db27d47d5fa43912181eac19ed914eaaa0"
REPLAY_ID = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
REPLAY_MANIFEST_SHA = "7383dd69d4165d0e18f89ad690d155305e062d7f81ad9b0087233a90a044a888"
ISSUED_AT_UTC = "2026-08-11T01:00:00Z"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_helpers(repo_root: Path) -> Any:
    module_path = repo_root / "src/aggie_analytics/temporal/rankings_pit.py"
    spec = importlib.util.spec_from_file_location("rankings_pit", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rankings PIT helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_parquet(rows: list[dict[str, Any]], path: Path, sort_columns: list[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(rows, infer_schema_length=None).sort(sort_columns)
    frame.write_parquet(path, compression="zstd", statistics=True)
    return {"name": path.name, "rows": frame.height, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def install_immutable(stage: Path, destination: Path) -> None:
    if destination.exists():
        staged = {item.relative_to(stage): sha256_file(item) for item in stage.rglob("*") if item.is_file()}
        existing = {
            item.relative_to(destination): sha256_file(item)
            for item in destination.rglob("*")
            if item.is_file()
        }
        if staged != existing:
            raise FileExistsError(f"immutable destination differs: {destination}")
        shutil.rmtree(stage)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), str(destination))


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    normalization_manifest = (
        data_root
        / "manifests/historical_rankings/sha256"
        / NORMALIZATION_ID
        / "ap_rankings_normalization.json"
    )
    reconciliation_manifest = (
        data_root
        / "manifests/historical_known_at/sha256"
        / RECONCILIATION_ID
        / "rankings_reconciliation.json"
    )
    replay_manifest = (
        data_root / "manifests/historical_known_at/sha256" / REPLAY_ID / "known_at_replay_manifest.json"
    )
    contract = repo_root / "configs/historical_rankings_pit_contract.json"
    expected = {
        normalization_manifest: NORMALIZATION_MANIFEST_SHA,
        reconciliation_manifest: RECONCILIATION_MANIFEST_SHA,
        replay_manifest: REPLAY_MANIFEST_SHA,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"pinned input missing or drifted: {path}")
    paths = {
        "normalization_root": data_root / "quarantine/historical_rankings/sha256" / NORMALIZATION_ID / "ap_rankings",
        "poll_alignment": data_root
        / "quarantine/historical_known_at/sha256"
        / RECONCILIATION_ID
        / "rankings/poll_alignment_candidates.parquet",
        "historical_games": data_root
        / "pit_state/historical_known_at/sha256"
        / REPLAY_ID
        / "accepted_game_outcomes.parquet",
        "contemporary_targets": data_root
        / "features/historical_known_at/sha256"
        / REPLAY_ID
        / "target_game_cutoffs.parquet",
        "contract": contract,
    }
    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(path)
    return {
        "paths": paths,
        "input_hashes": {
            "normalization_manifest_sha256": NORMALIZATION_MANIFEST_SHA,
            "reconciliation_manifest_sha256": RECONCILIATION_MANIFEST_SHA,
            "replay_manifest_sha256": REPLAY_MANIFEST_SHA,
            "poll_alignment_sha256": sha256_file(paths["poll_alignment"]),
            "historical_games_sha256": sha256_file(paths["historical_games"]),
            "contemporary_targets_sha256": sha256_file(paths["contemporary_targets"]),
            "contract_sha256": sha256_file(contract),
        },
    }


def materialize(inputs: dict[str, Any], helpers: Any) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    paths = inputs["paths"]
    alignment = pl.read_parquet(paths["poll_alignment"]).filter(pl.col("season").is_between(2010, 2025))
    alignment_rows = alignment.sort(["season", "cpa_poll_id"]).to_dicts()
    allowed_polls = {
        int(row["cpa_poll_id"])
        for row in alignment_rows
        if helpers.poll_admission_reason(row) is None
    }
    poll_quarantine = []
    for row in alignment_rows:
        reason = helpers.poll_admission_reason(row)
        if reason:
            item = {
                "schema_version": "1.0.0",
                "classification": helpers.CLASSIFICATION,
                "grain": "POLL",
                "season": int(row["season"]),
                "poll_id": int(row["cpa_poll_id"]),
                "poll_label": str(row["cpa_poll_label"]),
                "poll_date": row.get("cpa_poll_date"),
                "alignment_state": str(row["alignment_state"]),
                "quarantine_reason": reason,
            }
            item["quarantine_id"] = "ap_poll_quarantine_" + helpers.stable_hash(item)[:24]
            poll_quarantine.append(item)

    candidate_frames = [
        pl.read_parquet(paths["normalization_root"] / f"season={season}" / "ap_rankings_candidate_rows.parquet")
        for season in range(2010, 2026)
    ]
    candidates = pl.concat(candidate_frames, how="diagonal_relaxed").sort(
        ["season", "poll_order", "source_row_number"]
    )
    state_rows: list[dict[str, Any]] = []
    identity_quarantine: list[dict[str, Any]] = []
    for row in candidates.filter(pl.col("poll_id").is_in(allowed_polls)).to_dicts():
        reason = helpers.team_row_admission_reason(row)
        if reason:
            item = {
                "schema_version": "1.0.0",
                "classification": helpers.CLASSIFICATION,
                "grain": "POLL_TEAM_ROW",
                "season": int(row["season"]),
                "poll_id": int(row["poll_id"]),
                "source_row_number": int(row["source_row_number"]),
                "school": str(row["school"]),
                "source_record_sha256": str(row["record_sha256"]),
                "quarantine_reason": reason,
            }
            item["quarantine_id"] = "ap_team_quarantine_" + helpers.stable_hash(item)[:24]
            identity_quarantine.append(item)
        else:
            state_rows.append(helpers.build_state_row(row))

    historical = pl.read_parquet(paths["historical_games"]).select(
        [
            pl.col("canonical_game_id").alias("game_id"),
            "season",
            pl.col("season_type").cast(pl.String),
            pl.col("game_start_utc").alias("start_utc"),
            "home_team_id",
            "away_team_id",
        ]
    )
    contemporary = pl.read_parquet(paths["contemporary_targets"]).select(
        ["game_id", "season", "season_type", "start_utc", "home_team_id", "away_team_id"]
    )
    games_frame = pl.concat([historical, contemporary], how="vertical_relaxed").unique(
        subset=["game_id"], keep="none"
    ).sort(["start_utc", "game_id"])
    if games_frame.height != historical.height + contemporary.height:
        raise ValueError("duplicate target game identity across historical and contemporary inputs")
    games = games_frame.to_dicts()
    target_rows = []
    for row in games:
        item = dict(row)
        item.update(
            {
                "schema_version": "1.0.0",
                "classification": helpers.CLASSIFICATION,
                "cutoff_utc": helpers.format_utc(helpers.parse_utc(str(row["start_utc"])) - helpers.timedelta(hours=24)),
                "cutoff_lead_hours": 24,
            }
        )
        target_rows.append(item)
    feature_rows = helpers.build_feature_rows(games, state_rows)
    quarantine = sorted(
        poll_quarantine + identity_quarantine,
        key=lambda row: (int(row["season"]), int(row["poll_id"]), str(row["grain"]), str(row["quarantine_id"])),
    )
    stats = {
        "source_seasons": [2010, 2025],
        "candidate_rows": candidates.height,
        "aligned_polls": alignment.height,
        "admitted_polls": len(allowed_polls),
        "admitted_state_rows": len(state_rows),
        "admitted_canonical_teams": len({row["canonical_team_id"] for row in state_rows}),
        "target_games": len(target_rows),
        "feature_rows": len(feature_rows),
        "games_with_eligible_poll": len({row["target_game_id"] for row in feature_rows if row["poll_available"]}),
        "feature_rows_with_source_team": sum(bool(row["team_listed_in_poll"]) for row in feature_rows),
        "feature_rows_with_numeric_rank": sum(row["rank"] is not None for row in feature_rows),
        "poll_quarantine_records": len(poll_quarantine),
        "identity_quarantine_records": len(identity_quarantine),
        "quarantine_reasons": dict(Counter(row["quarantine_reason"] for row in quarantine)),
    }
    return state_rows, target_rows, feature_rows, quarantine, stats


def execute(repo_root: Path, input_root: Path, output_root: Path) -> dict[str, Any]:
    helpers = load_helpers(repo_root)
    inputs = load_inputs(repo_root, input_root)
    state_rows, target_rows, feature_rows, quarantine_rows, stats = materialize(inputs, helpers)
    stage = output_root / "runtime/POST-SUBTASK-170/rankings-pit-stage"
    if stage.exists():
        shutil.rmtree(stage)
    state_info = write_parquet(state_rows, stage / "state/rankings_pit_state.parquet", ["season", "poll_id", "canonical_team_id"])
    target_info = write_parquet(target_rows, stage / "features/target_game_cutoffs.parquet", ["start_utc", "game_id"])
    feature_info = write_parquet(feature_rows, stage / "features/rankings_pit_features.parquet", ["start_utc", "target_game_id", "team_side"])
    quarantine_info = write_parquet(quarantine_rows, stage / "quarantine/rankings_pit_quarantine.parquet", ["season", "poll_id", "grain", "quarantine_id"])
    code_hashes = {
        "module_sha256": sha256_file(repo_root / "src/aggie_analytics/temporal/rankings_pit.py"),
        "runner_sha256": sha256_file(repo_root / "tools/build_historical_rankings_pit.py"),
        "validator_sha256": sha256_file(repo_root / "tools/validate_historical_rankings_pit.py"),
    }
    state_identity = helpers.stable_hash({"kind": "state", "payload": state_info, "policy": helpers.POLICY_VERSION})
    feature_identity = helpers.stable_hash({"kind": "features", "targets": target_info, "payload": feature_info, "policy": helpers.POLICY_VERSION})
    quarantine_identity = helpers.stable_hash({"kind": "quarantine", "payload": quarantine_info, "policy": helpers.POLICY_VERSION})
    run_identity = helpers.stable_hash(
        {
            "schema_version": "1.0.0",
            "inputs": inputs["input_hashes"],
            "code": code_hashes,
            "policy": helpers.POLICY_VERSION,
            "state_identity": state_identity,
            "feature_identity": feature_identity,
            "quarantine_identity": quarantine_identity,
        }
    )
    locations = {
        "state": f"pit_state/historical_rankings/sha256/{state_identity}",
        "features": f"features/historical_rankings/sha256/{feature_identity}",
        "quarantine": f"quarantine/historical_rankings_pit/sha256/{quarantine_identity}",
        "manifest": f"manifests/historical_rankings_pit/sha256/{run_identity}/rankings_pit_manifest.json",
    }
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_AP_RANKINGS_PIT_ADMISSION",
        "classification": helpers.CLASSIFICATION,
        "decision_unit": "POST-SUBTASK-170",
        "issued_at_utc": ISSUED_AT_UTC,
        "run_identity": run_identity,
        "state_identity": state_identity,
        "feature_identity": feature_identity,
        "quarantine_identity": quarantine_identity,
        "input_identities": {
            "normalization": NORMALIZATION_ID,
            "reconciliation": RECONCILIATION_ID,
            "historical_replay": REPLAY_ID,
        },
        "input_hashes": inputs["input_hashes"],
        "code_hashes": code_hashes,
        "temporal_policy": {
            "version": helpers.POLICY_VERSION,
            "source_precision": "DATE_ONLY",
            "publication_timestamp_claimed": False,
            "publication_interval": "[poll_date-1dT00:00:00Z, poll_date+2dT00:00:00Z)",
            "first_eligible_at": "POLL_DATE_PLUS_TWO_DAYS_UTC_CONSERVATIVE_UPPER_BOUND",
            "target_cutoff_lead_hours": 24,
        },
        "payloads": {
            "state": state_info,
            "targets": target_info,
            "features": feature_info,
            "quarantine": quarantine_info,
        },
        "population": stats,
        "external_locations": locations,
        "eligibility": {
            "canonical_team_identity": "ADMITTED_EXACT_VERIFIED_ONLY",
            "pit_state": "ADMITTED_EXACT_DATED_WEEKLY_POLL_ONLY",
            "development_and_preliminary_feature_use": True,
            "protected_evaluation": False,
            "production_promotion": False,
        },
        "negative_findings": [
            "Preseason and final polls remain excluded because their source headings do not carry an explicit date.",
            "Two 2020 high-coverage polls with conflicts and one low-agreement 2020 poll remain quarantined.",
            "Unresolved or non-exact team identities remain quarantined and never receive a name-only merge.",
            "A team absent from the latest eligible source poll receives a null numeric rank and explicit missingness state.",
            "No exact publication timestamp is inferred from the archive date heading.",
        ],
        "protected_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "champion_promoted": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_claimed": False,
        },
    }
    manifest_stage = stage / "manifest/rankings_pit_manifest.json"
    manifest_stage.parent.mkdir(parents=True, exist_ok=True)
    manifest_stage.write_bytes(helpers.canonical_json(manifest) + b"\n")
    manifest_sha = sha256_file(manifest_stage)
    install_immutable(stage / "state", output_root / locations["state"])
    install_immutable(stage / "features", output_root / locations["features"])
    install_immutable(stage / "quarantine", output_root / locations["quarantine"])
    install_immutable(stage / "manifest", (output_root / locations["manifest"]).parent)
    if stage.exists():
        shutil.rmtree(stage)
    return {
        "result": "PASS",
        "run_identity": run_identity,
        "state_identity": state_identity,
        "feature_identity": feature_identity,
        "quarantine_identity": quarantine_identity,
        "manifest_sha256": manifest_sha,
        "population": stats,
        "locations": locations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input-data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path)
    args = parser.parse_args()
    result = execute(args.repo_root.resolve(), args.input_data_root.resolve(), args.output_data_root.resolve())
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.summary_path:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
