"""Confirmed appointments require locatable raw spans, not string-built IDs."""

from __future__ import annotations

from typing import Any, Mapping

from aggie_analytics.cycle33.span_locate import locate_person_title


class ConfirmedSpanError(ValueError):
    """Raised when a CONFIRMED cell cannot be bound to a raw body/title offset."""


def require_locatable_confirmed(
    html: str, *, person: str, title: str = ""
) -> dict[str, Any]:
    found = locate_person_title(html, person=person, title=title)
    if not found.get("locatable"):
        raise ConfirmedSpanError(
            "CONFIRMED assignment requires locatable person/title offsets"
        )
    return found


def quarantine_unlocatable_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    """Downgrade CONFIRMED rows whose episodes are not locatable in cached HTML."""

    disposition = str(cell.get("disposition") or "")
    if disposition not in {"CONFIRMED_APPOINTMENT", "CONFIRMED_CO_SHARED_ROLE"}:
        return dict(cell)
    episodes = list(cell.get("episode_refs") or [])
    locatable = [ep for ep in episodes if ep.get("locatable")]
    if locatable and len(locatable) == len(episodes):
        return {**dict(cell), "span_adjudicated": True}
    if locatable:
        return {
            **dict(cell),
            "episode_refs": locatable,
            "quarantined_unlocatable_episodes": [
                ep for ep in episodes if not ep.get("locatable")
            ],
            "disposition": "CONFIRMED_PARTIAL_SPAN_LOCATABLE",
            "span_adjudicated": True,
            "pit_admitted": False,
        }
    return {
        **dict(cell),
        "disposition": "SPAN_NOT_LOCATABLE_QUARANTINE",
        "span_adjudicated": True,
        "pit_admitted": False,
    }
