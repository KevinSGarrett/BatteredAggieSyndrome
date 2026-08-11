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
        raise RuntimeError("team-membership PIT materialization requires the optional data-engineering environment") from exc
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
        digest.update(canonical_json_bytes(row) + b"\n")
    return digest.hexdigest()


def _duplicate_rows(frame: Any, keys: Iterable[str]) -> int:
    return int(frame.group_by(list(keys)).len().filter(_polars().col("len") > 1)["len"].sum() or 0)


def _load_candidates(data_root: Path, contract: dict[str, Any]) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("team-membership candidate manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"] or manifest.get("domain") != "team_season_membership" or manifest.get("grain") != "TEAM_SEASON":
        raise ValueError("team-membership candidate identity, domain, or grain drift")
    payloads = sorted(manifest["payloads"], key=lambda item: int(item["season"]))
    if len(payloads) != contract["acceptance"]["expected_source_files"]:
        raise ValueError("team-membership source file count drift")
    source_inputs = {int(item["role"].rsplit("_", 1)[-1]): item for item in manifest["inputs"] if str(item.get("role", "")).startswith("VERSIONED_REPOSITORY_TEAM_MEMBERSHIP_")}
    root = data_root / Path(source["candidate_payload_root"])
    frames, profiles = [], []
    required = set(contract["admission"]["admitted_fields"]) | {"canonical_resolution_state", "canonical_source_id_option_count", "reconciliation_disposition", "venue_fields_present"}
    for item in payloads:
        season = int(item["season"]); path = root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"team-membership payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if frame.height != item["rows"] or set(frame.columns) < required or frame["season"].unique().to_list() != [season]:
            raise ValueError(f"team-membership payload population or schema drift for {season}")
        upstream = source_inputs[season]
        for field, expected in {"source_capture_id": upstream["capture_id"], "source_payload_sha256": upstream["payload_sha256"], "source_commit_sha": source["source_commit_sha"], "source_known_at_utc": source["source_known_at_utc"]}.items():
            if frame[field].unique().to_list() != [expected]:
                raise ValueError(f"team-membership source lineage drift for {season}: {field}")
        frames.append(frame); profiles.append({"season": season, "rows": frame.height, "bytes": path.stat().st_size, "sha256": item["sha256"], "source_payload_sha256": upstream["payload_sha256"], "source_schema_sha256": frame["source_schema_sha256"][0]})
    return pl.concat(frames, how="diagonal_relaxed").sort(["season", "canonical_team_id"]), manifest, profiles


def _minimum_target_cutoff(data_root: Path, contract: dict[str, Any]) -> tuple[str, Path]:
    pl = _polars(); source = contract["source_contract"]; path = data_root / Path(source["target_cutoff_relative_path"])
    if not path.is_file() or sha256_file(path) != source["target_cutoff_sha256"]:
        raise ValueError("target cutoff identity drift")
    targets = pl.read_parquet(path); lead = "cutoff_lead_hours" if "cutoff_lead_hours" in targets.columns else "lead_hours"
    if set(targets["season"].unique().to_list()) != set(source["target_seasons"]):
        raise ValueError("target cutoff season drift")
    minimum = min(cutoff_utc(row["start_utc"], row[lead]) for row in targets.select("start_utc", lead).iter_rows(named=True))
    if minimum != contract["acceptance"]["expected_minimum_target_cutoff_utc"] or parse_utc(source["source_known_at_utc"]) >= parse_utc(minimum):
        raise ValueError("target cutoff chronology drift")
    return minimum, path


def _transition_count(frame: Any) -> int:
    count = 0
    for _, group in frame.sort(["canonical_team_id", "season"]).group_by("canonical_team_id", maintain_order=True):
        rows = group.select("conference", "division").iter_rows()
        previous = None
        for current in rows:
            if previous is not None and current != previous:
                count += 1
            previous = current
    return count


def _admit(candidates: Any, contract: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    pl = _polars(); admission = contract["admission"]; acceptance = contract["acceptance"]
    exact = (
        (pl.col("reconciliation_disposition") == admission["eligible_disposition"])
        & (pl.col("canonical_resolution_state") == admission["required_resolution_state"])
        & (pl.col("canonical_source_id_option_count") == admission["required_source_id_option_count"])
        & pl.col("canonical_team_id").is_not_null()
        & (pl.col("venue_fields_present") == False)  # noqa: E712
    )
    admitted_source = candidates.filter(exact)
    if admitted_source.height != candidates.height or admitted_source.height != acceptance["expected_admitted_rows"]:
        raise ValueError("non-exact or unexpected team-membership population")
    duplicates_observation = _duplicate_rows(admitted_source, ["observation_id"])
    duplicates_natural = _duplicate_rows(admitted_source, admission["natural_key"])
    if duplicates_observation or duplicates_natural:
        raise ValueError("duplicate team-membership identity or natural key")
    admitted = admitted_source.select(admission["admitted_fields"]).with_columns(
        pl.lit("SEASON").alias("membership_effective_grain"),
        pl.lit(None, dtype=pl.String).alias("membership_effective_day_utc"),
        pl.lit(True).alias("team_season_membership"),
        pl.lit(False).alias("venue_or_capacity_truth"),
        pl.lit(False).alias("branding_effective_truth"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "canonical_team_id"])
    validation = {"source_rows": candidates.height, "admitted_rows": admitted.height, "nonadmitted_rows": candidates.height - admitted.height, "distinct_teams": admitted["canonical_team_id"].n_unique(), "duplicate_observation_ids": duplicates_observation, "duplicate_natural_keys": duplicates_natural, "conference_nulls": admitted["conference"].null_count(), "division_nulls": admitted["division"].null_count(), "conference_or_division_transitions": _transition_count(admitted)}
    checks = {"distinct_teams": "expected_distinct_teams", "conference_nulls": "expected_conference_nulls", "division_nulls": "expected_division_nulls", "conference_or_division_transitions": "expected_transitions"}
    for actual, expected in checks.items():
        if validation[actual] != acceptance[expected]:
            raise ValueError(f"team-membership validation drift: {actual}")
    return admitted, validation


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars(); contract_path = repo_root / "configs" / "historical_team_membership_pit_contract.json"; contract_bytes = contract_path.read_bytes(); contract = json.loads(contract_bytes)
    core_path = Path(__file__).resolve(); builder_path = repo_root / "tools" / "build_historical_team_membership_pit.py"
    candidates, candidate_manifest, profiles = _load_candidates(input_data_root, contract); minimum_cutoff, target_path = _minimum_target_cutoff(input_data_root, contract)
    acceptance = contract["acceptance"]
    if candidates.height != acceptance["expected_source_rows"] or set(candidates["season"].unique().to_list()) != set(contract["source_contract"]["source_seasons"]) or candidates["source_schema_sha256"].n_unique() != acceptance["expected_source_schema_hashes"]:
        raise ValueError("team-membership source population, season, or schema drift")
    admitted, validation = _admit(candidates, contract)
    admitted_by_season = {str(row["season"]): int(row["len"]) for row in admitted.group_by("season").len().sort("season").iter_rows(named=True)}
    if admitted_by_season != acceptance["expected_admitted_by_season"]:
        raise ValueError("team-membership per-season population drift")
    forbidden = set(contract["forbidden_admitted_fields"]) & set(admitted.columns)
    if forbidden:
        raise ValueError(f"forbidden team-membership fields admitted: {sorted(forbidden)}")
    record_sha = dataframe_record_sha256(admitted)
    identity = stable_hash({"contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path), "candidate_manifest_sha256": contract["source_contract"]["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]], "target_cutoff_sha256": sha256_file(target_path), "admitted_record_sha256": record_sha, "classification": contract["classification"]})
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / identity; manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / identity
    state_root.mkdir(parents=True, exist_ok=True); manifest_root.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "historical_team_memberships.parquet"; admitted.write_parquet(state_path, compression="zstd", statistics=True)
    manifest = {"schema_version": "1.0.0", "artifact_type": "HISTORICAL_TEAM_MEMBERSHIP_PIT", "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"], "classification": contract["classification"], "dataset_identity": identity, "issued_at_utc": issued_at_utc, "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)}, "input_identities": {"candidate_dataset": contract["source_contract"]["candidate_dataset_identity"], "candidate_manifest_sha256": contract["source_contract"]["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]], "target_cutoff_payload_sha256": sha256_file(target_path)}, "source_profiles": profiles, "population": {**validation, "source_files": len(profiles), "seasons": contract["source_contract"]["source_seasons"], "admitted_by_season": admitted_by_season}, "chronology": {"source_known_at_utc": contract["source_contract"]["source_known_at_utc"], "minimum_target_cutoff_utc": minimum_cutoff, "source_known_at_before_target_cutoff": True, "backcast_before_source_known_at": False}, "semantic_source_schema_hashes": candidates["source_schema_sha256"].n_unique(), "forbidden_admitted_fields_present": sorted(forbidden), "payloads": [{"role": "DEVELOPMENT_ONLY_TEAM_MEMBERSHIPS", "name": state_path.name, "rows": admitted.height, "bytes": state_path.stat().st_size, "sha256": sha256_file(state_path), "record_sha256": record_sha}], "authority": contract["authority"], "negative_findings": contract["negative_findings"], "scientific_nonclaims": {"historical_population_ready": False, "gap_002_resolved": False, "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False}}
    manifest_path = manifest_root / "historical_team_membership_pit_manifest.json"; manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "state_path": str(state_path), "manifest": manifest}
