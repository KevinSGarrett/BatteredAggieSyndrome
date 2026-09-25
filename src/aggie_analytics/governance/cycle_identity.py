"""Canonical non-floating cycle identifiers.

Integer coercion is forbidden as an identity parser: ``int(25.5)`` becomes 25,
``int("25.5")`` raises, and ``int(True)`` becomes 1. Callers must use this module
for uniqueness, ordering, and ledger mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

CANONICAL_PREFIX = "CYCLE-"
LEGACY_INTEGER_MAX_WHOLE_CYCLE = 25
CYCLE_25_5 = "CYCLE-25.5"
CYCLE_26 = "CYCLE-26"
COMMENT_14723_LEGACY_CYCLE_FIELD = 26
COMMENT_14723_CANONICAL_ID = CYCLE_25_5
COMMENT_14723_ID = "14723"


class CycleIdentityError(ValueError):
    """Raised when a cycle identifier cannot be canonically parsed."""


@dataclass(frozen=True, slots=True)
class CycleIdentity:
    canonical_id: str
    order: Decimal
    legacy_integer: int | None
    source: str


def _reject_boolean(value: Any, *, field: str) -> None:
    if isinstance(value, bool):
        raise CycleIdentityError(f"{field}: boolean cycle identifiers are forbidden")


def parse_cycle_identity(
    value: Any,
    *,
    field: str = "cycle",
    comment_id: str | None = None,
) -> CycleIdentity:
    """Parse a cycle value into a canonical identifier.

    Legacy integer 26 on comment 14723 maps to CYCLE-25.5 without rounding
    other values. Whole-number integers 1-25 map to CYCLE-N. CYCLE-25.5 is
    the only fractional identifier currently admitted.
    """
    _reject_boolean(value, field=field)
    if value is None or value == "":
        raise CycleIdentityError(f"{field}: missing cycle identity")
    if isinstance(value, float) and not value.is_integer():
        raise CycleIdentityError(
            f"{field}: raw floating cycle values are forbidden; use {CYCLE_25_5}"
        )
    if isinstance(value, int):
        if comment_id == COMMENT_14723_ID and value == COMMENT_14723_LEGACY_CYCLE_FIELD:
            return CycleIdentity(
                canonical_id=COMMENT_14723_CANONICAL_ID,
                order=Decimal("25.5"),
                legacy_integer=COMMENT_14723_LEGACY_CYCLE_FIELD,
                source="legacy_comment_14723_integer_26",
            )
        if value < 1:
            raise CycleIdentityError(f"{field}: cycle integer must be >= 1")
        if value == COMMENT_14723_LEGACY_CYCLE_FIELD:
            raise CycleIdentityError(
                f"{field}: integer 26 collides with mis-attributed comment 14723; "
                f"use {CYCLE_26} after the 25.5 attribution supersession"
            )
        return CycleIdentity(
            canonical_id=f"{CANONICAL_PREFIX}{value}",
            order=Decimal(value),
            legacy_integer=value,
            source="legacy_integer",
        )
    text = str(value).strip()
    if not text:
        raise CycleIdentityError(f"{field}: empty cycle identity")
    if text == "True" or text == "False":
        raise CycleIdentityError(f"{field}: boolean cycle identifiers are forbidden")
    upper = text.upper()
    if upper.startswith(CANONICAL_PREFIX):
        body = text[len(CANONICAL_PREFIX) :]
        if body == "25.5":
            return CycleIdentity(
                canonical_id=CYCLE_25_5,
                order=Decimal("25.5"),
                legacy_integer=None,
                source="canonical",
            )
        if body.isdigit() and int(body) >= 1:
            number = int(body)
            if number == COMMENT_14723_LEGACY_CYCLE_FIELD:
                return CycleIdentity(
                    canonical_id=CYCLE_26,
                    order=Decimal(26),
                    legacy_integer=None,
                    source="canonical",
                )
            return CycleIdentity(
                canonical_id=f"{CANONICAL_PREFIX}{number}",
                order=Decimal(number),
                legacy_integer=number,
                source="canonical",
            )
        raise CycleIdentityError(f"{field}: unsupported canonical cycle {text}")
    if text == "25.5":
        raise CycleIdentityError(
            f"{field}: use {CYCLE_25_5}; unprefixed 25.5 is not a unique identity"
        )
    if text.isdigit():
        return parse_cycle_identity(int(text), field=field, comment_id=comment_id)
    raise CycleIdentityError(f"{field}: unrecognized cycle identity {text!r}")


def cycle_order(value: Any, *, comment_id: str | None = None) -> Decimal:
    return parse_cycle_identity(value, comment_id=comment_id).order


def canonical_cycle_id(value: Any, *, comment_id: str | None = None) -> str:
    return parse_cycle_identity(value, comment_id=comment_id).canonical_id


def reject_cycle_collision(
    left: Any,
    right: Any,
    *,
    left_comment_id: str | None = None,
    right_comment_id: str | None = None,
) -> None:
    left_id = parse_cycle_identity(left, comment_id=left_comment_id)
    right_id = parse_cycle_identity(right, comment_id=right_comment_id)
    if left_id.canonical_id == right_id.canonical_id:
        raise CycleIdentityError(
            f"duplicate canonical cycle {left_id.canonical_id}"
        )


def ledger_canonical_cycle(entry: Mapping[str, Any]) -> CycleIdentity:
    comment_id = str(entry.get("comment_id") or "") or None
    if entry.get("canonical_cycle_id"):
        return parse_cycle_identity(
            entry["canonical_cycle_id"],
            field="canonical_cycle_id",
            comment_id=comment_id,
        )
    return parse_cycle_identity(
        entry.get("cycle"),
        field="cycle",
        comment_id=comment_id,
    )
