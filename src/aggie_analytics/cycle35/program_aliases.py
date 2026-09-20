"""R35-02/R35-07: declared program-name alias crosswalk.

NCAA.com publishes participants as abbreviated slugs (`arizona-st`,
`ga-southern`, `fla-atlantic`, `nc-at`) while the canonical membership
carries full display names (`Arizona State`, `Georgia Southern`,
`Florida Atlantic`, `North Carolina A&T`). Without a crosswalk, 473 of 770
real observations could not bind a canonical participant -- not because the
programs are absent from the population, but because nothing translated the
publisher's abbreviation convention.

Two rules keep this a crosswalk rather than a guess:

* **Expansion is declared, not inferred.** Every abbreviation below is an
  explicit token rule. Nothing is fuzzy-matched, edit-distance-matched or
  prefix-matched, so `arizona-st` cannot quietly become `Arizona`.
* **Ambiguity fails closed.** An expansion is accepted only when it produces
  exactly ONE canonical program. Any candidate that resolves to zero or to
  several programs stays UNRESOLVED and is reported, because a participant
  the source did not unambiguously name is not a participant we know.

Programs that legitimately are not in the current national membership (a
Division II, Division III or NAIA opponent, a discontinued program) also
stay UNRESOLVED and must remain visible as external opponents. Their absence
from a 266-row current membership is a fact about the population boundary,
not a defect to paper over.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

CROSSWALK_VERSION = "BAS-PROGRAM-ALIAS-CROSSWALK-v35.1"

#: Token-level abbreviation expansions used by NCAA.com slugs. Each entry is
#: `abbreviation -> expansion`; a slug token matching the key is replaced.
TOKEN_EXPANSIONS: dict[str, str] = {
    "st": "state",
    "so": "southern",
    "ga": "georgia",
    "fla": "florida",
    "ark": "arkansas",
    "la": "louisiana",
    "tenn": "tennessee",
    "mich": "michigan",
    "miss": "mississippi",
    "val": "valley",
    "ky": "kentucky",
    "ill": "illinois",
    "ala": "alabama",
    "car": "carolina",
    "colo": "colorado",
    "wash": "washington",
    "intl": "international",
    "se": "se",
    "nc": "north-carolina",
    "sc": "south-carolina",
    "nw": "northwestern",
    "ne": "northeastern",
}

#: Whole-slug aliases where a token rule cannot express the mapping.
WHOLE_SLUG_ALIASES: dict[str, str] = {
    "fiu": "florida-international",
    "miami-fl": "miami",
    "miami-oh": "miami-oh",
    "hawaii": "hawai-i",
    "nc-at": "north-carolina-a-t",
    "ark-pine-bluff": "arkansas-pine-bluff",
    "long-island": "long-island-university",
    "app-st": "app-state",
    "southern-miss": "southern-miss",
    "umass": "massachusetts",
    "utsa": "utsa",
    "utep": "utep",
    "uab": "uab",
    "ucf": "ucf",
    "smu": "smu",
    "tcu": "tcu",
    "byu": "byu",
    "lsu": "lsu",
    "unlv": "unlv",
    "usc": "usc",
    "ucla": "ucla",
    "vmi": "vmi",
    # Publisher display names whose canonical program is unambiguous but not
    # derivable by token expansion. Each was confirmed against the declared
    # membership before being listed; anything that would have matched more
    # than one program is deliberately absent and stays unresolved.
    "alcorn": "alcorn-state",
    "central-conn-st": "central-connecticut",
    "mississippi-val": "mississippi-valley-state",
    "penn": "pennsylvania",
    "prairie-view": "prairie-view-a-m",
    "san-jose-st": "san-jose-state",
    "southeast-mo-st": "southeast-missouri-state",
    "southeastern-la": "se-louisiana",
    "southern-california": "usc",
    "southern-u": "southern",
    "uiw": "incarnate-word",
    "ulm": "ul-monroe",
    "uni": "northern-iowa",
    "utrgv": "ut-rio-grande-valley",
}

#: Characters a publisher may emit where the canonical name carries a
#: diacritic or a replacement byte (`San Jos� State` in the captured
#: membership file). Folded to ASCII on both sides so the two spellings meet.
_DIACRITIC_FOLD = str.maketrans(
    {
        "é": "e", "è": "e", "ê": "e",
        "á": "a", "à": "a", "â": "a",
        "í": "i", "ì": "i", "î": "i",
        "ó": "o", "ò": "o", "ô": "o",
        "ú": "u", "ù": "u", "û": "u",
        "ñ": "n", "ç": "c", "�": "",
    }
)


#: Period-abbreviated forms NCAA.com uses in display names (`Mississippi
#: Val.`, `Northern Ariz.`, `Central Conn. St.`). Expanding these is safe
#: only because an expansion that does not land on exactly one canonical
#: program is discarded -- `Bowie St.` expands to `Bowie State`, finds no
#: match in the declared population, and correctly stays unresolved.
DISPLAY_ABBREVIATIONS: dict[str, str] = {
    "st": "state",
    "val": "valley",
    "ariz": "arizona",
    "conn": "connecticut",
    "mich": "michigan",
    "miss": "mississippi",
    "tenn": "tennessee",
    "ky": "kentucky",
    "ill": "illinois",
    "ala": "alabama",
    "ark": "arkansas",
    "colo": "colorado",
    "wash": "washington",
    "okla": "oklahoma",
    "caro": "carolina",
    "fla": "florida",
    "ga": "georgia",
    "la": "louisiana",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
}

_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def unescape_source_name(text: Any) -> str:
    r"""Decode `\uXXXX` escapes left in a publisher's display name.

    The NCAA.com payload is JSON embedded in a JS string, and the producer's
    regular-expression extractor lifts `name` fields out of it without
    decoding, so `Alabama A&M` arrives as the literal eight characters
    `A&M`. That is not a canonicalization nicety: it made five real
    Alabama A&M observations, plus Florida A&M and East Texas A&M, fail to
    bind to programs that are unambiguously present in the population.
    """

    raw = str(text or "")
    return _UNICODE_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), raw)


def slug(text: Any) -> str:
    """Lowercase hyphen slug. `Hawai'i` -> `hawai-i`, `Texas A&M` -> `texas-a-m`."""

    folded = unescape_source_name(text).casefold().translate(_DIACRITIC_FOLD)
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def candidate_slugs(raw: Any) -> list[str]:
    """Every declared spelling this source value could canonically mean.

    Returns the original slug first, then whole-slug aliases, then the
    token-expanded form. Order is only for reporting which rule fired; the
    caller still requires a unique match across the whole candidate set.
    """

    base = slug(raw)
    if not base:
        return []
    candidates = [base]
    alias = WHOLE_SLUG_ALIASES.get(base)
    if alias and alias not in candidates:
        candidates.append(alias)
    tokens = base.split("-")
    expanded = [TOKEN_EXPANSIONS.get(token, token) for token in tokens]
    joined = "-".join(expanded)
    if joined not in candidates:
        candidates.append(joined)
    # Trailing-abbreviation only (e.g. `boise-st` -> `boise-state`) without
    # touching leading tokens, which is the commonest NCAA.com form.
    if len(tokens) > 1 and tokens[-1] in TOKEN_EXPANSIONS:
        tail = "-".join(tokens[:-1] + [TOKEN_EXPANSIONS[tokens[-1]]])
        if tail not in candidates:
            candidates.append(tail)
    # Period-abbreviated display form (`Mississippi Val.` -> `mississippi-valley`).
    display_expanded = "-".join(
        DISPLAY_ABBREVIATIONS.get(token, token) for token in tokens
    )
    if display_expanded not in candidates:
        candidates.append(display_expanded)
    # `Alabama A&M` slugs to `alabama-a-m` from the canonical display name but
    # to `alabama-am` from some source spellings; offer the collapsed form of
    # every candidate so single-letter fragments cannot split a match.
    for candidate in list(candidates):
        collapsed = re.sub(r"\b([a-z])-([a-z])\b", r"\1\2", candidate)
        if collapsed != candidate and collapsed not in candidates:
            candidates.append(collapsed)
    return candidates


def build_crosswalk(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Map canonical slug -> program_id from a declared membership population.

    A slug shared by two programs is recorded as ambiguous and excluded; the
    population has an identity problem there and picking one would hide it.
    """

    by_slug: dict[str, set[str]] = {}
    display_by_id: dict[str, str] = {}
    row_count = 0
    for row in rows:
        row_count += 1
        program_id = str(row.get("program_id") or "").strip()
        if not program_id:
            continue
        display = str(row.get("display_name") or "")
        display_by_id.setdefault(program_id, display)
        by_slug.setdefault(slug(display), set()).add(program_id)
        # Index the collapsed single-letter form too, so `Alabama A&M`
        # (`alabama-a-m`) is reachable from a source spelling that renders
        # the ampersand away entirely (`alabama-am`).
        collapsed = re.sub(r"\b([a-z])-([a-z])\b", r"\1\2", slug(display))
        if collapsed != slug(display):
            by_slug.setdefault(collapsed, set()).add(program_id)
    ambiguous = {key: sorted(value) for key, value in by_slug.items() if len(value) > 1}
    usable = {key: next(iter(value)) for key, value in by_slug.items() if len(value) == 1}
    return {
        "crosswalk_version": CROSSWALK_VERSION,
        "by_slug": usable,
        "display_by_id": display_by_id,
        "ambiguous_slugs": ambiguous,
        "membership_rows": row_count,
        "distinct_slugs": len(by_slug),
        "usable_slugs": len(usable),
    }


def resolve_program(raw: Any, crosswalk: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one source-published participant name to a canonical program.

    The verdict always names the rule that fired, so an alias-resolved
    binding is never indistinguishable from a direct one in the evidence.
    """

    by_slug = crosswalk.get("by_slug") or {}
    candidates = candidate_slugs(raw)
    matches: dict[str, str] = {}
    for index, candidate in enumerate(candidates):
        program_id = by_slug.get(candidate)
        if program_id:
            matches[program_id] = (
                "DIRECT_SLUG" if index == 0 else "DECLARED_ALIAS_EXPANSION"
            )
    if not matches:
        return {
            "raw": raw,
            "resolution_state": "UNRESOLVED_NOT_IN_DECLARED_POPULATION",
            "program_id": None,
            "rule": None,
            "candidates_tried": candidates,
        }
    if len(matches) > 1:
        return {
            "raw": raw,
            "resolution_state": "AMBIGUOUS_MULTIPLE_CANONICAL_MATCHES",
            "program_id": None,
            "rule": None,
            "candidates_tried": candidates,
            "matched_program_ids": sorted(matches),
        }
    program_id, rule = next(iter(matches.items()))
    return {
        "raw": raw,
        "resolution_state": "RESOLVED",
        "program_id": program_id,
        "rule": rule,
        "candidates_tried": candidates,
    }
