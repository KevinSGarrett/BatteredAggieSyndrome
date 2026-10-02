"""Employer/person identity joins. Substring membership is not identity."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.coaching import wiki_career_title_matches_person

#: A page carrying no identifying field is genuinely unidentified. This is
#: a STATE, never a join key: two pages that are both unidentified are not
#: thereby the same page.
UNRESOLVED_PAGE_IDENTITY = "UNRESOLVED_PAGE_IDENTITY"

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

# MR33-04 re-repair (R34-06): sports mascot/nickname tokens are NEVER used to
# distinguish between two different real institutions the way "tech"/"state"/
# "a&m" genuinely are (Virginia Tech is a real, different school from the
# University of Virginia; there is no real school called "Western Michigan
# Broncos" distinct from "Western Michigan"). A mascot suffix is therefore
# safe to strip when one side's name is exactly the other side's name plus a
# trailing mascot token -- unlike a generic word, this is intentionally
# checked only as a SUFFIX match (see employer_evidence_matches), never a
# substring/subset match anywhere in the name, so it cannot be used to widen
# an unrelated pair into a false match. Deliberately excludes any token that
# is also a real distinguishing qualifier (e.g. no "tech", "state", "a&m").
MASCOT_TOKENS = frozenset(
    {
        "aggies", "aggie", "broncos", "bronco", "buckeyes", "buckeye",
        "bulldogs", "bulldog", "cardinal", "cardinals", "cougars", "cougar",
        "ducks", "duck", "beavers", "beaver", "huskies", "husky", "bruins",
        "bruin", "trojans", "trojan", "wolverines", "wolverine",
        "golden", "gophers", "gopher", "longhorns", "longhorn", "tigers",
        "tiger", "wildcats", "wildcat", "hokies", "hokie", "gators", "gator",
        "seminoles", "seminole", "hurricanes", "hurricane", "sooners",
        "sooner", "crimson", "tide", "volunteers", "razorbacks",
        "razorback", "rebels", "rebel", "commodores", "gamecocks",
        "gamecock", "jayhawks", "jayhawk", "cyclones", "cyclone",
        "cowboys", "cowboy", "horned", "frogs", "frog", "mountaineers",
        "mountaineer", "hoosiers", "hoosier", "boilermakers",
        "boilermaker", "badgers", "badger", "spartans", "spartan",
        "nittany", "lions", "lion", "terrapins", "terrapin", "scarlet",
        "knights", "knight", "hawkeyes", "hawkeye", "cornhuskers",
        "cornhusker", "bearkats", "jackrabbits", "jackrabbit",
        "vandals", "vandal", "falcons", "falcon", "penguins", "penguin",
        "minutemen", "flames", "flame", "utes", "ute", "buffaloes",
        "buffalo", "sooners", "aztecs", "aztec", "rams", "ram", "owls",
        "owl", "eagles", "eagle", "bearcats", "bearcat", "panthers",
        "panther", "demon", "deacons", "deacon", "orange", "pirates",
        "pirate",
    }
)

ALIAS_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"virginia", "university of virginia", "uva"}),
    frozenset({"virginia tech", "virginia polytechnic", "vpi", "hokies"}),
    frozenset({"texas a&m", "texas am", "tamu", "texas a and m"}),
    frozenset({"miami (fl)", "miami florida", "miami fl"}),
    frozenset({"miami (oh)", "miami ohio", "miami oh"}),
    # A real deliberate institutional rebrand (athletics dropped "State" from
    # public branding in 2021 while the legal/academic name kept it) -- an
    # alias, not a mascot-suffix case, since "State" is otherwise a genuine
    # distinguishing qualifier (Washington vs Washington State) that must
    # not be stripped generically.
    frozenset({"sam houston", "sam houston state", "sam houston state university"}),
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
    # MR33-04 re-repair: a trailing mascot/nickname suffix on ONE side only
    # (e.g. "Western Michigan" vs "Western Michigan Broncos") must not read
    # as a non-match the way an actual distinguishing qualifier would
    # ("Virginia" vs "Virginia Tech" still correctly falls through to False
    # below, since "tech" is not in MASCOT_TOKENS). Checked as an exact
    # leading-prefix relationship, not a substring/subset test, so this
    # cannot widen an unrelated pair -- the shorter side's full core token
    # sequence must appear, in order, at the START of the longer side's core
    # tokens, with every remaining token a known mascot word.
    if left_core and right_core and left_core != right_core:
        if len(left_core) < len(right_core):
            shorter, longer = left_core, right_core
        else:
            shorter, longer = right_core, left_core
        if longer[: len(shorter)] == shorter:
            extra = longer[len(shorter):]
            if extra and all(tok in MASCOT_TOKENS for tok in extra):
                protected_left = any(phrase in left for phrase in PROTECTED_PHRASES)
                protected_right = any(phrase in right for phrase in PROTECTED_PHRASES)
                if not (protected_left or protected_right):
                    return True
    return False


def career_page_title_matches_person(title: str, person: str) -> bool:
    """Bind a biography title to a person. Team-season pages are not careers."""

    if wiki_career_title_matches_person(title, person):
        return True
    title_n = re.sub(r"\s+", " ", str(title or "")).strip()
    person_n = re.sub(r"\s+", " ", str(person or "")).strip()
    if not title_n or not person_n:
        return False
    folded_title = title_n.casefold()
    folded_person = person_n.casefold()
    if (
        any(
            token in folded_title
            for token in (
                "basketball",
                "baseball",
                "soccer",
                "hockey",
                "softball",
                "disambiguation",
                "politician",
                "mayor",
                "senator",
                "representative",
            )
        )
        and "football" not in folded_title
    ):
        return False
    if folded_title.startswith(folded_person + " (") and any(
        token in folded_title for token in ("coach", "football")
    ):
        return True
    return False


def index_career_pages(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    """Index biography pages by person. Team-season infobox hits stay out."""

    by_name: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for page in pages:
        title = str(page.get("title") or page.get("requested_title") or "")
        candidates = {
            str(page.get("occupant_person") or "").strip(),
            title.partition(" (")[0].strip(),
        }
        for episode in page.get("episodes") or []:
            candidates.add(str(episode.get("person") or "").strip())
        identity = page_identity_key(page)
        occupant = str(page.get("occupant_person") or "").strip()
        for person in candidates:
            if not person:
                continue
            title_hit = career_page_title_matches_person(title, person)
            occupant_hit = _fold(person) == _fold(occupant) and (
                career_page_title_matches_person(title, occupant)
                or _fold(title) == _fold(occupant)
            )
            if not title_hit and not occupant_hit:
                continue
            key = _fold(person)
            if identity in seen[key]:
                continue
            seen[key].add(identity)
            by_name[key].append(page)
    return by_name


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
    # MR34-04 repair: the previous fallback was `f"opaque:{id(page)}"` -- a
    # CPython process memory address. That is not an identity. It is unstable
    # across runs and reused once an object is freed, so two unrelated
    # observations could be merged into "one person", or one observation
    # split into two, depending on allocator behaviour. A page carrying no
    # identifying field is genuinely unidentified, and the only honest answer
    # is to say so.
    return UNRESOLVED_PAGE_IDENTITY


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


def page_own_person_evidence(page: Mapping[str, Any]) -> tuple[str, ...]:
    """Who the PAGE ITSELF says it is about, ignoring any caller assertion.

    `occupant_person` is deliberately excluded: it is a field a caller writes
    onto the page dict, not evidence the source published.
    """

    names: list[str] = []
    title = str(page.get("title") or page.get("requested_title") or "").strip()
    if title:
        names.append(title)
    for episode in page.get("episodes") or []:
        value = str(episode.get("person") or "").strip()
        if value:
            names.append(value)
    return tuple(dict.fromkeys(names))


def _person_identity_matches_page(person: str, page: Mapping[str, Any]) -> bool:
    """MR33-04/MR34-04: the join's own person-identity check.

    MR33-04 established that a caller-side title prefilter is not sufficient.
    MR34-04 showed the remaining hole: `occupant_person` was consulted as an
    independent identity source, so a caller could assert "Bob Example" onto
    a page whose own title and episodes both say "Alice Example" and receive
    an EVIDENCE_BOUND_CAREER_JOIN. A caller-provided name is a *claim being
    tested*, never evidence for itself.

    The rule is therefore ordered: when the page publishes its own person
    evidence (title or episode `person`), that evidence decides, and a
    contrary caller occupant cannot rescue it. `occupant_person` is consulted
    only when the page carries no own-person evidence at all, and even then
    it merely fails to contradict -- `join_occupant_to_pages` still reports
    the weaker state.
    """

    person_key = _fold(person)
    if not person_key:
        return False
    own_evidence = page_own_person_evidence(page)
    if own_evidence:
        title = str(page.get("title") or page.get("requested_title") or "")
        if title and career_page_title_matches_person(title, person):
            return True
        episode_persons = {
            _fold(str(episode.get("person") or ""))
            for episode in page.get("episodes") or []
        }
        if person_key in episode_persons:
            return True
        # The page names someone, and it is not this person. A caller-side
        # `occupant_person` claiming otherwise is exactly the override this
        # repair closes.
        return False
    occupant = _fold(str(page.get("occupant_person") or ""))
    return bool(occupant) and occupant == person_key


def _episode_locator(page: Mapping[str, Any], episode: Mapping[str, Any]) -> dict[str, Any]:
    """The exact assertion a join matched, with its own provenance."""

    return {
        "program_raw": episode.get("program_raw"),
        "role_raw": episode.get("role") or episode.get("title"),
        "season": episode.get("season"),
        "valid_from": episode.get("valid_from") or episode.get("start"),
        "valid_to": episode.get("valid_to") or episode.get("end"),
        "source_title": page.get("title") or page.get("requested_title"),
        "source_revision": page.get("wikimedia_revision") or page.get("revision"),
        "source_locator": episode.get("source_locator") or episode.get("locator"),
        "source_class": episode.get("source_class"),
    }


def _episode_matches_role(episode: Mapping[str, Any], role: str) -> bool:
    claimed = _fold(role)
    if not claimed:
        return False
    for field in ("role", "title", "role_raw"):
        if _fold(str(episode.get(field) or "")) == claimed:
            return True
    return False


def _episode_covers_season(episode: Mapping[str, Any], season: str) -> bool:
    wanted = str(season or "").strip()
    if not wanted:
        return False
    if str(episode.get("season") or "").strip() == wanted:
        return True
    start = str(episode.get("valid_from") or episode.get("start") or "")[:4]
    end = str(episode.get("valid_to") or episode.get("end") or "")[:4]
    if not start.isdigit():
        return False
    if not end.isdigit():
        # An open interval covers any season at or after its start.
        return int(wanted) >= int(start)
    return int(start) <= int(wanted) <= int(end)


def join_occupant_to_pages(
    *,
    person: str,
    program_display: str,
    pages: Sequence[Mapping[str, Any]],
    role: str = "",
    season: str = "",
) -> dict[str, Any]:
    """Evidence-bound career join or an exact unresolved state.

    MR34-04 repair, second half: resolving a PERSON to a PAGE is not the same
    question as verifying that the person held a particular ROLE in a
    particular SEASON at that employer. The previous signature could not even
    express the second question -- it took no role and no time -- yet its
    EVIDENCE_BOUND_CAREER_JOIN verdict was consumed as appointment
    verification.

    `role` and `season` are therefore accepted and, when supplied, must be
    satisfied by a single concrete episode on the resolved page; the matched
    episode and its own source/revision/locator are returned so a consumer
    can see exactly which assertion carried the join rather than trusting an
    employer-level match. When they are omitted the result is explicitly
    labelled a person/employer resolution only, and `role_time_bound` is
    False -- an honest "we did not ask" rather than an implied yes.
    """

    football_pages = [
        page for page in pages if football_career_context(page)["accepted"]
    ]
    person_matched_pages = [
        page for page in football_pages if _person_identity_matches_page(person, page)
    ]
    identities = {page_identity_key(page) for page in person_matched_pages}
    resolvable_identities = identities - {UNRESOLVED_PAGE_IDENTITY}
    matched_episode: Mapping[str, Any] | None = None
    role_time_requested = bool(str(role or "").strip() or str(season or "").strip())
    role_time_bound = False
    if not pages:
        state = "CAREER_PAGE_MISSING"
        page = None
    elif not football_pages:
        state = "NAME_ONLY_CANDIDATE_NOT_ACCEPTED"
        page = None
    elif not person_matched_pages:
        # A same-employer football page exists, but not for this person --
        # this must never fall through to an EVIDENCE_BOUND_CAREER_JOIN.
        state = "FOOTBALL_PAGE_PERSON_IDENTITY_UNMATCHED"
        page = None
    elif len(identities) > 1:
        state = "AMBIGUOUS_MULTIPLE_FOOTBALL_PAGES"
        page = None
    elif not resolvable_identities:
        # Every candidate page is unidentified; there is no key to join on.
        state = "PAGE_IDENTITY_UNRESOLVED"
        page = None
    else:
        page = person_matched_pages[0]
        org_episodes = []
        if str(program_display or "").strip():
            org_episodes = [
                row
                for row in (page.get("episodes") or [])
                if employer_evidence_matches(
                    program_display, str(row.get("program_raw") or "")
                )
            ]
        if not org_episodes:
            state = "FOOTBALL_PAGE_ORG_IDENTITY_UNBOUND"
        elif not role_time_requested:
            state = "EVIDENCE_BOUND_CAREER_JOIN"
        else:
            candidates = org_episodes
            if str(role or "").strip():
                candidates = [
                    row for row in candidates if _episode_matches_role(row, role)
                ]
            if str(season or "").strip():
                candidates = [
                    row for row in candidates if _episode_covers_season(row, season)
                ]
            if len(candidates) == 1:
                matched_episode = candidates[0]
                role_time_bound = True
                state = "EVIDENCE_BOUND_ROLE_TIME_JOIN"
            elif not candidates:
                state = "ROLE_TIME_NOT_SUPPORTED_BY_ANY_EPISODE"
            else:
                # Co/shared occupancy and sequential replacement are real;
                # picking one silently would invent a fact.
                state = "AMBIGUOUS_MULTIPLE_MATCHING_EPISODES"
    bound_states = {"EVIDENCE_BOUND_CAREER_JOIN", "EVIDENCE_BOUND_ROLE_TIME_JOIN"}
    return {
        "person": person,
        "program_display": program_display,
        "role": role or None,
        "season": season or None,
        "career_join_state": state,
        "same_name_only": state not in bound_states,
        "page_identity": None if page is None else page_identity_key(page),
        "cached_football_pages": len(football_pages),
        "distinct_page_identities": len(identities),
        "page_own_person_evidence": (
            list(page_own_person_evidence(page)) if page is not None else []
        ),
        "caller_occupant_cannot_override_page_evidence": True,
        # Person/page resolution and appointment verification are different
        # questions; the answer says which one it actually answered.
        "role_time_requested": role_time_requested,
        "role_time_bound": role_time_bound,
        "matched_episode": (
            _episode_locator(page, matched_episode)
            if page is not None and matched_episode is not None
            else None
        ),
        "revision_ids_are_not_people": True,
        "pit_admitted": False,
    }
