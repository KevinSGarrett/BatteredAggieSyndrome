from __future__ import annotations

import hashlib
import json
import math
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("venue-assignment PIT materialization requires the optional data-engineering environment") from exc
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
    value = parse_utc(start_utc) - timedelta(hours=int(lead_hours))
    return value.isoformat().replace("+00:00", "Z")


def normalize_numeric_identifier(value: Any) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError("numeric identifier is absent or boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"numeric identifier is not a finite integer: {value}")
        return str(int(value))
    text = str(value).strip()
    if not text:
        raise ValueError("numeric identifier is blank")
    try:
        numeric = float(text)
    except ValueError as exc:
        raise ValueError(f"numeric identifier is not numeric: {text}") from exc
    if not math.isfinite(numeric) or not numeric.is_integer():
        raise ValueError(f"numeric identifier is not a finite integer: {text}")
    return str(int(numeric))


def schema_sha256(schema: Any) -> str:
    return stable_hash(sorted((str(name), str(dtype)) for name, dtype in schema.items()))


def remove_rebuild_root(path: Path) -> None:
    resolved = path.resolve()
    if "validation" not in {part.lower() for part in resolved.parts}:
        raise ValueError(f"refusing to clean non-validation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _load_sources(data_root: Path, contract: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    manifest_root = data_root / Path(source["capture_manifest_root"])
    payload_root = data_root / Path(source["payload_root"])
    venue_fields = contract["venue_field_contract"]
    frames: list[Any] = []
    source_profiles: list[dict[str, Any]] = []
    required = {"game_id", "season", "season_type", *venue_fields}
    for item in source["captures"]:
        manifest_path = manifest_root / f"{item['capture_id']}.json"
        if not manifest_path.is_file() or sha256_file(manifest_path) != item["capture_manifest_sha256"]:
            raise ValueError(f"capture manifest identity drift for season {item['season']}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key, expected in {
            "capture_id": item["capture_id"], "season": item["season"], "commit_sha": item["commit_sha"],
            "historical_known_at_candidate": item["known_at_utc"],
        }.items():
            if manifest.get(key) != expected:
                raise ValueError(f"capture manifest field drift for season {item['season']}: {key}")
        if manifest.get("repository") != source["repository"] or manifest["payload"]["sha256"] != item["payload_sha256"]:
            raise ValueError(f"capture repository or payload drift for season {item['season']}")
        payload_path = payload_root / item["payload_sha256"] / "payload.parquet"
        if (
            not payload_path.is_file()
            or payload_path.stat().st_size != item["payload_bytes"]
            or sha256_file(payload_path) != item["payload_sha256"]
        ):
            raise ValueError(f"source payload identity drift for season {item['season']}")
        frame = pl.read_parquet(payload_path)
        if frame.height != item["source_rows"] or set(frame.columns) < required:
            raise ValueError(f"source population or required-field drift for season {item['season']}")
        actual_schema = schema_sha256(frame.schema)
        if actual_schema != item["schema_sha256"] or str(frame.schema["game_id"]) != item["game_id_dtype"]:
            raise ValueError(f"source schema drift for season {item['season']}")
        normalized = frame.select(
            pl.col("game_id").map_elements(normalize_numeric_identifier, return_dtype=pl.String).alias("source_game_id"),
            pl.col("season").cast(pl.Int64),
            pl.col("season_type").cast(pl.Int64).alias("source_season_type"),
            pl.col("venue_id").cast(pl.String).str.strip_chars().replace("", None),
            pl.col("venue_full_name").cast(pl.String).str.strip_chars().replace("", None),
            pl.col("venue_address_city").cast(pl.String).str.strip_chars().replace("", None),
            pl.col("venue_address_state").cast(pl.String).str.strip_chars().replace("", None),
            pl.col("venue_capacity").cast(pl.Float64).alias("venue_capacity_source_raw"),
            pl.when(pl.col("venue_capacity").cast(pl.Float64) > 0)
            .then(pl.col("venue_capacity").cast(pl.Float64)).otherwise(None).alias("venue_capacity"),
            pl.col("venue_indoor").cast(pl.Boolean),
        ).with_columns(
            pl.lit(item["capture_id"]).alias("venue_source_capture_id"),
            pl.lit(item["payload_sha256"]).alias("venue_source_payload_sha256"),
            pl.lit(item["commit_sha"]).alias("venue_source_commit_sha"),
            pl.lit(item["known_at_utc"]).alias("venue_source_known_at_utc"),
            pl.lit(item["schema_sha256"]).alias("venue_source_schema_sha256"),
            pl.lit(item["game_id_dtype"]).alias("source_game_id_dtype"),
            pl.lit(int(item["season"]) in source["partial_source_seasons"]).alias("partial_source_season"),
        )
        frames.append(normalized)
        source_profiles.append({
            "season": int(item["season"]), "rows": frame.height, "schema_sha256": actual_schema,
            "game_id_dtype": str(frame.schema["game_id"]), "venue_id_dtype": str(frame.schema["venue_id"]),
            "venue_id_present": int(normalized["venue_id"].is_not_null().sum()),
            "venue_name_present": int(normalized["venue_full_name"].is_not_null().sum()),
            "nonpositive_capacity_rows": int((normalized["venue_capacity_source_raw"] <= 0).fill_null(False).sum()),
        })
    sources = pl.concat(frames, how="vertical_relaxed").sort(["season", "source_game_id"])
    return sources, source_profiles


def _load_outcomes_and_targets(data_root: Path, contract: dict[str, Any]) -> tuple[Any, Any, Path, Path]:
    pl = _polars()
    source = contract["source_contract"]
    identity = source["accepted_outcome_identity"]
    outcome_path = data_root / "pit_state" / "historical_known_at" / "sha256" / identity / "accepted_game_outcomes.parquet"
    target_path = data_root / "features" / "historical_known_at" / "sha256" / identity / "target_game_cutoffs.parquet"
    if not outcome_path.is_file() or sha256_file(outcome_path) != source["accepted_outcome_sha256"]:
        raise ValueError("accepted historical-outcome identity drift")
    if not target_path.is_file() or sha256_file(target_path) != source["target_cutoff_sha256"]:
        raise ValueError("target-cutoff identity drift")
    outcomes = pl.read_parquet(outcome_path).with_columns(
        pl.col("source_game_id").map_elements(normalize_numeric_identifier, return_dtype=pl.String),
        pl.col("season").cast(pl.Int64),
        pl.col("season_type").cast(pl.Int64),
    )
    return outcomes, pl.read_parquet(target_path), outcome_path, target_path


def _validate_and_join(sources: Any, outcomes: Any, targets: Any, contract: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    pl = _polars()
    acceptance = contract["acceptance"]
    source = contract["source_contract"]
    if sources.height != acceptance["expected_source_rows"] or outcomes.height != acceptance["expected_accepted_outcome_rows"]:
        raise ValueError("source or accepted-outcome population drift")
    if sources["source_game_id"].null_count() or outcomes["source_game_id"].null_count():
        raise ValueError("source or accepted-outcome game identity is absent")
    if set(outcomes["reconciliation_disposition"].unique().to_list()) != {source["eligible_outcome_disposition"]}:
        raise ValueError("accepted-outcome reconciliation disposition drift")
    source_duplicates = sources.group_by(["season", "source_game_id"]).len().filter(pl.col("len") > 1)
    outcome_duplicates = outcomes.group_by(["season", "source_game_id"]).len().filter(pl.col("len") > 1)
    if source_duplicates.height != acceptance["expected_duplicate_source_keys"] or outcome_duplicates.height:
        raise ValueError("duplicate normalized season/source-game key")
    joined = outcomes.select(
        "source_game_id", "canonical_game_id", "season", "season_type", "game_start_utc",
        "home_team_id", "away_team_id", "source_capture_id", "source_payload_sha256",
        "source_record_evidence_sha256", "reconciliation_disposition",
    ).join(sources, on=["season", "source_game_id"], how="left", validate="1:1")
    if joined.height != acceptance["expected_exact_join_rows"] or joined["venue_source_capture_id"].null_count():
        raise ValueError("accepted outcomes do not join exactly one-to-one to venue source records")
    if not (joined["season_type"] == joined["source_season_type"]).all():
        raise ValueError("source/accepted season-type conflict")
    schema_variants = sources["venue_source_schema_sha256"].n_unique()
    if schema_variants != acceptance["expected_schema_variants"]:
        raise ValueError("source schema-variant count drift")
    pairs = sources.filter(pl.col("venue_id").is_not_null() & pl.col("venue_full_name").is_not_null()).select(
        "venue_id", "venue_full_name"
    ).unique()
    ambiguity_count = (
        pairs.group_by("venue_id").agg(pl.col("venue_full_name").n_unique().alias("n")).filter(pl.col("n") > 1).height
        + pairs.group_by("venue_full_name").agg(pl.col("venue_id").n_unique().alias("n")).filter(pl.col("n") > 1).height
    )
    if ambiguity_count != acceptance["expected_venue_id_name_ambiguities"]:
        raise ValueError("venue ID/name ambiguity drift")
    cutoffs = [cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]) for row in targets.iter_rows(named=True)]
    minimum_cutoff = min(cutoffs, key=parse_utc)
    maximum_known_at = max(joined["venue_source_known_at_utc"].unique().to_list(), key=parse_utc)
    if minimum_cutoff != acceptance["earliest_target_cutoff_utc"] or parse_utc(maximum_known_at) > parse_utc(minimum_cutoff):
        raise ValueError("source known-at exceeds or target cutoff differs from the pinned chronology")
    if sorted(targets["season"].unique().to_list()) != source["target_seasons"]:
        raise ValueError("target season drift")
    target_overlap = set(joined["canonical_game_id"].to_list()) & set(targets["game_id"].to_list())
    if target_overlap or max(source["source_seasons"]) >= min(source["target_seasons"]):
        raise ValueError("target-game or target-season overlap detected")
    return joined, {
        "source_duplicate_keys": source_duplicates.height,
        "outcome_duplicate_keys": outcome_duplicates.height,
        "exact_join_rows": joined.height,
        "schema_variants": schema_variants,
        "venue_id_name_ambiguities": ambiguity_count,
        "minimum_target_cutoff_utc": minimum_cutoff,
        "maximum_source_known_at_utc": maximum_known_at,
        "target_game_overlap": 0,
    }


def _lineage(row: dict[str, Any]) -> str:
    return stable_hash(row)


def _disposition(joined: Any, contract: dict[str, Any]) -> tuple[Any, Any]:
    pl = _polars()
    venue_present = pl.col("venue_id").is_not_null() & pl.col("venue_full_name").is_not_null()
    allowed = [
        "source_game_id", "canonical_game_id", "season", "season_type", "game_start_utc", "home_team_id", "away_team_id",
        "venue_id", "venue_full_name", "venue_address_city", "venue_address_state", "venue_capacity", "venue_indoor",
        "venue_capacity_source_raw",
        "venue_source_capture_id", "venue_source_payload_sha256", "venue_source_commit_sha", "venue_source_known_at_utc",
        "venue_source_schema_sha256", "source_game_id_dtype", "partial_source_season",
    ]
    base = joined.select(*allowed)
    evidence_fields = ["source_game_id", "season", "venue_id", "venue_full_name", "venue_address_city", "venue_address_state", "venue_capacity_source_raw", "venue_capacity", "venue_indoor", "venue_source_payload_sha256"]
    state = base.filter(venue_present).with_columns(
        pl.struct(evidence_fields).map_elements(_lineage, return_dtype=pl.String).alias("venue_record_evidence_sha256"),
        pl.lit(contract["classification"]).alias("admission_state"),
        pl.lit(True).alias("venue_evidence_present"),
        pl.lit(False).alias("timeless_canonical_venue_truth"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "canonical_game_id"])
    quarantine = base.filter(~venue_present).with_columns(
        pl.struct(evidence_fields).map_elements(_lineage, return_dtype=pl.String).alias("venue_record_evidence_sha256"),
        pl.when(pl.col("venue_id").is_null() & pl.col("venue_full_name").is_null())
        .then(pl.lit("NOT_PRESENT_VENUE_ID_AND_NAME"))
        .otherwise(pl.lit("QUARANTINE_PARTIAL_VENUE_ID_NAME"))
        .alias("disposition"),
        pl.lit(False).alias("venue_evidence_present"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "canonical_game_id"])
    return state, quarantine


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str,
    contract_name: str = "historical_venue_assignment_pit_contract.json",
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / contract_name
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    core_path = Path(__file__).resolve()
    builder_path = repo_root / "tools" / "build_historical_venue_assignment_pit.py"
    core_sha256 = sha256_file(core_path)
    builder_sha256 = sha256_file(builder_path)
    sources, source_profiles = _load_sources(input_data_root, contract)
    outcomes, targets, outcome_path, target_path = _load_outcomes_and_targets(input_data_root, contract)
    joined, validation = _validate_and_join(sources, outcomes, targets, contract)
    state, quarantine = _disposition(joined, contract)
    acceptance = contract["acceptance"]
    if state.height != acceptance["expected_admitted_rows"] or quarantine.height != acceptance["expected_not_present_rows"]:
        raise ValueError("admitted or NOT_PRESENT population drift")
    nonpositive_capacity = int((state["venue_capacity_source_raw"] <= 0).fill_null(False).sum())
    if nonpositive_capacity != acceptance["expected_nonpositive_capacity_rows_in_admitted"] or state["venue_capacity"].null_count() != nonpositive_capacity:
        raise ValueError("nonpositive venue-capacity placeholder normalization drift")
    if sources["venue_id"].drop_nulls().n_unique() != acceptance["expected_source_distinct_venue_ids"] or sources["venue_full_name"].drop_nulls().n_unique() != acceptance["expected_source_distinct_venue_names"]:
        raise ValueError("distinct source venue identity count drift")
    if state["venue_id"].n_unique() != acceptance["expected_admitted_distinct_venue_ids"] or state["venue_full_name"].n_unique() != acceptance["expected_admitted_distinct_venue_names"]:
        raise ValueError("distinct admitted venue identity count drift")
    identity = stable_hash({
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "core_sha256": core_sha256,
        "builder_sha256": builder_sha256,
        "accepted_outcome_sha256": sha256_file(outcome_path),
        "target_cutoff_sha256": sha256_file(target_path),
        "capture_payload_sha256": [item["payload_sha256"] for item in contract["source_contract"]["captures"]],
        "state": state.to_dicts(), "quarantine": quarantine.to_dicts(), "classification": contract["classification"],
    })
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / identity
    quarantine_root = output_data_root / "quarantine" / "historical_known_at" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / identity
    for path in (state_root, quarantine_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "historical_venue_assignments.parquet"
    quarantine_path = quarantine_root / "historical_venue_assignment_quarantine.parquet"
    state.write_parquet(state_path, compression="zstd", statistics=True)
    quarantine.write_parquet(quarantine_path, compression="zstd", statistics=True)
    payloads = [
        {"role": "DEVELOPMENT_ONLY_VENUE_ASSIGNMENTS", "name": state_path.name, "rows": state.height, "bytes": state_path.stat().st_size, "sha256": sha256_file(state_path)},
        {"role": "NOT_PRESENT_AND_PARTIAL_VENUE_EVIDENCE", "name": quarantine_path.name, "rows": quarantine.height, "bytes": quarantine_path.stat().st_size, "sha256": sha256_file(quarantine_path)},
    ]
    per_season = []
    for season in contract["source_contract"]["source_seasons"]:
        season_joined = joined.filter(pl.col("season") == season)
        season_state = state.filter(pl.col("season") == season)
        season_quarantine = quarantine.filter(pl.col("season") == season)
        per_season.append({
            "season": season, "source_rows": sources.filter(pl.col("season") == season).height,
            "accepted_outcome_rows": season_joined.height, "exact_join_rows": season_joined.height,
            "admitted_rows": season_state.height, "not_present_or_quarantine_rows": season_quarantine.height,
            "partial_source_season": season in contract["source_contract"]["partial_source_seasons"],
        })
    missingness = {field: int(state[field].null_count()) for field in contract["venue_field_contract"]}
    manifest = {
        "schema_version": "1.0.0", "artifact_type": "HISTORICAL_VENUE_ASSIGNMENT_PIT",
        "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"],
        "classification": contract["classification"], "dataset_identity": identity, "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {
            "python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__,
            "core_sha256": core_sha256, "builder_sha256": builder_sha256,
        },
        "accepted_outcome_sha256": sha256_file(outcome_path), "target_cutoff_sha256": sha256_file(target_path),
        "source_contract": contract["source_contract"], "source_profiles": source_profiles,
        "population": {
            "source_rows": sources.height, "accepted_outcome_rows": outcomes.height, "exact_join_rows": joined.height,
            "admitted_rows": state.height, "not_present_or_quarantine_rows": quarantine.height,
            "source_distinct_venue_ids": sources["venue_id"].drop_nulls().n_unique(), "source_distinct_venue_names": sources["venue_full_name"].drop_nulls().n_unique(),
            "admitted_distinct_venue_ids": state["venue_id"].n_unique(), "admitted_distinct_venue_names": state["venue_full_name"].n_unique(),
            "source_seasons": contract["source_contract"]["source_seasons"], "target_seasons": contract["source_contract"]["target_seasons"],
            "per_season": per_season,
        },
        "temporal_and_identity_validation": validation, "field_missingness_in_admitted_state": missingness,
        "placeholder_normalization": {"nonpositive_capacity_rows": nonpositive_capacity, "analytical_capacity_disposition": "NULL_RAW_VALUE_RETAINED"},
        "quarantine_dispositions": {str(row["disposition"]): int(row["len"]) for row in quarantine.group_by("disposition").len().iter_rows(named=True)},
        "payloads": payloads, "authority": contract["authority"], "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {
            "historical_population_ready": False, "gap_002_resolved": False, "production_model_ready": False,
            "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    manifest_path = manifest_root / "historical_venue_assignment_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "state_path": str(state_path), "quarantine_path": str(quarantine_path), "manifest": manifest,
    }
