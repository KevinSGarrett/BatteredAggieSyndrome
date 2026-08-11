from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq


COMMIT_SHA = "b9b838e44f16131b897489e6ae3da355f8c99865"
COMMIT_KNOWN_AT_UTC = "2022-07-25T17:33:07Z"
COMMIT_API_SHA256 = "850173173cd819b0da74be2a169c198b23961ae8a8b82718fb441b3fa56a5eef"
CANONICAL_REGISTRY_SHA256 = "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"
SUPPLEMENTAL_IDENTITY = "813276328568574a1d19173018ba328fd1c4a63a8aa34b34255ef1a2d880020f"
SOURCE_FILES = {
    2011: {
        "bytes": 51_327_641,
        "sha256": "0be6b656396aa804eaa992e320fa0593b60e21f11537a6f4b2925b3e99b4c782",
        "rows": 138_564,
    },
    2020: {
        "bytes": 36_476_557,
        "sha256": "48e3aa3ae95b9d83e613f5455863c9f9b49716411bfb4fb18c420130a93894b2",
        "rows": 96_293,
    },
}
PLAY_DISPOSITION = "CANDIDATE_VERSION_BOUND_EXACT_PLAY_CANONICAL_GAME"
DRIVE_DISPOSITION = "CANDIDATE_VERSION_BOUND_EXACT_DRIVE_CANONICAL_GAME"
QUARANTINE_DISPOSITION = "QUARANTINED_VERSION_BOUND_IDENTITY_OR_SCHEMA_FAILURE"


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


def schema_sha256(table: pa.Table) -> str:
    return hashlib.sha256(table.schema.serialize().to_pybytes()).hexdigest()


def immutable_copy(source: Path, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != expected_sha256:
            raise ValueError(f"immutable destination hash drift: {destination}")
        return
    shutil.copyfile(source, destination)
    if sha256_file(destination) != expected_sha256:
        destination.unlink(missing_ok=True)
        raise ValueError(f"copied payload hash drift: {destination}")


def immutable_json(path: Path, value: Any) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable JSON collision: {path}")
        return
    path.write_bytes(payload)


def immutable_parquet(path: Path, rows: list[dict[str, Any]]) -> pa.Table:
    table = pa.Table.from_pylist(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        prior = pq.ParquetFile(path).read()
        if not table.equals(prior):
            raise ValueError(f"immutable Parquet collision: {path}")
        return prior
    pq.write_table(table, path, compression="zstd", write_statistics=True)
    return table


def as_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def clock_parts(value: Any) -> tuple[int | None, int | None]:
    if not value or ":" not in str(value):
        return None, None
    minutes, seconds = str(value).split(":", 1)
    return int(minutes), int(seconds)


def load_registry(path: Path) -> tuple[dict[str, dict[str, str]], set[str]]:
    games: dict[str, dict[str, str]] = {}
    team_ids: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (
                row["record_type"] == "ENTITY"
                and row["source_system_id"] == "SRC-002"
                and row["resolution_state"] == "AUTO_ACCEPTED_VERIFIED"
            ):
                if row["entity_type"] == "game":
                    games[row["source_entity_key"]] = row
                elif row["entity_type"] == "team":
                    team_ids.add(row["source_entity_key"])
    return games, team_ids


def load_supplemental(data_root: Path, season: int) -> tuple[set[str], set[tuple[Any, ...]], dict[str, dict[str, Any]]]:
    base = (
        data_root
        / "quarantine"
        / "historical_known_at"
        / "sha256"
        / SUPPLEMENTAL_IDENTITY
        / "supplemental_play_drive"
        / f"season={season}"
    )
    plays = pq.ParquetFile(base / "candidate_play_rows.parquet").read(
        columns=["source_play_id", "source_game_id", "play_text", "period", "yards_gained"]
    )
    drives = pq.ParquetFile(base / "candidate_drive_rows.parquet").read(
        columns=["source_drive_id", "source_game_id", "drive_result", "plays_reported", "yards_reported"]
    )
    play_ids: set[str] = set()
    signatures: Counter[tuple[Any, ...]] = Counter()
    for row in plays.to_pylist():
        play_ids.add(str(row["source_play_id"]))
        signatures[(
            str(row["source_game_id"]),
            (row["play_text"] or "").strip(),
            as_int(row["period"]),
            as_int(row["yards_gained"]),
        )] += 1
    drive_rows = {str(row["source_drive_id"]): row for row in drives.to_pylist()}
    unique_signatures = {key for key, count in signatures.items() if count == 1}
    return play_ids, unique_signatures, drive_rows


def derived_play_ids(game_id: str, sequence: str) -> set[str]:
    values = {f"{game_id}{sequence}"}
    if len(sequence) < 3:
        values.add(f"{game_id}{sequence.zfill(3)}")
    return values


def selected_columns(path: Path) -> pa.Table:
    available = set(pq.read_schema(path).names)
    desired = [
        "sequenceNumber", "text", "awayScore", "homeScore", "scoringPlay", "statYardage",
        "type.id", "type.text", "period.number", "clock.displayValue", "start.down",
        "start.distance", "start.yardLine", "start.yardsToEndzone", "start.team.id",
        "end.down", "end.distance", "end.yardLine", "end.yardsToEndzone", "end.team.id",
        "drive.id", "drive.result", "drive.offensivePlays", "drive.yards", "drive.team.abbreviation",
        "game_id", "season",
        "seasonType", "homeTeamId", "awayTeamId", "homeTeamAbbrev", "awayTeamAbbrev",
        "game_play_number", "start.pos_team.id",
        "start.def_pos_team.id", "playType", "week", "EPA", "wp_before", "wp_after", "wpa",
        "rush", "pass", "sack", "int", "completion", "pass_attempt", "td_play",
        "penalty_flag", "receiver_player_name", "passer_player_name", "rusher_player_name",
        "athlete_name", "modified",
    ]
    return pq.ParquetFile(path).read(columns=[name for name in desired if name in available])


def normalize_season(
    *,
    season: int,
    source_path: Path,
    capture_id: str,
    payload_sha256: str,
    games: dict[str, dict[str, str]],
    team_ids: set[str],
    supplemental_play_ids: set[str],
    supplemental_signatures: set[tuple[Any, ...]],
    supplemental_drives: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    table = selected_columns(source_path)
    source_schema = schema_sha256(table)
    plays: list[dict[str, Any]] = []
    drive_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dispositions: Counter[str] = Counter()
    exact_id_matches = 0
    exact_content_matches = 0

    for row_number, source in enumerate(table.to_pylist()):
        game_id = str(source["game_id"])
        sequence = str(source["sequenceNumber"])
        game = games.get(game_id)
        offense_team_id = as_int(source.get("start.pos_team.id"))
        defense_team_id = as_int(source.get("start.def_pos_team.id"))
        modified = source.get("modified")
        canonical_game_id = game["canonical_id"] if game else None
        identity_valid = bool(
            canonical_game_id
            and offense_team_id is not None
            and defense_team_id is not None
            and str(offense_team_id) in team_ids
            and str(defense_team_id) in team_ids
            and modified
        )
        disposition = PLAY_DISPOSITION if identity_valid else QUARANTINE_DISPOSITION
        dispositions[disposition] += 1
        candidate_ids = derived_play_ids(game_id, sequence)
        exact_id = sorted(candidate_ids & supplemental_play_ids)
        signature = (
            game_id,
            (source.get("text") or "").strip(),
            as_int(source.get("period.number")),
            as_int(source.get("statYardage")),
        )
        exact_content = signature in supplemental_signatures
        exact_id_matches += int(bool(exact_id))
        exact_content_matches += int(exact_content)
        minutes, seconds = clock_parts(source.get("clock.displayValue"))
        evidence = {
            "game_id": game_id,
            "sequence_number": sequence,
            "text": source.get("text"),
            "period": as_int(source.get("period.number")),
            "clock": source.get("clock.displayValue"),
            "stat_yardage": as_int(source.get("statYardage")),
            "offense_team_id": offense_team_id,
            "defense_team_id": defense_team_id,
            "modified": modified,
            "source_payload_sha256": payload_sha256,
            "source_row_number": row_number,
        }
        evidence_sha = stable_hash(evidence)
        normalized = {
            "schema_version": "1.0.0",
            "observation_id": f"versioned_gap_play_{evidence_sha[:24]}",
            "source_row_number": row_number,
            "canonical_game_id": canonical_game_id,
            "sequence_number": sequence,
            "play_text": source.get("text"),
            "away_score": as_int(source.get("awayScore")),
            "home_score": as_int(source.get("homeScore")),
            "scoring_play": bool(source.get("scoringPlay")) if source.get("scoringPlay") is not None else None,
            "stat_yardage": as_int(source.get("statYardage")),
            "play_type_id": str(source["type.id"]) if source.get("type.id") is not None else None,
            "play_type_text": source.get("type.text"),
            "period": as_int(source.get("period.number")),
            "clock_minutes": minutes,
            "clock_seconds": seconds,
            "start_down": as_int(source.get("start.down")),
            "start_distance": as_int(source.get("start.distance")),
            "start_yard_line": as_int(source.get("start.yardLine")),
            "start_yards_to_endzone": as_int(source.get("start.yardsToEndzone")),
            "start_team_id": as_int(source.get("start.team.id")),
            "end_down": as_int(source.get("end.down")),
            "end_distance": as_int(source.get("end.distance")),
            "end_yard_line": as_int(source.get("end.yardLine")),
            "end_yards_to_endzone": as_int(source.get("end.yardsToEndzone")),
            "end_team_id": as_int(source.get("end.team.id")),
            "drive_id": str(source["drive.id"]) if source.get("drive.id") is not None else None,
            "drive_result": source.get("drive.result"),
            "game_id": game_id,
            "season": season,
            "season_type": as_int(source.get("seasonType")),
            "home_team_id": as_int(source.get("homeTeamId")),
            "away_team_id": as_int(source.get("awayTeamId")),
            "game_play_number": as_int(source.get("game_play_number")),
            "offense_team_id": offense_team_id,
            "defense_team_id": defense_team_id,
            "play_type": source.get("playType"),
            "week": as_int(source.get("week")),
            "down": as_int(source.get("start.down")),
            "distance": as_int(source.get("start.distance")),
            "epa": as_float(source.get("EPA")),
            "win_probability_before": as_float(source.get("wp_before")),
            "win_probability_after": as_float(source.get("wp_after")),
            "win_probability_added": as_float(source.get("wpa")),
            "rush": bool(source.get("rush")) if source.get("rush") is not None else None,
            "pass": bool(source.get("pass")) if source.get("pass") is not None else None,
            "sack": bool(source.get("sack")) if source.get("sack") is not None else None,
            "interception": bool(source.get("int")) if source.get("int") is not None else None,
            "completion": bool(source.get("completion")) if source.get("completion") is not None else None,
            "pass_attempt": bool(source.get("pass_attempt")) if source.get("pass_attempt") is not None else None,
            "touchdown_play": bool(source.get("td_play")) if source.get("td_play") is not None else None,
            "penalty_flag": bool(source.get("penalty_flag")) if source.get("penalty_flag") is not None else None,
            "receiver_name": source.get("receiver_player_name"),
            "passer_name": source.get("passer_player_name"),
            "rusher_name": source.get("rusher_player_name"),
            "athlete_name": source.get("athlete_name"),
            "effective_at_utc": modified,
            "source_capture_id": capture_id,
            "source_payload_sha256": payload_sha256,
            "source_commit_sha": COMMIT_SHA,
            "source_known_at_utc": COMMIT_KNOWN_AT_UTC,
            "source_schema_sha256": source_schema,
            "source_record_evidence_sha256": evidence_sha,
            "current_cfbd_exact_match": bool(exact_id),
            "current_cfbd_content_signature_match": exact_content,
            "current_cfbd_play_id": exact_id[0] if exact_id else None,
            "upstream_independence": "NOT_CLAIMED_SHARED_ESPN_DERIVATION_POSSIBLE",
            "admission_state": "DEVELOPMENT_PIT_ELIGIBLE" if identity_valid else "QUARANTINED",
            "reconciliation_disposition": disposition,
            "downstream_pit_contract": "DEVELOPMENT_ONLY; source_known_at_utc <= cutoff; source_game_id != target_game_id",
        }
        normalized["row_lineage_sha256"] = stable_hash(normalized)
        plays.append(normalized)
        if source.get("drive.id") is not None:
            drive_abbreviation = source.get("drive.team.abbreviation")
            home_abbreviation = source.get("homeTeamAbbrev")
            away_abbreviation = source.get("awayTeamAbbrev")
            home_team_id = as_int(source.get("homeTeamId"))
            away_team_id = as_int(source.get("awayTeamId"))
            if drive_abbreviation and drive_abbreviation == home_abbreviation:
                drive_offense_team_id = home_team_id
                drive_defense_team_id = away_team_id
            elif drive_abbreviation and drive_abbreviation == away_abbreviation:
                drive_offense_team_id = away_team_id
                drive_defense_team_id = home_team_id
            else:
                drive_offense_team_id = None
                drive_defense_team_id = None
            drive_groups[str(source["drive.id"])].append(normalized | {
                "reported_drive_plays": as_int(source.get("drive.offensivePlays")),
                "reported_drive_yards": as_int(source.get("drive.yards")),
                "drive_team_abbreviation": drive_abbreviation,
                "drive_offense_team_id": drive_offense_team_id,
                "drive_defense_team_id": drive_defense_team_id,
            })

    drives: list[dict[str, Any]] = []
    drive_dispositions: Counter[str] = Counter()
    for drive_id in sorted(drive_groups):
        rows = drive_groups[drive_id]
        identity_sets = {
            name: {row.get(name) for row in rows if row.get(name) is not None}
            for name in (
                "game_id",
                "canonical_game_id",
                "drive_offense_team_id",
                "drive_defense_team_id",
                "drive_result",
            )
        }
        identity_valid = (
            len(identity_sets["game_id"]) == 1
            and len(identity_sets["canonical_game_id"]) == 1
            and len(identity_sets["drive_offense_team_id"]) == 1
            and len(identity_sets["drive_defense_team_id"]) == 1
            and all(row["reconciliation_disposition"] == PLAY_DISPOSITION for row in rows)
        )
        disposition = DRIVE_DISPOSITION if identity_valid else QUARANTINE_DISPOSITION
        drive_dispositions[disposition] += 1
        first = min(rows, key=lambda row: row["source_row_number"])
        last = max(rows, key=lambda row: row["source_row_number"])
        drive_offense_team_id = next(iter(identity_sets["drive_offense_team_id"]), None)
        drive_defense_team_id = next(iter(identity_sets["drive_defense_team_id"]), None)
        drive_result = next(iter(identity_sets["drive_result"]), None)
        current = supplemental_drives.get(drive_id)
        evidence = {
            "drive_id": drive_id,
            "game_id": first["game_id"],
            "source_play_rows": len(rows),
            "first_row_lineage": first["row_lineage_sha256"],
            "last_row_lineage": last["row_lineage_sha256"],
            "source_payload_sha256": payload_sha256,
        }
        evidence_sha = stable_hash(evidence)
        drive = {
            "schema_version": "1.0.0",
            "observation_id": f"versioned_gap_drive_{evidence_sha[:24]}",
            "game_id": first["game_id"],
            "drive_id": drive_id,
            "canonical_game_id": first["canonical_game_id"],
            "season": season,
            "drive_result": drive_result,
            "source_play_rows": len(rows),
            "first_source_row_number": first["source_row_number"],
            "last_source_row_number": last["source_row_number"],
            "first_period": first["period"],
            "first_clock_minutes": first["clock_minutes"],
            "first_clock_seconds": first["clock_seconds"],
            "last_period": last["period"],
            "last_clock_minutes": last["clock_minutes"],
            "last_clock_seconds": last["clock_seconds"],
            "offense_team_id": drive_offense_team_id,
            "defense_team_id": drive_defense_team_id,
            "source_capture_id": capture_id,
            "source_payload_sha256": payload_sha256,
            "source_commit_sha": COMMIT_SHA,
            "source_known_at_utc": COMMIT_KNOWN_AT_UTC,
            "source_schema_sha256": source_schema,
            "source_record_evidence_sha256": evidence_sha,
            "current_cfbd_exact_id_match": current is not None,
            "current_cfbd_result_match": bool(current and (current.get("drive_result") or "").strip().upper() == (drive_result or "").strip().upper()),
            "current_cfbd_drive_result": current.get("drive_result") if current else None,
            "current_cfbd_reported_plays": as_int(current.get("plays_reported")) if current else None,
            "current_cfbd_reported_yards": as_int(current.get("yards_reported")) if current else None,
            "upstream_independence": "NOT_CLAIMED_SHARED_ESPN_DERIVATION_POSSIBLE",
            "admission_state": "DEVELOPMENT_PIT_ELIGIBLE" if identity_valid else "QUARANTINED",
            "reconciliation_disposition": disposition,
            "downstream_pit_contract": "DEVELOPMENT_ONLY; source_known_at_utc <= cutoff; source_game_id != target_game_id",
        }
        drive["row_lineage_sha256"] = stable_hash(drive)
        drives.append(drive)

    population = {
        "source_rows": table.num_rows,
        "normalized_play_rows": len(plays),
        "play_disposition_counts": dict(sorted(dispositions.items())),
        "repository_games": len({row["game_id"] for row in plays}),
        "canonical_games": len({row["canonical_game_id"] for row in plays if row["canonical_game_id"]}),
        "exact_cfbd_play_id_matches": exact_id_matches,
        "unique_cfbd_content_signature_matches": exact_content_matches,
        "repository_drives": len(drives),
        "drive_disposition_counts": dict(sorted(drive_dispositions.items())),
        "exact_cfbd_drive_id_matches": sum(row["current_cfbd_exact_id_match"] for row in drives),
        "exact_cfbd_drive_result_matches": sum(row["current_cfbd_result_match"] for row in drives),
        "supplemental_play_rows": len(supplemental_play_ids),
        "supplemental_drive_rows": len(supplemental_drives),
        "supplemental_only_games": len(
            {str(row["source_game_id"]) for row in supplemental_drives.values()}
            - {row["game_id"] for row in plays}
        ),
    }
    return plays, drives, population


def payload_contract(path: Path, root: Path, table: pa.Table, role: str, season: int) -> dict[str, Any]:
    return {
        "role": role,
        "season": season,
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "rows": table.num_rows,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "schema_sha256": schema_sha256(table),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()

    commit_path = args.download_dir / f"commit_{COMMIT_SHA}.json"
    if sha256_file(commit_path) != COMMIT_API_SHA256:
        raise ValueError("commit API capture SHA-256 mismatch")
    commit = json.loads(commit_path.read_text(encoding="utf-8"))
    if commit["sha"] != COMMIT_SHA or commit["commit"]["committer"]["date"] != COMMIT_KNOWN_AT_UTC:
        raise ValueError("commit identity or committer timestamp mismatch")

    registry_path = (
        args.data_root / "canonical" / "BAT-387" / "sha256" / CANONICAL_REGISTRY_SHA256 / "canonical_core_registry.csv"
    )
    if sha256_file(registry_path) != CANONICAL_REGISTRY_SHA256:
        raise ValueError("canonical registry SHA-256 mismatch")
    games, team_ids = load_registry(registry_path)
    builder_sha = sha256_file(Path(__file__))
    contract_path = args.repo_root / "configs" / "versioned_play_drive_gap_contract.json"
    contract_sha = sha256_file(contract_path)
    identity_contract = {
        "decision_unit": "POST-SUBTASK-183",
        "commit_sha": COMMIT_SHA,
        "commit_known_at_utc": COMMIT_KNOWN_AT_UTC,
        "commit_api_sha256": COMMIT_API_SHA256,
        "source_payloads": SOURCE_FILES,
        "canonical_registry_sha256": CANONICAL_REGISTRY_SHA256,
        "supplemental_identity": SUPPLEMENTAL_IDENTITY,
        "contract_sha256": contract_sha,
        "builder_sha256": builder_sha,
    }
    dataset_identity = stable_hash(identity_contract)
    output_root = args.data_root / "quarantine" / "historical_known_at" / "sha256" / dataset_identity
    payloads: list[dict[str, Any]] = []
    population: dict[str, Any] = {}
    capture_ids: dict[str, str] = {}

    commit_raw = args.data_root / "raw" / "historical_known_at" / "github" / "sha256" / COMMIT_API_SHA256 / "commit.json"
    immutable_copy(commit_path, commit_raw, COMMIT_API_SHA256)
    for season, expected in SOURCE_FILES.items():
        source = args.download_dir / f"play_by_play_{season}.parquet"
        if source.stat().st_size != expected["bytes"] or sha256_file(source) != expected["sha256"]:
            raise ValueError(f"source payload identity mismatch: {season}")
        if pq.ParquetFile(source).metadata.num_rows != expected["rows"]:
            raise ValueError(f"source row count mismatch: {season}")
        raw_payload = (
            args.data_root / "raw" / "historical_known_at" / "github" / "sha256" / expected["sha256"] / "payload.parquet"
        )
        immutable_copy(source, raw_payload, expected["sha256"])
        capture_contract = {
            "schema_version": "1.0.0",
            "capture_type": "IMMUTABLE_REPOSITORY_VERSION_EVIDENCE",
            "decision_unit": "POST-SUBTASK-183",
            "jira_key": "BAT-540",
            "repository": "sportsdataverse/cfbfastR-data",
            "source_path": f"pbp/parquet/play_by_play_{season}.parquet",
            "source_url": f"https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/{COMMIT_SHA}/pbp/parquet/play_by_play_{season}.parquet",
            "season": season,
            "domain": "play_drive",
            "commit_sha": COMMIT_SHA,
            "commit_committer_date": COMMIT_KNOWN_AT_UTC,
            "known_at_evidence_class": "GIT_COMMITTER_DATE_IN_PUBLIC_REPOSITORY_HISTORY",
            "historical_known_at_candidate": COMMIT_KNOWN_AT_UTC,
            "payload": {
                "bytes": expected["bytes"],
                "sha256": expected["sha256"],
                "logical_path": f"<external-data-root>/raw/historical_known_at/github/sha256/{expected['sha256']}/payload.parquet",
            },
            "commit_api_capture": {
                "api_sha256": COMMIT_API_SHA256,
                "logical_path": f"<external-data-root>/raw/historical_known_at/github/sha256/{COMMIT_API_SHA256}/commit.json",
                "api_url": f"https://api.github.com/repos/sportsdataverse/cfbfastR-data/commits/{COMMIT_SHA}",
            },
            "acquired_at_utc": args.issued_at_utc,
            "admission_state": "CAPTURED_PENDING_RECORD_LEVEL_GATE",
        }
        capture_id = stable_hash(
            {key: value for key, value in capture_contract.items() if key != "acquired_at_utc"}
        )
        capture_contract["capture_id"] = capture_id
        capture_ids[str(season)] = capture_id
        immutable_json(args.data_root / "manifests" / "historical_known_at" / "captures" / f"{capture_id}.json", capture_contract)

        supplemental_play_ids, supplemental_signatures, supplemental_drives = load_supplemental(args.data_root, season)
        plays, drives, season_population = normalize_season(
            season=season,
            source_path=raw_payload,
            capture_id=capture_id,
            payload_sha256=expected["sha256"],
            games=games,
            team_ids=team_ids,
            supplemental_play_ids=supplemental_play_ids,
            supplemental_signatures=supplemental_signatures,
            supplemental_drives=supplemental_drives,
        )
        play_path = output_root / "plays" / f"season={season}" / "candidate_play_rows.parquet"
        drive_path = output_root / "drives" / f"season={season}" / "candidate_drive_rows.parquet"
        play_table = immutable_parquet(play_path, plays)
        drive_table = immutable_parquet(drive_path, drives)
        payloads.append(payload_contract(play_path, args.data_root, play_table, "VERSION_BOUND_PLAY_ROWS", season))
        payloads.append(payload_contract(drive_path, args.data_root, drive_table, "VERSION_BOUND_DRIVE_ROWS", season))
        population[str(season)] = season_population

    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "VERSIONED_PLAY_DRIVE_GAP_RECONCILIATION_MANIFEST",
        "decision_unit": "POST-SUBTASK-183",
        "jira_key": "BAT-540",
        "dataset_identity": dataset_identity,
        "issued_at_utc": args.issued_at_utc,
        "identity_contract": identity_contract,
        "capture_ids": capture_ids,
        "population": population,
        "payloads": payloads,
        "authority": {
            "immutable_raw_capture": True,
            "historical_known_at_eligible": True,
            "canonical_game_identity_required": True,
            "canonical_team_identity_required": True,
            "development_pit_admission": True,
            "preliminary_unprotected_candidate": True,
            "protected_training_admission": False,
            "protected_evaluation_admission": False,
            "champion_or_production_promotion": False,
        },
        "negative_findings": [
            "The immutable repository row populations do not equal the later CFBD supplemental capture populations; unmatched rows remain explicitly measured.",
            "Cross-route exact play IDs are incomplete, especially in 2011, because historical sequence identifiers differ; repository admission therefore relies on immutable repository evidence plus exact canonical game and source-team identities, not a fabricated one-to-one claim.",
            "A small measured set of 2020 supplemental games is absent from the pinned repository payload and is not promoted by this work unit.",
            "No repository row from 2023-2025 is admitted, and no target-game or future information enters this source layer.",
            "Authority remains development-only PIT and preliminary unprotected research; protected and production authority remain closed.",
        ],
    }
    manifest_path = (
        args.data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / dataset_identity
        / "versioned_play_drive_gap_reconciliation.json"
    )
    immutable_json(manifest_path, manifest)
    print(json.dumps({
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "capture_ids": capture_ids,
        "population": population,
        "payloads": payloads,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
