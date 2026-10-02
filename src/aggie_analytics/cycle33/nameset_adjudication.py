"""Same-record adjudication of current HC/OC/DC occupants.

Name presence on a page is not concurrent DC/OC occupancy. CSV and the
predecessor BAS matrix are claims. Successors re-extract from official HTML
and primary bio cards using cycle33 taxonomy.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle33.role_taxonomy import (
    ROLE_DC,
    ROLE_HC,
    ROLE_OC,
    assignments_from_title,
    principal_role_families,
)
from aggie_analytics.cycle33.span_locate import bind_person_role, iter_staff_records

OFFICIAL_HTML = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\official_staff"
)
PRIMARY = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews"
    r"\cycle33_user_coaches\20260914T051702Z\primary_sources"
)

COLUMN_TO_ROLE = {
    "Head Coach": ROLE_HC,
    "Offensive Coordinator": ROLE_OC,
    "Defensive Coordinator": ROLE_DC,
}

DISPUTES: tuple[dict[str, Any], ...] = (
    {
        "team": "Iowa",
        "program_id": "SRC-002:TEAM:2294",
        "role": ROLE_DC,
        "csv_people": ("Phil Parker",),
        "bas_people": ("Seth Wallace", "Phil Parker"),
        "inspect": ("Phil Parker", "Seth Wallace"),
        "primary_html": None,
    },
    {
        "team": "San Jose State",
        "program_id": "SRC-002:TEAM:23",
        "role": ROLE_HC,
        "csv_people": ("Ken Niumatalolo",),
        "bas_people": ("Nu'u Tafisi",),
        "inspect": ("Ken Niumatalolo", "Nu'u Tafisi"),
        "primary_html": "sjsu_head_2026.html",
    },
    {
        "team": "South Carolina",
        "program_id": "SRC-002:TEAM:2579",
        "role": ROLE_DC,
        "csv_people": ("Clayton White", "Torrian Gray"),
        "bas_people": ("Kyle Lindquist", "Torrian Gray", "Clayton White"),
        "inspect": ("Clayton White", "Torrian Gray", "Kyle Lindquist"),
        "primary_html": None,
    },
    {
        "team": "Texas A&M",
        "program_id": "SRC-002:TEAM:245",
        "role": ROLE_DC,
        "csv_people": ("Elijah Robinson", "Lyle Hemphill"),
        "bas_people": ("Elijah Robinson",),
        "inspect": ("Elijah Robinson", "Lyle Hemphill"),
        "primary_html": None,
    },
    {
        "team": "Virginia Tech",
        "program_id": "SRC-002:TEAM:259",
        "role": ROLE_HC,
        "csv_people": ("James Franklin",),
        "bas_people": ("Michael Hazel",),
        "inspect": ("James Franklin", "Michael Hazel"),
        "primary_html": "vt_head_2026.html",
    },
    {
        "team": "Princeton",
        "program_id": "SRC-002:TEAM:163",
        "role": ROLE_DC,
        "csv_people": ("E.J. Henderson", "Mike Weick"),
        "bas_people": ("Steve Verbit", "Mike Weick", "E.J. Henderson"),
        "inspect": ("E.J. Henderson", "Mike Weick", "Steve Verbit"),
        "primary_html": "princeton_staff_2026.html",
    },
    {
        "team": "Lehigh",
        "program_id": "SRC-002:TEAM:2329",
        "role": ROLE_OC,
        "csv_people": ("Dan Hunt",),
        "bas_people": ("Dan Hunt", "Mike Morita"),
        "inspect": ("Dan Hunt", "Mike Morita"),
        "primary_html": "lehigh_staff_2026.html",
    },
)


def _fold(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()


def load_html(url: str) -> tuple[str, str | None]:
    if not url:
        return "", None
    cache = OFFICIAL_HTML / f"{sha256_json({'url': url})}.html"
    if cache.is_file():
        return cache.read_text(encoding="utf-8", errors="replace"), str(cache)
    return "", None


def claimed_title_for_role(role: str) -> str:
    return {
        ROLE_HC: "Head Coach",
        ROLE_OC: "Offensive Coordinator",
        ROLE_DC: "Defensive Coordinator",
    }.get(role, role)


_CURRENT_NOT_PRINCIPAL_ROLE = re.compile(
    r"\bchief of staff\b|"
    r"\bassociate\s+(?:athletic\s+director|ad)\b|"
    r"\bexecutive director of football\b|"
    r"\bathletic performance\b|"
    r"\bstrength(?:\s+and\s+conditioning)?\b|"
    r"\binfield\b|"
    r"\bbaseball\b|"
    r"\bsoftball\b|"
    r"\bbasketball\b|"
    r"\bvolleyball\b|"
    r"\bwrestling\b|"
    r"\bhockey\b",
    re.I,
)


def current_title_blocks_role(title: str, role: str) -> bool:
    """Chief-of-staff / AD / performance titles are not current HC/OC/DC."""

    if not title or role not in {ROLE_HC, ROLE_OC, ROLE_DC}:
        return False
    return bool(_CURRENT_NOT_PRINCIPAL_ROLE.search(title))


def occupancy_for_role(title: str, role: str) -> str | None:
    if current_title_blocks_role(title, role):
        return None
    for item in assignments_from_title(title):
        if item["role"] == role:
            return str(item["occupancy"])
    if role in principal_role_families(title):
        return "PRINCIPAL"
    return None


def adjudicate_person(
    html: str,
    *,
    person: str,
    role: str,
    page_url: str = "",
    source_kind: str = "official_staff_html",
) -> dict[str, Any]:
    claimed = claimed_title_for_role(role)
    found = bind_person_role(html, person=person, title=claimed)
    record_title = str(found.get("record_title") or "")
    occupancy = occupancy_for_role(record_title, role) if record_title else None
    principal = occupancy in {"PRINCIPAL", "CO_SHARED"}
    verdict = "NOT_ON_PAGE"
    if found.get("role_claim_supported") and principal:
        verdict = "PRINCIPAL_OR_CO_ROLE_SUPPORTED"
    elif found.get("person_record_bound") and occupancy == "QUALIFIED_NOT_PRINCIPAL":
        verdict = "QUALIFIED_NOT_PRINCIPAL"
    elif found.get("person_record_bound"):
        verdict = "PERSON_BOUND_ROLE_REJECTED"
    elif found.get("string_located"):
        verdict = "STRING_LOCATED_ONLY"
    return {
        "person": person,
        "role": role,
        "claimed_title": claimed,
        "page_url": page_url,
        "source_kind": source_kind,
        "string_located": found.get("string_located"),
        "person_record_bound": found.get("person_record_bound"),
        "role_claim_supported": found.get("role_claim_supported"),
        "record_title": record_title or None,
        "record_selector": found.get("record_selector"),
        "occupancy": occupancy,
        "verdict": verdict,
        "reject_reason": found.get("reject_reason"),
        "contrary_records": found.get("contrary_records") or [],
        "parser_version": found.get("parser_version"),
        "source_hash_sha256": found.get("source_hash_sha256"),
        "pit_admitted": False,
        "name_presence_is_not_concurrency": True,
    }


def _occupant_row(
    *,
    person: str,
    title: str,
    occupancy: str,
    page_url: str,
    record: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "person": person,
        "source_title": title,
        "occupancy": occupancy,
        "page_url": page_url,
        "record_kind": (record or {}).get("kind"),
        "record_selector": (record or {}).get("selector"),
        "relationship": (
            "CONCURRENT_SHARED" if occupancy == "CO_SHARED" else "CONFIRMED_APPOINTMENT"
        ),
        "source": "OFFICIAL_STAFF_HTML",
        "season": 2026,
        "role_claim_supported": True,
        "pit_admitted": False,
    }
    if extra:
        row.update(dict(extra))
    return row


def principal_occupants(
    html: str,
    *,
    role: str,
    page_url: str = "",
    staff_html: str = "",
) -> list[dict[str, Any]]:
    """Current occupants. Staff-directory COS/AD titles beat a coaches-page DC."""

    by_person: dict[str, dict[str, Any]] = {}
    pages = [(html, page_url)]
    if staff_html:
        pages.append((staff_html, "staff_directory_or_primary"))
    blocked: dict[str, str] = {}
    historical: dict[str, list[str]] = {}
    for body, url in pages:
        if not body:
            continue
        for record in iter_staff_records(body):
            person = str(record.get("person") or "").strip()
            title = str(record.get("title") or "")
            key = _fold(person)
            if not person:
                continue
            if current_title_blocks_role(title, role):
                blocked[key] = title
                continue
            occupancy = occupancy_for_role(title, role)
            if occupancy not in {"PRINCIPAL", "CO_SHARED"}:
                continue
            historical.setdefault(key, []).append(title)
            prior = by_person.get(key)
            if prior is None or (
                occupancy == "PRINCIPAL" and prior.get("occupancy") != "PRINCIPAL"
            ):
                by_person[key] = _occupant_row(
                    person=person,
                    title=title,
                    occupancy=occupancy,
                    page_url=url,
                    record=record,
                )
    occupants: list[dict[str, Any]] = []
    for key, row in by_person.items():
        if key in blocked:
            historical.setdefault(key, []).append(row["source_title"])
            continue
        occupants.append(row)
    occupants.sort(
        key=lambda item: (0 if item["occupancy"] == "PRINCIPAL" else 1, item["person"])
    )
    if blocked:
        for row in occupants:
            row["excluded_current_titles"] = [
                {"person_key": key, "current_title": title}
                for key, title in blocked.items()
            ]
    return occupants


def page_url_from_matrix(cells: Sequence[Mapping[str, Any]], program_id: str) -> str:
    for cell in cells:
        if str(cell.get("program_id")) != program_id:
            continue
        for ep in cell.get("episode_refs") or []:
            url = str(ep.get("page_url") or "")
            if url:
                return url
    return ""


def rebuild_matrix_from_html(
    predecessor_cells: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Successor occupants from same-record HTML. Predecessor cells are kept."""

    html_cache: dict[str, str] = {}
    staff_by_program = {
        str(item["program_id"]): str(item["primary_html"])
        for item in DISPUTES
        if item.get("primary_html")
    }
    successor: list[dict[str, Any]] = []
    for cell in predecessor_cells:
        program_id = str(cell.get("program_id") or "")
        role = str(cell.get("role") or "")
        url = page_url_from_matrix([cell], program_id) or page_url_from_matrix(
            predecessor_cells, program_id
        )
        if url not in html_cache:
            html_cache[url], _cache_path = load_html(url)
        html = html_cache.get(url) or ""
        staff_html = ""
        staff_name = staff_by_program.get(program_id)
        if staff_name:
            staff_path = PRIMARY / staff_name
            if staff_path.is_file():
                staff_html = staff_path.read_text(encoding="utf-8", errors="replace")
        if not html or role not in {ROLE_HC, ROLE_OC, ROLE_DC}:
            successor.append(
                {
                    **dict(cell),
                    "span_adjudicated": False,
                    "html_missing": not bool(html),
                    "successor_from_html": False,
                    "predecessor_preserved": True,
                    "pit_admitted": False,
                }
            )
            continue
        occupants = principal_occupants(
            html, role=role, page_url=url, staff_html=staff_html
        )
        if occupants:
            disposition = (
                "CONFIRMED_CO_SHARED_ROLE"
                if len(occupants) > 1
                or any(item["occupancy"] == "CO_SHARED" for item in occupants)
                else "CONFIRMED_APPOINTMENT"
            )
            successor.append(
                {
                    **dict(cell),
                    "disposition": disposition,
                    "episode_refs": occupants,
                    "episode_cardinality": len(occupants),
                    "principal_people": [
                        item["person"]
                        for item in occupants
                        if item.get("occupancy") == "PRINCIPAL"
                    ],
                    "co_people": [
                        item["person"]
                        for item in occupants
                        if item.get("occupancy") == "CO_SHARED"
                    ],
                    "span_adjudicated": True,
                    "successor_from_html": True,
                    "predecessor_episode_refs": cell.get("episode_refs"),
                    "pit_admitted": False,
                }
            )
            continue
        successor.append(
            {
                **dict(cell),
                "disposition": "UNKNOWN_NOT_LISTED",
                "episode_refs": [],
                "episode_cardinality": 0,
                "span_adjudicated": True,
                "successor_from_html": True,
                "predecessor_episode_refs": cell.get("episode_refs"),
                "rejected_predecessor_occupants": cell.get("episode_refs"),
                "pit_admitted": False,
            }
        )
    return successor


def _people_from_csv_text(csv_text: str) -> list[str]:
    names: list[str] = []
    for part in str(csv_text or "").replace("–", "—").split("|"):
        name = part.split("—")[0].strip()
        if name:
            names.append(name)
    return names


def reconstruct_comparison_row(
    row: Mapping[str, Any],
    successor_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
    html_by_program: Mapping[str, str],
    url_by_program: Mapping[str, str],
) -> dict[str, Any]:
    program_ids = [str(item) for item in row.get("candidate_program_ids") or []]
    role = COLUMN_TO_ROLE.get(str(row.get("column") or ""), "")
    csv_people = _people_from_csv_text(str(row.get("csv_text") or ""))
    successor_people: list[str] = []
    for pid in program_ids:
        cell = successor_by_key.get((pid, role), {})
        successor_people.extend(
            str(ep.get("person") or "")
            for ep in cell.get("episode_refs") or []
            if ep.get("person")
        )
    html = ""
    url = ""
    for pid in program_ids:
        html = html_by_program.get(pid) or html
        url = url_by_program.get(pid) or url
    csv_adjudicated: list[dict[str, Any]] = []
    csv_fold = {_fold(name) for name in csv_people if name}
    suc_fold = {_fold(name) for name in successor_people if name}
    if not csv_people and not successor_people:
        classification = "BOTH_ABSENT_RECONSTRUCTION"
    elif csv_fold == suc_fold:
        classification = "NAME_SET_AGREEMENT_NOT_FACTUAL_CORROBORATION"
    elif csv_fold & suc_fold:
        classification = "PARTIAL_OVERLAP_NEEDS_RECORD_EVIDENCE"
    else:
        classification = "NAME_SET_DIFFERENCE_RECORD_ADJUDICATION"
    return {
        **dict(row),
        "reconstruction_classification": classification,
        "csv_people": csv_people,
        "successor_people": successor_people,
        "csv_adjudicated": csv_adjudicated,
        "identity_accepted": False,
        "fact_verified": False,
        "name_agreement_is_not_independent_confirmation": True,
        "pit_admitted": False,
    }


def adjudicate_disputes(
    predecessor_cells: Sequence[Mapping[str, Any]],
    successor_cells: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pred_by = {
        (str(cell.get("program_id")), str(cell.get("role"))): cell
        for cell in predecessor_cells
    }
    suc_by = {
        (str(cell.get("program_id")), str(cell.get("role"))): cell
        for cell in successor_cells
    }
    rows: list[dict[str, Any]] = []
    for dispute in DISPUTES:
        pid = str(dispute["program_id"])
        role = str(dispute["role"])
        pred = pred_by.get((pid, role), {})
        suc = suc_by.get((pid, role), {})
        url = page_url_from_matrix(predecessor_cells, pid)
        html, cache_path = load_html(url)
        primary_html = ""
        primary_name = dispute.get("primary_html")
        if primary_name:
            path = PRIMARY / str(primary_name)
            if path.is_file():
                primary_html = path.read_text(encoding="utf-8", errors="replace")
        inspections = [
            adjudicate_person(html, person=person, role=role, page_url=url)
            for person in dispute["inspect"]
            if html
        ]
        primary_inspections = [
            adjudicate_person(
                primary_html,
                person=person,
                role=role,
                page_url=str(primary_name),
                source_kind="primary_staff_or_bio_html",
            )
            for person in dispute["inspect"]
            if primary_html
        ]
        rows.append(
            {
                "team": dispute["team"],
                "program_id": pid,
                "role": role,
                "season": 2026,
                "csv_people": list(dispute["csv_people"]),
                "bas_predecessor_people": list(dispute["bas_people"]),
                "before_people": [
                    ep.get("person") for ep in pred.get("episode_refs") or []
                ],
                "after_people": [
                    ep.get("person") for ep in suc.get("episode_refs") or []
                ],
                "principal_people": list(suc.get("principal_people") or []),
                "co_people": list(suc.get("co_people") or []),
                "before_disposition": pred.get("disposition"),
                "after_disposition": suc.get("disposition"),
                "page_url": url,
                "cache_path": cache_path,
                "official_inspections": inspections,
                "primary_inspections": primary_inspections,
                "supported_principal": [
                    row["person"]
                    for row in inspections
                    if row["verdict"] == "PRINCIPAL_OR_CO_ROLE_SUPPORTED"
                    and row.get("occupancy") == "PRINCIPAL"
                ],
                "supported_co": [
                    row["person"]
                    for row in inspections
                    if row["verdict"] == "PRINCIPAL_OR_CO_ROLE_SUPPORTED"
                    and row.get("occupancy") == "CO_SHARED"
                ],
                "rejected_role_claims": [
                    {
                        "person": row["person"],
                        "record_title": row["record_title"],
                        "verdict": row["verdict"],
                    }
                    for row in inspections + primary_inspections
                    if row["verdict"] != "PRINCIPAL_OR_CO_ROLE_SUPPORTED"
                    or current_title_blocks_role(
                        str(row.get("record_title") or ""), role
                    )
                ],
                "operator_overlay_not_applied": True,
                "source_title_occupancy_not_relabeled": True,
                "automated_verdict_forbidden": False,
                "csv_does_not_automatically_win": True,
                "bas_matrix_does_not_automatically_win": True,
                "pit_admitted": False,
            }
        )
    return rows


def matrix_summary(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("disposition") or "") for row in cells)
    supported = 0
    fbs = 0
    fcs = 0
    for cell in cells:
        if str(cell.get("disposition") or "") in {
            "CONFIRMED_APPOINTMENT",
            "CONFIRMED_CO_SHARED_ROLE",
        } and cell.get("episode_refs"):
            supported += 1
    return {
        "cell_count": len(cells),
        "disposition_counts": dict(counts),
        "supported_role_cells": supported,
        "requires_nonempty_fbs_and_fcs": True,
        "fbs_placeholder_not_inferred": fbs,
        "fcs_placeholder_not_inferred": fcs,
        "pit_admitted": False,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
