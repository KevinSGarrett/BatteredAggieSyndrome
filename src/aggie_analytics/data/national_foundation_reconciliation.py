from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

# Independent reconciliation of the national capture foundation.
#
# Nothing here is a point-in-time admission. Capture time is not historical
# publication time, and a verified raw inventory is not national completeness.
# The normalized game table produced here is a reference candidate only.

SCHEMA_VERSION = "aggie.data.national_foundation_reconciliation.v1"
CONTRACT_RELATIVE = "configs/national_foundation_reconciliation_contract.json"
CONTRACT_ID = "BAT-651-NATIONAL-FOUNDATION-RECONCILIATION-V2"
GATE_RELATIVE = "artifacts/data_lake/national_foundation_reconciliation_gate.json"
EVIDENCE_RELATIVE = (
    "artifacts/jira_evidence/POST-TASK-NATIONAL-FOUNDATION-RECONCILIATION-V2-001.json"
)
PASS_RESULT = "PASS_NATIONAL_FOUNDATION_RECONCILED_NORMALIZED_CANDIDATE_ONLY"
CLASSIFICATION = "NATIONAL_FOUNDATION_RECONCILIATION_AND_NORMALIZED_GAME_CANDIDATE"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

HISTORICAL_KNOWN_AT_STATE = (
    "CAPTURE_TIME_KNOWN; SOURCE_PUBLICATION_AND_FINAL_WHISTLE_TIMES_UNKNOWN"
)

ELIGIBILITY_STATES = (
    "RAW_CAPTURED",
    "NORMALIZED_CANDIDATE",
    "CANONICAL_ENTITY_RESOLVED",
    "OUTCOME_REFERENCE_ELIGIBLE",
    "PIT_FEATURE_ELIGIBLE",
    "DEVELOPMENT_MATRIX_ELIGIBLE",
    "PROTECTED_ELIGIBLE",
    "QUARANTINED",
    "SOURCE_ABSENT",
)

NORMALIZED_GAME_FIELDS = (
    "canonical_game_id",
    "source_id",
    "source_game_id",
    "season",
    "season_type",
    "week",
    "neutral_site",
    "conference_game",
    "venue_id",
    "venue_name",
    "home_team_source_id",
    "home_team_name",
    "home_conference",
    "home_classification",
    "away_team_source_id",
    "away_team_name",
    "away_conference",
    "away_classification",
    "start_date_utc_text",
    "start_time_tbd",
    "completed",
    "home_points",
    "away_points",
    "attendance",
)

# The outcome label is materialized separately from the game/feature row so no
# consumer can accidentally join a postgame result onto a pregame surface.
OUTCOME_LABEL_FIELDS = (
    "canonical_game_id",
    "season",
    "home_points",
    "away_points",
    "point_margin_home_minus_away",
    "outcome_result",
    "outcome_reference_eligible",
)

QUARANTINE_FIELDS = ("canonical_game_id", "source_game_id", "season", "reason_code", "detail")

# Issue time and producer environment are recorded but never identity-bearing, so a
# rebuild at a different wall-clock time stays byte-identical where it matters.
NON_AUTHORITATIVE_MANIFEST_KEYS = frozenset({"issued_at_utc", "producer"})

NON_FINAL_TOKENS = ("canceled", "cancelled", "postponed", "suspended")

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "capture_inventory",
    "classification",
    "contract_id",
    "contract_sha256",
    "dataset_identity",
    "decision_unit",
    "domain_coverage",
    "eligibility_census",
    "gap_002",
    "jira_key",
    "manifest",
    "normalized_inventory",
    "parent_jira_key",
    "payloads",
    "protected_lane",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "source_identities",
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding_identity(payload: Mapping[str, Any], identity_field: str) -> str:
    """Identity as the cross-surface binding validator recomputes it."""
    reduced = {key: value for key, value in payload.items() if key != identity_field}
    encoded = json.dumps(
        reduced, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def manifest_authoritative_sha256(manifest: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            key: value
            for key, value in manifest.items()
            if key not in NON_AUTHORITATIVE_MANIFEST_KEYS
        }
    )


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _require_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned input: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"pinned input SHA-256 drift: {path}")


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("national foundation reconciliation contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("national foundation reconciliation schema drift")
    if list(contract.get("eligibility_states") or []) != list(ELIGIBILITY_STATES):
        raise ValueError("eligibility state vocabulary drift")
    authority = contract["authority"]
    if authority.get("national_foundation_reconciliation_use") is not True:
        raise ValueError("national foundation reconciliation authority is not enabled")
    for key in (
        "historical_pit_admission",
        "pregame_feature_use",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"national foundation authority is open: {key}")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("protected lane must remain blocked")
    return contract


def _coverage_season(entry: Mapping[str, Any]) -> int | None:
    season = entry.get("coverage", {}).get("season")
    return int(season) if isinstance(season, (int, float)) else None


def build_capture_inventory(
    *, data_root: Path, master_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Rehash every declared capture and classify it. Absence is recorded, never assumed away."""
    records: list[dict[str, Any]] = []
    for entry in master_manifest["snapshot_index"]:
        content = entry["content_identity"]
        coverage = entry.get("coverage", {})
        relative = content["external_relative_path"]
        path = data_root / relative
        declared_sha = content["sha256"]
        declared_bytes = int(content["bytes"])
        if not path.is_file():
            state, observed_sha, observed_bytes = "SOURCE_ABSENT", None, None
        else:
            observed_bytes = path.stat().st_size
            observed_sha = sha256_file(path)
            if observed_bytes != declared_bytes or observed_sha != declared_sha:
                state = "QUARANTINED"
            else:
                state = "RAW_CAPTURED"
        records.append(
            {
                "snapshot_id": entry["snapshot_id"],
                "source_id": entry["source_contract"]["source_id"],
                "relative_path": relative,
                "declared_sha256": declared_sha,
                "declared_bytes": declared_bytes,
                "observed_sha256": observed_sha,
                "observed_bytes": observed_bytes,
                "grain": coverage.get("grain"),
                "season": _coverage_season(entry),
                "row_count": int(coverage.get("row_count") or 0),
                "domain_uses": sorted(coverage.get("domain_uses") or []),
                "pit_eligibility_declared": entry.get("quality_and_eligibility", {}).get(
                    "pit_eligibility"
                ),
                "capture_state": state,
            }
        )
    records.sort(key=lambda row: row["snapshot_id"])

    by_state = Counter(row["capture_state"] for row in records)
    by_source = Counter(row["source_id"] for row in records)
    verified = [row for row in records if row["capture_state"] == "RAW_CAPTURED"]
    seasons = sorted({row["season"] for row in verified if row["season"] is not None})
    duplicate_payload_sha256 = sum(
        count - 1
        for count in Counter(row["declared_sha256"] for row in records).values()
        if count > 1
    )
    return {
        "records": records,
        "summary": {
            "declared_captures": len(records),
            "verified_captures": len(verified),
            "absent_captures": by_state.get("SOURCE_ABSENT", 0),
            "quarantined_captures": by_state.get("QUARANTINED", 0),
            "verified_payload_bytes": sum(row["observed_bytes"] or 0 for row in verified),
            "declared_payload_bytes": sum(row["declared_bytes"] for row in records),
            "duplicate_payload_sha256": duplicate_payload_sha256,
            "captures_by_source": dict(sorted(by_source.items())),
            "captures_by_state": dict(sorted(by_state.items())),
            "observed_season_range": [seasons[0], seasons[-1]] if seasons else [],
            "observed_season_count": len(seasons),
        },
    }


def build_domain_coverage(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    captures: Counter[str] = Counter()
    rows: Counter[str] = Counter()
    seasons: defaultdict[str, set[int]] = defaultdict(set)
    for record in records:
        if record["capture_state"] != "RAW_CAPTURED":
            continue
        for domain in record["domain_uses"]:
            captures[domain] += 1
            rows[domain] += record["row_count"]
            if record["season"] is not None:
                seasons[domain].add(record["season"])
    return {
        domain: {
            "verified_captures": captures[domain],
            "declared_source_rows": rows[domain],
            "season_count": len(seasons[domain]),
            "season_range": (
                [min(seasons[domain]), max(seasons[domain])] if seasons[domain] else []
            ),
        }
        for domain in sorted(captures)
    }


def _outcome_result(home_points: int | None, away_points: int | None) -> str | None:
    if home_points is None or away_points is None:
        return None
    if home_points > away_points:
        return "HOME_WIN"
    if home_points < away_points:
        return "AWAY_WIN"
    return "TIE"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_game_row(
    row: Mapping[str, Any], *, source_id: str, protected_seasons: frozenset[int]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (normalized_row, quarantine_row). Exactly one is populated."""
    source_game_id = _int(row.get("id"))
    season = _int(row.get("season"))
    canonical_game_id = f"{source_id}:GAME:{source_game_id}"

    def reject(reason_code: str, detail: str) -> tuple[None, dict[str, Any]]:
        return None, {
            "canonical_game_id": canonical_game_id,
            "source_game_id": source_game_id,
            "season": season,
            "reason_code": reason_code,
            "detail": detail,
        }

    if source_game_id is None:
        return reject("MISSING_SOURCE_GAME_ID", "source row has no usable integer id")
    if season is None:
        return reject("MISSING_SEASON", "source row has no usable integer season")
    home_name = _text(row.get("homeTeam"))
    away_name = _text(row.get("awayTeam"))
    if home_name is None or away_name is None:
        return reject("MISSING_TEAM_IDENTITY", "home or away team name is absent")
    if home_name == away_name:
        return reject("SELF_MATCHUP", f"home and away resolve to the same team: {home_name}")
    notes = " ".join(filter(None, (_text(row.get("notes")), _text(row.get("seasonType"))))).lower()
    for token in NON_FINAL_TOKENS:
        if token in notes:
            return reject("NON_FINAL_GAME", f"source row carries a {token} marker")

    home_points = _int(row.get("homePoints"))
    away_points = _int(row.get("awayPoints"))
    completed = bool(row.get("completed"))
    if completed and (home_points is None or away_points is None):
        return reject("COMPLETED_WITHOUT_SCORES", "completed game is missing a final score")
    if not completed and (home_points is not None or away_points is not None):
        return reject("SCORES_WITHOUT_COMPLETION", "incomplete game carries a score")

    normalized = {
        "canonical_game_id": canonical_game_id,
        "source_id": source_id,
        "source_game_id": source_game_id,
        "season": season,
        "season_type": _text(row.get("seasonType")),
        "week": _int(row.get("week")),
        "neutral_site": bool(row.get("neutralSite")),
        "conference_game": bool(row.get("conferenceGame")),
        "venue_id": _int(row.get("venueId")),
        "venue_name": _text(row.get("venue")),
        "home_team_source_id": _int(row.get("homeId")),
        "home_team_name": home_name,
        "home_conference": _text(row.get("homeConference")),
        "home_classification": _text(row.get("homeClassification")),
        "away_team_source_id": _int(row.get("awayId")),
        "away_team_name": away_name,
        "away_conference": _text(row.get("awayConference")),
        "away_classification": _text(row.get("awayClassification")),
        "start_date_utc_text": _text(row.get("startDate")),
        "start_time_tbd": bool(row.get("startTimeTBD")),
        "completed": completed,
        "home_points": home_points,
        "away_points": away_points,
        "attendance": _int(row.get("attendance")),
        "_protected": season in protected_seasons,
    }
    return normalized, None


def _missingness(rows: list[Mapping[str, Any]], fields: Iterable[str]) -> dict[str, int]:
    return {field: sum(1 for row in rows if row.get(field) is None) for field in fields}


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    contract_bytes = (repo_root / CONTRACT_RELATIVE).read_bytes()
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    protected_seasons = frozenset(int(year) for year in contract["protected_seasons"])
    development_season = int(contract["development_season"])

    master_path = repo_root / source["master_manifest_relative_path"]
    _require_file(master_path, source["master_manifest_sha256"])
    _require_file(
        data_root / source["cfbd_acquisition_manifest_relative_path"],
        source["cfbd_acquisition_manifest_sha256"],
    )
    _require_file(
        data_root / source["sportsdataverse_manifest_relative_path"],
        source["sportsdataverse_manifest_sha256"],
    )
    _require_file(
        repo_root / source["source_acquisition_registry_relative_path"],
        source["source_acquisition_registry_sha256"],
    )
    master_manifest = _read_json(master_path)

    inventory = build_capture_inventory(data_root=data_root, master_manifest=master_manifest)
    summary = inventory["summary"]
    if summary["declared_captures"] != int(acceptance["expected_snapshot_count"]):
        raise ValueError(
            f"declared capture count drift: {summary['declared_captures']} != "
            f"{acceptance['expected_snapshot_count']}"
        )
    if summary["declared_payload_bytes"] != int(acceptance["expected_payload_bytes"]):
        raise ValueError("declared payload byte drift against the pinned acceptance total")
    if sorted(summary["captures_by_source"]) != sorted(acceptance["expected_source_ids"]):
        raise ValueError("national source route drift")
    if summary["absent_captures"] or summary["quarantined_captures"]:
        raise ValueError(
            "national foundation reconciliation failed closed: "
            f"{summary['absent_captures']} absent and "
            f"{summary['quarantined_captures']} tampered captures"
        )
    if summary["observed_season_range"] != list(acceptance["expected_season_range"]):
        raise ValueError("observed season range drift")

    domain_coverage = build_domain_coverage(inventory["records"])

    game_captures = [
        record
        for record in inventory["records"]
        if record["grain"] == "GAME" and record["capture_state"] == "RAW_CAPTURED"
    ]
    if len(game_captures) != int(acceptance["expected_game_grain_captures"]):
        raise ValueError("GAME-grain capture count drift")

    normalized: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    source_rows = 0
    for record in game_captures:
        payload = _read_json(data_root / record["relative_path"])
        if not isinstance(payload, list):
            raise ValueError(f"GAME capture is not a JSON array: {record['relative_path']}")
        if len(payload) != record["row_count"]:
            raise ValueError(f"GAME capture row-count drift: {record['relative_path']}")
        source_rows += len(payload)
        for row in payload:
            accepted, rejected = normalize_game_row(
                row, source_id=record["source_id"], protected_seasons=protected_seasons
            )
            if accepted is not None:
                normalized.append(accepted)
            else:
                quarantined.append(rejected)
    if source_rows != int(acceptance["expected_game_grain_source_rows"]):
        raise ValueError(f"GAME-grain source row drift: {source_rows}")

    seen: dict[str, dict[str, Any]] = {}
    deduplicated: list[dict[str, Any]] = []
    for row in normalized:
        key = row["canonical_game_id"]
        previous = seen.get(key)
        if previous is None:
            seen[key] = row
            deduplicated.append(row)
            continue
        if canonical_json_bytes(previous) == canonical_json_bytes(row):
            quarantined.append(
                {
                    "canonical_game_id": key,
                    "source_game_id": row["source_game_id"],
                    "season": row["season"],
                    "reason_code": "DUPLICATE_IDENTICAL_GAME",
                    "detail": "byte-identical duplicate canonical game row",
                }
            )
        else:
            quarantined.append(
                {
                    "canonical_game_id": key,
                    "source_game_id": row["source_game_id"],
                    "season": row["season"],
                    "reason_code": "DUPLICATE_CONFLICTING_GAME",
                    "detail": "duplicate canonical game id with conflicting attributes",
                }
            )
    deduplicated.sort(key=lambda row: (row["season"], row["source_game_id"]))
    quarantined.sort(
        key=lambda row: (row["season"] or -1, row["reason_code"], row["source_game_id"] or -1)
    )

    # Team alias census: one canonical source team id may surface several names.
    alias_map: defaultdict[int, set[str]] = defaultdict(set)
    unresolved_team_identities = 0
    for row in deduplicated:
        for id_field, name_field in (
            ("home_team_source_id", "home_team_name"),
            ("away_team_source_id", "away_team_name"),
        ):
            team_id = row[id_field]
            if team_id is None:
                unresolved_team_identities += 1
            else:
                alias_map[team_id].add(row[name_field])
    alias_groups = sorted(team_id for team_id, names in alias_map.items() if len(names) > 1)
    alias_rows = sum(len(alias_map[team_id]) for team_id in alias_groups)

    game_rows = [
        {field: row[field] for field in NORMALIZED_GAME_FIELDS} for row in deduplicated
    ]
    outcome_rows: list[dict[str, Any]] = []
    for row in deduplicated:
        if not row["completed"]:
            continue
        eligible = (
            not row["_protected"]
            and row["home_points"] is not None
            and row["away_points"] is not None
        )
        outcome_rows.append(
            {
                "canonical_game_id": row["canonical_game_id"],
                "season": row["season"],
                "home_points": row["home_points"],
                "away_points": row["away_points"],
                "point_margin_home_minus_away": row["home_points"] - row["away_points"],
                "outcome_result": _outcome_result(row["home_points"], row["away_points"]),
                "outcome_reference_eligible": eligible,
            }
        )

    canonical_entity_resolved = sum(
        1
        for row in deduplicated
        if row["home_team_source_id"] is not None and row["away_team_source_id"] is not None
    )
    outcome_reference_eligible = sum(1 for row in outcome_rows if row["outcome_reference_eligible"])
    development_matrix_eligible = sum(
        1
        for row in outcome_rows
        if row["outcome_reference_eligible"] and row["season"] == development_season
    )
    protected_excluded = sum(1 for row in deduplicated if row["_protected"])

    eligibility_census = {
        "RAW_CAPTURED": summary["verified_captures"],
        "NORMALIZED_CANDIDATE": len(game_rows),
        "CANONICAL_ENTITY_RESOLVED": canonical_entity_resolved,
        "OUTCOME_REFERENCE_ELIGIBLE": outcome_reference_eligible,
        # Historical known-at is unproven, so no row may enter a PIT feature surface.
        "PIT_FEATURE_ELIGIBLE": 0,
        "DEVELOPMENT_MATRIX_ELIGIBLE": development_matrix_eligible,
        # 2024/2025 remain sealed.
        "PROTECTED_ELIGIBLE": 0,
        "QUARANTINED": len(quarantined),
        "SOURCE_ABSENT": summary["absent_captures"],
    }
    if sorted(eligibility_census) != sorted(ELIGIBILITY_STATES):
        raise ValueError("eligibility census does not cover the declared state vocabulary")
    if eligibility_census["PIT_FEATURE_ELIGIBLE"] != 0:
        raise ValueError("historical PIT feature admission is closed and must stay at zero")
    if eligibility_census["PROTECTED_ELIGIBLE"] != 0:
        raise ValueError("protected admission is sealed and must stay at zero")

    rows_by_season = Counter(row["season"] for row in game_rows)
    normalized_inventory = {
        "table_name": contract["normalized_successor"]["name"],
        "grain": "GAME",
        "rows": len(game_rows),
        "source_rows": source_rows,
        "quarantined_rows": len(quarantined),
        "quarantine_reasons": dict(sorted(Counter(r["reason_code"] for r in quarantined).items())),
        "duplicate_canonical_game_ids": sum(
            1 for r in quarantined if r["reason_code"].startswith("DUPLICATE_")
        ),
        "team_alias_groups": len(alias_groups),
        "team_alias_rows": alias_rows,
        "unresolved_team_identities": unresolved_team_identities,
        "distinct_source_team_ids": len(alias_map),
        "seasons": sorted(rows_by_season),
        "rows_by_season": {str(season): rows_by_season[season] for season in sorted(rows_by_season)},
        "protected_rows_excluded_from_labels": protected_excluded,
        "outcome_label_rows": len(outcome_rows),
        "missingness_game_fields": _missingness(game_rows, NORMALIZED_GAME_FIELDS),
        "missingness_outcome_fields": _missingness(outcome_rows, OUTCOME_LABEL_FIELDS),
    }

    record_hashes = {
        "capture_inventory": stable_hash(inventory["records"]),
        "normalized_games": stable_hash(game_rows),
        "outcome_labels": stable_hash(outcome_rows),
        "quarantine": stable_hash(quarantined),
    }
    module_path = Path(__file__).resolve()
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "builder_sha256": sha256_file(module_path),
            "master_manifest_sha256": source["master_manifest_sha256"],
            "cfbd_manifest_sha256": source["cfbd_acquisition_manifest_sha256"],
            "sportsdataverse_manifest_sha256": source["sportsdataverse_manifest_sha256"],
            "registry_sha256": source["source_acquisition_registry_sha256"],
            "record_hashes": record_hashes,
            "classification": CLASSIFICATION,
        }
    )

    return {
        "contract": contract,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identity": sha256_file(module_path),
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "capture_inventory": inventory,
        "domain_coverage": domain_coverage,
        "normalized_inventory": normalized_inventory,
        "eligibility_census": eligibility_census,
        "game_rows": game_rows,
        "outcome_rows": outcome_rows,
        "quarantined": quarantined,
    }


def _gap_002_verdict(expected: Mapping[str, Any]) -> dict[str, Any]:
    """GAP-002 cannot close on file existence. It closes on PIT-eligible materialization."""
    census = expected["eligibility_census"]
    return {
        "state": "OPEN",
        "materially_advanced": True,
        "advance": (
            "Every declared national capture was independently rehashed and a deterministic "
            f"normalized national game candidate of {census['NORMALIZED_CANDIDATE']} rows was "
            "materialized from the GAME-grain capture route."
        ),
        "why_still_open": (
            "Historical source-publication and final-whistle times remain unproven, so "
            "PIT_FEATURE_ELIGIBLE is zero. A normalized reference candidate is not a "
            "PIT-admitted national population."
        ),
        "closure_requires": [
            "Proven historical known-at basis for every admitted feature domain",
            "Chronological replay with target-game exclusion over the normalized population",
            "Domain-level PIT admission beyond outcome reference candidates",
        ],
        "file_existence_alone_closes_gap": False,
    }


def build_gate(
    *, expected: Mapping[str, Any], manifest_entry: Mapping[str, Any], payloads: list[dict[str, Any]]
) -> dict[str, Any]:
    contract = expected["contract"]
    summary = expected["capture_inventory"]["summary"]
    source = contract["source_contract"]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_FOUNDATION_RECONCILIATION_GATE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": payloads,
        "capture_inventory": summary,
        "domain_coverage": expected["domain_coverage"],
        "normalized_inventory": expected["normalized_inventory"],
        "eligibility_census": expected["eligibility_census"],
        "source_identities": {
            "master_manifest_sha256": source["master_manifest_sha256"],
            "cfbd_acquisition_manifest_sha256": source["cfbd_acquisition_manifest_sha256"],
            "sportsdataverse_manifest_sha256": source["sportsdataverse_manifest_sha256"],
            "source_acquisition_registry_sha256": source["source_acquisition_registry_sha256"],
            "source_acquisition_registry_sha256_recorded_in_master_manifest": source[
                "source_acquisition_registry_sha256_recorded_in_master_manifest"
            ],
            "source_acquisition_registry_drifted_since_master_manifest": (
                source["source_acquisition_registry_sha256"]
                != source["source_acquisition_registry_sha256_recorded_in_master_manifest"]
            ),
            "historical_known_at_state": HISTORICAL_KNOWN_AT_STATE,
        },
        "authority": contract["authority"],
        "gap_002": _gap_002_verdict(expected),
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "trained_production_champion": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = expected["dataset_identity"]

    canonical_root = data_root / "canonical" / "national_foundation_reconciliation" / "sha256" / identity
    quarantine_root = data_root / "quarantine" / "national_foundation_reconciliation" / "sha256" / identity
    manifest_root = data_root / "manifests" / "national_foundation_reconciliation" / "sha256" / identity

    written: list[tuple[str, str, Path, bytes]] = [
        (
            "national_capture_inventory.jsonl",
            "NATIONAL_CAPTURE_INVENTORY",
            canonical_root / "national_capture_inventory.jsonl",
            _jsonl_bytes(expected["capture_inventory"]["records"]),
        ),
        (
            "national_normalized_games.jsonl",
            "NATIONAL_NORMALIZED_GAME_CANDIDATE",
            canonical_root / "national_normalized_games.jsonl",
            _jsonl_bytes(expected["game_rows"]),
        ),
        (
            "national_game_outcome_labels.jsonl",
            "NATIONAL_GAME_OUTCOME_REFERENCE_CANDIDATE",
            canonical_root / "national_game_outcome_labels.jsonl",
            _jsonl_bytes(expected["outcome_rows"]),
        ),
        (
            "national_normalization_quarantine.jsonl",
            "NATIONAL_NORMALIZATION_QUARANTINE",
            quarantine_root / "national_normalization_quarantine.jsonl",
            _jsonl_bytes(expected["quarantined"]),
        ),
    ]

    payloads: list[dict[str, Any]] = []
    for name, role, path, payload_bytes in written:
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": payload_bytes.count(b"\n"),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_FOUNDATION_RECONCILIATION_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "classification": CLASSIFICATION,
        "capture_inventory": expected["capture_inventory"]["summary"],
        "domain_coverage": expected["domain_coverage"],
        "normalized_inventory": expected["normalized_inventory"],
        "eligibility_census": expected["eligibility_census"],
        "record_hashes": expected["record_hashes"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": expected["code_identity"],
            "contract_sha256": expected["contract_sha256"],
        },
    }
    manifest_path = manifest_root / "national_foundation_reconciliation_manifest.json"
    manifest_bytes = canonical_json_bytes(manifest) + b"\n"
    _write_bytes(manifest_path, manifest_bytes)

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate_payloads = [
        {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")} for item in payloads
    ]
    gate = build_gate(expected=expected, manifest_entry=manifest_entry, payloads=gate_payloads)
    _write_bytes(repo_root / GATE_RELATIVE, canonical_json_bytes(gate) + b"\n")
    return {"gate": gate, "manifest": manifest, "expected": expected}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate if gate is not None else _read_json(repo_root / GATE_RELATIVE))
    if gate.get("result") != PASS_RESULT:
        raise ValueError(f"national foundation gate is not passing: {gate.get('result')}")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("national foundation gate opened the protected lane")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value is not False:
            raise ValueError(f"national foundation gate asserted a forbidden claim: {key}")
    if gate.get("gap_002", {}).get("state") != "OPEN":
        raise ValueError("GAP-002 cannot be closed by this reconciliation")
    if gate.get("eligibility_census", {}).get("PIT_FEATURE_ELIGIBLE") != 0:
        raise ValueError("gate admitted PIT features while historical known-at is unproven")
    if not require_rebuild:
        return {"result": "PASS", "mode": "SCHEMA_ONLY", "gate_identity": gate.get("gate_identity")}

    if expected is None:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    manifest_path = data_root / gate["manifest"]["relative_path"]
    manifest = dict(manifest if manifest is not None else _read_json(manifest_path))

    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("eligibility_census", gate["eligibility_census"], expected["eligibility_census"], errors)
    _compare("normalized_inventory", gate["normalized_inventory"], expected["normalized_inventory"], errors)
    _compare("domain_coverage", gate["domain_coverage"], expected["domain_coverage"], errors)
    _compare(
        "capture_inventory",
        gate["capture_inventory"],
        expected["capture_inventory"]["summary"],
        errors,
    )
    _compare("manifest.record_hashes", manifest.get("record_hashes"), expected["record_hashes"], errors)
    if manifest_authoritative_sha256(manifest) != gate["manifest"].get("authoritative_sha256"):
        errors.append("manifest authoritative content drift")

    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest.get("payloads", []) if item["name"] == payload["name"]),
            None,
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    reconstructed = {key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate}
    if len(reconstructed) != len(GATE_IDENTITY_FIELDS):
        errors.append("gate is missing identity-bearing fields")
    elif compute_gate_identity(gate) != gate.get("gate_identity"):
        errors.append("gate identity does not match its own identity-bearing fields")
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        errors.append("cross-surface binding identity drift")

    if errors:
        raise ValueError(
            "independent national foundation validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
    }
