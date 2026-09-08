"""Coaching schema, lattices, row-bound extraction, and attempt ledgers.

Equal-length name/title arrays are not a safe join. No DISPLAY: program IDs.
Coaching remains out of fitted models this cycle.
"""

from __future__ import annotations

import csv
import html as html_lib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle30.temporal import parse_aware_utc

ROLE_HC = "head_coach"
ROLE_OC = "offensive_coordinator"
ROLE_DC = "defensive_coordinator"
PRIMARY_ROLES = (ROLE_HC, ROLE_OC, ROLE_DC)

CONCURRENT = "CONCURRENT_SHARED"
SEQUENTIAL = "SEQUENTIAL_CHANGE"
NOT_ATTEMPTED = "NOT_ATTEMPTED"

DISPOSITIONS = (
    "CONFIRMED_APPOINTMENT",
    "CONFIRMED_CO_SHARED_ROLE",
    "CONFIRMED_VACANCY",
    "ROLE_NOT_APPLICABLE",
    "UNKNOWN_NOT_LISTED",
    "ACQUISITION_FAILED",
    "RIGHTS_BLOCKED",
    "CONFLICT",
    "CANDIDATE_ONLY",
    "APPLICABILITY_UNRESOLVED",
    "QUEUED_FOR_BACKFILL",
    NOT_ATTEMPTED,
)


class CoachingError(ValueError):
    """Raised when a coaching contract is violated."""


def reject_play_caller_from_title(title: str, role_type: str) -> None:
    lowered = title.lower()
    coordinator = any(
        token in lowered
        for token in (
            "offensive coordinator",
            "defensive coordinator",
            "special teams coordinator",
            " co-offensive",
            " co-defensive",
        )
    ) or lowered.strip() in {"oc", "dc", "stc"}
    if coordinator and role_type in {"offense_play_caller", "defense_play_caller"}:
        raise CoachingError("play-caller cannot be inferred from coordinator title")


def reject_cfbd_assistant(source: str, role_type: str) -> None:
    if source.upper() == "CFBD" and role_type != ROLE_HC:
        raise CoachingError("CFBD head-coach backbone cannot populate assistant roles")


def reject_name_only(method: str, state: str) -> None:
    if (
        method.lower().replace("-", "_") in {"name_only", "nameonly"}
        and state != "CANDIDATE_ONLY"
    ):
        raise CoachingError("name-only coach identity cannot be auto-admitted")


def reject_composite_title_bypass(title: str, recognized: bool) -> None:
    lowered = title.lower()
    composite = "coordinator" in lowered and (
        "co-" in lowered or "interim" in lowered or "/" in lowered
    )
    if composite and not recognized:
        raise CoachingError("normalized composite-title recognition required")


def extract_row_bound_staff(nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Bind person/title in the same DOM node/table row/source span."""

    extracted: list[dict[str, str]] = []
    for node in nodes:
        person = node.get("person") or node.get("name")
        title = node.get("title")
        span_id = node.get("span_id") or node.get("row_id") or node.get("node_id")
        names = node.get("names")
        titles = node.get("titles")
        if names is not None or titles is not None:
            raise CoachingError(
                "equal-length name/title arrays are not a safe join; "
                "person and title must share one source span"
            )
        if person is None or title is None or span_id is None:
            raise CoachingError("person/title/span must be co-located on one node")
        extracted.append(
            {
                "person": str(person),
                "title": str(title),
                "span_id": str(span_id),
                "source_title": str(title),
                "interim": "interim" in str(title).lower(),
                "co_role": str(title).lower().startswith("co-")
                or " co-" in str(title).lower(),
            }
        )
    return extracted


def reject_array_zip_mispair(parent_nodes: Sequence[Mapping[str, Any]]) -> None:
    extract_row_bound_staff(parent_nodes)


def role_families_from_title(title: str) -> tuple[str, ...]:
    """Map a source title onto HC/OC/DC. Other titles remain observed, not cells."""

    lowered = re.sub(r"\s+", " ", str(title or "")).strip().casefold()
    if not lowered:
        return ()
    families: list[str] = []
    if re.search(r"\bhead(?:\s+football)?\s+coach\b", lowered) and not re.search(
        r"\b(associate|assistant)\b", lowered
    ):
        families.append(ROLE_HC)
    if re.search(r"\boffensive coordinator\b", lowered):
        families.append(ROLE_OC)
    if re.search(r"\bdefensive coordinator\b", lowered):
        families.append(ROLE_DC)
    return tuple(families)


def role_family_from_title(title: str) -> str | None:
    families = role_families_from_title(title)
    return families[0] if families else None


_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_SIDEARM_PAIR = re.compile(
    r'<a href="/staff/[^"]+" class="[^"]*staff-directory-table-member-position__link--name[^"]*"[^>]*>'
    r"(?P<name>.*?)</a>.*?"
    r'class="[^"]*staff-directory-table-member-position__position[^"]*"[^>]*>'
    r"(?P<title>.*?)</",
    re.I | re.S,
)
_COACH_CARD = re.compile(
    r'class="[^"]*(?:sidearm-roster-coach-name|sidearm-coach-name|'
    r's-person-card__name|c-coach-card__name)[^"]*"[^>]*>(?P<name>.*?)</'
    r".{0,400}?"
    r'class="[^"]*(?:sidearm-roster-coach-title|sidearm-coach-title|'
    r's-person-card__title|c-coach-card__title)[^"]*"[^>]*>(?P<title>.*?)</',
    re.I | re.S,
)
_SIDEARM_VUE_PAIR = re.compile(
    r"""href=['"](/sports/[^'"]*coaches/[^'"]+)['"][^>]*>\s*"""
    r"(?:<span[^>]*>)?(?P<name>[^<]{2,80})(?:</span>)?\s*</a>",
    re.I,
)
_NEAR_TITLE_SPAN = re.compile(
    r"<span[^>]*>(?P<title>[^<]{3,90})</span>",
    re.I,
)
_SIDEARM_COACH_ROW = re.compile(
    r'<tr[^>]*class="[^"]*sidearm-coaches-coach[^"]*"[^>]*>(?P<row>.*?)</tr>',
    re.I | re.S,
)
_COACH_HREF_NAME = re.compile(
    r"<a[^>]*href=['\"][^'\"]*coaches/[^'\"]+['\"][^>]*>(?P<name>.*?)</a>",
    re.I | re.S,
)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)
_NOT_FOUND_TITLE = re.compile(
    r"<title>[^<]*(?:page not found \(404\)|page not found|404 - )[^<]*</title>",
    re.I,
)
_TAG = re.compile(r"<[^>]+>")


def _plain(text: str) -> str:
    cleaned = html_lib.unescape(_TAG.sub(" ", text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def html_is_not_found_shell(html: str) -> bool:
    """HTTP 200 error shells are not staff directories."""

    return bool(_NOT_FOUND_TITLE.search(html or ""))


def historical_season_page_title(current_title: str, year: int) -> str | None:
    """Map a current program football page onto a season-page title."""

    title = (current_title or "").strip()
    if not title or title.casefold().startswith("list of"):
        return None
    lowered = title.casefold()
    if re.match(r"^\d{4}\s", title) and "football" in lowered:
        rest = re.sub(r"^\d{4}\s+", "", title).strip()
        return f"{year} {rest}"
    if lowered.endswith(" football"):
        return f"{year} {title} team"
    if "football team" in lowered:
        return f"{year} {title}"
    return f"{year} {title} football team"


def _nodes_from_sidearm_coach_table(
    html: str, *, page_url: str
) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for match in _SIDEARM_COACH_ROW.finditer(html or ""):
        row = match.group("row")
        href = _COACH_HREF_NAME.search(row)
        name = _plain(href.group("name") if href else "")
        if not name:
            heading = re.search(r"<th[^>]*>(.*?)</th>", row, re.I | re.S)
            name = _plain(heading.group(1) if heading else "")
        title = ""
        for cell in _TD.findall(row):
            text = _plain(cell)
            if not text or "[REDACTED" in text:
                continue
            if re.fullmatch(r"[\d\s.()+-]+", text):
                continue
            title = text
            break
        if name and title:
            nodes.append(
                {
                    "person": name,
                    "title": title,
                    "span_id": f"dom:{page_url}:{name}:{title}",
                }
            )
    return nodes


def parse_official_staff_html(html: str, *, page_url: str) -> list[dict[str, str]]:
    """Row-bound official staff extraction. Not PIT. No email/phone stored."""

    if html_is_not_found_shell(html or ""):
        return []
    nodes: list[dict[str, str]] = []
    for match in _JSON_LD.finditer(html or ""):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        blocks = payload if isinstance(payload, list) else [payload]
        for block in blocks:
            if not isinstance(block, Mapping):
                continue
            graph = block.get("@graph")
            entries = graph if isinstance(graph, list) else [block]
            for node in entries:
                if not isinstance(node, Mapping):
                    continue
                name = node.get("name")
                title = node.get("jobTitle") or node.get("roleName")
                if isinstance(title, list):
                    title = " / ".join(str(item) for item in title if item)
                if isinstance(name, str) and isinstance(title, str):
                    nodes.append(
                        {
                            "person": _plain(name),
                            "title": _plain(title),
                            "span_id": f"jsonld:{page_url}:{_plain(name)}:{_plain(title)}",
                        }
                    )
    if "sidearm-coaches-coach" in (html or "").casefold():
        nodes.extend(_nodes_from_sidearm_coach_table(html or "", page_url=page_url))
    if "coaches/" in (html or "") and 'href="/sports/' in (html or ""):
        for match in _SIDEARM_VUE_PAIR.finditer(html or ""):
            name = _plain(match.group("name"))
            nearby = (html or "")[match.end() : match.end() + 500]
            title_match = _NEAR_TITLE_SPAN.search(nearby)
            title = _plain(title_match.group("title") if title_match else "")
            if name and title:
                nodes.append(
                    {
                        "person": name,
                        "title": title,
                        "span_id": f"dom:{page_url}:{name}:{title}",
                    }
                )
    if "staff-directory-table-member" in (html or ""):
        for match in _SIDEARM_PAIR.finditer(html or ""):
            name = _plain(match.group("name"))
            title = _plain(match.group("title"))
            if name and title:
                nodes.append(
                    {
                        "person": name,
                        "title": title,
                        "span_id": f"dom:{page_url}:{name}:{title}",
                    }
                )
    if any(
        token in (html or "")
        for token in (
            "sidearm-roster-coach",
            "sidearm-coach-name",
            "s-person-card__name",
            "c-coach-card__name",
        )
    ):
        for match in _COACH_CARD.finditer(html or ""):
            name = _plain(match.group("name"))
            title = _plain(match.group("title"))
            if name and title:
                nodes.append(
                    {
                        "person": name,
                        "title": title,
                        "span_id": f"dom:{page_url}:{name}:{title}",
                    }
                )
    if not nodes:
        return []
    extracted = extract_row_bound_staff(nodes)
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in extracted:
        try:
            reject_personal_contact(row["person"])
            reject_personal_contact(row["title"])
        except CoachingError:
            continue
        key = (row["person"].casefold(), row["title"].casefold())
        if key in seen:
            continue
        seen.add(key)
        family = role_family_from_title(row["title"])
        if "[REDACTED" in row["person"] or "[REDACTED" in row["title"]:
            continue
        out.append({**row, "role": family or "OTHER_POSITION", "page_url": page_url})
    return out


_WEBSITE_URL_FIELD = re.compile(r"\n\|\s*WebsiteURL\s*=\s*(?P<value>[^\n]+)", re.I)
_WEBSITE_NAME_FIELD = re.compile(r"\n\|\s*WebsiteName\s*=\s*(?P<value>[^\n]+)", re.I)
_HTTP_URL = re.compile(r"https?://[^\s\]\|<>\"]+", re.I)
_BARE_HOST = re.compile(r"^(?P<host>[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?P<path>/[\w./-]*)?$")
_SKIP_WEBSITE_HOSTS = (
    "wikipedia.org",
    "wikimedia.org",
    "ncaa.org",
    "pro-football-reference",
    "sports-reference",
    "youtube.com",
    "twitter.com",
    "facebook.com",
    "instagram.com",
    "archive.org",
    "web.archive",
    "espn.com",
)


def _clean_website_candidate(raw: str) -> str | None:
    text = _plain(raw).split("|")[0].strip().strip("'\"[]")
    if not text:
        return None
    match = _HTTP_URL.search(text)
    if match:
        url = match.group(0).rstrip(".,);")
    else:
        bare = _BARE_HOST.match(text.split()[0] if text else "")
        if not bare:
            return None
        url = "https://" + bare.group("host") + (bare.group("path") or "")
    lowered = url.casefold()
    if any(token in lowered for token in _SKIP_WEBSITE_HOSTS):
        return None
    return url


def extract_athletics_website_from_wikitext(wikitext: str) -> str | None:
    """Prefer infobox WebsiteURL; WebsiteName is origin-only fallback."""

    prefixed = "\n" + (wikitext or "")
    url_match = _WEBSITE_URL_FIELD.search(prefixed)
    if url_match:
        parsed = _clean_website_candidate(url_match.group("value"))
        if parsed:
            return parsed
    name_match = _WEBSITE_NAME_FIELD.search(prefixed)
    if name_match:
        return _clean_website_candidate(name_match.group("value"))
    return None


def reject_wikimedia_as_pit(
    revision_bound: bool, admitted_as_historical_pit: bool
) -> None:
    if admitted_as_historical_pit:
        raise CoachingError("revised Wikimedia page cannot be admitted as earlier PIT")
    if not revision_bound:
        raise CoachingError(
            "Wikimedia evidence must be revision-bound and candidate-only"
        )


def role_cell(
    *,
    program_id: str,
    as_of_utc: str,
    role: str,
    episode_refs: Sequence[Mapping[str, Any]],
    disposition: str,
) -> dict[str, Any]:
    parse_aware_utc(as_of_utc)
    if str(program_id).startswith("DISPLAY:"):
        raise CoachingError("DISPLAY: identities cannot be canonical program IDs")
    if disposition not in DISPOSITIONS:
        raise CoachingError(f"unknown role-cell disposition {disposition}")
    if not episode_refs and disposition == "CONFIRMED_APPOINTMENT":
        raise CoachingError("empty episode list cannot imply a confirmed appointment")
    if len(episode_refs) > 1:
        relations = {str(item.get("relationship")) for item in episode_refs}
        if relations == {SEQUENTIAL} and disposition == "CONFIRMED_CO_SHARED_ROLE":
            raise CoachingError(
                "sequential occupants cannot be collapsed to co-coordinators"
            )
        if disposition == "CONFIRMED_APPOINTMENT":
            raise CoachingError(
                "multi-occupant role cannot collapse to an arbitrary first coach"
            )
    return {
        "program_id": program_id,
        "role": role,
        "as_of_utc": as_of_utc,
        "disposition": disposition,
        "episode_refs": list(episode_refs),
        "episode_cardinality": len(episode_refs),
    }


def hc_oc_dc_matrix(program_ids: Sequence[str], as_of_utc: str) -> list[dict[str, Any]]:
    parse_aware_utc(as_of_utc)
    if any(str(item).startswith("DISPLAY:") for item in program_ids):
        raise CoachingError("DISPLAY: identities cannot be canonical program IDs")
    n = len(program_ids)
    cells = []
    for program_id in program_ids:
        for role in PRIMARY_ROLES:
            cells.append(
                role_cell(
                    program_id=program_id,
                    as_of_utc=as_of_utc,
                    role=role,
                    episode_refs=[],
                    disposition=NOT_ATTEMPTED,
                )
            )
    if len(cells) != 3 * n:
        raise CoachingError("primary matrix must contain exactly 3N cells")
    return cells


def _cfbd_hc_episodes(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    episodes = []
    for item in items:
        person = (
            str(item.get("firstName") or "").strip()
            + " "
            + str(item.get("lastName") or "").strip()
        ).strip()
        if not person:
            continue
        reject_cfbd_assistant("CFBD", ROLE_HC)
        episodes.append(
            {
                "person": person,
                "source": "CFBD",
                "relationship": "CONFIRMED_APPOINTMENT",
                "season": 2026,
            }
        )
    return episodes


def _official_role_episodes(
    people: Sequence[Mapping[str, Any]], role: str
) -> list[dict[str, Any]]:
    episodes = []
    for person in people:
        title = str(person.get("title") or "")
        families = role_families_from_title(title)
        stored_role = person.get("role")
        if role not in families and stored_role != role:
            continue
        episodes.append(
            {
                "person": person.get("person"),
                "source": "OFFICIAL_STAFF_HTML",
                "relationship": CONCURRENT
                if person.get("co_role") or "co-" in title.casefold()
                else "CONFIRMED_APPOINTMENT",
                "season": 2026,
                "source_title": title,
                "span_id": person.get("span_id"),
                "page_url": person.get("page_url"),
            }
        )
    return episodes


def fill_current_role_matrix(
    cells: Sequence[Mapping[str, Any]],
    *,
    programs: Sequence[Mapping[str, Any]],
    cfbd_hc_by_school: Mapping[str, Sequence[Mapping[str, Any]]],
    official_people_by_program: Mapping[str, Sequence[Mapping[str, Any]]],
    official_attempts_by_program: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Official HTML first. CFBD may fill HC only. Attempted blanks are not NOT_ATTEMPTED."""

    program_by_id = {str(row["program_id"]): row for row in programs}
    filled: list[dict[str, Any]] = []
    for cell in cells:
        program = program_by_id.get(str(cell["program_id"]), {})
        display = str(program.get("display_name") or "")
        attempt = official_attempts_by_program.get(str(cell["program_id"]))
        people = official_people_by_program.get(str(cell["program_id"]), [])
        role = str(cell["role"])
        official_episodes = _official_role_episodes(people, role)
        attempt_status = str((attempt or {}).get("status") or NOT_ATTEMPTED)
        if official_episodes:
            disposition = (
                "CONFIRMED_CO_SHARED_ROLE"
                if len(official_episodes) > 1
                or any(
                    item.get("relationship") == CONCURRENT for item in official_episodes
                )
                else "CONFIRMED_APPOINTMENT"
            )
            filled.append(
                {
                    **cell,
                    "disposition": disposition,
                    "episode_refs": official_episodes,
                    "episode_cardinality": len(official_episodes),
                    "attempt_count": int((attempt or {}).get("attempt_count") or 1),
                }
            )
            continue
        if role == ROLE_HC and cfbd_hc_by_school.get(display):
            episodes = _cfbd_hc_episodes(cfbd_hc_by_school[display])
            if episodes:
                disposition = (
                    "CONFIRMED_APPOINTMENT"
                    if len(episodes) == 1
                    else "CONFIRMED_CO_SHARED_ROLE"
                )
                filled.append(
                    {
                        **cell,
                        "disposition": disposition,
                        "episode_refs": episodes,
                        "episode_cardinality": len(episodes),
                    }
                )
                continue
        if attempt_status in {NOT_ATTEMPTED, ""}:
            filled.append({**cell, "disposition": NOT_ATTEMPTED})
            continue
        if attempt_status in {"ACQUISITION_FAILED", "ATTEMPTED_NO_URL"}:
            filled.append(
                {
                    **cell,
                    "disposition": "ACQUISITION_FAILED"
                    if attempt_status == "ACQUISITION_FAILED"
                    else "UNKNOWN_NOT_LISTED",
                    "attempt_count": int((attempt or {}).get("attempt_count") or 1),
                }
            )
            continue
        filled.append(
            {
                **cell,
                "disposition": "UNKNOWN_NOT_LISTED",
                "attempt_count": int((attempt or {}).get("attempt_count") or 1),
            }
        )
    return filled


def attempt_ledger_count(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Derived attempt count from request evidence. No literal attempted:true."""

    if not attempts:
        return {
            "attempted": False,
            "attempt_count": 0,
            "disposition": NOT_ATTEMPTED,
        }
    required = ("request_identity_sha256", "receipt_identity", "route", "status")
    for row in attempts:
        missing = [field for field in required if not row.get(field)]
        if missing:
            raise CoachingError(f"attempt row missing {missing}")
    return {
        "attempted": True,
        "attempt_count": len(attempts),
        "disposition": "ATTEMPTED_WITH_EVIDENCE",
        "attempts": list(attempts),
    }


def reject_literal_attempted(payload: Mapping[str, Any], ledger_count: int) -> None:
    if payload.get("attempted") is True and ledger_count == 0:
        raise CoachingError("literal attempted:true without request evidence")


def reject_week1_as_national_coaching(
    w: int, n: int | None, claimed_complete: bool
) -> None:
    if claimed_complete:
        raise CoachingError(
            "complete Week 1 coverage cannot satisfy CURRENT_NATIONAL_HC_OC_DC_COMPLETE"
            f" even when W={w} equals N={n}"
        )


def position_role_contract(role_families: Sequence[str]) -> dict[str, Any]:
    if not role_families:
        raise CoachingError("position role families must be predeclared")
    return {
        "artifact_type": "POSITION_ROLE_OPPORTUNITY_CONTRACT",
        "role_families": list(role_families),
        "observed_titles_cannot_create_denominator": True,
    }


def historical_lattice(
    program_seasons: Sequence[Mapping[str, Any]],
    role_families: Sequence[str],
) -> list[dict[str, Any]]:
    cells = []
    for row in program_seasons:
        if str(row.get("program_id") or "").startswith("DISPLAY:"):
            raise CoachingError("DISPLAY: identities cannot be canonical program IDs")
        for role in role_families:
            cells.append(
                {
                    "program_id": row["program_id"],
                    "season": row["season"],
                    "role_family": role,
                    "applicability": row.get(
                        "applicability", "APPLICABILITY_UNRESOLVED"
                    ),
                    "evidence_disposition": NOT_ATTEMPTED
                    if not row.get("attempt_count")
                    else row.get("evidence_disposition", "ATTEMPTED_WITH_EVIDENCE"),
                }
            )
    return cells


def overlay_historical_lattice(
    cells: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach retrospective episodes without shrinking the opportunity denominator."""

    by_key: dict[tuple[str, int, str], list[Mapping[str, Any]]] = {}
    for episode in episodes:
        season = episode.get("season")
        if season is None:
            continue
        role = str(episode.get("role") or episode.get("role_family") or "")
        key = (str(episode.get("program_id")), int(season), role)
        by_key.setdefault(key, []).append(episode)
    overlaid: list[dict[str, Any]] = []
    for cell in cells:
        key = (
            str(cell["program_id"]),
            int(cell["season"]),
            str(cell["role_family"]),
        )
        found = by_key.get(key)
        if not found:
            overlaid.append(dict(cell))
            continue
        overlaid.append(
            {
                **cell,
                "evidence_disposition": "RETROSPECTIVE_CANDIDATE_ONLY",
                "episode_cardinality": len(found),
                "attempt_count": max(int(cell.get("attempt_count") or 0), 1),
                "pit_admitted": False,
            }
        )
    if len(overlaid) != len(cells):
        raise CoachingError("lattice overlay cannot change opportunity cardinality")
    return overlaid


def reject_omitted_role_family(
    contract_families: Sequence[str], lattice_families: Sequence[str]
) -> None:
    if set(contract_families) - set(lattice_families):
        raise CoachingError(
            "predeclared historical position-role family omitted from lattice"
        )


def reconcile_predecessor_observations(
    accepted_ids: Sequence[str],
    provisional: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    seen: set[str] = set()
    rows = []
    for record_id in accepted_ids:
        if record_id in seen:
            raise CoachingError("accepted identity duplicated")
        seen.add(record_id)
        rows.append(
            {
                "predecessor_record_id": record_id,
                "predecessor_category": "ACCEPTED_COACH_ROLE_EPISODE",
                "successor_disposition": "RETAINED_NONADMITTED_CONTEXT",
            }
        )
    provisional_counts = {
        "CANDIDATE_GENERATED": 0,
        "REVIEW_REQUIRED": 0,
        "UNRESOLVED": 0,
    }
    for item in provisional:
        record_id = str(item["record_id"])
        if record_id in seen:
            raise CoachingError("provisional identity collides with accepted identity")
        seen.add(record_id)
        category = str(item["category"])
        if category not in provisional_counts:
            raise CoachingError(f"unknown provisional category {category}")
        provisional_counts[category] += 1
        rows.append(
            {
                "predecessor_record_id": record_id,
                "predecessor_category": category,
                "successor_disposition": "NONADMITTED_EXPLICIT",
            }
        )
    return {
        "accepted_count": len(accepted_ids),
        "provisional_count": len(provisional),
        "provisional_category_counts": provisional_counts,
        "row_count": len(rows),
        "rows": rows,
        "model_admitted": 0,
    }


def reject_dropped_identity(
    input_ids: Sequence[str], output_ids: Sequence[str], category_counts_ok: bool
) -> None:
    if sorted(input_ids) != sorted(output_ids):
        raise CoachingError(
            "predecessor coaching identity dropped, duplicated, or collapsed"
        )
    if not category_counts_ok:
        raise CoachingError("predecessor category counts not conserved")


def extract_registry_identities(csv_path: Path) -> dict[str, Any]:
    accepted: list[str] = []
    provisional: list[dict[str, str]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            record_type = row.get("record_type")
            record_id = str(row.get("record_id") or "")
            resolution = str(row.get("resolution_state") or "")
            if record_type == "COACH_ROLE_EPISODE":
                accepted.append(record_id)
            elif record_type == "STAFF_ROLE_OBSERVATION":
                if resolution == "CANDIDATE_GENERATED":
                    category = "CANDIDATE_GENERATED"
                elif resolution == "REVIEW_REQUIRED":
                    category = "REVIEW_REQUIRED"
                else:
                    category = "UNRESOLVED"
                provisional.append({"record_id": record_id, "category": category})
    return {"accepted_ids": accepted, "provisional": provisional}


def model_admission_gate() -> dict[str, Any]:
    return {
        "artifact_type": "COACHING_MODEL_ADMISSION_GATE",
        "coaching_enters_model": False,
        "current_coverage_is_not_historical_pit": True,
        "formal_title_is_not_functional_responsibility": True,
        "candidate_is_not_admitted": True,
        "missing_role_is_not_negative_healthy": True,
        "current_historical_semantics_not_assumed_equivalent": True,
        "no_prediction_changed_because_of_coaching": True,
        "no_all22_output_changes_bas_scientific_authority": True,
        "play_caller_unknown_unless_independently_evidenced": True,
        "later_admission_requires_ablation_plan": True,
    }


def availability_unknown_not_healthy(report_present: bool) -> str:
    if report_present:
        return "REPORTED"
    return "UNKNOWN"


_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_PHONE = re.compile(
    r"(?:\+1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4})",
    re.IGNORECASE,
)
_WIKI_LINK = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]")
_INFOBOX_ROW = re.compile(
    r"^\|\s*(?P<key>[A-Za-z0-9_ ]+?)\s*=\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)
COACH_INFOBOX_KEYS = {
    "head_coach": ROLE_HC,
    "head coach": ROLE_HC,
    "headcoach": ROLE_HC,
    "current_head_coach": ROLE_HC,
    "currentheadcoach": ROLE_HC,
    "offensive_coordinator": ROLE_OC,
    "offensive coordinator": ROLE_OC,
    "offensivecoordinator": ROLE_OC,
    "off_coach": ROLE_OC,
    "offcoach": ROLE_OC,
    "defensive_coordinator": ROLE_DC,
    "defensive coordinator": ROLE_DC,
    "defensivecoordinator": ROLE_DC,
    "def_coach": ROLE_DC,
    "defcoach": ROLE_DC,
    "oc": ROLE_OC,
    "dc": ROLE_DC,
}


def redact_personal_contact(text: str) -> str:
    """Strip ingestible contact before any coach field is stored."""

    redacted = _EMAIL.sub("[REDACTED_EMAIL]", text or "")
    return _PHONE.sub("[REDACTED_PHONE]", redacted)


def reject_personal_contact(text: str) -> None:
    if _EMAIL.search(text or "") or _PHONE.search(text or ""):
        raise CoachingError("personal email/phone cannot be ingested")


def parser_family(source_system_id: str, mapping_method: str) -> str:
    source = str(source_system_id or "UNKNOWN_SOURCE")
    method = str(mapping_method or "UNKNOWN_METHOD")
    return f"{source}|{method}"


def stratified_predecessor_sample(
    csv_path: Path, *, per_family: int = 2
) -> dict[str, Any]:
    """Deterministic sample of predecessor coach/staff rows back to source fields."""

    families: dict[str, list[dict[str, str]]] = {}
    failures: list[dict[str, str]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            record_type = row.get("record_type")
            if record_type not in {"COACH_ROLE_EPISODE", "STAFF_ROLE_OBSERVATION"}:
                continue
            family = parser_family(
                str(row.get("source_system_id") or ""),
                str(row.get("mapping_method") or ""),
            )
            record_id = str(row.get("record_id") or "")
            payload_hash = str(row.get("source_payload_sha256s") or "")
            capture_ids = str(row.get("source_capture_ids") or "")
            if not record_id:
                failures.append(
                    {"family": family, "reason": "MISSING_RECORD_ID", "record_id": ""}
                )
                continue
            if not payload_hash or not capture_ids:
                failures.append(
                    {
                        "family": family,
                        "reason": "MISSING_SOURCE_LINK",
                        "record_id": record_id,
                    }
                )
            families.setdefault(family, []).append(
                {
                    "record_id": record_id,
                    "record_type": str(record_type),
                    "parser_family": family,
                    "source_system_id": str(row.get("source_system_id") or ""),
                    "mapping_method": str(row.get("mapping_method") or ""),
                    "display_name": str(row.get("display_name") or ""),
                    "role": str(row.get("role") or ""),
                    "team_label": str(row.get("team_label") or ""),
                    "season": str(row.get("season") or ""),
                    "source_capture_ids": capture_ids,
                    "source_payload_sha256s": payload_hash,
                    "resolution_state": str(row.get("resolution_state") or ""),
                    "pit_admitted": "false",
                }
            )
    sample: list[dict[str, str]] = []
    for family, rows in sorted(families.items()):
        ordered = sorted(rows, key=lambda item: sha256_json(item["record_id"]))
        sample.extend(ordered[:per_family])
    return {
        "artifact_type": "COACHING_STRATIFIED_RAW_SAMPLE",
        "artifact_class": "REAL_EVIDENCE",
        "family_count": len(families),
        "sample_count": len(sample),
        "failure_count": len(failures),
        "expanded_failed_families": sorted({row["family"] for row in failures}),
        "sample": sample,
        "failures": failures[:50],
        "counts_are_not_content_validation": True,
    }


def parse_wikimedia_infobox(
    wikitext: str, *, revision_id: str, page_title: str
) -> list[dict[str, str]]:
    """Row-bound infobox keys. Wikimedia is revision-bound candidate history, not PIT."""

    wikitext = redact_personal_contact(wikitext)
    if not revision_id:
        raise CoachingError("Wikimedia evidence must be revision-bound")
    extracted: list[dict[str, str]] = []
    for match in _INFOBOX_ROW.finditer(wikitext):
        raw_key = match.group("key").strip()
        key = raw_key.lower().replace(" ", "_")
        compact = raw_key.lower().replace(" ", "").replace("_", "")
        if compact.endswith("year") or compact in {"headcoachyear", "ocyear", "dcyear"}:
            continue
        role = (
            COACH_INFOBOX_KEYS.get(key)
            or COACH_INFOBOX_KEYS.get(raw_key.lower())
            or COACH_INFOBOX_KEYS.get(compact)
        )
        if not role:
            continue
        value = match.group("value").strip()
        if "[REDACTED_EMAIL]" in value or "[REDACTED_PHONE]" in value:
            continue
        link = _WIKI_LINK.search(value)
        person = link.group(1) if link else re.sub(r"<[^>]+>", "", value).strip()
        person = person.split("{{")[0].strip(" []'")
        if not person or person.lower() in {"", "vacant", "tbd", "none"}:
            continue
        if "@" in person or "[REDACTED" in person:
            continue
        extracted.append(
            {
                "person": person,
                "title": match.group("key").strip(),
                "role": role,
                "span_id": f"wikimedia:{page_title}:{revision_id}:{key}",
                "source_title": match.group("key").strip(),
                "wikimedia_revision": revision_id,
                "pit_admitted": "false",
                "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
            }
        )
    return extracted
