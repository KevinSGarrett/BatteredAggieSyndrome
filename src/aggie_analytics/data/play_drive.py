from __future__ import annotations

"""Deterministic candidate normalization for historical CFBD plays and drives."""

import hashlib
import json
from typing import Any, Mapping


PLAY_POLICY_VERSION = "cfbd-supplemental-play-candidate-v1"
DRIVE_POLICY_VERSION = "cfbd-supplemental-drive-candidate-v1"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def clock_parts(value: object) -> tuple[int | None, int | None]:
    if not isinstance(value, Mapping):
        return None, None
    return optional_int(value.get("minutes")), optional_int(value.get("seconds"))


def _base_candidate(
    *,
    domain: str,
    season: int,
    source_game_id: str | None,
    canonical_game_id: str | None,
    source_record_id: str | None,
    raw: Mapping[str, Any],
    source_context: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_core = {
        "source_response_sha256": source_context["source_response_sha256"],
        "source_row_number": int(source_context["source_row_number"]),
        "source_record_sha256": stable_hash(raw),
    }
    return {
        "schema_version": "1.0.0",
        "observation_id": f"cfbd_{domain}_" + stable_hash(evidence_core)[:24],
        "domain": domain,
        "season": season,
        "source_system_id": "SRC-002",
        "source_game_id": source_game_id,
        "canonical_game_id": canonical_game_id,
        "source_record_id": source_record_id,
        "source_request_id": source_context["source_request_id"],
        "source_capture_id": source_context["source_capture_id"],
        "source_response_sha256": source_context["source_response_sha256"],
        "source_immutable_path": source_context["source_immutable_path"],
        "source_row_number": int(source_context["source_row_number"]),
        "source_retrieved_at_utc": source_context["source_retrieved_at_utc"],
        "source_capture_known_at_utc": source_context["source_capture_known_at_utc"],
        "source_season_type": source_context["source_season_type"],
        "source_record_evidence_sha256": evidence_core["source_record_sha256"],
        "historical_publication_time_state": "UNKNOWN",
        "historical_known_at_eligible": False,
        "canonical_or_pit_admission": False,
        "feature_or_training_admission": False,
        "protected_use_admission": False,
        "target_game_feature_admission": False,
    }


def normalize_play_candidate(
    *,
    season: int,
    raw: Mapping[str, Any],
    canonical_game_id: str | None,
    known_drive_ids: set[str],
    source_context: Mapping[str, Any],
) -> dict[str, Any]:
    source_game_id = optional_text(raw.get("gameId"))
    source_play_id = optional_text(raw.get("id"))
    source_drive_id = optional_text(raw.get("driveId"))
    clock_minutes, clock_seconds = clock_parts(raw.get("clock"))
    if not source_game_id or not source_play_id or not source_drive_id:
        disposition = "QUARANTINE_INVALID_PLAY_CORE"
    elif canonical_game_id is None:
        disposition = "QUARANTINE_CANONICAL_GAME_ID_MISSING"
    elif source_drive_id not in known_drive_ids:
        disposition = "QUARANTINE_DRIVE_LINK_MISSING"
    else:
        disposition = "CANDIDATE_EXACT_CANONICAL_GAME_AND_DRIVE"
    row = {
        **_base_candidate(
            domain="plays",
            season=season,
            source_game_id=source_game_id,
            canonical_game_id=canonical_game_id,
            source_record_id=source_play_id,
            raw=raw,
            source_context=source_context,
        ),
        "source_play_id": source_play_id,
        "source_drive_id": source_drive_id,
        "period": optional_int(raw.get("period")),
        "clock_minutes": clock_minutes,
        "clock_seconds": clock_seconds,
        "play_number": optional_int(raw.get("playNumber")),
        "drive_number": optional_int(raw.get("driveNumber")),
        "home_team_label": optional_text(raw.get("home")),
        "away_team_label": optional_text(raw.get("away")),
        "offense_team_label": optional_text(raw.get("offense")),
        "defense_team_label": optional_text(raw.get("defense")),
        "offense_conference_label": optional_text(raw.get("offenseConference")),
        "defense_conference_label": optional_text(raw.get("defenseConference")),
        "offense_score": optional_int(raw.get("offenseScore")),
        "defense_score": optional_int(raw.get("defenseScore")),
        "down": optional_int(raw.get("down")),
        "distance": optional_int(raw.get("distance")),
        "yardline": optional_int(raw.get("yardline")),
        "yards_to_goal": optional_int(raw.get("yardsToGoal")),
        "yards_gained": optional_int(raw.get("yardsGained")),
        "play_type": optional_text(raw.get("playType")),
        "play_text": optional_text(raw.get("playText")),
        "scoring": bool(raw.get("scoring")) if raw.get("scoring") is not None else None,
        "ppa_source": optional_float(raw.get("ppa")),
        "wallclock_source": optional_text(raw.get("wallclock")),
        "reconciliation_disposition": disposition,
        "quarantined": disposition.startswith("QUARANTINE_"),
        "policy_version": PLAY_POLICY_VERSION,
    }
    row["row_lineage_sha256"] = stable_hash(row)
    return row


def normalize_drive_candidate(
    *,
    season: int,
    raw: Mapping[str, Any],
    canonical_game_id: str | None,
    play_linked_drive_ids: set[str],
    source_context: Mapping[str, Any],
) -> dict[str, Any]:
    source_game_id = optional_text(raw.get("gameId"))
    source_drive_id = optional_text(raw.get("id"))
    start_minutes, start_seconds = clock_parts(raw.get("startTime"))
    end_minutes, end_seconds = clock_parts(raw.get("endTime"))
    elapsed_minutes, elapsed_seconds = clock_parts(raw.get("elapsed"))
    if not source_game_id or not source_drive_id:
        disposition = "QUARANTINE_INVALID_DRIVE_CORE"
    elif canonical_game_id is None:
        disposition = "QUARANTINE_CANONICAL_GAME_ID_MISSING"
    elif source_drive_id not in play_linked_drive_ids:
        disposition = "CANDIDATE_EXACT_CANONICAL_GAME_DRIVE_WITHOUT_PLAY_ROWS"
    else:
        disposition = "CANDIDATE_EXACT_CANONICAL_GAME_AND_PLAY_LINKS"
    row = {
        **_base_candidate(
            domain="drives",
            season=season,
            source_game_id=source_game_id,
            canonical_game_id=canonical_game_id,
            source_record_id=source_drive_id,
            raw=raw,
            source_context=source_context,
        ),
        "source_drive_id": source_drive_id,
        "drive_number": optional_int(raw.get("driveNumber")),
        "offense_team_label": optional_text(raw.get("offense")),
        "defense_team_label": optional_text(raw.get("defense")),
        "offense_conference_label": optional_text(raw.get("offenseConference")),
        "defense_conference_label": optional_text(raw.get("defenseConference")),
        "is_home_offense": bool(raw.get("isHomeOffense")) if raw.get("isHomeOffense") is not None else None,
        "drive_result": optional_text(raw.get("driveResult")),
        "scoring": bool(raw.get("scoring")) if raw.get("scoring") is not None else None,
        "plays_reported": optional_int(raw.get("plays")),
        "yards_reported": optional_int(raw.get("yards")),
        "start_period": optional_int(raw.get("startPeriod")),
        "start_clock_minutes": start_minutes,
        "start_clock_seconds": start_seconds,
        "start_yardline": optional_int(raw.get("startYardline")),
        "start_yards_to_goal": optional_int(raw.get("startYardsToGoal")),
        "start_offense_score": optional_int(raw.get("startOffenseScore")),
        "start_defense_score": optional_int(raw.get("startDefenseScore")),
        "end_period": optional_int(raw.get("endPeriod")),
        "end_clock_minutes": end_minutes,
        "end_clock_seconds": end_seconds,
        "end_yardline": optional_int(raw.get("endYardline")),
        "end_yards_to_goal": optional_int(raw.get("endYardsToGoal")),
        "end_offense_score": optional_int(raw.get("endOffenseScore")),
        "end_defense_score": optional_int(raw.get("endDefenseScore")),
        "elapsed_minutes": elapsed_minutes,
        "elapsed_seconds": elapsed_seconds,
        "play_rows_present": source_drive_id in play_linked_drive_ids if source_drive_id else False,
        "reconciliation_disposition": disposition,
        "quarantined": disposition.startswith("QUARANTINE_"),
        "policy_version": DRIVE_POLICY_VERSION,
    }
    row["row_lineage_sha256"] = stable_hash(row)
    return row
