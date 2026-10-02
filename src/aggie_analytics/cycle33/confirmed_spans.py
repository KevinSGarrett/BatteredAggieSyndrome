"""Confirmed appointments require same-record person/role evidence.

STRING_LOCATED / locatable-on-page is not CONFIRMED. Empty titles are
name observations only. Preserve predecessor cells; successors quarantine
unsupported confirmations.
"""

from __future__ import annotations

from typing import Any, Mapping

from aggie_analytics.cycle33.span_locate import bind_person_role


class ConfirmedSpanError(ValueError):
    """Raised when a CONFIRMED cell cannot be bound to a same-record role."""


def require_locatable_confirmed(
    html: str, *, person: str, title: str = ""
) -> dict[str, Any]:
    found = bind_person_role(html, person=person, title=title)
    if not str(title or "").strip():
        raise ConfirmedSpanError(
            "CONFIRMED assignment requires an explicit linked title/claim"
        )
    if found.get("person_record_bound") is not True:
        raise ConfirmedSpanError(
            "CONFIRMED assignment requires a person bound to one staff record"
        )
    if not role_support_is_confirmed(found):
        raise ConfirmedSpanError(
            "CONFIRMED assignment requires the claimed role on the same record"
        )
    return found


def role_support_is_confirmed(episode: Mapping[str, Any]) -> bool:
    """A role is supported only by the Boolean `True`, never by truthiness.

    MR34-03 repair: `role_claim_supported` is a scientific assertion, so its
    type is part of its meaning. Python truthiness accepts the string
    `"false"`, the integer `1` and any nonempty string as support -- and the
    string `"false"` asserts the OPPOSITE of what truthiness reads from it.
    A value that is not exactly `True` is unsupported or malformed; both fail
    closed, and neither may confirm a role.
    """

    return episode.get("role_claim_supported") is True


def quarantine_unlocatable_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    """Downgrade CONFIRMED rows whose episodes are not same-record supported."""

    disposition = str(cell.get("disposition") or "")
    if disposition not in {"CONFIRMED_APPOINTMENT", "CONFIRMED_CO_SHARED_ROLE"}:
        return dict(cell)
    episodes = list(cell.get("episode_refs") or [])
    supported = [ep for ep in episodes if role_support_is_confirmed(ep)]
    if supported and len(supported) == len(episodes):
        return {**dict(cell), "span_adjudicated": True}
    if supported:
        # MR33-05 repair: every non-supported episode is quarantined, whether
        # or not it happens to be "locatable" on the page -- locatable-but-
        # unsupported observations must not silently vanish from both arrays.
        # len(episode_refs) + len(quarantined_unlocatable_episodes) == the
        # original episode count is an invariant, not a side effect.
        unsupported = [ep for ep in episodes if not role_support_is_confirmed(ep)]
        return {
            **dict(cell),
            "episode_refs": supported,
            "quarantined_unlocatable_episodes": unsupported,
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
