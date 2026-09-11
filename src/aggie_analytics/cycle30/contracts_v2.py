"""Proposed GameContextV2 / StaffSnapshotV2 packet checks.

Adoption is pending C01/CFIP owners. These tests do not activate shared contracts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.cycle30.temporal import TemporalError, parse_aware_utc

ROOT = Path(__file__).resolve().parents[3]
GAME_SCHEMA_PATH = (
    ROOT / "docs" / "contracts" / "proposed" / "GameContextV2.schema.json"
)

GAME_REQUIRED = (
    "canonical_game_id",
    "source_order",
    "canonical_home_id",
    "canonical_away_id",
    "designated_home_id",
    "site_class",
    "ordinary_home_exposure_designated_home",
    "unknowns",
)
GAME_SITE = {"NEUTRAL", "NON_NEUTRAL", "UNKNOWN", "CONFLICT"}
STAFF_REQUIRED = (
    "program_id",
    "as_of_utc",
    "role",
    "formal_title",
    "responsibility",
    "episode_refs",
    "episode_cardinality",
    "disposition",
    "attempt_count",
    "pit_admitted",
)
STAFF_OPTIONAL = (
    "source_id",
    "source_span_id",
    "source_receipt_id",
    "role_scope",
    "notes",
    "bas_episode_extension",
)
STAFF_ALLOWED = set(STAFF_REQUIRED + STAFF_OPTIONAL)
STAFF_ROLE = {"head_coach", "offensive_coordinator", "defensive_coordinator"}
STAFF_DISPOSITION = {
    "CONFIRMED_SINGLE_OCCUPANT",
    "CONFIRMED_CO_SHARED_ROLE",
    "SEQUENTIAL_MULTI_OCCUPANT",
    "CONFLICTING_CANDIDATES",
    "UNKNOWN_NOT_LISTED",
    "ACQUISITION_FAILED",
    "NOT_ATTEMPTED",
}
STAFF_RESPONSIBILITY = {"UNKNOWN", "UNVERIFIED", "ROLE_FAMILY_ONLY"}


class ContractV2Error(ValueError):
    """Raised when a proposed packet is invalid or silently squeezed."""


def load_game_schema() -> dict[str, Any]:
    return json.loads(GAME_SCHEMA_PATH.read_text(encoding="utf-8"))


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not str(value).strip() or value.strip().lower() in {"none", "null"}:
        raise ContractV2Error(f"GameContextV2 {field} must be a non-empty string")
    return value


def _require_natural_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractV2Error(f"StaffSnapshotV2 {field} must be a genuine integer")
    if value < 0:
        raise ContractV2Error(f"StaffSnapshotV2 {field} cannot be negative")
    return value


def _require_finite_number(value: Any, field: str, *, allow_null: bool = True) -> float | None:
    if value is None:
        if allow_null:
            return None
        raise ContractV2Error(f"{field} cannot be null")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractV2Error(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ContractV2Error(f"{field} must be finite")
    return number


def round_trip_game_context(packet: Mapping[str, Any]) -> dict[str, Any]:
    schema = load_game_schema()
    allowed = set(schema["properties"])
    missing = [field for field in GAME_REQUIRED if field not in packet]
    if missing:
        raise ContractV2Error(f"GameContextV2 missing required fields: {missing}")
    extra = [key for key in packet if key not in allowed]
    if extra:
        raise ContractV2Error(f"GameContextV2 unknown fields: {extra}")
    game_id = packet.get("canonical_game_id")
    _require_nonempty_string(game_id, "canonical_game_id")
    source_order = packet.get("source_order")
    if not isinstance(source_order, list) or len(source_order) != 2:
        raise ContractV2Error("GameContextV2 source_order must be a two-team array")
    if any(not isinstance(item, str) or not item.strip() for item in source_order):
        raise ContractV2Error("GameContextV2 source_order identities must be strings")
    home = _require_nonempty_string(packet.get("canonical_home_id"), "canonical_home_id")
    away = _require_nonempty_string(packet.get("canonical_away_id"), "canonical_away_id")
    if home == away:
        raise ContractV2Error("GameContextV2 participants must be distinct")
    designated = packet.get("designated_home_id")
    _require_nonempty_string(designated, "designated_home_id")
    if designated not in {home, away}:
        raise ContractV2Error("designated home is not a contest participant")
    if packet["site_class"] not in GAME_SITE:
        raise ContractV2Error("invalid site_class")
    if packet["site_class"] == "NEUTRAL" and packet.get(
        "ordinary_home_exposure_designated_home"
    ) not in {0, 0.0, None}:
        raise ContractV2Error("verified neutral cannot carry ordinary HFA")
    unknowns = packet.get("unknowns")
    if not isinstance(unknowns, list):
        raise ContractV2Error("GameContextV2 unknowns must be an array")
    lat = _require_finite_number(packet.get("venue_latitude"), "venue_latitude")
    lon = _require_finite_number(packet.get("venue_longitude"), "venue_longitude")
    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise ContractV2Error("impossible venue latitude")
    if lon is not None and not (-180.0 <= lon <= 180.0):
        raise ContractV2Error("impossible venue longitude")
    for travel_field in ("travel_home_km", "travel_away_km"):
        distance = _require_finite_number(packet.get(travel_field), travel_field)
        if distance is not None and distance < 0:
            raise ContractV2Error(f"{travel_field} cannot be negative")
    encoded = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"))
    restored = json.loads(encoded)
    again = json.dumps(restored, sort_keys=True, separators=(",", ":"))
    if again != encoded:
        raise ContractV2Error("GameContextV2 round trip mutated the packet")
    return restored


def reject_v1_squeeze(packet: Mapping[str, Any], dropped_unknowns: bool) -> None:
    if dropped_unknowns or "unknowns" not in packet or "site_class" not in packet:
        raise ContractV2Error(
            "unknown or neutral fields must not be dropped to pass GameContextV1"
        )


def round_trip_staff_snapshot(packet: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in STAFF_REQUIRED if field not in packet]
    if missing:
        raise ContractV2Error(f"StaffSnapshotV2 missing required fields: {missing}")
    extra = [key for key in packet if key not in STAFF_ALLOWED]
    if extra:
        raise ContractV2Error(f"StaffSnapshotV2 unknown fields: {extra}")
    program_id = packet.get("program_id")
    if not isinstance(program_id, str) or not program_id.strip():
        raise ContractV2Error("StaffSnapshotV2 program_id must be a non-empty string")
    if program_id.startswith("DISPLAY:"):
        raise ContractV2Error("DISPLAY: identities are not canonical")
    if packet["role"] not in STAFF_ROLE:
        raise ContractV2Error("StaffSnapshotV2 unsupported role")
    if packet["disposition"] not in STAFF_DISPOSITION:
        raise ContractV2Error("StaffSnapshotV2 unsupported disposition")
    if packet["responsibility"] not in STAFF_RESPONSIBILITY:
        raise ContractV2Error("StaffSnapshotV2 unsupported responsibility")
    try:
        parse_aware_utc(str(packet["as_of_utc"]))
    except TemporalError as exc:
        raise ContractV2Error("StaffSnapshotV2 as_of_utc must be aware UTC") from exc
    attempts = _require_natural_int(packet.get("attempt_count"), "attempt_count")
    if packet.get("attempted") is True and attempts == 0:
        raise ContractV2Error("literal attempted:true without ledger count")
    if not isinstance(packet["pit_admitted"], bool):
        raise ContractV2Error("StaffSnapshotV2 pit_admitted must be boolean")
    if packet["pit_admitted"]:
        raise ContractV2Error("StaffSnapshotV2 cannot claim PIT admission")
    episode_refs = packet["episode_refs"]
    if not isinstance(episode_refs, list):
        raise ContractV2Error("StaffSnapshotV2 episode_refs must be a list")
    if any((not isinstance(ref, str)) or (not ref.strip()) for ref in episode_refs):
        raise ContractV2Error("StaffSnapshotV2 episode_refs must be non-empty strings")
    if len(episode_refs) != len(set(episode_refs)):
        raise ContractV2Error("StaffSnapshotV2 episode_refs must be unique")
    episode_cardinality = _require_natural_int(
        packet["episode_cardinality"], "episode_cardinality"
    )
    if episode_cardinality != len(episode_refs):
        raise ContractV2Error(
            "StaffSnapshotV2 episode_cardinality must match episode_refs"
        )
    if packet["disposition"] == "CONFIRMED_SINGLE_OCCUPANT" and len(episode_refs) != 1:
        raise ContractV2Error(
            "confirmed-single requires exactly one supported episode"
        )
    encoded = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"))
    restored = json.loads(encoded)
    again = json.dumps(restored, sort_keys=True, separators=(",", ":"))
    if again != encoded:
        raise ContractV2Error("StaffSnapshotV2 round trip mutated the packet")
    return restored


def reject_missing_release_bom(consumed: bool, bom_present: bool) -> None:
    if consumed and not bom_present:
        raise ContractV2Error("C01 consumption blocked until release/BOM pass")


_BAS_TO_V2_DISPOSITION = {
    "CONFIRMED_APPOINTMENT": "CONFIRMED_SINGLE_OCCUPANT",
    "CONFIRMED_CO_SHARED_ROLE": "CONFIRMED_CO_SHARED_ROLE",
    "UNKNOWN_NOT_LISTED": "UNKNOWN_NOT_LISTED",
    "ACQUISITION_FAILED": "ACQUISITION_FAILED",
    "NOT_ATTEMPTED": "NOT_ATTEMPTED",
    "CANDIDATE_ONLY": "CONFLICTING_CANDIDATES",
    "CONFIRMED_SINGLE_OCCUPANT": "CONFIRMED_SINGLE_OCCUPANT",
    "SEQUENTIAL_MULTI_OCCUPANT": "SEQUENTIAL_MULTI_OCCUPANT",
    "CONFLICTING_CANDIDATES": "CONFLICTING_CANDIDATES",
}


def staff_snapshot_v2_from_bas_matrix_cell(
    cell: Mapping[str, Any], *, as_of_utc: str | None = None
) -> dict[str, Any]:
    """Convert a BAS role-matrix cell into StaffSnapshotV2 without dropping episodes."""

    refs = cell.get("episode_refs") or []
    string_refs: list[str] = []
    extension: list[dict[str, Any]] = []
    for episode in refs:
        if isinstance(episode, str):
            if not episode.strip():
                raise ContractV2Error("empty episode ref")
            string_refs.append(episode)
            continue
        if not isinstance(episode, Mapping):
            raise ContractV2Error("BAS episode refs must be strings or objects")
        span = str(episode.get("span_id") or "").strip()
        if not span:
            raise ContractV2Error("BAS episode object is missing span_id")
        string_refs.append(span)
        extension.append(dict(episode))
    if len(string_refs) != len(set(string_refs)):
        raise ContractV2Error("duplicate episode refs")
    source_disposition = str(cell.get("disposition") or "")
    disposition = _BAS_TO_V2_DISPOSITION.get(source_disposition)
    if disposition is None:
        raise ContractV2Error(f"unsupported BAS disposition {source_disposition}")
    if source_disposition == "CONFIRMED_APPOINTMENT" and len(string_refs) != 1:
        disposition = (
            "CONFIRMED_CO_SHARED_ROLE"
            if len(string_refs) > 1
            else "UNKNOWN_NOT_LISTED"
        )
    titles = [
        str(item.get("source_title") or item.get("title") or "")
        for item in refs
        if isinstance(item, Mapping)
    ]
    formal_title = next((title for title in titles if title), None)
    packet = {
        "program_id": cell.get("program_id"),
        "as_of_utc": as_of_utc or cell.get("as_of_utc"),
        "role": cell.get("role"),
        "formal_title": formal_title,
        "responsibility": "ROLE_FAMILY_ONLY",
        "episode_refs": string_refs,
        "episode_cardinality": len(string_refs),
        "disposition": disposition,
        "attempt_count": cell.get("attempt_count") if cell.get("attempt_count") is not None else 0,
        "pit_admitted": False,
        "bas_episode_extension": extension,
    }
    return round_trip_staff_snapshot(packet)
