r"""Bind a capture to the program its *bytes* say it belongs to.

MF36-01 and MF37-05 repair. Both were reported as one school's page being
assigned to a differently named school -- 55 Ohio State rows filed under
Ohio, New Mexico State's coaches filed under New Mexico. Neither is a naming
problem, and neither is fixed by special-casing those names.

The mechanism, reproduced from the acquisition ledger, is this. Two
acquisition attempts for two *different* programs resolved to the same URL
and therefore produced the same payload, so the ledger holds two attempt
records carrying the same ``receipt_identity``. The ingest indexed attempts
by that identity with::

    by_receipt.setdefault(identity, attempt)

which keeps whichever record appears first in the file and discards the
other without a word. Over the delivered 266-record ledger that is seven
colliding digests, fourteen attempts, seven discarded -- and because the
winner is decided by file order, five of the seven bindings are wrong and
two happen to be right. "Sometimes correct" is the signature of an ordering
accident, not of a name-specific bug.

So the rule implemented here is: **a declared program is a claim about a
capture, not a fact about it.** The capture's own bytes carry a page
identity -- ``<title>``, ``<link rel=canonical>``, ``og:site_name``, and the
asset hosts the markup references -- and the acquisition route carries a
requested host. A binding is admitted only when the declared program is
corroborated by that evidence. Where the evidence contradicts the claim, or
cannot distinguish two claimants, the capture is **quarantined** and its
observations are marked, never silently filed under one of them.

Nothing here decides that a quarantined capture is worthless. It decides
that an unproven binding is not an admitted one.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

__all__ = [
    "BINDING_CONFIRMED",
    "BINDING_CONTRADICTED",
    "BINDING_NAME_NOT_MATCHED",
    "BINDING_QUARANTINED_AMBIGUOUS",
    "BINDING_UNCORROBORATED",
    "CaptureIdentity",
    "ProgramClaim",
    "adjudicate",
    "host_tokens",
    "name_tokens",
    "page_identity",
]

#: The declared program is corroborated by the capture's own identity.
BINDING_CONFIRMED = "CONFIRMED_BY_SOURCE_IDENTITY"
#: The capture's own identity names a different program than the claim.
BINDING_CONTRADICTED = "CONTRADICTED_BY_SOURCE_IDENTITY"
#: More than one program claims this payload and the evidence cannot separate
#: them, or it separates them and more than one still matches.
BINDING_QUARANTINED_AMBIGUOUS = "QUARANTINED_AMBIGUOUS_CLAIM"
#: No usable identity evidence was found in the capture. Not a contradiction;
#: not a confirmation either.
BINDING_UNCORROBORATED = "UNCORROBORATED_NO_SOURCE_IDENTITY"

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_CANONICAL = re.compile(
    r"""<link[^>]+rel\s*=\s*["']?canonical["']?[^>]*>""", re.I
)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_META_CONTENT = re.compile(r"""content\s*=\s*["']([^"']*)["']""", re.I)
_OG_SITE_NAME = re.compile(
    r"""<meta[^>]+(?:property|name)\s*=\s*["']?og:site_name["']?[^>]*>""", re.I
)
_ASSET_HOST = re.compile(
    r"""(?:src|href|content)\s*=\s*["'](?:https?:)?//([A-Za-z0-9.\-]+)""", re.I
)

#: Tokens that carry no discriminating power in a school or host name. Left
#: deliberately small: dropping "state" would erase the exact distinction
#: these findings are about.
_NOISE_TOKENS = frozenset(
    {
        "the", "of", "at", "university", "universities", "college", "colleges",
        "athletics", "athletic", "sports", "official", "site", "website",
        "home", "football", "coaches", "coaching", "staff", "directory",
        "www", "com", "org", "net", "edu", "gov", "sidearmsports", "https",
        "http",
    }
)

#: Substitutions applied before tokenising, so a host spells its school the
#: way the school does. Each is a general orthographic rule, not a per-school
#: correction: expanding them is how "nmstatesports" becomes comparable to
#: "New Mexico State" without anyone writing down that pair.
_HOST_EXPANSIONS: Sequence[tuple[str, str]] = (
    ("state", " state "),
    ("univ", " university "),
    ("tech", " tech "),
    ("intl", " international "),
)


#: A trailing parenthetical is a disambiguator the catalogue adds, not a word
#: the school's own page uses: "Miami (OH)" appears on its site as "Miami
#: University". It is separated so coverage can be judged on the name and the
#: qualifier can still be reported.
_PARENTHETICAL = re.compile(r"\s*\(([^)]*)\)\s*")


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def split_qualifier(value: str) -> tuple[str, str | None]:
    """Separate a catalogue disambiguator from the name it qualifies."""

    match = _PARENTHETICAL.search(str(value))
    if not match:
        return str(value), None
    return _PARENTHETICAL.sub(" ", str(value)).strip(), match.group(1).strip() or None


def name_tokens(value: str) -> frozenset[str]:
    """Discriminating tokens of a program or page name.

    Purely numeric tokens are dropped. ``2026 Football Coaches | Ohio State``
    is a season plus a school, and counting ``2026`` as part of the school's
    name made the page look like it named a *longer* program than "Ohio
    State" -- which quarantined the one collision this repair most needed to
    resolve. A year is a date; no program is named one.
    """

    base, _ = split_qualifier(value)
    return frozenset(
        token
        for token in _fold(base).split()
        if token and token not in _NOISE_TOKENS and not token.isdigit()
    )


#: Connecting words an institutional acronym leaves out.
_ACRONYM_SKIP_WORDS = frozenset({"of", "the", "at", "and", "for", "in"})



def _acronym_of(tokens_in_order: Sequence[str]) -> str:
    return "".join(token[0] for token in tokens_in_order if token)


def _acronym_covers(claim: frozenset[str], evidence_text: str) -> bool:
    """Whether a short all-letters claim is the evidence's own initials.

    "FIU" never appears as a token in "Florida International University", but
    it is that name's acronym. This is a general orthographic rule: no school
    is named here, and a claim only matches when its letters are exactly the
    initials of consecutive words in the evidence.
    """

    if len(claim) != 1:
        return False
    candidate = next(iter(claim))
    if not (2 <= len(candidate) <= 5) or not candidate.isalpha():
        return False
    words = [word for word in _fold(evidence_text).split() if word]
    # Institutional acronyms skip the small connecting words: UNLV is
    # U(niversity of) N(evada) L(as) V(egas), not "uonlv". Both spellings are
    # tried so neither convention has to be guessed.
    kept = [word for word in words if word not in _ACRONYM_SKIP_WORDS]
    for sequence in (words, kept):
        for start in range(len(sequence)):
            for end in range(start + 2, min(start + 7, len(sequence)) + 1):
                if _acronym_of(sequence[start:end]) == candidate:
                    return True
    return False


def host_tokens(host: str) -> frozenset[str]:
    """Discriminating tokens of a hostname.

    ``nmstatesports.com`` yields ``{"nm", "state"}`` and
    ``ohiostatebuckeyes.com`` yields ``{"ohiostatebuckeyes"}`` plus its
    ``state``-split parts. Host tokens are weaker evidence than a page title
    and are treated as such by :func:`adjudicate`.
    """

    label = _fold(host)
    for pattern, replacement in _HOST_EXPANSIONS:
        label = label.replace(pattern, replacement)
    return frozenset(
        token for token in label.split() if token and token not in _NOISE_TOKENS
    )


@dataclass(frozen=True)
class CaptureIdentity:
    """What a capture's own bytes say about whose page it is."""

    title: str | None = None
    canonical_href: str | None = None
    og_site_name: str | None = None
    asset_hosts: tuple[str, ...] = ()
    route_host: str | None = None

    def evidence(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "canonical_href": self.canonical_href,
            "og_site_name": self.og_site_name,
            "asset_hosts": list(self.asset_hosts),
            "route_host": self.route_host,
        }

    def has_any(self) -> bool:
        return any(
            (self.title, self.canonical_href, self.og_site_name, self.asset_hosts, self.route_host)
        )

    def tokens(self) -> dict[str, frozenset[str]]:
        """Token sets by evidence kind, strongest first."""

        sets: dict[str, frozenset[str]] = {}
        if self.title:
            sets["title"] = name_tokens(self.title)
        if self.og_site_name:
            sets["og_site_name"] = name_tokens(self.og_site_name)
        if self.route_host:
            sets["route_host"] = host_tokens(self.route_host)
        if self.asset_hosts:
            merged: set[str] = set()
            for host in self.asset_hosts:
                merged |= host_tokens(host)
            if merged:
                sets["asset_hosts"] = frozenset(merged)
        return sets


@dataclass
class ProgramClaim:
    """One acquisition attempt's claim that a capture belongs to a program."""

    program_id: str
    display_name: str
    route: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


def page_identity(text: str, *, route: str | None = None, asset_host_limit: int = 12) -> CaptureIdentity:
    """Read a capture's identity out of its own markup.

    Every field is optional: a capture with no title and no canonical link
    yields an identity with nothing in it, and :func:`adjudicate` reports
    that as uncorroborated rather than inventing agreement.
    """

    title_match = _TITLE.search(text)
    title = " ".join(title_match.group(1).split()) if title_match else None

    canonical = None
    canonical_match = _CANONICAL.search(text)
    if canonical_match:
        href = _HREF.search(canonical_match.group(0))
        if href:
            canonical = href.group(1)

    site_name = None
    og_match = _OG_SITE_NAME.search(text)
    if og_match:
        content = _META_CONTENT.search(og_match.group(0))
        if content:
            site_name = " ".join(content.group(1).split()) or None

    hosts: list[str] = []
    for match in _ASSET_HOST.finditer(text):
        host = match.group(1).casefold()
        if host and host not in hosts:
            hosts.append(host)
        if len(hosts) >= asset_host_limit:
            break

    route_host = None
    if route:
        try:
            route_host = urlsplit(route).hostname or None
        except ValueError:
            route_host = None
    if canonical and canonical.startswith(("http://", "https://")):
        try:
            canonical_host = urlsplit(canonical).hostname
        except ValueError:
            canonical_host = None
        if canonical_host and canonical_host not in hosts:
            hosts.insert(0, canonical_host)

    return CaptureIdentity(
        title=title,
        canonical_href=canonical,
        og_site_name=site_name,
        asset_hosts=tuple(hosts),
        route_host=route_host,
    )


def _score(
    claim: ProgramClaim,
    identity: CaptureIdentity,
    *,
    token_sets: Mapping[str, frozenset[str]] | None = None,
    raw_text: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """How well one claim is supported, and by which evidence.

    ``token_sets`` and ``raw_text`` are the capture's, not the claim's, so a
    caller scoring many candidates against one capture computes them once.
    Recomputing them per candidate turned a whole-cache adjudication into a
    quadratic one.
    """

    base_name, qualifier = split_qualifier(claim.display_name)
    wanted = name_tokens(claim.display_name)
    if raw_text is None:
        raw_text = {
            "title": identity.title or "",
            "og_site_name": identity.og_site_name or "",
            "route_host": identity.route_host or "",
            "asset_hosts": " ".join(identity.asset_hosts),
        }
    per_kind: dict[str, dict[str, Any]] = {}
    for kind, tokens in (token_sets if token_sets is not None else identity.tokens()).items():
        overlap = wanted & tokens
        # A claim is *contradicted* when the evidence carries a
        # discriminating token the claim lacks while also covering the
        # claim's own tokens -- "New Mexico State" over a claim of "New
        # Mexico". A merely different token set is not a contradiction.
        extra = tokens - wanted
        by_token = bool(wanted) and wanted <= tokens
        by_acronym = (not by_token) and _acronym_covers(wanted, raw_text.get(kind, ""))
        per_kind[kind] = {
            "evidence_tokens": sorted(tokens),
            "claim_tokens": sorted(wanted),
            "claim_qualifier": qualifier,
            "claim_base_name": base_name,
            "overlap": sorted(overlap),
            "covers_claim": by_token or by_acronym,
            "covered_by": "tokens" if by_token else ("acronym" if by_acronym else None),
            "evidence_only_tokens": sorted(extra) if by_token else [],
        }
    strength = {"title": 3, "og_site_name": 3, "canonical_host": 2, "route_host": 2, "asset_hosts": 1}
    supported = sum(
        strength.get(kind, 1)
        for kind, row in per_kind.items()
        if row["covers_claim"]
    )
    strictly_extended = any(
        row["covers_claim"] and row["evidence_only_tokens"]
        for kind, row in per_kind.items()
        if kind in {"title", "og_site_name"}
    )
    return {
        "program_id": claim.program_id,
        "display_name": claim.display_name,
        "route": claim.route,
        "per_evidence": per_kind,
        "support_score": supported,
        "covered_by_any_evidence": supported > 0,
        "evidence_names_a_longer_program": strictly_extended,
    }


#: A page whose evidence does not cover the claim, and does not cover any
#: other known program either. The commonest cause is branding the catalogue
#: does not carry -- "UK Athletics", "NDSU", "Hotty Toddy" -- not a wrong
#: school. Resolving it needs an alias source, not a stricter guess.
BINDING_NAME_NOT_MATCHED = "UNCORROBORATED_NAME_FORM_NOT_MATCHED"


def adjudicate(
    identity: CaptureIdentity,
    claims: Iterable[ProgramClaim],
    *,
    known_program_names: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Decide which claim -- if any -- the capture's own bytes support.

    The outcome is never "the first one". With several claims the best
    strictly-supported one wins and anything else quarantines.

    ``known_program_names`` is what makes a *contradiction* meaningful, and
    supplying it is a correction to this method's own first version. Without
    the catalogue, "the title does not contain the claim's tokens" was
    reported as CONTRADICTED -- and over the real cache that labelled 61
    captures wrong when most were ordinary branding: ``Kentucky`` against
    "UK Athletics", ``North Dakota State`` against "NDSU", ``Ole Miss``
    against "Ole Miss Athletics - Hotty Toddy", ``Iowa`` against "Iowa
    Hawkeyes". None of those is another school's page.

    With the catalogue, a contradiction requires a positive finding: some
    *other declared program* is the one this page covers. Absent that, a
    non-matching page is :data:`BINDING_NAME_NOT_MATCHED` -- unresolved, and
    honestly so.
    """

    claim_list = list(claims)
    # Computed once for the capture and reused for every candidate below.
    token_sets = identity.tokens()
    raw_text = {
        "title": identity.title or "",
        "og_site_name": identity.og_site_name or "",
        "route_host": identity.route_host or "",
        "asset_hosts": " ".join(identity.asset_hosts),
    }
    page_tokens = name_tokens(identity.title or "") | name_tokens(
        identity.og_site_name or ""
    )
    if not claim_list:
        return {
            "state": BINDING_QUARANTINED_AMBIGUOUS,
            "reason": "no declared program claimed this capture",
            "identity": identity.evidence(),
            "claims": [],
            "admitted_program_id": None,
        }

    scored = [
        _score(claim, identity, token_sets=token_sets, raw_text=raw_text)
        for claim in claim_list
    ]
    result: dict[str, Any] = {
        "identity": identity.evidence(),
        "claims": scored,
        "claim_count": len(scored),
        "admitted_program_id": None,
    }

    if not identity.has_any():
        result["state"] = BINDING_UNCORROBORATED
        result["reason"] = "the capture carries no title, canonical link, site name or host"
        return result

    supported = [row for row in scored if row["covered_by_any_evidence"]]

    # Which OTHER declared programs this page's evidence covers. This is the
    # only thing that can turn "does not match the claim" into "is another
    # school's page"; without it the two are indistinguishable.
    claimed_ids = {claim.program_id for claim in claim_list}
    rival_matches: list[dict[str, Any]] = []
    if known_program_names:
        for program_id, display_name in known_program_names.items():
            if program_id in claimed_ids:
                continue
            rival_tokens = name_tokens(str(display_name))
            # A rival whose name is strictly *contained* in the page's own
            # name is not evidence about whose page this is: "Louisiana" sits
            # inside "University of Louisiana Monroe" and "Nevada" inside
            # "University of Nevada Las Vegas". Treating either as proof
            # produced four wrong findings over the real cache. A rival whose
            # name the page states in full -- "Clemson" on Clemson's own page
            # -- is not contained and still counts.
            if rival_tokens and page_tokens and rival_tokens < page_tokens:
                continue
            rival = _score(
                ProgramClaim(str(program_id), str(display_name)),
                identity,
                token_sets=token_sets,
                raw_text=raw_text,
            )
            # An acronym match is strong evidence FOR a claim and weak
            # evidence that some other program owns the page, so a rival has
            # to be covered by actual tokens.
            covered_by_tokens = any(
                row["covers_claim"] and row.get("covered_by") == "tokens"
                for row in rival["per_evidence"].values()
            )
            if covered_by_tokens:
                rival_matches.append(
                    {
                        "program_id": str(program_id),
                        "display_name": str(display_name),
                        "support_score": rival["support_score"],
                        "name_token_count": len(rival_tokens),
                    }
                )
    rival_matches.sort(key=lambda row: (-row["support_score"], row["display_name"]))
    result["other_programs_the_page_covers"] = rival_matches[:8]
    result["catalogue_consulted"] = bool(known_program_names)

    if len(claim_list) == 1:
        only = scored[0]
        claim_token_set = frozenset(
            next(iter(only["per_evidence"].values()))["claim_tokens"]
        ) if only["per_evidence"] else frozenset()
        strictly_longer_rivals = [
            row
            for row in rival_matches
            if claim_token_set and claim_token_set < name_tokens(row["display_name"])
        ]
        if supported and strictly_longer_rivals:
            result["state"] = BINDING_CONTRADICTED
            result["reason"] = (
                f"the capture's own page identity also covers "
                f"{strictly_longer_rivals[0]['display_name']!r}, a declared "
                f"program whose name strictly contains "
                f"{only['display_name']!r}: this is that school's page"
            )
            return result
        if supported:
            result["state"] = BINDING_CONFIRMED
            result["admitted_program_id"] = only["program_id"]
            result["reason"] = (
                "the declared program is covered by the capture's own identity"
            )
            return result
        if rival_matches:
            result["state"] = BINDING_CONTRADICTED
            result["reason"] = (
                f"no evidence covers {only['display_name']!r}, and the page's "
                f"identity does cover the declared program "
                f"{rival_matches[0]['display_name']!r}"
            )
            return result
        result["state"] = BINDING_NAME_NOT_MATCHED
        result["reason"] = (
            f"no evidence in the capture covers {only['display_name']!r} and "
            f"no other declared program is covered either"
            + (
                ". The page is most likely branded in a form the catalogue "
                "does not carry (an abbreviation, a mascot or a legal name); "
                "resolving it needs an alias source, not a stricter guess."
                if known_program_names
                else ". No program catalogue was supplied, so a contradiction "
                "cannot be distinguished from an unmatched name form."
            )
        )
        return result

    # Several programs claim the same payload.
    if not supported:
        result["state"] = BINDING_QUARANTINED_AMBIGUOUS
        result["reason"] = (
            f"{len(claim_list)} programs claim this payload and none is "
            f"covered by the capture's own identity"
        )
        return result

    best = max(row["support_score"] for row in supported)
    winners = [row for row in supported if row["support_score"] == best]

    # Two independent reasons a covered claim still loses, both of which say
    # "a shorter name is contained in a longer one, and containment is not
    # identity":
    #
    #  1. another equally supported claim's own tokens strictly contain this
    #     claim's -- "Ohio" inside "Ohio State";
    #  2. the page identity itself names more than the claim does.
    #
    # The first is checked between the claims, which is more robust than
    # reading extras out of a title: a title carries navigation and section
    # words that are not part of anybody's name.
    token_sets = {
        row["program_id"]: frozenset(
            next(iter(row["per_evidence"].values()))["claim_tokens"]
        )
        if row["per_evidence"]
        else frozenset()
        for row in winners
    }
    def _strictly_contained(row: dict[str, Any]) -> bool:
        mine = token_sets.get(row["program_id"], frozenset())
        return any(
            mine < other
            for pid, other in token_sets.items()
            if pid != row["program_id"]
        )

    for row in winners:
        row["strictly_contained_in_another_claim"] = _strictly_contained(row)

    decisive = [
        row
        for row in winners
        if not row["evidence_names_a_longer_program"]
        and not row["strictly_contained_in_another_claim"]
    ]
    if len(decisive) == 1:
        result["state"] = BINDING_CONFIRMED
        result["admitted_program_id"] = decisive[0]["program_id"]
        result["reason"] = (
            f"{len(claim_list)} programs claim this payload; "
            f"{decisive[0]['display_name']!r} is the only one the capture's "
            f"own identity supports without naming a longer program"
        )
        return result

    result["state"] = BINDING_QUARANTINED_AMBIGUOUS
    result["reason"] = (
        f"{len(claim_list)} programs claim this payload and the capture's own "
        f"identity does not separate them "
        f"({[row['display_name'] for row in winners]}); refusing to choose by "
        f"file order"
    )
    return result
