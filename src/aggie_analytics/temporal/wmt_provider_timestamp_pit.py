from __future__ import annotations

import bisect
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("WMT provider-timestamp PIT materialization requires the data-engineering environment") from exc
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


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def cutoff_utc(start_utc: str, lead_hours: int) -> str:
    return format_utc(parse_utc(start_utc) - timedelta(hours=int(lead_hours)))


def nested_record(value: dict[str, Any], path: list[str]) -> dict[str, Any]:
    current: Any = value
    for part in path:
        if not isinstance(current, dict) or not isinstance(current.get(part), dict):
            return {}
        current = current[part]
    return current if isinstance(current, dict) else {}


def provider_known_at(record: dict[str, Any], fields: list[str]) -> tuple[str, list[str]]:
    parsed: list[tuple[datetime, str]] = []
    for field in fields:
        raw = record.get(field)
        if raw in {None, ""}:
            continue
        parsed.append((parse_utc(str(raw)), field))
    if not parsed:
        raise ValueError("exact record has no provider timestamp")
    maximum = max(value for value, _ in parsed)
    used = sorted(field for value, field in parsed if value == maximum)
    return format_utc(maximum), used


def _source_paths(data_root: Path, contract: dict[str, Any]) -> tuple[Path, Path, Path]:
    source = contract["source_contract"]
    base = (
        data_root / "quarantine" / "historical_known_at" / "sha256"
        / source["reconciliation_identity"] / "tamu_official_gamebooks"
    )
    manifest = (
        data_root / "manifests" / "historical_known_at" / "sha256"
        / source["reconciliation_identity"] / "tamu_official_gamebook_reconciliation.json"
    )
    targets = (
        data_root / "features" / "historical_known_at" / "sha256"
        / source["target_replay_identity"] / "target_game_cutoffs.parquet"
    )
    return base, manifest, targets


def _verify_sources(data_root: Path, contract: dict[str, Any]) -> tuple[dict[str, Path], Any, dict[str, Any]]:
    pl = _polars()
    base, manifest_path, target_path = _source_paths(data_root, contract)
    if not manifest_path.is_file() or not target_path.is_file():
        raise FileNotFoundError("pinned WMT reconciliation manifest or target cutoff matrix is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = contract["source_contract"]
    if manifest["dataset_identity"] != source["reconciliation_identity"]:
        raise ValueError("WMT reconciliation identity drift")
    if manifest["input"]["acquisition_identity"] != source["acquisition_identity"]:
        raise ValueError("WMT acquisition identity drift")
    payload_by_domain = {item["domain"]: item for item in manifest["payloads"]}
    paths: dict[str, Path] = {}
    for domain in contract["acceptance"]["required_domains"]:
        payload = payload_by_domain.get(domain)
        if not payload:
            raise ValueError(f"missing pinned domain payload: {domain}")
        path = base / f"domain={domain}" / "candidate_records.parquet"
        if not path.is_file() or sha256_file(path) != payload["sha256"]:
            raise ValueError(f"pinned domain payload hash drift: {domain}")
        paths[domain] = path
    targets = pl.read_parquet(target_path)
    if sorted(targets["season"].unique().to_list()) != source["target_seasons"]:
        raise ValueError("target cutoff season drift")
    return paths, targets, manifest


def _extract_records(paths: dict[str, Path], targets: Any, contract: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    pl = _polars()
    maximum_cutoff = max(
        (parse_utc(cutoff_utc(row["start_utc"], row["cutoff_lead_hours"])) for row in targets.iter_rows(named=True))
    )
    rows: list[dict[str, Any]] = []
    scanned = Counter()
    excluded_after_all_cutoffs = Counter()
    timestamp_field_counts: dict[str, Counter[str]] = defaultdict(Counter)
    season_domain_counts: dict[str, Counter[int]] = defaultdict(Counter)
    for domain, path in paths.items():
        domain_spec = contract["source_contract"]["domains"][domain]
        frame = pl.read_parquet(path)
        for source_row in frame.iter_rows(named=True):
            scanned[domain] += 1
            normalized = json.loads(source_row["normalized_record_json"])
            exact = nested_record(normalized, domain_spec["record_path"])
            known_at, used_fields = provider_known_at(exact, domain_spec["timestamp_fields"])
            effective_at = format_utc(parse_utc(source_row["game_date"]))
            available_at = max(parse_utc(known_at), parse_utc(effective_at))
            if available_at >= maximum_cutoff:
                excluded_after_all_cutoffs[domain] += 1
                continue
            for field in used_fields:
                timestamp_field_counts[domain][field] += 1
            season_domain_counts[domain][int(source_row["season"])] += 1
            rows.append(
                {
                    "domain": domain,
                    "season": int(source_row["season"]),
                    "wmt_game_id": str(source_row["wmt_game_id"]),
                    "record_id": str(source_row["record_id"]),
                    "source_json_pointer": str(source_row["source_json_pointer"]),
                    "source_record_sha256": str(source_row["source_record_sha256"]),
                    "source_response_sha256": str(source_row["source_response_sha256"]),
                    "effective_at_utc": effective_at,
                    "provider_known_at_utc": known_at,
                    "available_at_utc": format_utc(available_at),
                    "provider_timestamp_fields_json": canonical_json_bytes(used_fields).decode("utf-8"),
                    "authority": "DEVELOPMENT_ONLY_PIT",
                    "protected_eligible": False,
                }
            )
    if not rows:
        raise ValueError("no WMT records are eligible before any target cutoff")
    rows.sort(key=lambda row: (row["domain"], row["season"], row["wmt_game_id"], row["record_id"]))
    frame = pl.DataFrame(rows)
    if frame.select(pl.struct(["domain", "record_id"]).n_unique()).item() != frame.height:
        raise ValueError("domain/record identity is not unique")
    stats = {
        "scanned_records_by_domain": dict(sorted(scanned.items())),
        "admitted_records_by_domain": dict(sorted(Counter(frame["domain"].to_list()).items())),
        "excluded_after_all_target_cutoffs_by_domain": dict(sorted(excluded_after_all_cutoffs.items())),
        "timestamp_field_counts": {key: dict(sorted(value.items())) for key, value in sorted(timestamp_field_counts.items())},
        "season_domain_counts": {key: dict(sorted(value.items())) for key, value in sorted(season_domain_counts.items())},
    }
    return frame, stats


def _build_coverage(records: Any, targets: Any, classification: str) -> Any:
    pl = _polars()
    domains = sorted(records["domain"].unique().to_list())
    record_availability: dict[str, list[datetime]] = {}
    game_availability: dict[str, list[datetime]] = {}
    for domain in domains:
        subset = records.filter(pl.col("domain") == domain)
        record_availability[domain] = sorted(parse_utc(value) for value in subset["available_at_utc"].to_list())
        game_minimums = subset.group_by("wmt_game_id").agg(pl.col("available_at_utc").min())
        game_availability[domain] = sorted(parse_utc(value) for value in game_minimums["available_at_utc"].to_list())
    rows: list[dict[str, Any]] = []
    for target in targets.iter_rows(named=True):
        cutoff = cutoff_utc(target["start_utc"], target["cutoff_lead_hours"])
        parsed_cutoff = parse_utc(cutoff)
        row: dict[str, Any] = {
            "game_id": target["game_id"],
            "season": int(target["season"]),
            "season_type": target["season_type"],
            "week": int(target["week"]),
            "start_utc": target["start_utc"],
            "cutoff_utc": cutoff,
            "classification": classification,
            "coverage_diagnostic_only": True,
            "protected_eligible": False,
        }
        total = 0
        for domain in domains:
            count = bisect.bisect_left(record_availability[domain], parsed_cutoff)
            row[f"{domain}_record_count"] = count
            row[f"{domain}_game_count"] = bisect.bisect_left(game_availability[domain], parsed_cutoff)
            total += count
        row["total_record_count"] = total
        rows.append(row)
    return pl.DataFrame(rows).sort(["season", "start_utc", "game_id"])


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    contract_path = repo_root / "configs" / "wmt_provider_timestamp_pit_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    paths, targets, source_manifest = _verify_sources(input_data_root, contract)
    records, stats = _extract_records(paths, targets, contract)
    coverage = _build_coverage(records, targets, contract["classification"])
    record_digest = stable_hash(records.to_dicts())
    coverage_digest = stable_hash(coverage.to_dicts())
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "source_identity": contract["source_contract"]["reconciliation_identity"],
            "target_identity": contract["source_contract"]["target_replay_identity"],
            "record_digest": record_digest,
            "coverage_digest": coverage_digest,
        }
    )
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / dataset_identity
    feature_root = output_data_root / "features" / "historical_known_at" / "sha256" / dataset_identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / dataset_identity
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "wmt_provider_timestamp_records.parquet"
    feature_path = feature_root / "target_cutoff_wmt_domain_features.parquet"
    records.write_parquet(state_path, compression="zstd", statistics=True)
    coverage.write_parquet(feature_path, compression="zstd", statistics=True)
    payloads = [
        {"role": "DEVELOPMENT_ONLY_WMT_RECORD_PIT", "rows": records.height, "bytes": state_path.stat().st_size, "sha256": sha256_file(state_path)},
        {"role": "TARGET_CUTOFF_DOMAIN_COVERAGE_DIAGNOSTIC", "rows": coverage.height, "bytes": feature_path.stat().st_size, "sha256": sha256_file(feature_path)},
    ]
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "WMT_PROVIDER_TIMESTAMP_PIT",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "source_manifest_sha256": sha256_file(_source_paths(input_data_root, contract)[1]),
        "source_population": source_manifest["population"],
        "population": {
            **stats,
            "admitted_records": records.height,
            "admitted_games": records["wmt_game_id"].n_unique(),
            "target_cutoff_rows": coverage.height,
            "target_games": coverage["game_id"].n_unique(),
            "target_seasons": sorted(coverage["season"].unique().to_list()),
            "minimum_provider_known_at_utc": records["provider_known_at_utc"].min(),
            "maximum_provider_known_at_utc": records["provider_known_at_utc"].max(),
            "minimum_effective_at_utc": records["effective_at_utc"].min(),
            "maximum_effective_at_utc": records["effective_at_utc"].max(),
        },
        "content_digests": {"records": record_digest, "coverage": coverage_digest},
        "payloads": payloads,
        "authority": contract["authority"],
        "negative_findings": [
            "Provider version time is conservative current-record-version availability, not proof that every field existed at the original game time.",
            "Records whose provider version or source game date does not precede a target cutoff are excluded only from that cutoff/domain.",
            "The target-cutoff matrix is a coverage diagnostic, not a direct predictive feature or canonical data mutation.",
            "No current capture time, game time as known-at, PDF metadata, inferred timestamp, target, outcome, or model output is admitted.",
            "This development-only artifact does not establish final historical readiness, protected performance, production promotion, A&M lift, BAS, Aggie Excess, or any scientific result.",
        ],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    manifest_path = manifest_root / "wmt_provider_timestamp_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "state_path": str(state_path),
        "feature_path": str(feature_path),
        "manifest": manifest,
    }


def remove_rebuild_root(path: Path) -> None:
    resolved = path.resolve()
    if "validation" not in {part.lower() for part in resolved.parts}:
        raise ValueError(f"refusing to clean non-validation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
