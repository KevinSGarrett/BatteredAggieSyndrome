"""Proposed GameContextV2 / StaffSnapshotV2 packet checks.

Adoption is pending C01/CFIP owners. These tests do not activate shared contracts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

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


class ContractV2Error(ValueError):
    """Raised when a proposed packet is invalid or silently squeezed."""


def load_game_schema() -> dict[str, Any]:
    return json.loads(GAME_SCHEMA_PATH.read_text(encoding="utf-8"))


def round_trip_game_context(packet: Mapping[str, Any]) -> dict[str, Any]:
    schema = load_game_schema()
    allowed = set(schema["properties"])
    missing = [field for field in GAME_REQUIRED if field not in packet]
    if missing:
        raise ContractV2Error(f"GameContextV2 missing required fields: {missing}")
    extra = [key for key in packet if key not in allowed]
    if extra:
        raise ContractV2Error(f"GameContextV2 unknown fields: {extra}")
    if packet["site_class"] not in GAME_SITE:
        raise ContractV2Error("invalid site_class")
    if packet["site_class"] == "NEUTRAL" and packet.get(
        "ordinary_home_exposure_designated_home"
    ) not in {0, None}:
        raise ContractV2Error("verified neutral cannot carry ordinary HFA")
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
    if str(packet["program_id"]).startswith("DISPLAY:"):
        raise ContractV2Error("DISPLAY: identities are not canonical")
    if packet.get("attempted") is True and int(packet.get("attempt_count") or 0) == 0:
        raise ContractV2Error("literal attempted:true without ledger count")
    encoded = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"))
    restored = json.loads(encoded)
    again = json.dumps(restored, sort_keys=True, separators=(",", ":"))
    if again != encoded:
        raise ContractV2Error("StaffSnapshotV2 round trip mutated the packet")
    return restored


def reject_missing_release_bom(consumed: bool, bom_present: bool) -> None:
    if consumed and not bom_present:
        raise ContractV2Error("C01 consumption blocked until release/BOM pass")
