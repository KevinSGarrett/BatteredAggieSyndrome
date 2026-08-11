from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("roster-membership PIT materialization requires the optional data-engineering environment") from exc
    return polars


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def cutoff_utc(start_utc: str, lead_hours: int) -> str:
    return (parse_utc(start_utc) - timedelta(hours=int(lead_hours))).isoformat().replace("+00:00", "Z")


def dataframe_record_sha256(frame: Any) -> str:
    digest = hashlib.sha256()
    for row in frame.iter_rows(named=True):
        digest.update(canonical_json_bytes(row))
        digest.update(b"\n")
    return digest.hexdigest()


def _duplicate_rows(frame: Any, keys: Iterable[str]) -> int:
    return int(frame.group_by(list(keys)).len().filter(_polars().col("len") > 1)["len"].sum() or 0)


def _load_candidates(data_root: Path, contract: dict[str, Any]) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("candidate roster manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"] or manifest.get("domain") != "rosters":
        raise ValueError("candidate roster dataset identity or domain drift")
    if manifest.get("grain") != "PLAYER_TEAM_SEASON_ROSTER_MEMBERSHIP":
        raise ValueError("candidate roster grain drift")
    payloads = sorted(manifest.get("payloads", []), key=lambda item: int(item["season"]))
    if len(payloads) != contract["acceptance"]["expected_source_files"]:
        raise ValueError("candidate roster source-file count drift")
    source_inputs = {int(item["role"].rsplit("_", 1)[-1]): item for item in manifest.get("inputs", []) if str(item.get("role", "")).startswith("VERSIONED_REPOSITORY_ROSTER_")}
    payload_root = data_root / Path(source["candidate_payload_root"])
    required = set(contract["admission"]["admitted_fields"]) | {
        "athlete_id_occurrence", "canonical_membership_player_id", "canonical_membership_resolution_state",
        "team_label_exact_match", "canonical_membership_option_count", "canonical_membership_exact_team_option_count",
        "canonical_membership_ambiguous", "reconciliation_disposition",
    }
    frames: list[Any] = []
    profiles: list[dict[str, Any]] = []
    for item in payloads:
        season = int(item["season"])
        path = payload_root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"candidate roster payload identity drift for season {season}")
        frame = pl.read_parquet(path)
        if frame.height != int(item["rows"]) or set(frame.columns) < required:
            raise ValueError(f"candidate roster population or required-field drift for season {season}")
        if frame["season"].n_unique() != 1 or int(frame["season"][0]) != season:
            raise ValueError(f"candidate roster season drift for season {season}")
        upstream = source_inputs.get(season)
        if not upstream:
            raise ValueError(f"candidate roster source capture missing for season {season}")
        expected_fields = {
            "source_capture_id": upstream["capture_id"], "source_payload_sha256": upstream["payload_sha256"],
            "source_commit_sha": source["source_commit_sha"], "source_known_at_utc": source["source_known_at_utc"],
        }
        for field, expected in expected_fields.items():
            values = frame[field].drop_nulls().unique().to_list()
            if values != [expected]:
                raise ValueError(f"candidate roster source lineage drift for season {season}: {field}")
        frames.append(frame)
        profiles.append({
            "season": season, "rows": frame.height, "bytes": path.stat().st_size, "sha256": item["sha256"],
            "physical_schema": sorted((name, str(dtype)) for name, dtype in frame.schema.items()),
            "source_schema_sha256": frame["source_schema_sha256"][0],
        })
    candidates = pl.concat(frames, how="diagonal_relaxed").sort(["season", "observation_id"])
    return candidates, manifest, profiles


def _minimum_target_cutoff(data_root: Path, contract: dict[str, Any]) -> tuple[str, Path]:
    pl = _polars()
    source = contract["source_contract"]
    target_path = data_root / Path(source["target_cutoff_relative_path"])
    if not target_path.is_file() or sha256_file(target_path) != source["target_cutoff_sha256"]:
        raise ValueError("target-cutoff payload identity drift")
    targets = pl.read_parquet(target_path)
    if set(targets["season"].unique().to_list()) != set(source["target_seasons"]):
        raise ValueError("target-cutoff season population drift")
    lead_column = "cutoff_lead_hours" if "cutoff_lead_hours" in targets.columns else "lead_hours"
    cutoffs = [cutoff_utc(row["start_utc"], row[lead_column]) for row in targets.select("start_utc", lead_column).iter_rows(named=True)]
    minimum = min(cutoffs)
    if minimum != contract["acceptance"]["expected_minimum_target_cutoff_utc"]:
        raise ValueError("minimum target cutoff drift")
    if parse_utc(source["source_known_at_utc"]) >= parse_utc(minimum):
        raise ValueError("source known-at does not precede approved target cutoffs")
    return minimum, target_path


def _disposition(candidates: Any, contract: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    pl = _polars()
    admission = contract["admission"]
    acceptance = contract["acceptance"]
    exact = (
        (pl.col("reconciliation_disposition") == admission["eligible_disposition"])
        & pl.col("canonical_player_id").is_not_null()
        & pl.col("canonical_team_id").is_not_null()
        & (pl.col("canonical_player_id") == pl.col("canonical_membership_player_id"))
        & (pl.col("canonical_membership_resolution_state") == admission["required_resolution_state"])
        & (pl.col("team_label_exact_match") == True)  # noqa: E712
        & (pl.col("canonical_membership_exact_team_option_count") == admission["required_exact_team_option_count"])
        & (pl.col("canonical_membership_ambiguous") == False)  # noqa: E712
        & (pl.col("athlete_id_occurrence") == admission["required_athlete_id_occurrence"])
    )
    exact_candidates = candidates.filter(exact)
    eligible_disposition_rows = candidates.filter(pl.col("reconciliation_disposition") == admission["eligible_disposition"]).height
    if exact_candidates.height != eligible_disposition_rows:
        raise ValueError("eligible roster disposition contains a non-exact identity or membership row")
    if exact_candidates.height != acceptance["expected_admitted_rows"]:
        raise ValueError("admitted roster population drift")
    if _duplicate_rows(exact_candidates, ["observation_id"]) != acceptance["expected_duplicate_observation_ids"]:
        raise ValueError("duplicate admitted roster observation identity")
    if _duplicate_rows(exact_candidates, admission["natural_key"]) != acceptance["expected_duplicate_natural_keys"]:
        raise ValueError("duplicate admitted roster natural key")
    if exact_candidates.filter(pl.col("team") != pl.col("canonical_team_label")).height:
        raise ValueError("admitted roster historical team label mismatch")
    admitted = exact_candidates.select(admission["admitted_fields"]).with_columns(
        pl.col("class_year").cast(pl.Int64),
        pl.lit("SEASON").alias("membership_effective_grain"),
        pl.lit(None, dtype=pl.String).alias("membership_effective_day_utc"),
        pl.lit(True).alias("season_roster_membership"),
        pl.lit(False).alias("game_time_availability"),
        pl.lit(False).alias("depth_or_starter_status"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "canonical_player_id", "canonical_team_id", "observation_id"])
    nonadmitted = candidates.filter(~exact).sort(["season", "observation_id"])
    if nonadmitted.height != acceptance["expected_nonadmitted_rows"]:
        raise ValueError("non-admitted roster population drift")
    disposition_counts = {str(row["reconciliation_disposition"]): int(row["len"]) for row in nonadmitted.group_by("reconciliation_disposition").len().iter_rows(named=True)}
    if disposition_counts != acceptance["expected_nonadmitted_dispositions"]:
        raise ValueError("non-admitted roster disposition drift")
    multi_team = admitted.group_by(["season", "canonical_player_id"]).agg(pl.col("canonical_team_id").n_unique().alias("teams")).filter(pl.col("teams") > 1)
    validation = {
        "source_rows": candidates.height,
        "admitted_rows": admitted.height,
        "nonadmitted_rows": nonadmitted.height,
        "distinct_players": admitted["canonical_player_id"].n_unique(),
        "distinct_teams": admitted["canonical_team_id"].n_unique(),
        "multi_team_player_seasons": multi_team.height,
        "maximum_teams_in_player_season": int(multi_team["teams"].max() or 1),
        "duplicate_observation_ids": _duplicate_rows(admitted, ["observation_id"]),
        "duplicate_natural_keys": _duplicate_rows(admitted, admission["natural_key"]),
        "nonadmitted_dispositions": disposition_counts,
    }
    for key, expected_key in (("distinct_players", "expected_distinct_players"), ("distinct_teams", "expected_distinct_teams"), ("multi_team_player_seasons", "expected_multi_team_player_seasons")):
        if validation[key] != acceptance[expected_key]:
            raise ValueError(f"roster validation drift: {key}")
    return admitted, nonadmitted, validation


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_roster_membership_pit_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    core_path = Path(__file__).resolve()
    builder_path = repo_root / "tools" / "build_historical_roster_membership_pit.py"
    candidates, candidate_manifest, source_profiles = _load_candidates(input_data_root, contract)
    minimum_target_cutoff, target_path = _minimum_target_cutoff(input_data_root, contract)
    acceptance = contract["acceptance"]
    if candidates.height != acceptance["expected_source_rows"] or set(candidates["season"].unique().to_list()) != set(contract["source_contract"]["source_seasons"]):
        raise ValueError("candidate roster population or season coverage drift")
    if candidates["source_schema_sha256"].n_unique() != acceptance["expected_source_schema_hashes"]:
        raise ValueError("candidate roster semantic schema drift")
    admitted, nonadmitted, validation = _disposition(candidates, contract)
    admitted_by_season = {str(row["season"]): int(row["len"]) for row in admitted.group_by("season").len().sort("season").iter_rows(named=True)}
    if admitted_by_season != acceptance["expected_admitted_by_season"]:
        raise ValueError("admitted roster per-season population drift")
    missingness = {field: int(admitted[field].null_count()) for field in acceptance["expected_admitted_missingness"]}
    if missingness != acceptance["expected_admitted_missingness"]:
        raise ValueError("admitted roster attribute missingness drift")
    forbidden = set(contract["forbidden_admitted_fields"]) & set(admitted.columns)
    if forbidden:
        raise ValueError(f"forbidden fields entered admitted roster state: {sorted(forbidden)}")
    record_hashes = {"admitted": dataframe_record_sha256(admitted), "nonadmitted": dataframe_record_sha256(nonadmitted)}
    identity = stable_hash({
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path),
        "candidate_manifest_sha256": sha256_file(input_data_root / Path(contract["source_contract"]["candidate_manifest_relative_path"])),
        "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
        "target_cutoff_sha256": sha256_file(target_path), "record_hashes": record_hashes,
        "classification": contract["classification"],
    })
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / identity
    quarantine_root = output_data_root / "quarantine" / "historical_known_at" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / identity
    for path in (state_root, quarantine_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "historical_roster_memberships.parquet"
    quarantine_path = quarantine_root / "historical_roster_membership_nonadmitted.parquet"
    admitted.write_parquet(state_path, compression="zstd", statistics=True)
    nonadmitted.write_parquet(quarantine_path, compression="zstd", statistics=True)
    payloads = [
        {"role": "DEVELOPMENT_ONLY_ROSTER_MEMBERSHIPS", "name": state_path.name, "rows": admitted.height, "bytes": state_path.stat().st_size, "sha256": sha256_file(state_path), "record_sha256": record_hashes["admitted"]},
        {"role": "NONADMITTED_ROSTER_EVIDENCE", "name": quarantine_path.name, "rows": nonadmitted.height, "bytes": quarantine_path.stat().st_size, "sha256": sha256_file(quarantine_path), "record_sha256": record_hashes["nonadmitted"]},
    ]
    manifest = {
        "schema_version": "1.0.0", "artifact_type": "HISTORICAL_ROSTER_MEMBERSHIP_PIT",
        "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"], "classification": contract["classification"],
        "dataset_identity": identity, "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)},
        "input_identities": {
            "candidate_dataset": contract["source_contract"]["candidate_dataset_identity"],
            "candidate_manifest_sha256": contract["source_contract"]["candidate_manifest_sha256"],
            "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
            "target_cutoff_payload_sha256": sha256_file(target_path),
        },
        "source_profiles": source_profiles,
        "population": {**validation, "source_files": len(source_profiles), "seasons": contract["source_contract"]["source_seasons"], "admitted_by_season": admitted_by_season},
        "chronology": {"source_known_at_utc": contract["source_contract"]["source_known_at_utc"], "minimum_target_cutoff_utc": minimum_target_cutoff, "source_known_at_before_target_cutoff": True, "backcast_before_source_known_at": False},
        "field_missingness_in_admitted_state": missingness,
        "physical_schema_variants": len({stable_hash(item["physical_schema"]) for item in source_profiles}),
        "semantic_source_schema_hashes": candidates["source_schema_sha256"].n_unique(),
        "forbidden_admitted_fields_present": sorted(forbidden),
        "payloads": payloads, "authority": contract["authority"], "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {"historical_population_ready": False, "gap_002_resolved": False, "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False},
    }
    manifest_path = manifest_root / "historical_roster_membership_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "state_path": str(state_path), "quarantine_path": str(quarantine_path), "manifest": manifest}
