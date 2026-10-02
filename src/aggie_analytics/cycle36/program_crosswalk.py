"""Versioned, source-backed program identity and alias crosswalk.

MR35R-07 left 864 staff cells unresolved across eleven distinct program
names. The Cycle #35 position -- that mapping them would be inference -- was
right about hand-mapping and wrong about there being nothing to map from.
The cached CFBD ``/teams`` payloads already carry the two facts a crosswalk
needs:

* a **stable source entity id** that survives an institutional rename, so
  ``SRC-002:TEAM:3101`` is one program whether the source displays it as
  Dixie State or Utah Tech; and
* an **alternateNames** list that records the other spellings the source
  itself accepts for that entity.

Those two facts settle *identity*. They deliberately do not settle
*effective dates*: every cached payload, including ``year=2013``, renders
the program under its CURRENT display name, so the payload proves that
"Dixie State" and "Utah Tech" denote one entity and proves nothing about
when the name changed. Effective intervals therefore come from a separate,
explicitly-cited rename source or stay
``EFFECTIVE_INTERVAL_UNKNOWN_FROM_THIS_SOURCE``. Conflating the two is the
error TP36-01 names: "Preserve source spelling, effective interval,
publication/observation time and provider namespace."

Three rules keep this from becoming fuzzy matching:

1. **Never merge on name similarity.** A raw name resolves only through an
   exact normalized match against a source-declared school name or
   alternate name. "Albany" matches both UAlbany (399) and Albany State
   (2013), so it stays ``AMBIGUOUS`` forever rather than picking the bigger
   program.
2. **Never merge distinct institutions.** ``SRC-002:TEAM:2837`` (East Texas
   A&M, formerly Texas A&M-Commerce) and ``SRC-002:TEAM:245`` (Texas A&M,
   College Station) are separate entities in the source and stay separate
   here. A regression test asserts it.
3. **Never invent membership.** Resolving a name to a canonical program is
   not a claim that the program was an FBS/FCS member in the asked-about
   season; membership is a separate table with its own evidence.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CROSSWALK_VERSION = "BAS-PROGRAM-CROSSWALK-v36.1"

RESOLVED = "RESOLVED_SINGLE_CANONICAL_PROGRAM"
AMBIGUOUS = "UNRESOLVED_NAME_MATCHES_MORE_THAN_ONE_CANONICAL_PROGRAM"
#: What a failed lookup actually establishes. The earlier value of this
#: constant was UNRESOLVED_NAME_ABSENT_FROM_EVERY_DECLARED_SOURCE_PAYLOAD,
#: which asserted far more than the code tested: resolution is an exact match
#: on two declared normalisations, so a miss means those two keys matched no
#: declared name -- not that no payload names the program. It does not: the
#: payloads carry "McNeese" for the query "McNeese State", "Troy" for "Troy
#: State", "Saint Francis" for "Saint Francis (PA)" and "UAlbany" for
#: "Albany". A state that overstates its own evidence is the defect this
#: cycle exists to repair, so it is named for what it measured.
ABSENT = "UNRESOLVED_NO_DECLARED_NAME_MATCHES_THIS_QUERY"

#: Tokens that carry no institutional identity on their own. A shared token
#: drawn only from this set is not evidence that two names denote the same
#: program, so candidate reporting ignores them.
GENERIC_NAME_TOKENS = frozenset(
    {
        "state",
        "university",
        "college",
        "univ",
        "of",
        "the",
        "at",
        "and",
        "a",
        # Compass and "new" prefixes distinguish institutions from each other
        # ("Northwest Missouri State" is not "Missouri State"), so they must
        # never be the only thing two names share.
        "new",
        "north",
        "south",
        "east",
        "west",
        "northern",
        "southern",
        "eastern",
        "western",
        "central",
        "san",
        "los",
    }
)

#: The one orthographic pair these sources genuinely alternate between. It is
#: used ONLY to widen candidate REPORTING and never to resolve a name: an
#: abbreviation expansion can merge two different institutions, which is
#: exactly what resolution must not do.
_REPORTING_ONLY_VARIANTS = {"saint": "st", "st": "saint"}

CANDIDATE_VARIANT = "CANDIDATE_BY_DECLARED_ORTHOGRAPHIC_VARIANT_NOT_MERGED"
CANDIDATE_TOKEN_SUBSET = "CANDIDATE_BY_TOKEN_SUBSET_NOT_MERGED"
CANDIDATE_TIGHT_CONTAINMENT = "CANDIDATE_BY_ORTHOGRAPHIC_CONTAINMENT_NOT_MERGED"
NO_CANDIDATE = "NO_CANDIDATE_NAME_IN_ANY_DECLARED_PAYLOAD"


def _reporting_tokens(name: str) -> frozenset[str]:
    tokens = set(normalize_name(name).split())
    for token in list(tokens):
        variant = _REPORTING_ONLY_VARIANTS.get(token)
        if variant:
            tokens.add(variant)
    return frozenset(tokens)


def related_candidates(
    queried: str, declared_names: Mapping[str, Sequence[str]]
) -> list[dict[str, Any]]:
    """Individually inspect one unresolved name against every declared name.

    ``declared_names`` maps a canonical program id to the display names the
    declared payloads actually write for it. The result NAMES the canonical
    programs whose declared spelling is related to ``queried`` under two
    written-down rules, and says for each that it is a candidate requiring
    source rename evidence. Nothing here resolves, merges or changes a cell:
    the pack forbids fuzzy-merging Albany or any similarly named program by
    convenience, and a candidate list is the opposite of a merge -- it is the
    individual inspection that makes the remaining unknown specific.
    """

    query_tokens = _reporting_tokens(queried)
    discriminative = {
        token
        for token in query_tokens
        if len(token) >= 3 and token not in GENERIC_NAME_TOKENS
    }
    query_tight = normalize_name_tight(queried)
    found: list[dict[str, Any]] = []
    for program_id, names in sorted(declared_names.items()):
        for name in names:
            name_tokens = _reporting_tokens(name)
            shared = query_tokens & name_tokens
            discriminative_shared = bool(discriminative & name_tokens)
            # Equal only once "Saint" and "St." are treated as the one pair
            # these sources alternate between. Resolution refuses that
            # expansion because it can merge two institutions; reporting it
            # as a candidate names the possibility without acting on it.
            variant = (
                query_tokens == name_tokens
                and normalize_name(queried) != normalize_name(name)
                and discriminative_shared
            )
            subset = (
                (query_tokens < name_tokens or name_tokens < query_tokens)
                and discriminative_shared
            )
            name_tight = normalize_name_tight(name)
            # Containment has to align to one end. A free-floating substring
            # relates "Eastern" to "Southeastern Louisiana" and "West Texas"
            # to "Southwest Texas State", which are different institutions
            # that merely share letters across a word boundary. Requiring a
            # prefix or a suffix keeps "Albany" inside "UAlbany" and drops
            # those.
            shorter, longer = sorted((query_tight, name_tight), key=len)
            contained = (
                len(shorter) >= 6
                and query_tight != name_tight
                and (longer.startswith(shorter) or longer.endswith(shorter))
            )
            if not (variant or subset or contained):
                continue
            if variant:
                basis = CANDIDATE_VARIANT
            elif subset:
                basis = CANDIDATE_TOKEN_SUBSET
            else:
                basis = CANDIDATE_TIGHT_CONTAINMENT
            found.append(
                {
                    "canonical_program_id": program_id,
                    "declared_name": name,
                    "basis": basis,
                    "shared_tokens": sorted(shared),
                    "disposition": (
                        "CANDIDATE_REQUIRES_SOURCE_RENAME_EVIDENCE_NOT_MERGED"
                    ),
                }
            )
            break
    return found
OUT_OF_POPULATION = "RESOLVED_BUT_OUTSIDE_THE_FBS_FCS_FOOTBALL_POPULATION"

EFFECTIVE_UNKNOWN = "EFFECTIVE_INTERVAL_UNKNOWN_FROM_THIS_SOURCE"
EFFECTIVE_CITED = "EFFECTIVE_INTERVAL_FROM_CITED_RENAME_SOURCE"

#: Divisions the national football denominator keeps. Others are retained
#: as identities but flagged out-of-population rather than deleted.
FOOTBALL_POPULATION_CLASSIFICATIONS = frozenset({"fbs", "fcs"})

_PUNCT = re.compile(r"[^a-z0-9]+")
_LEADING_SEASON = re.compile(r"^\s*(?:18|19|20)\d\d\s+")
_TRAILING_TEAM = re.compile(
    r"\s+(?:football\s+team|football|team)\s*$", re.I
)


def normalize_name(raw: str) -> str:
    """Fold a display name to a comparison key.

    Case, punctuation, diacritics and the en/em dashes these sources mix
    freely are removed. Nothing else is: no token dropping, no stemming and
    no abbreviation expansion, because each of those would let two different
    institutions collide.
    """

    text = unicodedata.normalize("NFKD", str(raw or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("–", "-").replace("—", "-").replace("’", "'")
    text = text.casefold()
    text = _PUNCT.sub(" ", text).strip()
    return re.sub(r"\s+", " ", text)


def normalize_name_tight(raw: str) -> str:
    """The same fold with punctuation removed instead of spaced.

    The source writes ``Hawai'i`` and the research corpus writes ``Hawaii``.
    Under the spacing fold those are ``hawai i`` and ``hawaii`` and never
    meet, although they differ by one apostrophe inside a word. Producing a
    second, tighter key is a declared *orthographic* variant of the same
    string -- it drops no token and expands no abbreviation -- and a match
    still has to be exact and unique against a source-declared name. Both
    keys are indexed, and a tight key that would collide two programs is
    refused exactly like any other collision.
    """

    text = unicodedata.normalize("NFKD", str(raw or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("–", " ").replace("—", " ").replace("’", "")
    text = text.casefold().replace("'", "")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", "", text).strip()


def strip_season_and_suffix(raw: str) -> str:
    """Turn "2011 Louisiana-Monroe Warhawks football team" into a school name.

    Wikimedia team-season page titles carry the season, the nickname and a
    "football team" suffix. Removing them is lexical tidying of a known
    title shape, not an identity guess: the residue still has to match a
    declared source name exactly.
    """

    text = _LEADING_SEASON.sub("", str(raw or "").strip())
    text = _TRAILING_TEAM.sub("", text).strip()
    return text


@dataclass(frozen=True)
class AliasRecord:
    """One source-declared spelling for one canonical program."""

    canonical_program_id: str
    source_namespace: str
    source_entity_id: str
    original_alias: str
    normalized_alias: str
    alias_basis: str
    observed_in_seasons: tuple[int, ...]
    effective_state: str
    effective_start: str | None = None
    effective_end: str | None = None
    source_payload_sha256: str | None = None
    source_locator: str | None = None
    rename_source_url: str | None = None
    rename_source_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_program_id": self.canonical_program_id,
            "source_namespace": self.source_namespace,
            "source_entity_id": self.source_entity_id,
            "original_alias": self.original_alias,
            "normalized_alias": self.normalized_alias,
            "alias_basis": self.alias_basis,
            "observed_in_seasons": list(self.observed_in_seasons),
            "effective_state": self.effective_state,
            "effective_start": self.effective_start,
            "effective_end": self.effective_end,
            "source_payload_sha256": self.source_payload_sha256,
            "source_locator": self.source_locator,
            "rename_source_url": self.rename_source_url,
            "rename_source_note": self.rename_source_note,
        }


@dataclass
class CanonicalProgram:
    """One program identity as the source namespace defines it."""

    canonical_program_id: str
    source_namespace: str
    source_entity_id: str
    display_names: set[str] = field(default_factory=set)
    mascots: set[str] = field(default_factory=set)
    classifications_by_season: dict[int, str] = field(default_factory=dict)
    seasons_observed: set[int] = field(default_factory=set)

    @property
    def in_football_population(self) -> bool:
        return any(
            value in FOOTBALL_POPULATION_CLASSIFICATIONS
            for value in self.classifications_by_season.values()
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_program_id": self.canonical_program_id,
            "source_namespace": self.source_namespace,
            "source_entity_id": self.source_entity_id,
            "display_names": sorted(self.display_names),
            "mascots": sorted(self.mascots),
            "seasons_observed": sorted(self.seasons_observed),
            "classification_by_season": {
                str(k): v for k, v in sorted(self.classifications_by_season.items())
            },
            "in_football_population": self.in_football_population,
        }


@dataclass
class Crosswalk:
    """Alias index plus the programs it points at."""

    version: str
    programs: dict[str, CanonicalProgram]
    aliases: dict[str, list[AliasRecord]]
    #: The same records keyed by the tighter orthographic fold, consulted
    #: only when the spacing fold finds nothing.
    tight_aliases: dict[str, list[AliasRecord]] = field(default_factory=dict)
    #: Rename evidence supplied outside the membership payloads, keyed by
    #: canonical program id.
    rename_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def resolve(
        self, raw_name: str, season: int | None = None, *, strip_title: bool = True
    ) -> dict[str, Any]:
        """Resolve one raw program spelling, with the reason on every path."""

        candidate_text = strip_season_and_suffix(raw_name) if strip_title else str(raw_name)
        key = normalize_name(candidate_text)
        record: dict[str, Any] = {
            "crosswalk_version": self.version,
            "raw_name": raw_name,
            "normalized_query": key,
            "season": season,
        }
        matches = self.aliases.get(key, [])
        record["match_basis"] = "EXACT_NORMALIZED_NAME"
        if not matches:
            tight = normalize_name_tight(candidate_text)
            record["normalized_tight_query"] = tight
            matches = self.tight_aliases.get(tight, [])
            if matches:
                record["match_basis"] = "ORTHOGRAPHIC_VARIANT_PUNCTUATION_REMOVED"
        distinct = sorted({m.canonical_program_id for m in matches})
        record["matched_alias_count"] = len(matches)
        record["candidate_program_ids"] = distinct
        if not matches:
            record.update(
                state=ABSENT,
                canonical_program_id=None,
                detail=(
                    "Neither declared normalisation of this spelling matches "
                    "a name any declared payload writes, so the observation "
                    "is retained unresolved rather than matched to a similar "
                    "name. This says what the lookup tested. It does NOT say "
                    "the payloads never name the program: related declared "
                    "spellings are reported separately by "
                    "related_candidates(), which names them without merging "
                    "them."
                ),
            )
            return record
        if len(distinct) > 1:
            record.update(
                state=AMBIGUOUS,
                canonical_program_id=None,
                detail=(
                    "This spelling is a declared name for more than one "
                    f"program ({distinct}). Choosing between them would be a "
                    "convenience merge, so the observation stays unresolved."
                ),
                matched_aliases=[m.as_dict() for m in matches[:8]],
            )
            return record
        program = self.programs[distinct[0]]
        alias = matches[0]
        record["matched_alias"] = alias.as_dict()
        record["program"] = program.as_dict()
        if not program.in_football_population:
            record.update(
                state=OUT_OF_POPULATION,
                canonical_program_id=program.canonical_program_id,
                detail=(
                    "The name resolves to exactly one source program, but the "
                    "source never classifies it as FBS or FCS in any acquired "
                    "season, so it is outside the national football "
                    "denominator. Its identity is kept; its cells are not "
                    "counted as national coverage."
                ),
            )
            return record
        record.update(
            state=RESOLVED,
            canonical_program_id=program.canonical_program_id,
            season_classification=(
                program.classifications_by_season.get(int(season))
                if season is not None
                else None
            ),
            season_membership_observed=(
                int(season) in program.seasons_observed if season is not None else None
            ),
            detail=(
                "The spelling is a declared name of exactly one source "
                "program. Resolving identity is not a claim that the program "
                "was an FBS/FCS member in this season; that is the membership "
                "table's separate question."
            ),
        )
        return record

    def as_dict(self) -> dict[str, Any]:
        return {
            "crosswalk_version": self.version,
            "program_count": len(self.programs),
            "alias_key_count": len(self.aliases),
            "alias_record_count": sum(len(v) for v in self.aliases.values()),
            "programs_in_football_population": sum(
                1 for p in self.programs.values() if p.in_football_population
            ),
            "rename_evidence": self.rename_evidence,
        }


def build_crosswalk(
    payloads_by_season: Mapping[int, tuple[str, Sequence[Mapping[str, Any]]]],
    source_namespace: str = "SRC-002",
    rename_evidence: Mapping[str, dict[str, Any]] | None = None,
    declared_name_rows: Sequence[Mapping[str, Any]] = (),
    declared_name_digest: str | None = None,
    declared_name_basis: str = "HISTORICAL_MEMBERSHIP_DISPLAY_NAME",
) -> Crosswalk:
    """Build the crosswalk from season-keyed ``/teams`` payloads.

    ``payloads_by_season`` maps a season to ``(payload_sha256, rows)``. Every
    row contributes its school name and every declared alternate name as an
    alias of that row's source entity id. An alias that two entities both
    declare is kept on both, which is what makes "Albany" resolve to
    ``AMBIGUOUS`` instead of silently to one of them.
    """

    programs: dict[str, CanonicalProgram] = {}
    aliases: dict[str, list[AliasRecord]] = {}
    alias_seasons: dict[tuple[str, str], set[int]] = {}
    alias_meta: dict[tuple[str, str], tuple[str, str, str | None]] = {}

    for season in sorted(payloads_by_season):
        digest, rows = payloads_by_season[season]
        for index, row in enumerate(rows):
            entity_id = str(row.get("id"))
            if entity_id in {"", "None"}:
                continue
            program_id = f"{source_namespace}:TEAM:{entity_id}"
            program = programs.get(program_id)
            if program is None:
                program = CanonicalProgram(
                    canonical_program_id=program_id,
                    source_namespace=source_namespace,
                    source_entity_id=entity_id,
                )
                programs[program_id] = program
            school = str(row.get("school") or "").strip()
            classification = row.get("classification")
            if school:
                program.display_names.add(school)
            if row.get("mascot"):
                program.mascots.add(str(row["mascot"]))
            program.seasons_observed.add(int(season))
            if classification:
                program.classifications_by_season[int(season)] = str(classification)

            spellings: list[tuple[str, str]] = []
            if school:
                spellings.append((school, "SOURCE_SCHOOL_NAME"))
            for alternate in row.get("alternateNames") or []:
                text = str(alternate or "").strip()
                if text:
                    spellings.append((text, "SOURCE_ALTERNATE_NAME"))
            # A school plus its mascot is the shape Wikimedia team-season
            # titles use ("Utah Tech Trailblazers"), so the source's own two
            # fields are combined rather than a nickname being guessed.
            if school and row.get("mascot"):
                spellings.append((f"{school} {row['mascot']}", "SOURCE_SCHOOL_PLUS_MASCOT"))
                for alternate in row.get("alternateNames") or []:
                    text = str(alternate or "").strip()
                    if text:
                        spellings.append(
                            (f"{text} {row['mascot']}", "SOURCE_ALTERNATE_PLUS_MASCOT")
                        )

            for text, basis in spellings:
                key = normalize_name(text)
                if not key:
                    continue
                pair = (program_id, key)
                alias_seasons.setdefault(pair, set()).add(int(season))
                if pair not in alias_meta:
                    alias_meta[pair] = (text, basis, digest)

    # A second declared source: the historical membership derivative states a
    # program id beside the display name the source used for that season.
    # Twenty programs that dropped football before the /teams coverage window
    # exist only here, so omitting it would erase their identities rather than
    # preserve them.
    for row in declared_name_rows:
        program_id = str(row.get("program_id") or "")
        display = str(row.get("display_name") or "").strip()
        if not program_id or not display:
            continue
        season = row.get("season")
        program = programs.get(program_id)
        if program is None:
            program = CanonicalProgram(
                canonical_program_id=program_id,
                source_namespace=source_namespace,
                source_entity_id=program_id.rsplit(":", 1)[-1],
            )
            programs[program_id] = program
        program.display_names.add(display)
        if season is not None:
            program.seasons_observed.add(int(season))
            classification = row.get("classification") or row.get("source_classification")
            if classification:
                program.classifications_by_season.setdefault(
                    int(season), str(classification)
                )
        key = normalize_name(display)
        if not key:
            continue
        pair = (program_id, key)
        if season is not None:
            alias_seasons.setdefault(pair, set()).add(int(season))
        else:
            alias_seasons.setdefault(pair, set())
        alias_meta.setdefault(pair, (display, declared_name_basis, declared_name_digest))

    rename_evidence = dict(rename_evidence or {})
    for (program_id, key), seasons in sorted(alias_seasons.items()):
        original, basis, digest = alias_meta[(program_id, key)]
        evidence = rename_evidence.get(program_id) or {}
        matched_rename = None
        for entry in evidence.get("names") or []:
            if normalize_name(entry.get("name", "")) == key:
                matched_rename = entry
                break
        aliases.setdefault(key, []).append(
            AliasRecord(
                canonical_program_id=program_id,
                source_namespace=source_namespace,
                source_entity_id=program_id.rsplit(":", 1)[-1],
                original_alias=original,
                normalized_alias=key,
                alias_basis=basis,
                observed_in_seasons=tuple(sorted(seasons)),
                effective_state=(
                    EFFECTIVE_CITED if matched_rename else EFFECTIVE_UNKNOWN
                ),
                effective_start=(matched_rename or {}).get("effective_start"),
                effective_end=(matched_rename or {}).get("effective_end"),
                source_payload_sha256=digest,
                source_locator=f"/teams payload rows -> id={program_id.rsplit(':',1)[-1]}",
                rename_source_url=(matched_rename or {}).get("source_url"),
                rename_source_note=(matched_rename or {}).get("note"),
            )
        )
    for records in aliases.values():
        records.sort(key=lambda r: (r.canonical_program_id, r.alias_basis))
    tight_aliases: dict[str, list[AliasRecord]] = {}
    for records in aliases.values():
        for record in records:
            tight_aliases.setdefault(
                normalize_name_tight(record.original_alias), []
            ).append(record)
    for records in tight_aliases.values():
        records.sort(key=lambda r: (r.canonical_program_id, r.alias_basis))
    return Crosswalk(
        version=CROSSWALK_VERSION,
        programs=programs,
        aliases=aliases,
        tight_aliases=tight_aliases,
        rename_evidence=rename_evidence,
    )


def conflict_report(crosswalk: Crosswalk) -> dict[str, Any]:
    """Every alias that more than one canonical program declares.

    These are the collisions a name-based join would silently resolve. They
    are published so a reviewer can see that the crosswalk refuses them.
    """

    collisions = []
    for basis, index in (
        ("EXACT_NORMALIZED_NAME", crosswalk.aliases),
        ("ORTHOGRAPHIC_VARIANT_PUNCTUATION_REMOVED", crosswalk.tight_aliases),
    ):
        for key, records in sorted(index.items()):
            program_ids = sorted({r.canonical_program_id for r in records})
            if len(program_ids) > 1:
                collisions.append(
                    {
                        "match_basis": basis,
                        "normalized_alias": key,
                        "canonical_program_ids": program_ids,
                        "original_spellings": sorted({r.original_alias for r in records}),
                        "disposition": AMBIGUOUS,
                    }
                )
    return {
        "crosswalk_version": crosswalk.version,
        "colliding_alias_count": len(collisions),
        "collisions": collisions,
    }


def load_payloads(
    raw_dir: Path,
    seasons: Iterable[int],
    request_identity,
    parameter_shapes: Sequence[dict[str, Any]] = ({}, {"classification": "fbs"}),
    endpoint: str = "/teams",
) -> dict[int, tuple[str, list[dict[str, Any]]]]:
    """Season-keyed cached payloads addressed by their request identity."""

    import hashlib

    found: dict[int, tuple[str, list[dict[str, Any]]]] = {}
    for season in seasons:
        for shape in parameter_shapes:
            parameters = {"year": int(season), **shape}
            path = raw_dir / f"{request_identity(endpoint, parameters)}.json"
            if not path.is_file():
                continue
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            rows = payload if isinstance(payload, list) else (
                payload.get("data") or payload.get("teams") or []
            )
            found[int(season)] = (
                hashlib.sha256(raw).hexdigest(),
                [row for row in rows if isinstance(row, Mapping)],
            )
            break
    return found
