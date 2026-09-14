"""Employer/person identity joins. Substring membership is not identity."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

GENERIC_TOKENS = frozenset(
    {
        "university",
        "univ",
        "the",
        "of",
        "and",
        "u",
    }
)
# Distinctive names where stripping "college"/"state" would collide.
PROTECTED_PHRASES = (
    "boston college",
    "boston university",
    "virginia tech",
    "virginia military",
    "miami (oh)",
    "miami (fl)",
    "miami ohio",
    "miami florida",
)

ALIAS_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"virginia", "university of virginia", "uva"}),
    frozenset({"virginia tech", "virginia polytechnic", "vpi", "hokies"}),
    frozenset({"texas a&m", "texas am", "tamu", "texas a and m"}),
    frozenset({"miami (fl)", "miami florida", "miami fl"}),
    frozenset({"miami (oh)", "miami ohio", "miami oh"}),
)


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _tokens(text: str) -> tuple[str, ...]:
    folded = _fold(text).replace("&", " and ")
    return tuple(re.findall(r"[a-z0-9]+", folded))


def _alias_key(text: str) -> str | None:
    folded = _fold(text)
    if not folded:
        return None
    for group in ALIAS_GROUPS:
        if folded in group:
            return sorted(group)[0]
        distinctive = tuple(tok for tok in _tokens(text) if tok not in GENERIC_TOKENS)
        for alias in group:
            alias_dist = tuple(
                tok for tok in _tokens(alias) if tok not in GENERIC_TOKENS
            )
            if distinctive and distinctive == alias_dist:
                return sorted(group)[0]
    return None


def employer_evidence_matches(employer: str, program_raw: str) -> bool:
    """Reject empty evidence. Virginia does not match Virginia Tech."""

    left_raw = str(employer or "").strip()
    right_raw = str(program_raw or "").strip()
    if not left_raw or not right_raw:
        return False
    left = _fold(left_raw)
    right = _fold(right_raw)
    if left == right:
        return True
    left_alias = _alias_key(left_raw)
    right_alias = _alias_key(right_raw)
    if left_alias and right_alias:
        return left_alias == right_alias
    left_tokens = _tokens(left_raw)
    right_tokens = _tokens(right_raw)
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    left_core = tuple(tok for tok in left_tokens if tok not in GENERIC_TOKENS)
    right_core = tuple(tok for tok in right_tokens if tok not in GENERIC_TOKENS)
    if left_core and right_core and left_core == right_core:
        protected_left = any(phrase in left for phrase in PROTECTED_PHRASES)
        protected_right = any(phrase in right for phrase in PROTECTED_PHRASES)
        if protected_left or protected_right:
            return left == right or left_alias == right_alias
        return True
    return False


def page_identity_key(page: Mapping[str, Any]) -> str:
    """Wikimedia page/person identity, not revision identity."""

    for field in (
        "wikimedia_page_id",
        "page_id",
        "pageid",
        "canonical_title",
        "title",
        "requested_title",
    ):
        value = page.get(field)
        if value not in {None, ""}:
            return f"{field}:{value}"
    return f"opaque:{id(page)}"


def football_career_context(page: Mapping[str, Any]) -> dict[str, Any]:
    """Positive football/person context. A revision-bound page is not enough."""

    title = str(page.get("title") or page.get("requested_title") or "")
    lowered = title.casefold()
    episodes = list(page.get("episodes") or [])
    sports = {
        str(row.get("sport") or row.get("scope_sport") or "").casefold()
        for row in episodes
        if row.get("sport") or row.get("scope_sport")
    }
    other_named = any(
        token in lowered
        for token in (
            "politician",
            "disambiguation",
            "mayor",
            "senator",
            "basketball",
            "baseball",
            "soccer",
        )
    )
    football_title = "football" in lowered
    football_episode = any(
        "football" in str(row.get("sport") or row.get("scope_sport") or "").casefold()
        or "football" in str(row.get("program_raw") or "").casefold()
        for row in episodes
    )
    accepted = football_title or football_episode
    if other_named and not football_title and not football_episode:
        accepted = False
    return {
        "accepted": accepted,
        "title": title,
        "page_identity": page_identity_key(page),
        "revision": page.get("wikimedia_revision") or page.get("revision"),
        "sports": sorted(sport for sport in sports if sport),
        "episode_count": len(episodes),
        "revision_bound_alone_insufficient": True,
        "non_college_segments_preserved": True,
    }


def join_occupant_to_pages(
    *,
    person: str,
    employer: str,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evidence-bound career join or an exact unresolved state."""

    football_pages = [
        page for page in pages if football_career_context(page)["accepted"]
    ]
    identities = {page_identity_key(page) for page in football_pages}
    if not pages:
        state = "CAREER_PAGE_MISSING"
        page = None
    elif not football_pages:
        state = "NAME_ONLY_CANDIDATE_NOT_ACCEPTED"
        page = None
    elif len(identities) > 1:
        state = "AMBIGUOUS_MULTIPLE_FOOTBALL_PAGES"
        page = None
    else:
        page = football_pages[0]
        employer_hit = False
        if str(employer or "").strip():
            employer_hit = any(
                employer_evidence_matches(employer, str(row.get("program_raw") or ""))
                for row in (page.get("episodes") or [])
            )
        else:
            employer_hit = False
        state = (
            "EVIDENCE_BOUND_CAREER_JOIN"
            if employer_hit
            else "FOOTBALL_PAGE_EMPLOYER_UNVERIFIED"
        )
    return {
        "person": person,
        "employer": employer,
        "career_join_state": state,
        "same_name_only": state != "EVIDENCE_BOUND_CAREER_JOIN",
        "page_identity": None if page is None else page_identity_key(page),
        "cached_football_pages": len(football_pages),
        "distinct_page_identities": len(identities),
        "revision_ids_are_not_people": True,
        "pit_admitted": False,
    }
