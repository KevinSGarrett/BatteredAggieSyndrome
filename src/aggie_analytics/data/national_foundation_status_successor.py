"""National-foundation scientific successor: structured status, not notes substring.

Predecessor foundation payloads are never rewritten. SRC-002:GAME:312472199 is
restored only from verified structured finality and identity, never from a
truthy completed string.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

FALSE_QUARANTINE_GAME_ID = "SRC-002:GAME:312472199"
FALSE_QUARANTINE_SOURCE_GAME_ID = 312472199
STRUCTURED_NON_FINAL_STATUS = frozenset(
    {"canceled", "cancelled", "postponed", "suspended"}
)
PREDECESSOR_NON_FINAL_TOKENS = ("canceled", "cancelled", "postponed", "suspended")
PROTECTED_SEASONS = frozenset({2024, 2025})

SCHEMA_VERSION = "aggie.data.national_foundation_status_successor.v1"
CONTRACT_ID = "CYCLE26-NATIONAL-FOUNDATION-STATUS-SUCCESSOR-V1"
JIRA_KEY = "BAT-651"
LOCAL_ISSUE_ID = "POST-TASK-NATIONAL-FOUNDATION-STATUS-SUCCESSOR-001"
CLASSIFICATION = "NATIONAL_FOUNDATION_STATUS_SUCCESSOR_CANDIDATE_ONLY"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_NATIONAL_FOUNDATION_STATUS_SUCCESSOR"
GATE_RELATIVE = "artifacts/data_lake/national_foundation_status_successor_gate.json"
PAYLOAD_SLUG = "national_foundation_status_successor"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
MASTER_MANIFEST_RELATIVE = "artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json"
PREDECESSOR_QUARANTINE_RELATIVE = (
    "quarantine/national_foundation_reconciliation/sha256/"
    "d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477/"
    "national_normalization_quarantine.jsonl"
)
PREDECESSOR_QUARANTINE_SHA256 = (
    "d60f8b93d77286f44c2bcade5e2284989c8e2fc080a3c97cdcb35985bb430680"
)
PREDECESSOR_NORMALIZED_RELATIVE = (
    "canonical/national_foundation_reconciliation/sha256/"
    "d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477/"
    "national_normalized_games.jsonl"
)
PREDECESSOR_NORMALIZED_SHA256 = (
    "8ac949ef3ecbdbc560bb8080e2f302cbd000ab96437dfafef9f1a14165d1c574"
)


class StatusSuccessorError(ValueError):
    """Raised when the structured-status successor cannot be materialized honestly."""


def _text(value: object) -> str:
    return str(value or "").strip()


def parse_completed_flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    return None


def canonical_game_id_for(row: Mapping[str, Any], *, source_id: str = "SRC-002") -> str:
    existing = _text(row.get("canonical_game_id"))
    if existing:
        if existing == str(FALSE_QUARANTINE_SOURCE_GAME_ID):
            return FALSE_QUARANTINE_GAME_ID
        return existing
    raw = row.get("id")
    if raw is None:
        raw = row.get("source_game_id")
    if raw is None or _text(raw) == "":
        return ""
    try:
        return f"{source_id}:GAME:{int(raw)}"
    except (TypeError, ValueError):
        return _text(raw)


def predecessor_substring_non_final_reason(row: Mapping[str, Any]) -> str | None:
    notes = " ".join(
        filter(None, (_text(row.get("notes")), _text(row.get("seasonType"))))
    ).lower()
    for token in PREDECESSOR_NON_FINAL_TOKENS:
        if token in notes:
            return f"source row carries a {token} marker"
    return None


def structured_non_final_reason(row: Mapping[str, Any]) -> str | None:
    status = _text(row.get("status") or row.get("gameStatus")).lower()
    if status in STRUCTURED_NON_FINAL_STATUS:
        return f"structured_status:{status}"
    completed = parse_completed_flag(row.get("completed"))
    if completed is None and row.get("completed") is not None:
        return "completed_flag_unproven"
    home_points = row.get("homePoints")
    away_points = row.get("awayPoints")
    if completed is not True:
        if home_points is not None or away_points is not None:
            return "scores_without_completion"
        return "not_completed"
    if home_points is None or away_points is None:
        return "completed_without_scores"
    return None


def classify_status_successor(row: Mapping[str, Any]) -> dict[str, Any]:
    game_id = canonical_game_id_for(row)
    predecessor = predecessor_substring_non_final_reason(row)
    structured = structured_non_final_reason(row)
    completed = parse_completed_flag(row.get("completed"))
    home_points = row.get("homePoints")
    away_points = row.get("awayPoints")
    false_quarantine = (
        game_id == FALSE_QUARANTINE_GAME_ID
        and predecessor is not None
        and structured is None
        and completed is True
        and home_points is not None
        and away_points is not None
    )
    if structured is not None:
        disposition = "QUARANTINE_STRUCTURED_NON_FINAL"
    elif false_quarantine:
        disposition = "RESTORE_FALSE_SUBSTRING_QUARANTINE"
    elif predecessor is not None and structured is None:
        disposition = "KEEP_COMPLETED_IGNORE_INCIDENTAL_NOTE_TOKEN"
    else:
        disposition = "ADMIT_COMPLETED"
    return {
        "canonical_game_id": game_id,
        "predecessor_substring_reason": predecessor,
        "structured_reason": structured,
        "false_quarantine_corrected": false_quarantine,
        "completed_flag": completed,
        "disposition": disposition,
        "protected_season": int(row.get("season") or 0) in PROTECTED_SEASONS,
    }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    lines = [
        json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for row in rows
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def _int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def outcome_result(home_points: int, away_points: int) -> str:
    if home_points > away_points:
        return "HOME_WIN"
    if home_points < away_points:
        return "AWAY_WIN"
    return "TIE"


def project_normalized_game(
    row: Mapping[str, Any], *, source_id: str = "SRC-002"
) -> dict[str, Any]:
    source_game_id = _int(
        row.get("id") if row.get("id") is not None else row.get("source_game_id")
    )
    season = _int(row.get("season"))
    home_points = _int(
        row.get("homePoints") if "homePoints" in row else row.get("home_points")
    )
    away_points = _int(
        row.get("awayPoints") if "awayPoints" in row else row.get("away_points")
    )
    completed = parse_completed_flag(row.get("completed"))
    return {
        "canonical_game_id": canonical_game_id_for(row, source_id=source_id),
        "source_id": source_id,
        "source_game_id": source_game_id,
        "season": season,
        "season_type": _optional_text(row.get("seasonType") or row.get("season_type")),
        "week": _int(row.get("week")),
        "neutral_site": bool(
            row.get("neutralSite") if "neutralSite" in row else row.get("neutral_site")
        ),
        "conference_game": bool(
            row.get("conferenceGame")
            if "conferenceGame" in row
            else row.get("conference_game")
        ),
        "venue_id": _int(
            row.get("venueId") if "venueId" in row else row.get("venue_id")
        ),
        "venue_name": _optional_text(row.get("venue") or row.get("venue_name")),
        "home_team_source_id": _int(
            row.get("homeId") if "homeId" in row else row.get("home_team_source_id")
        ),
        "home_team_name": _optional_text(
            row.get("homeTeam") or row.get("home_team_name")
        ),
        "home_conference": _optional_text(
            row.get("homeConference") or row.get("home_conference")
        ),
        "home_classification": _optional_text(
            row.get("homeClassification") or row.get("home_classification")
        ),
        "away_team_source_id": _int(
            row.get("awayId") if "awayId" in row else row.get("away_team_source_id")
        ),
        "away_team_name": _optional_text(
            row.get("awayTeam") or row.get("away_team_name")
        ),
        "away_conference": _optional_text(
            row.get("awayConference") or row.get("away_conference")
        ),
        "away_classification": _optional_text(
            row.get("awayClassification") or row.get("away_classification")
        ),
        "start_date_utc_text": _optional_text(
            row.get("startDate") or row.get("start_date_utc_text")
        ),
        "start_time_tbd": bool(
            row.get("startTimeTBD")
            if "startTimeTBD" in row
            else row.get("start_time_tbd")
        ),
        "completed": completed,
        "home_points": home_points,
        "away_points": away_points,
        "attendance": _int(row.get("attendance")),
    }


def load_predecessor_quarantine(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / PREDECESSOR_QUARANTINE_RELATIVE
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != PREDECESSOR_QUARANTINE_SHA256:
        raise StatusSuccessorError(f"predecessor quarantine rewritten: {digest}")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def load_false_quarantine_source_row(
    *, data_root: Path, repo_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    master_path = repo_root / MASTER_MANIFEST_RELATIVE
    if not master_path.is_file():
        raise StatusSuccessorError(f"missing master manifest: {master_path}")
    master = json.loads(master_path.read_text(encoding="utf-8-sig"))
    for entry in master["snapshot_index"]:
        coverage = entry.get("coverage") or {}
        if coverage.get("grain") != "GAME":
            continue
        if coverage.get("season") not in (2011, "2011"):
            continue
        relative = entry["content_identity"]["external_relative_path"]
        declared = entry["content_identity"]["sha256"]
        path = data_root / relative
        observed = sha256_file(path)
        if observed != declared:
            raise StatusSuccessorError(f"GAME capture hash drift: {relative}")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise StatusSuccessorError(f"GAME capture is not an array: {relative}")
        for row in payload:
            if _int(row.get("id")) == FALSE_QUARANTINE_SOURCE_GAME_ID:
                return dict(row), {
                    "relative_path": relative,
                    "sha256": declared,
                    "season": 2011,
                    "source_id": entry["source_contract"]["source_id"],
                }
    raise StatusSuccessorError("SRC-002:GAME:312472199 source row not found")


def restore_false_quarantine(row: Mapping[str, Any]) -> dict[str, Any]:
    classified = classify_status_successor(row)
    if classified["disposition"] != "RESTORE_FALSE_SUBSTRING_QUARANTINE":
        raise StatusSuccessorError(
            f"312472199 is not a structured restore: {classified['disposition']}"
        )
    if classified["completed_flag"] is not True:
        raise StatusSuccessorError(
            "restore rejected: completed flag is not a boolean true"
        )
    normalized = project_normalized_game(row)
    if normalized["canonical_game_id"] != FALSE_QUARANTINE_GAME_ID:
        raise StatusSuccessorError("restored identity mismatch")
    if normalized["home_points"] is None or normalized["away_points"] is None:
        raise StatusSuccessorError("restore rejected: missing scores")
    if normalized["season"] in PROTECTED_SEASONS:
        raise StatusSuccessorError("restore rejected: protected season")
    outcome = {
        "canonical_game_id": FALSE_QUARANTINE_GAME_ID,
        "season": normalized["season"],
        "home_points": normalized["home_points"],
        "away_points": normalized["away_points"],
        "point_margin_home_minus_away": normalized["home_points"]
        - normalized["away_points"],
        "outcome_result": outcome_result(
            int(normalized["home_points"]), int(normalized["away_points"])
        ),
        "outcome_reference_eligible": True,
        "pit_feature_eligible": False,
        "protected_eligible": False,
        "trust_classification": SHADOW_CLASSIFICATION,
        "successor_contract_id": CONTRACT_ID,
    }
    restored = dict(normalized)
    restored["eligibility_state"] = "OUTCOME_REFERENCE_ELIGIBLE"
    restored["pit_feature_eligible"] = False
    restored["predecessor_reason_code"] = "NON_FINAL_GAME"
    restored["successor_disposition"] = classified["disposition"]
    restored["false_quarantine_corrected"] = True
    restored["trust_classification"] = SHADOW_CLASSIFICATION
    restored["successor_contract_id"] = CONTRACT_ID
    restored["predecessor_rewritten"] = False
    return {
        "classification": classified,
        "normalized_game": restored,
        "outcome_label": outcome,
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    quarantine = load_predecessor_quarantine(data_root)
    if len(quarantine) != 1:
        raise StatusSuccessorError(
            f"expected 1 predecessor quarantine row, got {len(quarantine)}"
        )
    if quarantine[0].get("canonical_game_id") != FALSE_QUARANTINE_GAME_ID:
        raise StatusSuccessorError("predecessor quarantine identity drift")
    normalized_digest = sha256_file(data_root / PREDECESSOR_NORMALIZED_RELATIVE)
    if normalized_digest != PREDECESSOR_NORMALIZED_SHA256:
        raise StatusSuccessorError("predecessor normalized games rewritten")
    source_row, capture = load_false_quarantine_source_row(
        data_root=data_root, repo_root=repo_root
    )
    restored = restore_false_quarantine(source_row)
    game_bytes = jsonl_bytes([restored["normalized_game"]])
    outcome_bytes = jsonl_bytes([restored["outcome_label"]])
    dataset_seed = {
        "contract_id": CONTRACT_ID,
        "game_id": FALSE_QUARANTINE_GAME_ID,
        "game_sha256": sha256_bytes(game_bytes),
        "outcome_sha256": sha256_bytes(outcome_bytes),
        "source_capture_sha256": capture["sha256"],
    }
    dataset_identity = sha256_bytes(
        json.dumps(dataset_seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    payload_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / dataset_identity
    payload_root.mkdir(parents=True, exist_ok=True)
    game_name = "restored_normalized_game.jsonl"
    outcome_name = "restored_outcome_label.jsonl"
    (payload_root / game_name).write_bytes(game_bytes)
    (payload_root / outcome_name).write_bytes(outcome_bytes)
    if (
        sha256_file(data_root / PREDECESSOR_QUARANTINE_RELATIVE)
        != PREDECESSOR_QUARANTINE_SHA256
    ):
        raise StatusSuccessorError("predecessor quarantine mutated during materialize")
    if (
        sha256_file(data_root / PREDECESSOR_NORMALIZED_RELATIVE)
        != PREDECESSOR_NORMALIZED_SHA256
    ):
        raise StatusSuccessorError(
            "predecessor normalized games mutated during materialize"
        )
    gate = {
        "artifact_type": "NATIONAL_FOUNDATION_STATUS_SUCCESSOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "dataset_identity": dataset_identity,
        "predecessor_payloads_rewritten": False,
        "publication_label": SHADOW_CLASSIFICATION,
        "restored_game": {
            "canonical_game_id": FALSE_QUARANTINE_GAME_ID,
            "season": restored["normalized_game"]["season"],
            "home_team_name": restored["normalized_game"]["home_team_name"],
            "away_team_name": restored["normalized_game"]["away_team_name"],
            "home_points": restored["normalized_game"]["home_points"],
            "away_points": restored["normalized_game"]["away_points"],
            "outcome_result": restored["outcome_label"]["outcome_result"],
            "disposition": restored["classification"]["disposition"],
            "pit_feature_eligible": False,
        },
        "source_capture": capture,
        "predecessor": {
            "quarantine_relative_path": PREDECESSOR_QUARANTINE_RELATIVE,
            "quarantine_sha256": PREDECESSOR_QUARANTINE_SHA256,
            "normalized_relative_path": PREDECESSOR_NORMALIZED_RELATIVE,
            "normalized_sha256": PREDECESSOR_NORMALIZED_SHA256,
            "rewritten": False,
        },
        "payloads": {
            "restored_normalized_game": {
                "relative_path": (
                    f"canonical/{PAYLOAD_SLUG}/sha256/{dataset_identity}/{game_name}"
                ),
                "sha256": sha256_bytes(game_bytes),
                "bytes": len(game_bytes),
                "row_count": 1,
            },
            "restored_outcome_label": {
                "relative_path": (
                    f"canonical/{PAYLOAD_SLUG}/sha256/{dataset_identity}/{outcome_name}"
                ),
                "sha256": sha256_bytes(outcome_bytes),
                "bytes": len(outcome_bytes),
                "row_count": 1,
            },
        },
        "scientific_nonclaims": [
            "Does not rewrite the predecessor national foundation payloads.",
            "Does not admit PIT features; historical known-at remains unproven.",
            "Does not coerce a completed string into boolean true.",
            "Does not open the all-cycle trust gate or operator hold.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        json.dumps(
            {key: value for key, value in gate.items() if key != "gate_identity"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return gate
