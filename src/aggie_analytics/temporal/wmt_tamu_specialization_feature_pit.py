from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("WMT Texas A&M feature PIT materialization requires the data-engineering environment") from exc
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


def _source_paths(data_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    source = contract["source_contract"]
    candidate_root = (
        data_root
        / "quarantine"
        / "historical_known_at"
        / "sha256"
        / source["reconciliation_identity"]
        / "tamu_official_gamebooks"
    )
    record_pit_root = (
        data_root
        / "pit_state"
        / "historical_known_at"
        / "sha256"
        / source["provider_record_pit_identity"]
    )
    return {
        "reconciliation_manifest": data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / source["reconciliation_identity"]
        / "tamu_official_gamebook_reconciliation.json",
        "record_pit_manifest": data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / source["provider_record_pit_identity"]
        / "wmt_provider_timestamp_pit_manifest.json",
        "record_pit": record_pit_root / "wmt_provider_timestamp_records.parquet",
        "target_cutoffs": data_root
        / "features"
        / "historical_known_at"
        / "sha256"
        / source["target_replay_identity"]
        / "target_game_cutoffs.parquet",
        **{
            f"candidate_{domain}": candidate_root / f"domain={domain}" / "candidate_records.parquet"
            for domain in source["candidate_payload_sha256"]
        },
    }


def _verify_sources(data_root: Path, contract: dict[str, Any]) -> tuple[dict[str, Path], Any, Any]:
    pl = _polars()
    paths = _source_paths(data_root, contract)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing pinned WMT feature PIT input: {missing}")
    source = contract["source_contract"]
    reconciliation = json.loads(paths["reconciliation_manifest"].read_text(encoding="utf-8"))
    if reconciliation["dataset_identity"] != source["reconciliation_identity"]:
        raise ValueError("WMT reconciliation identity drift")
    record_manifest = json.loads(paths["record_pit_manifest"].read_text(encoding="utf-8"))
    if record_manifest["dataset_identity"] != source["provider_record_pit_identity"]:
        raise ValueError("provider record PIT identity drift")
    if sha256_file(paths["record_pit_manifest"]) != source["provider_record_pit_manifest_sha256"]:
        raise ValueError("provider record PIT manifest hash drift")
    if sha256_file(paths["record_pit"]) != source["provider_record_pit_payload_sha256"]:
        raise ValueError("provider record PIT payload hash drift")
    if sha256_file(paths["target_cutoffs"]) != source["target_cutoff_payload_sha256"]:
        raise ValueError("target cutoff payload hash drift")
    for domain, expected in source["candidate_payload_sha256"].items():
        if sha256_file(paths[f"candidate_{domain}"]) != expected:
            raise ValueError(f"candidate payload hash drift: {domain}")
    record_pit = pl.read_parquet(paths["record_pit"])
    targets = pl.read_parquet(paths["target_cutoffs"])
    if sorted(targets["season"].unique().to_list()) != source["target_seasons"]:
        raise ValueError("target season drift")
    if record_pit.select(pl.struct(["domain", "record_id"]).n_unique()).item() != record_pit.height:
        raise ValueError("provider PIT domain/record identity is not unique")
    return paths, record_pit, targets


def _build_tamu_identity_map(competitors: Any, contract: dict[str, Any]) -> tuple[Any, dict[str, dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    expected_school_id = source["wmt_tamu_school_id"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in competitors.iter_rows(named=True):
        groups[str(row["wmt_game_id"])].append(row)
    identity_rows: list[dict[str, Any]] = []
    mapping: dict[str, dict[str, Any]] = {}
    for game_id, rows in sorted(groups.items()):
        matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in rows:
            normalized = json.loads(row["normalized_record_json"])
            if str(normalized.get("schoolId")) == expected_school_id:
                matches.append((row, normalized))
        if len(matches) != 1:
            raise ValueError(f"WMT game {game_id} has {len(matches)} official schoolId {expected_school_id} competitors")
        row, normalized = matches[0]
        competitor_id = normalized.get("id")
        team_id = normalized.get("teamId")
        if competitor_id in {None, ""} or team_id in {None, ""}:
            raise ValueError(f"WMT game {game_id} has an incomplete Texas A&M provider identity")
        identity = {
            "season": int(row["season"]),
            "wmt_game_id": game_id,
            "source_game_date_utc": str(row["game_date"]),
            "wmt_tamu_school_id": expected_school_id,
            "wmt_tamu_competitor_id": str(competitor_id),
            "wmt_tamu_team_id": str(team_id),
            "tamu_home": bool(normalized.get("homeContest") or normalized.get("homeTeam")),
            "canonical_tamu_team_id": source["canonical_tamu_team_id"],
            "competitor_record_id": str(row["record_id"]),
            "competitor_source_record_sha256": str(row["source_record_sha256"]),
            "identity_authority": "OFFICIAL_WMT_SCHOOL_ID_AND_EXACT_PER_GAME_PROVIDER_IDS",
            "name_only_merge": False,
            "score_assisted_merge": False,
        }
        identity_rows.append(identity)
        mapping[game_id] = identity
    frame = pl.DataFrame(identity_rows).sort(["season", "source_game_date_utc", "wmt_game_id"])
    expected_games = contract["acceptance"]["expected_identity_games"]
    if competitors.height != contract["acceptance"]["expected_competitor_rows"] or frame.height != expected_games:
        raise ValueError("WMT competitor or Texas A&M identity population drift")
    return frame, mapping


def _nested_feature_record(domain: str, normalized: dict[str, Any]) -> dict[str, Any]:
    if domain == "actions":
        value = normalized.get("action")
    elif domain == "plays":
        value = normalized.get("play")
    elif domain == "drives":
        value = normalized.get("summary")
    else:
        value = normalized
    return value if isinstance(value, dict) else {}


def _record_is_tamu(domain: str, exact: dict[str, Any], identity: dict[str, Any]) -> bool:
    if domain in {"actions", "plays"}:
        return str(exact.get("competitor_id")) == identity["wmt_tamu_competitor_id"]
    if domain == "drives":
        return (
            str(exact.get("competitor_id")) == identity["wmt_tamu_competitor_id"]
            and str(exact.get("team_id")) == identity["wmt_tamu_team_id"]
        )
    if domain == "players":
        return str(exact.get("team_id")) == identity["wmt_tamu_team_id"]
    raise ValueError(f"unsupported feature domain: {domain}")


def _normalize_text(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value).strip().lower()


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"feature primitive is not numeric: {value!r}") from exc


def _extract_tamu_records(
    paths: dict[str, Path], record_pit: Any, identity_map: dict[str, dict[str, Any]], contract: dict[str, Any]
) -> Any:
    pl = _polars()
    admitted = {
        (str(row["domain"]), str(row["record_id"])): row
        for row in record_pit.iter_rows(named=True)
        if str(row["domain"]) in contract["acceptance"]["required_feature_domains"]
    }
    output: list[dict[str, Any]] = []
    candidate_seen: set[tuple[str, str]] = set()
    attributed_counts: Counter[str] = Counter()
    for domain in contract["acceptance"]["required_feature_domains"]:
        candidates = pl.read_parquet(paths[f"candidate_{domain}"])
        for source_row in candidates.iter_rows(named=True):
            key = (domain, str(source_row["record_id"]))
            pit_row = admitted.get(key)
            if pit_row is None:
                continue
            candidate_seen.add(key)
            if str(source_row["source_record_sha256"]) != str(pit_row["source_record_sha256"]):
                raise ValueError(f"provider PIT source-record hash mismatch: {key}")
            game_id = str(source_row["wmt_game_id"])
            identity = identity_map.get(game_id)
            if identity is None:
                raise ValueError(f"admitted feature record has no exact WMT Texas A&M identity: {key}")
            normalized = json.loads(source_row["normalized_record_json"])
            exact = _nested_feature_record(domain, normalized)
            if not _record_is_tamu(domain, exact, identity):
                continue
            attributed_counts[domain] += 1
            row = {
                "domain": domain,
                "season": int(source_row["season"]),
                "wmt_game_id": game_id,
                "record_id": key[1],
                "source_json_pointer": str(source_row["source_json_pointer"]),
                "source_record_sha256": str(source_row["source_record_sha256"]),
                "source_response_sha256": str(source_row["source_response_sha256"]),
                "provider_known_at_utc": str(pit_row["provider_known_at_utc"]),
                "effective_at_utc": str(pit_row["effective_at_utc"]),
                "available_at_utc": str(pit_row["available_at_utc"]),
                "canonical_tamu_team_id": contract["source_contract"]["canonical_tamu_team_id"],
                "wmt_tamu_competitor_id": identity["wmt_tamu_competitor_id"],
                "wmt_tamu_team_id": identity["wmt_tamu_team_id"],
                "action_type": None,
                "action_subtype": None,
                "scoring_play": None,
                "drive_plays": None,
                "drive_yards": None,
                "drive_result": None,
                "player_id": None,
                "game_player_id": None,
                "player_started": None,
                "authority": "DEVELOPMENT_ONLY_PIT",
                "protected_eligible": False,
            }
            if domain in {"actions", "plays"}:
                row["action_type"] = _normalize_text(exact.get("play_action_type"))
                row["action_subtype"] = _normalize_text(exact.get("play_action_sub_type"))
                if exact.get("scoring_play") is not None:
                    row["scoring_play"] = bool(exact["scoring_play"])
            elif domain == "drives":
                row["drive_plays"] = _to_float(exact.get("number_of_plays"))
                row["drive_yards"] = _to_float(exact.get("yards"))
                result = exact.get("end_how")
                row["drive_result"] = str(result).strip().upper() if result not in {None, ""} else None
            else:
                row["player_id"] = str(exact["player_id"]) if exact.get("player_id") not in {None, ""} else None
                row["game_player_id"] = (
                    str(exact["game_player_id"]) if exact.get("game_player_id") not in {None, ""} else None
                )
                if exact.get("games_started") is not None:
                    row["player_started"] = bool(int(exact["games_started"]))
            output.append(row)
    if candidate_seen != set(admitted):
        missing = sorted(set(admitted) - candidate_seen)
        raise ValueError(f"provider PIT records missing from pinned candidates: {missing[:5]}")
    expected_counts = contract["acceptance"]["expected_attributed_records_by_domain"]
    if dict(sorted(attributed_counts.items())) != dict(sorted(expected_counts.items())):
        raise ValueError(f"Texas A&M attributed record population drift: {dict(attributed_counts)}")
    output.sort(key=lambda row: (row["domain"], row["season"], row["wmt_game_id"], row["record_id"]))
    frame = pl.DataFrame(output, infer_schema_length=None)
    if frame.select(pl.struct(["domain", "record_id"]).n_unique()).item() != frame.height:
        raise ValueError("attributed domain/record identity is not unique")
    return frame


def _rate(values: Iterable[bool]) -> float | None:
    collected = list(values)
    return sum(collected) / len(collected) if collected else None


def _mean(values: Iterable[float | None]) -> float | None:
    collected = [value for value in values if value is not None]
    return sum(collected) / len(collected) if collected else None


def _domain_metrics(rows: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain"]].append(row)
    features = contract["feature_contract"]
    result: dict[str, Any] = {}
    for domain in contract["acceptance"]["required_feature_domains"]:
        domain_rows = by_domain[domain]
        result[f"{domain}_record_count"] = len(domain_rows)
        result[f"{domain}_game_count"] = len({row["wmt_game_id"] for row in domain_rows})
        result[f"{domain}_latest_available_at_utc"] = max(
            (row["available_at_utc"] for row in domain_rows), default=None, key=parse_utc
        )
    for prefix, domain, type_values in (
        ("action", "actions", features["action_type_values"]),
        ("play", "plays", features["play_type_values"]),
    ):
        domain_rows = by_domain[domain]
        for value in type_values:
            result[f"{prefix}_{value}_rate"] = _rate(row["action_type"] == value for row in domain_rows)
        if domain == "plays":
            for value in features["play_subtype_values"]:
                result[f"play_{value}_subtype_rate"] = _rate(
                    row["action_subtype"] == value for row in domain_rows
                )
        scoring_known = [row for row in domain_rows if row["scoring_play"] is not None]
        result[f"{prefix}_scoring_rate"] = _rate(row["scoring_play"] for row in scoring_known)
    drives = by_domain["drives"]
    result["drive_plays_mean"] = _mean(row["drive_plays"] for row in drives)
    result["drive_yards_mean"] = _mean(row["drive_yards"] for row in drives)
    for name, key in (
        ("touchdown", "touchdown_drive_results"),
        ("field_goal", "field_goal_drive_results"),
        ("turnover", "turnover_drive_results"),
        ("punt", "punt_drive_results"),
        ("downs", "downs_drive_results"),
    ):
        result[f"drive_{name}_rate"] = _rate(row["drive_result"] in features[key] for row in drives)
    players = by_domain["players"]
    result["player_participant_count"] = len({row["game_player_id"] for row in players if row["game_player_id"]})
    started_known = [row for row in players if row["player_started"] is not None]
    result["player_starter_known_count"] = len(started_known)
    result["player_starter_count"] = sum(bool(row["player_started"]) for row in started_known)
    result["player_starter_rate"] = _rate(bool(row["player_started"]) for row in started_known)
    return result


def _build_source_game_features(identity: Any, records: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    rows_by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records.iter_rows(named=True):
        rows_by_game[str(row["wmt_game_id"])].append(row)
    output: list[dict[str, Any]] = []
    for identity_row in identity.iter_rows(named=True):
        game_rows = rows_by_game[str(identity_row["wmt_game_id"])]
        output.append(
            {
                **identity_row,
                **_domain_metrics(game_rows, contract),
                "source_record_count": len(game_rows),
                "source_feature_available_at_utc": max(
                    (row["available_at_utc"] for row in game_rows), default=None, key=parse_utc
                ),
                "classification": contract["classification"],
                "protected_eligible": False,
            }
        )
    return pl.DataFrame(output).sort(["season", "source_game_date_utc", "wmt_game_id"])


def _build_target_features(targets: Any, records: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    source = contract["source_contract"]
    tamu_id = source["canonical_tamu_team_id"]
    target_rows = [
        row
        for row in targets.iter_rows(named=True)
        if str(row["home_team_id"]) == tamu_id or str(row["away_team_id"]) == tamu_id
    ]
    if len(target_rows) != contract["acceptance"]["expected_tamu_target_games"]:
        raise ValueError("Texas A&M target-game population drift")
    source_rows = records.to_dicts()
    output: list[dict[str, Any]] = []
    for target in target_rows:
        cutoff = cutoff_utc(str(target["start_utc"]), int(target["cutoff_lead_hours"]))
        parsed_cutoff = parse_utc(cutoff)
        eligible = [
            row
            for row in source_rows
            if parse_utc(row["available_at_utc"]) < parsed_cutoff
            and parse_utc(row["effective_at_utc"]) < parsed_cutoff
        ]
        metrics = _domain_metrics(eligible, contract)
        is_home = str(target["home_team_id"]) == tamu_id
        latest_available = max((row["available_at_utc"] for row in eligible), default=None, key=parse_utc)
        latest_effective = max((row["effective_at_utc"] for row in eligible), default=None, key=parse_utc)
        output.append(
            {
                "game_id": str(target["game_id"]),
                "season": int(target["season"]),
                "season_type": str(target["season_type"]),
                "week": int(target["week"]),
                "start_utc": str(target["start_utc"]),
                "cutoff_utc": cutoff,
                "cutoff_lead_hours": int(target["cutoff_lead_hours"]),
                "canonical_tamu_team_id": tamu_id,
                "team_role": "HOME" if is_home else "AWAY",
                "opponent_team_id": str(target["away_team_id"] if is_home else target["home_team_id"]),
                "neutral_site": bool(target["neutral_site"]),
                **metrics,
                "source_record_count": len(eligible),
                "source_game_count": len({row["wmt_game_id"] for row in eligible}),
                "latest_source_available_at_utc": latest_available,
                "latest_source_effective_at_utc": latest_effective,
                "cold_start": not eligible,
                "classification": contract["classification"],
                "protected_eligible": False,
            }
        )
    frame = pl.DataFrame(output).sort(["season", "start_utc", "game_id"])
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Texas A&M target feature game identity is not unique")
    return frame


def _feature_columns(frame: Any) -> list[str]:
    suffixes = ("_rate", "_mean", "_count")
    excluded = {"season", "week", "cutoff_lead_hours", "source_record_count", "source_game_count"}
    return [name for name in frame.columns if name not in excluded and name.endswith(suffixes)]


def _assert_output_boundary(frames: Iterable[Any], contract: dict[str, Any]) -> None:
    forbidden = {name.lower() for name in contract["feature_contract"]["forbidden_source_fields"]}
    for frame in frames:
        overlap = forbidden & {name.lower() for name in frame.columns}
        if overlap:
            raise ValueError(f"forbidden source field entered WMT Texas A&M output: {sorted(overlap)}")


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "wmt_tamu_specialization_feature_pit_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    paths, record_pit, targets = _verify_sources(input_data_root, contract)
    competitors = pl.read_parquet(paths["candidate_competitors"])
    identity, identity_map = _build_tamu_identity_map(competitors, contract)
    records = _extract_tamu_records(paths, record_pit, identity_map, contract)
    source_games = _build_source_game_features(identity, records, contract)
    target_features = _build_target_features(targets, records, contract)
    _assert_output_boundary((identity, records, source_games, target_features), contract)
    record_digest = stable_hash(records.to_dicts())
    source_game_digest = stable_hash(source_games.to_dicts())
    target_digest = stable_hash(target_features.to_dicts())
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "source_contract": contract["source_contract"],
            "record_digest": record_digest,
            "source_game_digest": source_game_digest,
            "target_digest": target_digest,
        }
    )
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / dataset_identity
    feature_root = output_data_root / "features" / "historical_known_at" / "sha256" / dataset_identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / dataset_identity
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    record_path = state_root / "wmt_tamu_feature_source_records.parquet"
    source_game_path = state_root / "wmt_tamu_source_game_features.parquet"
    target_path = feature_root / "wmt_tamu_target_cutoff_features.parquet"
    records.write_parquet(record_path, compression="zstd", statistics=True)
    source_games.write_parquet(source_game_path, compression="zstd", statistics=True)
    target_features.write_parquet(target_path, compression="zstd", statistics=True)
    payload_specs = [
        ("DEVELOPMENT_ONLY_TAMU_FEATURE_SOURCE_RECORD_LINEAGE", record_path, records.height),
        ("DEVELOPMENT_ONLY_TAMU_SOURCE_GAME_FEATURE_STATE", source_game_path, source_games.height),
        ("PRELIMINARY_UNPROTECTED_TAMU_TARGET_CUTOFF_FEATURES", target_path, target_features.height),
    ]
    payloads = [
        {
            "role": role,
            "rows": rows,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for role, path, rows in payload_specs
    ]
    attributed = dict(sorted(Counter(records["domain"].to_list()).items()))
    source_coverage = {
        domain: records.filter(pl.col("domain") == domain)["wmt_game_id"].n_unique()
        for domain in contract["acceptance"]["required_feature_domains"]
    }
    feature_columns = _feature_columns(target_features)
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "WMT_TAMU_SPECIALIZATION_FEATURE_PIT",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "population": {
            "competitor_rows": competitors.height,
            "identity_games": identity.height,
            "source_seasons": sorted(identity["season"].unique().to_list()),
            "attributed_records": records.height,
            "attributed_records_by_domain": attributed,
            "source_games_by_domain": source_coverage,
            "source_game_feature_rows": source_games.height,
            "target_games": target_features.height,
            "target_seasons": sorted(target_features["season"].unique().to_list()),
            "target_feature_columns": len(feature_columns),
            "minimum_target_source_records": target_features["source_record_count"].min(),
            "maximum_target_source_records": target_features["source_record_count"].max(),
            "minimum_provider_known_at_utc": records["provider_known_at_utc"].min(),
            "maximum_provider_known_at_utc": records["provider_known_at_utc"].max(),
            "minimum_source_effective_at_utc": records["effective_at_utc"].min(),
            "maximum_source_effective_at_utc": records["effective_at_utc"].max(),
            "minimum_target_cutoff_utc": target_features["cutoff_utc"].min(),
        },
        "missingness": {name: target_features[name].null_count() for name in feature_columns},
        "content_digests": {
            "source_records": record_digest,
            "source_games": source_game_digest,
            "target_features": target_digest,
        },
        "payloads": payloads,
        "authority": contract["authority"],
        "negative_findings": [
            "The official WMT route has no gamebook targets for 2010-2011 and only metadata for 2012; useful action, play, drive, and player coverage begins later and remains domain-specific.",
            "Provider team identifiers vary by season; attribution therefore uses official schoolId 697 plus exact per-game competitor and team IDs rather than a global raw team ID or a name-only merge.",
            "The play collection contains action-grain records, so play rates are explicitly action-record rates and are not represented as unique snap rates.",
            "Player records support participation and starter counts only; no provider player identity is promoted into the canonical player registry.",
            "Score, winner, tie, target outcome, current capture time, inferred timestamp, and fabricated missing values are excluded from every payload.",
            "This development-only candidate does not establish protected A&M lift, final historical readiness, production readiness, BAS, Aggie Excess, or any scientific result.",
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
    manifest_path = manifest_root / "wmt_tamu_specialization_feature_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "record_path": str(record_path),
        "source_game_path": str(source_game_path),
        "target_path": str(target_path),
        "manifest": manifest,
    }


def remove_rebuild_root(path: Path) -> None:
    resolved = path.resolve()
    if "validation" not in {part.lower() for part in resolved.parts}:
        raise ValueError(f"refusing to clean non-validation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
