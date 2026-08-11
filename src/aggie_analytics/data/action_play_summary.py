from __future__ import annotations

"""Deterministic recovery of play-summary candidates from paired WMT actions."""

import hashlib
import json
from typing import Any


POLICY_VERSION = "tamu-action-derived-play-summary-v1"
SEMANTIC_PAIR_FIELDS = (
    "game_id",
    "game_period_id",
    "period_number",
    "play_number",
    "play_by_play_text",
    "game_drive_id",
    "game_drive_number",
    "down_no",
    "location",
    "context",
    "yard_line",
    "yards_to_go",
    "home_score",
    "visitor_score",
    "scoring_play",
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def action_record(source_row: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(source_row["normalized_record_json"])
    action = payload.get("action")
    if not isinstance(action, dict):
        raise ValueError("normalized source row does not contain an action object")
    return action


def summary_group_key(source_row: dict[str, Any]) -> tuple[str, int | None, int | None]:
    action = action_record(source_row)
    return (
        str(source_row["wmt_game_id"]),
        action.get("period_number"),
        action.get("play_number"),
    )


def _source_ref(source_row: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": source_row["record_id"],
        "record_ordinal": int(source_row["record_ordinal"]),
        "json_pointer": source_row["source_json_pointer"],
        "record_sha256": source_row["source_record_sha256"],
        "record_evidence_sha256": source_row["source_record_evidence_sha256"],
        "response_sha256": source_row["source_response_sha256"],
        "capture_id": source_row["source_capture_id"],
        "capture_manifest_path": source_row["source_capture_manifest_path"],
        "action_id": str(action.get("id")),
    }


def classify_summary_pair(
    start_row: dict[str, Any] | None,
    end_row: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    """Return (CANDIDATE|EXCLUDED, a fully lineaged deterministic record)."""

    reasons: list[str] = []
    if start_row is None:
        reasons.append("START_RECORD_MISSING")
    if end_row is None:
        reasons.append("END_RECORD_MISSING")
    representative = start_row or end_row
    if representative is None:
        raise ValueError("at least one source row is required")

    start = action_record(start_row) if start_row is not None else None
    end = action_record(end_row) if end_row is not None else None
    if start is not None:
        if start.get("play_action_type") != "play":
            reasons.append("START_ACTION_TYPE_NOT_PLAY")
        if start.get("play_action_sub_type") != "start":
            reasons.append("START_ACTION_SUBTYPE_INVALID")
        if not isinstance(start.get("play_by_play_text"), str) or not start["play_by_play_text"].strip():
            reasons.append("PLAY_TEXT_MISSING_OR_EMPTY")
        try:
            positive_play_number = int(start.get("play_number")) > 0
        except (TypeError, ValueError):
            positive_play_number = False
        if not positive_play_number:
            reasons.append("PLAY_NUMBER_NOT_POSITIVE")
        if start.get("game_drive_number") is None:
            reasons.append("DRIVE_NUMBER_MISSING")
        if str(start.get("game_id")) != str(start_row["wmt_game_id"]):
            reasons.append("SOURCE_GAME_ID_MISMATCH")
    if end is not None:
        if end.get("play_action_type") != "play":
            reasons.append("END_ACTION_TYPE_NOT_PLAY")
        if end.get("play_action_sub_type") != "end":
            reasons.append("END_ACTION_SUBTYPE_INVALID")
        if str(end.get("game_id")) != str(end_row["wmt_game_id"]):
            reasons.append("SOURCE_GAME_ID_MISMATCH")
    if start is not None and end is not None:
        if any(start.get(field) != end.get(field) for field in SEMANTIC_PAIR_FIELDS):
            reasons.append("PAIR_SEMANTIC_MISMATCH")
        if str(end.get("play_by_play_id")) != str(start.get("id")):
            reasons.append("END_NOT_LINKED_TO_START")
        if summary_group_key(start_row) != summary_group_key(end_row):
            reasons.append("PAIR_GROUP_KEY_MISMATCH")

    reasons = list(dict.fromkeys(reasons))
    source_start = _source_ref(start_row, start) if start_row is not None and start is not None else None
    source_end = _source_ref(end_row, end) if end_row is not None and end is not None else None
    common = {
        "schema_version": "1.0.0",
        "policy_version": POLICY_VERSION,
        "season": int(representative["season"]),
        "wmt_game_id": str(representative["wmt_game_id"]),
        "boxscore_id": str(representative["boxscore_id"]),
        "game_date": representative.get("game_date"),
        "game_date_utc": representative.get("game_date_utc"),
        "native_play_collection_present": False,
        "source_domain": "actions",
        "source_start": source_start,
        "source_end": source_end,
        "historical_known_at_state": representative["historical_known_at_state"],
        "historical_known_at_eligible": False,
        "canonical_admission": False,
        "pit_state_admission": False,
        "feature_or_training_admission": False,
        "protected_evaluation_admission": False,
        "forecast_or_publication_admission": False,
    }
    if reasons:
        result = {
            **common,
            "grain": "ACTION_PLAY_SUMMARY_GROUP_EXCLUSION",
            "period_number": start.get("period_number") if start is not None else end.get("period_number"),
            "play_number": start.get("play_number") if start is not None else end.get("play_number"),
            "reason_codes": reasons,
            "reconciliation_disposition": "EXCLUDED_ACTION_PLAY_SUMMARY_GROUP",
        }
        result["exclusion_lineage_sha256"] = stable_hash(result)
        return "EXCLUDED", result

    assert start is not None and end is not None
    identity = {
        "policy_version": POLICY_VERSION,
        "wmt_game_id": str(representative["wmt_game_id"]),
        "period_number": int(start["period_number"]),
        "play_number": int(start["play_number"]),
        "source_start_record_evidence_sha256": source_start["record_evidence_sha256"],
        "source_end_record_evidence_sha256": source_end["record_evidence_sha256"],
    }
    result = {
        **common,
        "candidate_id": "action_play_summary_" + stable_hash(identity)[:24],
        "grain": "GAME_PERIOD_PLAY_NUMBER_ACTION_DERIVED_SUMMARY",
        "period_number": int(start["period_number"]),
        "play_number": int(start["play_number"]),
        "drive_id": None if start.get("game_drive_id") is None else str(start["game_drive_id"]),
        "drive_number": int(start["game_drive_number"]),
        "play_text": start["play_by_play_text"].strip(),
        "down": start.get("down_no"),
        "location": start.get("location"),
        "context": start.get("context"),
        "yard_line": start.get("yard_line"),
        "yards_to_go": start.get("yards_to_go"),
        "home_score": start.get("home_score"),
        "visitor_score": start.get("visitor_score"),
        "scoring_play": start.get("scoring_play"),
        "reconciliation_disposition": "CANDIDATE_PAIRED_ACTION_DERIVED_PLAY_SUMMARY",
    }
    result["row_lineage_sha256"] = stable_hash(result)
    return "CANDIDATE", result
