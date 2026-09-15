"""Independent Cycle 33 CS-05 labels and scoring.

Must not import producer span_locate, wiki_parameters, or coaching parsers.
Wiki line labels are attributed retrospective text, not official verification.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Mapping, Sequence

PROTOCOL_ID = "BAS-CS05-INDEPENDENT-LABEL-v33.2"
WIKI_LABEL_CLASS = "WIKI_ATTRIBUTED_RETROSPECTIVE_NOT_OFFICIAL"

_COACH_LINE = re.compile(
    r"^\s*\|\s*(?P<key>head_coach|coach|off_coach|def_coach|cooff_coach\d*|"
    r"codef_coach\d*|oc|dc|hc)\s*=\s*(?P<value>.*)$",
    re.I,
)
_LINK = re.compile(r"\[\[(?:[^\|\]]+\|)?([^\]]+)\]\]")
_KEY_ROLE = {
    "head_coach": "head_coach",
    "coach": "head_coach",
    "hc": "head_coach",
    "off_coach": "offensive_coordinator",
    "oc": "offensive_coordinator",
    "def_coach": "defensive_coordinator",
    "dc": "defensive_coordinator",
}

FROZEN_CURRENT_LABELS: tuple[dict[str, Any], ...] = (
    {
        "program": "Lehigh",
        "season": 2026,
        "subdivision": "FCS",
        "person": "Dan Hunt",
        "role": "offensive_coordinator",
        "qualification": "ASSOCIATE_HC_OC_QB",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Same-record title Associate Head Coach/Offensive Coordinator/Quarterbacks Coach",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Lehigh",
        "season": 2026,
        "subdivision": "FCS",
        "person": "Mike Morita",
        "role": "offensive_coordinator",
        "qualification": "ASSISTANT_OC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Assistant Offensive Coordinator is not a second principal OC",
        "expected_principal": False,
        "era": "current",
    },
    {
        "program": "Princeton",
        "season": 2026,
        "subdivision": "FCS",
        "person": "E.J. Henderson",
        "role": "defensive_coordinator",
        "qualification": "CO_DC",
        "occupancy": "CO_SHARED",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Co-defensive coordinator and defensive backs coach on the same staff record",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Princeton",
        "season": 2026,
        "subdivision": "FCS",
        "person": "Mike Weick",
        "role": "defensive_coordinator",
        "qualification": "CO_DC",
        "occupancy": "CO_SHARED",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Same-record title is Co-Defensive Coordinator; not relabeled principal from discussion wording",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Princeton",
        "season": 2026,
        "subdivision": "FCS",
        "person": "Steve Verbit",
        "role": "defensive_coordinator",
        "qualification": "CHIEF_OF_STAFF_ON_STAFF_PAGE",
        "temporal_precision": "source_page_specific",
        "source_kind": "primary_staff_html",
        "rationale": "Current staff listing is Chief of Staff; historical DC is not current",
        "expected_principal": False,
        "era": "current",
    },
    {
        "program": "San Jose State",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Ken Niumatalolo",
        "role": "head_coach",
        "qualification": "PRINCIPAL_HC",
        "temporal_precision": "current_bio_card",
        "source_kind": "official_bio_html",
        "rationale": "Bio H1/title card is Head Coach; Tafisi is not on that bio",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "San Jose State",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Nu'u Tafisi",
        "role": "head_coach",
        "qualification": "NOT_HC",
        "temporal_precision": "current_bio_card",
        "source_kind": "official_bio_html",
        "rationale": "Name is absent from the head-coach bio card",
        "expected_principal": False,
        "era": "current",
    },
    {
        "program": "Virginia Tech",
        "season": 2026,
        "subdivision": "FBS",
        "person": "James Franklin",
        "role": "head_coach",
        "qualification": "PRINCIPAL_HC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Same-record title Head Coach",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Virginia Tech",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Michael Hazel",
        "role": "head_coach",
        "qualification": "ASSOCIATE_AD",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Associate AD / Executive Director of Football is not Head Coach",
        "expected_principal": False,
        "era": "current",
    },
    {
        "program": "Iowa",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Phil Parker",
        "role": "defensive_coordinator",
        "qualification": "PRINCIPAL_DC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Defensive Coordinator/Secondary on Parker's record",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Iowa",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Seth Wallace",
        "role": "defensive_coordinator",
        "qualification": "NOT_DC_UNLESS_OWN_RECORD",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Assistant-head or LB title is not DC evidence",
        "expected_principal": False,
        "era": "current",
    },
    {
        "program": "Texas A&M",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Elijah Robinson",
        "role": "defensive_coordinator",
        "qualification": "CO_DC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Co-Defensive Coordinator/Defensive Line on Robinson's record",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "Texas A&M",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Lyle Hemphill",
        "role": "defensive_coordinator",
        "qualification": "PRINCIPAL_DC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Source title Defensive Coordiantor is a coordinator misspelling",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "South Carolina",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Clayton White",
        "role": "defensive_coordinator",
        "qualification": "PRINCIPAL_DC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Defensive Coordinator/LBs on White's record",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "South Carolina",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Torrian Gray",
        "role": "defensive_coordinator",
        "qualification": "CO_DC",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Co-Defensive Coordinator on Gray's record",
        "expected_principal": True,
        "era": "current",
    },
    {
        "program": "South Carolina",
        "season": 2026,
        "subdivision": "FBS",
        "person": "Kyle Lindquist",
        "role": "defensive_coordinator",
        "qualification": "WRONG_SPORT_INFIELD",
        "temporal_precision": "current_staff_directory",
        "source_kind": "official_staff_html",
        "rationale": "Infield Coach is baseball, not football DC occupancy",
        "expected_principal": False,
        "era": "current",
    },
)


def _display_name(value: str) -> str:
    text = str(value or "")
    link = _LINK.search(text)
    if link:
        text = link.group(1)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\{\{[^}]+\}\}", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _role_for_key(key: str) -> str | None:
    compact = re.sub(r"[\s_]+", "", key).casefold()
    if compact.startswith("cooffcoach") or compact.startswith("offcoach"):
        return "offensive_coordinator"
    if compact.startswith("codefcoach") or compact.startswith("defcoach"):
        return "defensive_coordinator"
    return _KEY_ROLE.get(key.casefold())


def independent_wiki_coach_lines(wikitext: str) -> list[dict[str, str]]:
    """Line-oriented infobox coach labels. Multiline values are out of scope."""

    found: list[dict[str, str]] = []
    for line in str(wikitext or "").splitlines():
        match = _COACH_LINE.match(line)
        if match is None:
            continue
        role = _role_for_key(match.group("key"))
        person = _display_name(match.group("value"))
        if not role or not person:
            continue
        found.append(
            {
                "person": person,
                "role": role,
                "source_parameter": match.group("key"),
                "label_class": WIKI_LABEL_CLASS,
            }
        )
    return found


def era_bucket(season: int | None) -> str:
    if season is None:
        return "unknown"
    year = int(season)
    if year >= 2024:
        return "current"
    if year >= 2013:
        return "2013_2023"
    if year >= 2000:
        return "2000_2012"
    return "earlier"


def _fold_token(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _qualifier(row: Mapping[str, Any]) -> str:
    occupancy = str(row.get("occupancy") or "").strip()
    if occupancy:
        return occupancy
    qualification = str(row.get("qualification") or "").strip()
    if qualification in {"CO_DC", "CO_OC"}:
        return "CO_SHARED"
    if qualification.startswith("PRINCIPAL") or qualification in {"ASSOCIATE_HC_OC_QB"}:
        return "PRINCIPAL"
    return qualification


def fact_key(
    row: Mapping[str, Any], *, include_role: bool = True, include_qualifier: bool = True
) -> tuple[str, ...]:
    parts = [
        _fold_token(row.get("program") or row.get("program_id")),
        str(row.get("season") or row.get("effective_interval") or ""),
        _fold_token(row.get("person")),
    ]
    if include_role:
        parts.append(str(row.get("role") or ""))
    if include_qualifier:
        parts.append(_qualifier(row))
    return tuple(parts)


def _set_metrics(
    expected: set[tuple[str, ...]], got: set[tuple[str, ...]]
) -> dict[str, Any]:
    tp = len(expected & got)
    fp = len(got - expected)
    fn = len(expected - got)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "expected_count": len(expected),
        "extracted_count": len(got),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
    }


def score_sets(
    expected: Sequence[Mapping[str, Any]],
    extracted: Sequence[Mapping[str, Any]],
    *,
    person_key: str = "person",
    role_key: str = "role",
) -> dict[str, Any]:
    expected_rows = []
    for row in expected:
        item = dict(row)
        if person_key != "person":
            item["person"] = item.get(person_key)
        if role_key != "role":
            item["role"] = item.get(role_key)
        if item.get("person"):
            expected_rows.append(item)
    extracted_rows = []
    for row in extracted:
        item = dict(row)
        if person_key != "person":
            item["person"] = item.get(person_key)
        if role_key != "role":
            item["role"] = item.get(role_key)
        if item.get("person"):
            extracted_rows.append(item)
    identity = _set_metrics(
        {
            fact_key(row, include_role=False, include_qualifier=False)
            for row in expected_rows
        },
        {
            fact_key(row, include_role=False, include_qualifier=False)
            for row in extracted_rows
        },
    )
    role = _set_metrics(
        {fact_key(row, include_qualifier=False) for row in expected_rows},
        {fact_key(row, include_qualifier=False) for row in extracted_rows},
    )
    fact = _set_metrics(
        {fact_key(row) for row in expected_rows},
        {fact_key(row) for row in extracted_rows},
    )
    return {
        **fact,
        "identity_metrics": identity,
        "role_metrics": role,
        "qualifier_metrics": fact,
        "person_role_only_is_not_staff_fact_validation": True,
        "wrong_program_or_season_is_not_true_positive": True,
        "unlabeled_pages_excluded": True,
        "protocol_id": PROTOCOL_ID,
    }


def stratified_counts(labels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_era: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    by_sub: Counter[str] = Counter()
    programs: set[tuple[str, str]] = set()
    for row in labels:
        season = row.get("season")
        year = int(season) if str(season or "").isdigit() else None
        by_era[str(row.get("era") or era_bucket(year))] += 1
        by_role[str(row.get("role") or "")] += 1
        by_sub[str(row.get("subdivision") or "unspecified")] += 1
        programs.add((str(row.get("program") or ""), str(season or "")))
    return {
        "label_count": len(labels),
        "program_season_count": len(programs),
        "by_era": dict(by_era),
        "by_role": dict(by_role),
        "by_subdivision": dict(by_sub),
        "protocol_id": PROTOCOL_ID,
        "does_not_certify_unsampled_population": True,
    }


def dump_labels(rows: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(list(rows), indent=2, ensure_ascii=False)
