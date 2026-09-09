"""Coaching schema, lattices, row-bound extraction, and attempt ledgers.

Equal-length name/title arrays are not a safe join. No DISPLAY: program IDs.
Coaching remains out of fitted models this cycle.
"""

from __future__ import annotations

import csv
import html as html_lib
import json
import re
import urllib.parse
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


_ASSOCIATE_OR_ASSISTANT_HEAD = re.compile(
    r"\b(?:associate|assoc\.|assistant|asst\.?)(?:\s|/|$)",
    re.I,
)
_OFFENSIVE_COORDINATOR_TITLE = re.compile(
    r"\boffensive coordinator\b|\boff\.?\s*coor(?:dinator)?\.?",
    re.I,
)
_DEFENSIVE_COORDINATOR_TITLE = re.compile(
    r"\bdefensive coordinator\b|\bdef\.?\s*coor(?:dinator)?\.?",
    re.I,
)


def role_families_from_title(title: str) -> tuple[str, ...]:
    """Map a source title onto HC/OC/DC. Other titles remain observed, not cells."""

    lowered = re.sub(r"\s+", " ", str(title or "")).strip().casefold()
    if not lowered:
        return ()
    families: list[str] = []
    if (
        re.search(r"\bhead(?:\s+football)?\s+coach\b", lowered)
        and not _ASSOCIATE_OR_ASSISTANT_HEAD.search(lowered)
        and "to the head coach" not in lowered
    ):
        families.append(ROLE_HC)
    if _OFFENSIVE_COORDINATOR_TITLE.search(lowered):
        families.append(ROLE_OC)
    if _DEFENSIVE_COORDINATOR_TITLE.search(lowered):
        families.append(ROLE_DC)
    return tuple(families)


def primary_role_coverage(people: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    """HC/OC/DC families actually present in row-bound official people."""

    found: set[str] = set()
    for person in people:
        found.update(role_families_from_title(str(person.get("title") or "")))
        role = str(person.get("role") or "")
        if role in PRIMARY_ROLES:
            found.add(role)
    return frozenset(found)


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
    r"<title>[^<]*(?:page not found(?:\s*\(404\))?|404\s*[-–|: ]|"
    r"not found\s*[-–])[^<]*</title>",
    re.I,
)
_WIKI_TWO_CELL = re.compile(
    r"^\|\s*(?P<left>.+?)\s*\|\|\s*(?P<title>[^|\n]+)\s*$",
    re.MULTILINE,
)
OFFICIAL_STAFF_ORIGIN_PATHS = (
    "/sports/football/coaches",
    "/staff-directory/department/football",
    "/sports/football/roster/coaches",
    "/sports/football/roster/staff",
    "/sports/football/staff",
    "/sports/football/coaches/index",
    "/staff.aspx?path=football",
    "/staff-directory?path=football",
    "/api/v2/Staff",
    "/sports/football/coaches.aspx",
    "/staff-directory/football",
    "/athletics/football/coaches",
    "/sports/m-footbl/coaches",
    "/sports/fball/coaches",
    "/sports/fball/coaches/index",
    "/coaches.aspx?path=football",
)
ATHLETICS_HOST_FALLBACKS = {
    "gocolgateraiders.com": ("colgateathletics.com",),
    "www.gocolgateraiders.com": ("colgateathletics.com",),
    "gosoutheast.com": ("www.gosoutheast.com", "semoredhawks.com"),
    "www.gosoutheast.com": ("gosoutheast.com", "semoredhawks.com"),
    "ccsubluedevils.com": ("www.ccsubluedevils.com",),
    "www.ccsubluedevils.com": ("ccsubluedevils.com",),
}
_TAG = re.compile(r"<[^>]+>")
_PRESTO_ARIA_BIO = re.compile(
    r'aria-label="(?P<name>[^"]{2,80}?),\s*(?P<title>[^"]{3,120}?),\s*Full Bio"',
    re.I,
)
_ROSTER_STAFF_MARK = re.compile(r"roster-staff-members-card-item", re.I)
_ROSTER_STAFF_NAME = re.compile(
    r'class="[^"]*roster-card__title-link[^"]*"[^>]*>(?P<name>.*?)</a>',
    re.I | re.S,
)
_ROSTER_STAFF_TITLE = re.compile(
    r'class="[^"]*roster-card__position[^"]*"[^>]*>(?P<title>.*?)</',
    re.I | re.S,
)
_S_TABLE_BODY_ROW = re.compile(
    r'<tr[^>]*class="[^"]*s-table-body__row[^"]*"[^>]*>(?P<row>.*?)</tr>',
    re.I | re.S,
)
_S_TABLE_TITLE_THEN_NAME = re.compile(
    r"<span[^>]*>(?P<title>[^<]{3,90})</span>.{0,350}?"
    r'href="/sports/[^"]*roster/coaches/[^"]+"[^>]*>\s*'
    r"(?:<span[^>]*>)?(?P<name>[^<]{2,80})",
    re.I | re.S,
)
_STAFF_DIR_ROW = re.compile(
    r"<tr[^>]*class=\"[^\"]*staff-directory-table-member-position[^\"]*\"[^>]*>"
    r"(?P<row>.*?)</tr>",
    re.I | re.S,
)
_STAFF_DIR_NAME_CELL = re.compile(
    r'class="[^"]*staff-directory-table-member-position__name[^"]*"[^>]*>'
    r"(?P<name>.*?)</td>",
    re.I | re.S,
)
_STAFF_DIR_TITLE_CELL = re.compile(
    r'class="[^"]*staff-directory-table-member-position__position[^"]*"[^>]*>'
    r"(?P<title>.*?)</td>",
    re.I | re.S,
)
_SIDEARM_CATEGORY = re.compile(
    r'<tr[^>]*class="[^"]*sidearm-staff-category[^"]*"[^>]*data-category-id="'
    r'(?P<cat>\d+)"[^>]*>\s*<th[^>]*>(?P<title>.*?)</th>',
    re.I | re.S,
)
_SIDEARM_MEMBER = re.compile(
    r'<tr[^>]*class="[^"]*sidearm-staff-member[^"]*"[^>]*data-category-id="'
    r'(?P<cat>\d+)"[^>]*>(?P<row>.*?)</tr>',
    re.I | re.S,
)
_SIDEARM_ARIA_NAME = re.compile(r"aria-label='([^']+)'", re.I)
_SIDEARM_TITLE_CELL = re.compile(
    r'<td[^>]*headers="[^"]*col-staff_title[^"]*"[^>]*>(?P<title>.*?)</td>',
    re.I | re.S,
)
_EMBEDDED_STAFF_OBJECT = re.compile(
    r'\{[^{}]{0,120}"firstName"\s*:\s*"(?P<first>[^"]+)"[^{}]{0,120}'
    r'"lastName"\s*:\s*"(?P<last>[^"]+)"[^{}]{0,240}'
    r'"(?:title|jobTitle)"\s*:\s*"(?P<title>[^"]{3,90})"',
    re.I | re.S,
)
_GENERIC_TR = re.compile(r"<tr\b[^>]*>(?P<row>.*?)</tr>", re.I | re.S)
_GENERIC_TD = re.compile(r"<td\b[^>]*>(?P<cell>.*?)</td>", re.I | re.S)
_PERSON_NAME_HINT = re.compile(
    r"^[A-Za-z][A-Za-z.'\-]+(?:\s+[A-Za-z][A-Za-z.'\-]+){1,3}$"
)


def _nodes_from_sidearm_staff_member_table(
    html: str, *, page_url: str, sport: str = "football"
) -> list[dict[str, str]]:
    sport_key = sport.casefold()
    football_cats: set[str] = set()
    for match in _SIDEARM_CATEGORY.finditer(html or ""):
        heading = _plain(match.group("title")).casefold()
        if heading == sport_key or heading.startswith(f"{sport_key} "):
            football_cats.add(match.group("cat"))
    nodes: list[dict[str, str]] = []
    for match in _SIDEARM_MEMBER.finditer(html or ""):
        if football_cats and match.group("cat") not in football_cats:
            continue
        row = match.group("row")
        aria = _SIDEARM_ARIA_NAME.search(row)
        name = ""
        if aria:
            name = _plain(aria.group(1).split(",")[0])
        if not name:
            href = _COACH_HREF_NAME.search(row)
            name = _plain(href.group("name") if href else "")
        title_match = _SIDEARM_TITLE_CELL.search(row)
        title = _plain(title_match.group("title") if title_match else "")
        if name and title:
            nodes.append(
                {
                    "person": name,
                    "title": title,
                    "span_id": f"dom:{page_url}:{name}:{title}",
                }
            )
    return nodes


def parse_official_staff_json(payload: Any, *, page_url: str) -> list[dict[str, str]]:
    """Row-bound Sidearm/WMT JSON staff. Email/phone are redacted, not stored."""

    items: list[Any] = []
    if isinstance(payload, Mapping):
        items = list(payload.get("items") or payload.get("staff") or [])
    elif isinstance(payload, list):
        items = payload
    nodes: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        category = item.get("category")
        cat_title = ""
        if isinstance(category, Mapping):
            cat_title = str(category.get("title") or "")
        first = str(item.get("firstName") or item.get("first_name") or "").strip()
        last = str(item.get("lastName") or item.get("last_name") or "").strip()
        name = _plain(f"{first} {last}".strip() or str(item.get("name") or ""))
        title = _plain(str(item.get("title") or item.get("jobTitle") or ""))
        if not name or not title:
            continue
        if cat_title and "football" not in cat_title.casefold():
            if (
                "coach" not in title.casefold()
                and "coordinator" not in title.casefold()
            ):
                continue
        try:
            reject_personal_contact(name)
            reject_personal_contact(title)
        except CoachingError:
            continue
        nodes.append(
            {
                "person": name,
                "title": title,
                "span_id": f"json:{page_url}:{name}:{title}",
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


def extract_official_website_from_wikidata_entity(
    entity: Mapping[str, Any],
) -> str | None:
    """P856 official website. Not inferred from social or Wikipedia sitelinks."""

    claims = entity.get("claims") if isinstance(entity, Mapping) else None
    if not isinstance(claims, Mapping):
        return None
    for statement in claims.get("P856") or []:
        if not isinstance(statement, Mapping):
            continue
        mainsnak = statement.get("mainsnak") or {}
        datavalue = (mainsnak.get("datavalue") or {}).get("value")
        parsed = _clean_website_candidate(str(datavalue or ""))
        if parsed:
            return parsed
    return None


def _wikidata_label_is_college_program(label: str) -> bool:
    lowered = (label or "").casefold()
    if not lowered:
        return False
    if any(
        token in lowered
        for token in (
            "footballer",
            "soccer",
            "association football",
            "national football team",
            "football club",
        )
    ):
        return False
    return any(token in lowered for token in ("football", "university", "college"))


def select_college_football_wiki_title(
    hits: Sequence[Mapping[str, Any]], school: str
) -> str | None:
    """Reject footballer/soccer/rivalry hits. Prefer program football pages."""

    school_key = str(school or "").casefold().strip()
    ranked: list[tuple[int, str]] = []
    for hit in hits:
        title = str(hit.get("title") or "").strip()
        lowered = title.casefold()
        if not title or not lowered:
            continue
        if any(
            token in lowered
            for token in (
                "footballer",
                "soccer",
                "football club",
                "f.c.",
                " rivalry",
                "list of",
                "plane crash",
            )
        ):
            continue
        if not season_title_matches_school(title, school):
            continue
        if re.search(r"\([^)]*american football\)\s*$", lowered) and not (
            lowered.endswith(" football") or "football team" in lowered
        ):
            continue
        if "football" not in lowered:
            continue
        score = 0
        if lowered.endswith(" football") or "football team" in lowered:
            score += 3
        if school_key and school_key in lowered:
            score += 4
        elif school_key and school_key.split()[0] in lowered:
            score += 1
        if re.match(r"^\d{4}\s", title):
            score -= 8
        ranked.append((score, title))
    current = [
        (score, title) for score, title in ranked if not re.match(r"^\d{4}\s", title)
    ]
    if current:
        ranked = current
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def match_wikidata_website(
    display_name: str, bindings: Sequence[Mapping[str, Any]]
) -> str | None:
    needle = str(display_name or "").casefold().strip()
    if not needle:
        return None
    aliases = {
        "nc state": ("north carolina state", "nc state wolfpack"),
        "hawai'i": ("hawaii", "university of hawaii"),
        "ualbany": ("albany", "albany great danes"),
        "long island university": ("liu", "liu sharks"),
        "st. thomas (mn)": ("st. thomas", "st thomas tommies"),
        "utah tech": ("utah tech", "dixie state"),
        "illinois state": ("illinois state redbirds",),
        "tennessee tech": ("tennessee tech golden eagles",),
    }
    needles = (needle, *aliases.get(needle, ()))
    preferred: str | None = None
    fallback: str | None = None
    for row in bindings:
        label = str(
            ((row.get("itemLabel") or {}).get("value"))
            if isinstance(row.get("itemLabel"), Mapping)
            else row.get("itemLabel") or row.get("label") or ""
        ).casefold()
        website = row.get("website")
        if isinstance(website, Mapping):
            website = website.get("value")
        if any(
            token in label
            for token in (
                "footballer",
                "soccer",
                "football club",
                "national football team",
            )
        ):
            continue
        if not any(token in label for token in needles) or not website:
            continue
        parsed = _clean_website_candidate(str(website))
        if not parsed:
            continue
        if _wikidata_label_is_college_program(label):
            preferred = parsed
            break
        if fallback is None:
            fallback = parsed
    return preferred or fallback


_INFOBOX_URL_FIELDS = (
    re.compile(r"\n\|\s*WebsiteURL\s*=\s*(?P<value>[^\n]+)", re.I),
    re.compile(r"\n\|\s*athletics(?:\s+website)?\s*=\s*(?P<value>[^\n]+)", re.I),
    re.compile(r"\n\|\s*WebsiteName\s*=\s*(?P<value>[^\n]+)", re.I),
    re.compile(r"\n\|\s*website\s*=\s*(?P<value>[^\n]+)", re.I),
    re.compile(r"\n\|\s*url\s*=\s*(?P<value>[^\n]+)", re.I),
)


def _plain(text: str) -> str:
    cleaned = html_lib.unescape(_TAG.sub(" ", text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def html_is_not_found_shell(html: str) -> bool:
    """HTTP 200 error shells are not staff directories.

    Title-only. Body-wide 404 template strings appear on valid Sidearm pages.
    """

    return bool(_NOT_FOUND_TITLE.search(html or ""))


def html_is_waf_challenge(html: str) -> bool:
    """AWS WAF interstitial pages are not staff directories."""

    text = html or ""
    return "gokuProps" in text or "awsWafCookieDomainList" in text


def official_staff_candidate_urls(website: str) -> list[str]:
    """Origin-relative staff paths plus documented athletics-host fallbacks."""

    parsed = urllib.parse.urlparse(website)
    if not parsed.scheme or not parsed.netloc:
        return []
    hosts: list[str] = []
    folded = parsed.netloc.casefold()
    for extra in ATHLETICS_HOST_FALLBACKS.get(folded, ()):
        if extra not in hosts:
            hosts.append(extra)
    bare = folded.removeprefix("www.")
    for extra in ATHLETICS_HOST_FALLBACKS.get(bare, ()):
        if extra not in hosts:
            hosts.append(extra)
    if parsed.netloc not in hosts:
        hosts.append(parsed.netloc)
    schemes = [parsed.scheme]
    if parsed.scheme.casefold() != "https":
        schemes.insert(0, "https")
    urls: list[str] = []
    path = parsed.path.casefold()
    for scheme in schemes:
        for host in hosts:
            origin = f"{scheme}://{host}"
            if "/fball" in path:
                urls.append(origin + "/sports/fball/coaches")
                urls.append(origin + "/sports/fball/coaches/index")
            if "/football" in path or "/fball" in path:
                base = urllib.parse.urlunparse(
                    (scheme, host, parsed.path, "", "", "")
                ).rstrip("/")
                if not base.casefold().endswith("/index"):
                    urls.append(base + "/coaches")
            for suffix in OFFICIAL_STAFF_ORIGIN_PATHS:
                urls.append(origin + suffix)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        key = url.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(url)
    return deduped


def _nodes_from_roster_staff_cards(html: str, *, page_url: str) -> list[dict[str, str]]:
    """Sidearm 2 roster-staff-members cards. Player roster cards are excluded."""

    nodes: list[dict[str, str]] = []
    marks = list(_ROSTER_STAFF_MARK.finditer(html or ""))
    for index, mark in enumerate(marks):
        end = (
            marks[index + 1].start() if index + 1 < len(marks) else mark.start() + 3000
        )
        window = (html or "")[mark.start() : end]
        name_match = _ROSTER_STAFF_NAME.search(window)
        title_match = _ROSTER_STAFF_TITLE.search(window)
        name = _plain(name_match.group("name") if name_match else "")
        title = _plain(title_match.group("title") if title_match else "")
        if name and title:
            nodes.append(
                {
                    "person": name,
                    "title": title,
                    "span_id": f"dom:{page_url}:{name}:{title}",
                }
            )
    return nodes


def _nodes_from_s_table_coaches(html: str, *, page_url: str) -> list[dict[str, str]]:
    """Title cell then roster/coaches name link in the same bounded window."""

    nodes: list[dict[str, str]] = []
    for match in _S_TABLE_TITLE_THEN_NAME.finditer(html or ""):
        name = _plain(match.group("name"))
        title = _plain(match.group("title"))
        if not name or not title:
            continue
        lowered = title.casefold()
        if not any(
            token in lowered
            for token in ("coach", "coordinator", "analyst", "assistant")
        ):
            continue
        nodes.append(
            {
                "person": name,
                "title": title,
                "span_id": f"dom:{page_url}:{name}:{title}",
            }
        )
    for match in _S_TABLE_BODY_ROW.finditer(html or ""):
        row = match.group("row")
        href = _COACH_HREF_NAME.search(row)
        name = _plain(href.group("name") if href else "")
        if not name:
            continue
        title = ""
        for span in re.findall(r"<span[^>]*>([^<]{2,90})</span>", row, re.I):
            cand = _plain(span)
            lowered = cand.casefold()
            if any(
                token in lowered
                for token in ("coach", "coordinator", "analyst", "assistant")
            ):
                title = cand
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


def _nodes_from_staff_directory_rows(
    html: str, *, page_url: str
) -> list[dict[str, str]]:
    """Next-gen staff-directory table rows. Name and title share one <tr>."""

    nodes: list[dict[str, str]] = []
    for match in _STAFF_DIR_ROW.finditer(html or ""):
        row = match.group("row")
        name_match = _STAFF_DIR_NAME_CELL.search(row)
        title_match = _STAFF_DIR_TITLE_CELL.search(row)
        name = _plain(name_match.group("name") if name_match else "")
        title = _plain(title_match.group("title") if title_match else "")
        if not name or not title:
            continue
        lowered = title.casefold()
        if not any(
            token in lowered
            for token in ("coach", "coordinator", "analyst", "assistant")
        ):
            continue
        nodes.append(
            {
                "person": name,
                "title": title,
                "span_id": f"dom:{page_url}:{name}:{title}",
            }
        )
    return nodes


PROGRAM_SEASON_TITLE_ALIASES = {
    "East Texas A&M": (
        "east texas a&m",
        "texas a&m-commerce",
        "texas a&m–commerce",
    ),
    "Utah Tech": ("utah tech", "dixie state"),
    "Mercyhurst": ("mercyhurst",),
    "New Haven": ("new haven",),
    "St. Thomas (MN)": ("st. thomas", "st thomas tommies"),
    "Chicago State": ("chicago state",),
    "UT Rio Grande Valley": ("rio grande", "utrgv"),
    "Southern Illinois": ("southern illinois",),
    "App State": ("appalachian state", "app state"),
    "BYU": ("brigham young", "byu"),
    "LSU": ("louisiana state", "lsu"),
    "Massachusetts": ("massachusetts", "umass"),
    "Miami (OH)": ("miami (oh)", "miami redhawks", "miami ohio"),
    "Pennsylvania": ("pennsylvania", "penn quakers"),
    "San José State": ("san jose state", "san josé state"),
    "TCU": ("texas christian", "tcu"),
    "USC": ("southern california", "usc trojans"),
    "VMI": ("virginia military", "vmi"),
    "SMU": ("southern methodist", "smu"),
    "Hawai'i": ("hawaii", "hawai'i"),
    "SE Louisiana": ("southeastern louisiana", "se louisiana"),
    "UCF": ("ucf", "central florida"),
    "UConn": ("uconn", "connecticut"),
    "UAB": ("uab", "alabama-birmingham", "alabama birmingham"),
    "FIU": ("fiu", "florida international"),
    "Florida International": ("florida international", "fiu"),
    "Arkansas State": ("arkansas state",),
    "Bethune-Cookman": ("bethune-cookman", "bethune cookman"),
    "West Florida": ("west florida",),
    "Long Island University": ("liu sharks", "liu"),
    "UAlbany": ("ualbany", "albany great danes"),
    "UL Monroe": ("ul monroe", "louisiana-monroe", "louisiana monroe"),
    "Cal Poly": ("cal poly", "cal poly mustangs"),
    "Lafayette": ("lafayette leopards", "lafayette college"),
    "Arizona State": ("arizona state", "sun devils"),
    "Texas State": ("texas state",),
    "Georgia State": ("georgia state",),
    "Colorado State": ("colorado state",),
    "Campbell": ("campbell fighting camels", "campbell camels"),
}


def season_title_matches_school(title: str, school: str) -> bool:
    """Reject a season page that names a different program."""

    title_l = (
        str(title or "")
        .casefold()
        .replace("é", "e")
        .replace("’", "'")
        .replace("`", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    school_l = (
        str(school or "")
        .casefold()
        .strip()
        .replace("é", "e")
        .replace("–", "-")
        .replace("—", "-")
    )
    if not title_l or not school_l:
        return False
    if "plane crash" in title_l:
        return False
    needles = [school_l, *PROGRAM_SEASON_TITLE_ALIASES.get(str(school or ""), ())]
    for token in needles:
        token_l = (
            str(token)
            .casefold()
            .strip()
            .replace("é", "e")
            .replace("–", "-")
            .replace("—", "-")
        )
        if not token_l:
            continue
        if len(token_l) <= 3:
            if re.search(rf"\b{re.escape(token_l)}\b", title_l):
                return True
            continue
        if token_l in title_l:
            return True
    return False


def historical_season_page_title(
    current_title: str, year: int, school: str = ""
) -> str | None:
    """Map a current program football page onto a season-page title."""

    title = (current_title or "").strip()
    school_name = str(school or "").strip()
    if not title or title.casefold().startswith("list of"):
        if school_name:
            return f"{year} {school_name} football team"
        return None
    lowered = title.casefold()
    if re.search(r"\([^)]*american football\)\s*$", lowered) and not (
        lowered.endswith(" football") or "football team" in lowered
    ):
        if school_name:
            return f"{year} {school_name} football team"
        return None
    if re.match(r"^\d{4}\s", title) and "football" in lowered:
        if school_name and school_name.casefold() not in lowered:
            return f"{year} {school_name} football team"
        rest = re.sub(r"^\d{4}\s+", "", title).strip()
        return f"{year} {rest}"
    if lowered.endswith(" football"):
        return f"{year} {title} team"
    if "football team" in lowered:
        return f"{year} {title}"
    return f"{year} {title} football team"


def program_coach_category_title(current_title: str) -> str | None:
    """Map a program football page onto its Wikipedia coaches category."""

    title = (current_title or "").strip()
    if not title or title.casefold().startswith("list of"):
        return None
    lowered = title.casefold()
    if lowered.endswith(" football"):
        return f"Category:{title} coaches"
    if lowered.endswith(" football team"):
        base = re.sub(r"\s+football team$", "", title, flags=re.I)
        return f"Category:{base} football coaches"
    return f"Category:{title} football coaches"


def _nodes_from_generic_name_title_rows(
    html: str, *, page_url: str
) -> list[dict[str, str]]:
    """Adjacent td name/title rows used by some WordPress staff directories."""

    nodes: list[dict[str, str]] = []
    for match in _GENERIC_TR.finditer(html or ""):
        cells = [_plain(cell) for cell in _GENERIC_TD.findall(match.group("row"))]
        cells = [cell for cell in cells if cell and "[REDACTED" not in cell]
        if len(cells) < 2:
            continue
        name = ""
        title = ""
        if _PERSON_NAME_HINT.match(cells[0]) and role_family_from_title(cells[1]):
            name, title = cells[0], cells[1]
        elif _PERSON_NAME_HINT.match(cells[1]) and role_family_from_title(cells[0]):
            name, title = cells[1], cells[0]
        if name and title:
            nodes.append(
                {
                    "person": name,
                    "title": title,
                    "span_id": f"dom:{page_url}:{name}:{title}",
                }
            )
    return nodes


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
            if (
                name
                and title
                and any(
                    token in title.casefold()
                    for token in ("coach", "coordinator", "analyst", "assistant")
                )
            ):
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
    if "roster-staff-members-card-item" in (html or "").casefold():
        nodes.extend(_nodes_from_roster_staff_cards(html or "", page_url=page_url))
    if "roster/coaches/" in (html or "") and (
        "s-table-body_cell" in (html or "")
        or "s-table-body__row" in (html or "").casefold()
    ):
        nodes.extend(_nodes_from_s_table_coaches(html or "", page_url=page_url))
    if "staff-directory-table-member-position" in (html or "").casefold():
        nodes.extend(_nodes_from_staff_directory_rows(html or "", page_url=page_url))
    if "sidearm-staff-member" in (html or "").casefold():
        nodes.extend(
            _nodes_from_sidearm_staff_member_table(
                html or "", page_url=page_url, sport="football"
            )
        )
    if '"firstName"' in (html or "") and '"lastName"' in (html or ""):
        for match in _EMBEDDED_STAFF_OBJECT.finditer(html or ""):
            name = _plain(f"{match.group('first')} {match.group('last')}")
            title = _plain(match.group("title"))
            if name and title:
                nodes.append(
                    {
                        "person": name,
                        "title": title,
                        "span_id": f"jsonobj:{page_url}:{name}:{title}",
                    }
                )
    if "full bio" in (html or "").casefold():
        for match in _PRESTO_ARIA_BIO.finditer(html or ""):
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
    if not nodes and (
        "coordinator" in (html or "").casefold()
        or "head coach" in (html or "").casefold()
    ):
        nodes.extend(_nodes_from_generic_name_title_rows(html or "", page_url=page_url))
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


_HTTP_URL = re.compile(r"https?://[^\s\]\|<>\"}]+", re.I)
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
    "richmondfc.com",
    "sandiegofc.com",
    "thefa.com",
)


def _clean_website_candidate(raw: str) -> str | None:
    text = _plain(raw)
    match = _HTTP_URL.search(text)
    if match:
        url = match.group(0).rstrip(".,);}{")
    else:
        stripped = re.sub(r"\{\{\s*url\s*\|\s*", "", text, flags=re.I)
        stripped = stripped.replace("}}", " ")
        token = stripped.split("|")[0].strip().strip("'\"[]")
        if not token:
            return None
        bare = _BARE_HOST.match(token.split()[0] if token else "")
        if not bare:
            return None
        url = "https://" + bare.group("host") + (bare.group("path") or "")
    lowered = url.casefold()
    if any(token in lowered for token in _SKIP_WEBSITE_HOSTS):
        return None
    return url


def _host_looks_like_athletics(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.casefold()
    if not host:
        return False
    if any(token in host for token in _SKIP_WEBSITE_HOSTS):
        return False
    return any(
        token in host
        for token in (
            "athletics",
            "sports",
            "flames",
            "gopack",
            "goredbirds",
            "gocolgate",
            "bluedevils",
        )
    )


def extract_athletics_website_from_wikitext(wikitext: str) -> str | None:
    """Prefer infobox WebsiteURL; athletics/website fields are origin-only fallback."""

    prefixed = "\n" + (wikitext or "")
    infobox: str | None = None
    for field in _INFOBOX_URL_FIELDS:
        match = field.search(prefixed)
        if not match:
            continue
        parsed = _clean_website_candidate(match.group("value"))
        if parsed:
            infobox = parsed
            if _host_looks_like_athletics(parsed) or not urllib.parse.urlparse(
                parsed
            ).netloc.casefold().endswith(".edu"):
                return parsed
            break
    for match in _HTTP_URL.finditer(wikitext or ""):
        parsed = _clean_website_candidate(match.group(0))
        if parsed and _host_looks_like_athletics(parsed):
            return parsed
    return infobox


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


SPORTSRADAR_MARKET_ALIASES = {
    "nc state": ("north carolina state",),
    "hawai'i": ("hawaii",),
    "ualbany": ("university at albany",),
    "st. thomas (mn)": ("st. thomas", "st. thomas (mn)"),
    "long island university": ("long island", "liu"),
    "connecticut": ("uconn", "connecticut"),
    "massachusetts": ("umass", "massachusetts"),
    "sam houston": ("sam houston state",),
    "southern miss": ("southern mississippi",),
    "app state": ("appalachian state",),
    "central connecticut": ("central connecticut state",),
    "grambling": ("grambling state",),
    "miami": ("miami (fl)",),
    "nicholls": ("nicholls state",),
    "pennsylvania": ("penn",),
    "san josé state": ("san jose state",),
    "san jose state": ("san jose state",),
    "se louisiana": ("southeastern louisiana",),
    "southern": ("southern university",),
    "ul monroe": ("louisiana-monroe",),
    "ut martin": ("tennessee-martin",),
}


def _fold_market(value: str) -> str:
    return (
        str(value or "")
        .casefold()
        .strip()
        .replace("é", "e")
        .replace("á", "a")
        .replace("ó", "o")
        .replace("í", "i")
        .replace("ú", "u")
        .replace("’", "'")
    )


def match_program_to_sportradar_team(
    display_name: str, teams: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    """Exact market/alias match. Do not map Alabama onto Alabama A&M."""

    needle = _fold_market(display_name)
    if not needle:
        return None
    needles = {
        needle,
        *(_fold_market(item) for item in SPORTSRADAR_MARKET_ALIASES.get(needle, ())),
    }
    exact: Mapping[str, Any] | None = None
    for team in teams:
        market = _fold_market(str(team.get("market") or ""))
        alias = _fold_market(str(team.get("alias") or ""))
        name = _fold_market(str(team.get("name") or ""))
        if market in needles or alias in needles:
            if exact is not None and str(exact.get("id")) != str(team.get("id")):
                return None
            exact = team
            continue
        combined = f"{market} {name}".strip()
        if needle == combined:
            if exact is not None and str(exact.get("id")) != str(team.get("id")):
                return None
            exact = team
    return exact


def parse_sportradar_coaches(
    payload: Mapping[str, Any], *, team_id: str, page_url: str
) -> list[dict[str, str]]:
    """Bind person and source position from the same SportsRadar coach object."""

    coaches = payload.get("coaches")
    if not isinstance(coaches, list):
        team = payload.get("team")
        coaches = team.get("coaches") if isinstance(team, Mapping) else []
    if not isinstance(coaches, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for coach in coaches:
        if not isinstance(coach, Mapping):
            continue
        title = str(coach.get("position") or "").strip()
        name = str(coach.get("full_name") or "").strip()
        if not name:
            name = " ".join(
                part
                for part in (
                    str(coach.get("first_name") or "").strip(),
                    str(coach.get("last_name") or "").strip(),
                    str(coach.get("name_suffix") or "").strip(),
                )
                if part
            ).strip()
        if not name or not title:
            continue
        key = (name.casefold(), title.casefold())
        if key in seen:
            continue
        seen.add(key)
        family = role_family_from_title(title) or "OTHER_POSITION"
        out.append(
            {
                "person": name,
                "title": title,
                "role": family,
                "source": "SPORTSRADAR_NCAAFB",
                "source_coach_id": str(coach.get("id") or ""),
                "span_id": f"sr:{team_id}:{coach.get('id')}:{title}",
                "page_url": page_url,
            }
        )
    return out


def _sportradar_role_episodes(
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
                "source": "SPORTSRADAR_NCAAFB",
                "relationship": CONCURRENT
                if "co-" in title.casefold()
                else "CONFIRMED_APPOINTMENT",
                "season": 2026,
                "source_title": title,
                "span_id": person.get("span_id"),
                "page_url": person.get("page_url"),
                "source_coach_id": person.get("source_coach_id"),
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


def _wikimedia_role_episodes(
    people: Sequence[Mapping[str, Any]], role: str
) -> list[dict[str, Any]]:
    episodes = []
    for person in people:
        title = str(person.get("title") or person.get("source_title") or "")
        families = role_families_from_title(title)
        stored_role = person.get("role")
        if role not in families and stored_role != role:
            continue
        episodes.append(
            {
                "person": person.get("person"),
                "source": "WIKIMEDIA",
                "relationship": "CANDIDATE_ONLY",
                "season": 2026,
                "source_title": title,
                "span_id": person.get("span_id"),
                "wikimedia_revision": person.get("wikimedia_revision"),
                "pit_admitted": False,
                "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
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
    sportradar_people_by_program: Mapping[str, Sequence[Mapping[str, Any]]]
    | None = None,
    sportradar_attempts_by_program: Mapping[str, Mapping[str, Any]] | None = None,
    wikimedia_people_by_program: Mapping[str, Sequence[Mapping[str, Any]]]
    | None = None,
) -> list[dict[str, Any]]:
    """Official HTML first, then SportsRadar, CFBD HC, Wikimedia candidates."""

    program_by_id = {str(row["program_id"]): row for row in programs}
    sr_people = sportradar_people_by_program or {}
    sr_attempts = sportradar_attempts_by_program or {}
    wiki_people = wikimedia_people_by_program or {}
    filled: list[dict[str, Any]] = []
    for cell in cells:
        program = program_by_id.get(str(cell["program_id"]), {})
        display = str(program.get("display_name") or "")
        attempt = official_attempts_by_program.get(str(cell["program_id"]))
        people = official_people_by_program.get(str(cell["program_id"]), [])
        role = str(cell["role"])
        official_episodes = _official_role_episodes(people, role)
        sr_episodes = _sportradar_role_episodes(
            sr_people.get(str(cell["program_id"]), []), role
        )
        sr_attempt = sr_attempts.get(str(cell["program_id"]))
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
        if sr_episodes:
            disposition = (
                "CONFIRMED_CO_SHARED_ROLE"
                if len(sr_episodes) > 1
                or any(item.get("relationship") == CONCURRENT for item in sr_episodes)
                else "CONFIRMED_APPOINTMENT"
            )
            filled.append(
                {
                    **cell,
                    "disposition": disposition,
                    "episode_refs": sr_episodes,
                    "episode_cardinality": len(sr_episodes),
                    "attempt_count": int((sr_attempt or {}).get("attempt_count") or 1),
                    "source": "SPORTSRADAR_NCAAFB",
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
        wiki_episodes = _wikimedia_role_episodes(
            wiki_people.get(str(cell["program_id"]), []), role
        )
        if wiki_episodes:
            filled.append(
                {
                    **cell,
                    "disposition": "CANDIDATE_ONLY",
                    "episode_refs": wiki_episodes,
                    "episode_cardinality": len(wiki_episodes),
                    "attempt_count": int((attempt or {}).get("attempt_count") or 1),
                    "source": "WIKIMEDIA",
                    "pit_admitted": False,
                }
            )
            continue
        if attempt_status in {NOT_ATTEMPTED, ""} and not sr_attempt:
            filled.append({**cell, "disposition": NOT_ATTEMPTED})
            continue
        if (
            attempt_status in {"ACQUISITION_FAILED", "ATTEMPTED_NO_URL"}
            and not sr_attempt
        ):
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
                "attempt_count": int(
                    (sr_attempt or attempt or {}).get("attempt_count") or 1
                ),
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
_WIKI_LINK = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")
_INFOBOX_ROW = re.compile(
    r"^\|\s*(?P<key>[A-Za-z0-9_ ]+?)\s*=\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)
_MULTILINE_COACH_FIELD = re.compile(
    r"^\|\s*(?P<key>head_coach|asst_coach|off_coach|def_coach|cooff_coach\d*"
    r"|codef_coach\d*|head_coach2|head_coach3)\s*=\s*\n"
    r"(?P<body>(?:[^\S\n]*\*.+\n)+)",
    re.IGNORECASE | re.MULTILINE,
)
_STAFF_BULLET = re.compile(r"^\*\s*(?P<body>\S.*)$", re.MULTILINE)
COACH_INFOBOX_KEYS = {
    "head_coach": ROLE_HC,
    "head coach": ROLE_HC,
    "headcoach": ROLE_HC,
    "head_coach2": ROLE_HC,
    "headcoach2": ROLE_HC,
    "head_coach3": ROLE_HC,
    "headcoach3": ROLE_HC,
    "current_head_coach": ROLE_HC,
    "currentheadcoach": ROLE_HC,
    "offensive_coordinator": ROLE_OC,
    "offensive coordinator": ROLE_OC,
    "offensivecoordinator": ROLE_OC,
    "off_coach": ROLE_OC,
    "offcoach": ROLE_OC,
    "cooff_coach": ROLE_OC,
    "cooffcoach": ROLE_OC,
    "cooff_coach1": ROLE_OC,
    "cooffcoach1": ROLE_OC,
    "cooff_coach2": ROLE_OC,
    "cooffcoach2": ROLE_OC,
    "defensive_coordinator": ROLE_DC,
    "defensive coordinator": ROLE_DC,
    "defensivecoordinator": ROLE_DC,
    "def_coach": ROLE_DC,
    "defcoach": ROLE_DC,
    "codef_coach": ROLE_DC,
    "codefcoach": ROLE_DC,
    "codef_coach1": ROLE_DC,
    "codefcoach1": ROLE_DC,
    "codef_coach2": ROLE_DC,
    "oc": ROLE_OC,
    "dc": ROLE_DC,
}
_SKIP_INFOBOX_KEYS = {
    "off_scheme",
    "def_scheme",
    "offscheme",
    "defscheme",
    "stadium",
    "capacity",
    "founded",
}


_SORTNAME = re.compile(r"\{\{\s*sortname\s*\|([^|}]+)\|([^|}]+)", re.I)
_COACH_LIKE_TITLE = re.compile(
    r"\b(?:coach|coordinator|analyst|graduate assistant|quality control|"
    r"recruiting|play[\s-]?caller)\b",
    re.I,
)
_NOT_STAFF_TITLE = re.compile(
    r"^(?:\d|conference|record|association|division|season|position|name|"
    r"previous|alma)\b",
    re.I,
)
OBSERVED_STAFF_ROLE_PATTERNS = (
    (r"\bspecial teams coordinator\b", "special_teams_coordinator"),
    (r"\bquarterbacks?\b|(?:^|[/,(])\s*qb(?:\b|/)", "quarterbacks"),
    (r"\brunning backs?\b|(?:^|[/,(])\s*rb(?:\b|/)", "running_backs"),
    (r"\bwide receivers?\b|(?:^|[/,(])\s*wr(?:\b|/)", "wide_receivers"),
    (r"\btight ends?\b|(?:^|[/,(])\s*te(?:\b|/)", "tight_ends"),
    (r"\boffensive linem(?:an|en)\b|\boffensive line\b", "offensive_line"),
    (r"\bdefensive linem(?:an|en)\b|\bdefensive line\b", "defensive_line"),
    (r"\blinebackers?\b", "linebackers"),
    (r"\bdefensive backs?\b", "defensive_backs"),
    (r"\bsafeties\b|\bsafety\b", "safeties"),
    (r"\bcornerbacks?\b", "cornerbacks"),
    (r"\bnickels?\b", "nickels"),
    (r"\b(?:kickers?|punters?)\b", "kickers_punters"),
    (r"\bstrength\b|\bconditioning\b", "strength_conditioning"),
    (r"\banalyst\b|\bquality control\b|\bgraduate assistant\b", "analyst_support"),
)
_COACH_YEARS_FIELD = re.compile(
    r"^\|\s*coach_years(?P<n>\d+)\s*=\s*(?P<years>.+)$",
    re.MULTILINE,
)
_COACH_TEAM_FIELD = re.compile(
    r"^\|\s*coach_team(?P<n>\d+)\s*=\s*(?P<team>.+)$",
    re.MULTILINE,
)
_YEAR_RANGE = re.compile(
    r"(?P<start>18\d{2}|19\d{2}|20\d{2})\s*[–\-]\s*(?P<end>18\d{2}|19\d{2}|20\d{2}|present)",
    re.I,
)
_SINGLE_YEAR = re.compile(r"^(?P<year>18\d{2}|19\d{2}|20\d{2})$")


def redact_personal_contact(text: str) -> str:
    """Strip ingestible contact before any coach field is stored."""

    redacted = _EMAIL.sub("[REDACTED_EMAIL]", text or "")
    return _PHONE.sub("[REDACTED_PHONE]", redacted)


def wiki_display_name(value: str) -> str:
    """Prefer piped display text, then page title, then plain wikitext."""

    sort = _SORTNAME.search(value or "")
    if sort:
        return f"{sort.group(1).strip()} {sort.group(2).strip()}"
    link = _WIKI_LINK.search(value or "")
    if link:
        return (link.group(2) or link.group(1)).strip()
    person = re.sub(r"<[^>]+>", "", value or "")
    person = re.sub(r"\{\{[^}]+\}\}", "", person)
    person = re.split(r"\s+[–—]\s+|\s+-\s+", person, maxsplit=1)[0]
    return person.strip(" []'*")


def observed_staff_roles_from_title(title: str) -> tuple[str, ...]:
    """Map a raw Wikipedia title onto lattice families without inventing cells."""

    lowered = re.sub(r"\s+", " ", str(title or "")).strip()
    if not lowered or _NOT_STAFF_TITLE.search(lowered):
        return ()
    families = list(role_families_from_title(title))
    for pattern, family in OBSERVED_STAFF_ROLE_PATTERNS:
        if re.search(pattern, lowered, re.I) and family not in families:
            families.append(family)
    if families:
        return tuple(families)
    if _COACH_LIKE_TITLE.search(lowered):
        return ("OTHER_POSITION",)
    return ()


CAREER_PAREN_ABBREV = {
    "hc": ROLE_HC,
    "oc": ROLE_OC,
    "dc": ROLE_DC,
    "co-oc": ROLE_OC,
    "cooc": ROLE_OC,
    "co-dc": ROLE_DC,
    "codc": ROLE_DC,
    "st": "special_teams_coordinator",
    "stc": "special_teams_coordinator",
    "qb": "quarterbacks",
    "rb": "running_backs",
    "wr": "wide_receivers",
    "te": "tight_ends",
    "ol": "offensive_line",
    "dl": "defensive_line",
    "lb": "linebackers",
    "db": "defensive_backs",
    "s": "safeties",
    "cb": "cornerbacks",
    "ga": "analyst_support",
    "qc": "analyst_support",
}


def roles_from_career_parenthetical(raw: str) -> tuple[str, ...]:
    """Map coach-infobox parentheticals. Empty/missing stays UNKNOWN, not HC."""

    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    if not text or text.casefold() == "unknown":
        return ("UNKNOWN",)
    families = list(observed_staff_roles_from_title(text))
    for token in re.split(r"[/,]", text):
        compact = token.strip().casefold().replace(" ", "")
        mapped = CAREER_PAREN_ABBREV.get(compact)
        if mapped and mapped not in families:
            families.append(mapped)
    if families:
        return tuple(families)
    return ("UNKNOWN",)


def expand_source_year_span(text: str) -> dict[str, Any]:
    """Expand 2009–2013; keep present open-ended. Never hardcode the retrieval year."""

    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    span = _YEAR_RANGE.search(raw)
    if span:
        ongoing = span.group("end").casefold() == "present"
        return {
            "source_year_text": raw,
            "start_year": int(span.group("start")),
            "end_year": None if ongoing else int(span.group("end")),
            "ongoing": ongoing,
        }
    single = _SINGLE_YEAR.match(raw)
    if single:
        year = int(single.group("year"))
        return {
            "source_year_text": raw,
            "start_year": year,
            "end_year": year,
            "ongoing": False,
        }
    return {
        "source_year_text": raw,
        "start_year": None,
        "end_year": None,
        "ongoing": False,
    }


def career_episode_seasons(
    episode: Mapping[str, Any], *, through_year: int = 2026
) -> list[int]:
    """Expand a career span into seasons. present stays open through_year."""

    start = episode.get("start_year")
    if start is None:
        return []
    if episode.get("ongoing"):
        end = through_year
    else:
        end = episode.get("end_year")
        if end is None:
            end = start
    start_i = int(start)
    end_i = int(end)
    if end_i < start_i:
        return []
    return list(range(start_i, end_i + 1))


def _wiki_title_from_bullet(body: str) -> tuple[str, str]:
    text = body.strip().lstrip("*").strip()
    person = wiki_display_name(text)
    remainder = text
    link = _WIKI_LINK.search(text) or _SORTNAME.search(text)
    if link:
        remainder = text[link.end() :].strip()
    remainder = remainder.lstrip(" –—-").strip()
    title = remainder or "UNKNOWN"
    return person, title


def _co_role_from_key(key: str) -> bool:
    compact = key.lower().replace(" ", "").replace("_", "")
    return compact.startswith("cooff") or compact.startswith("codef")


def _append_wiki_episode(
    extracted: list[dict[str, str]],
    seen: set[tuple[str, str]],
    *,
    person: str,
    title: str,
    role: str,
    span_id: str,
    revision_id: str,
    co_role: bool = False,
    interim: bool | None = None,
) -> None:
    person = person.strip()
    if not person or person.casefold() in {"", "vacant", "tbd", "none"}:
        return
    if re.fullmatch(r"\d{4}", person) or "@" in person or "[REDACTED" in person:
        return
    if "{{" in person or person.startswith("{"):
        return
    if "[REDACTED_EMAIL]" in title or "[REDACTED_PHONE]" in title:
        return
    key = (person.casefold(), role)
    if key in seen:
        return
    seen.add(key)
    flagged_interim = interim if interim is not None else "interim" in title.casefold()
    extracted.append(
        {
            "person": person,
            "title": title,
            "role": role,
            "span_id": span_id,
            "source_title": title,
            "wikimedia_revision": revision_id,
            "pit_admitted": "false",
            "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
            "interim": "true" if flagged_interim else "false",
            "co_role": "true" if co_role or " co-" in title.casefold() else "false",
        }
    )


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
    """Row-bound infobox, asst_coach lists, and staff tables. Not PIT."""

    wikitext = redact_personal_contact(wikitext)
    if not revision_id:
        raise CoachingError("Wikimedia evidence must be revision-bound")
    extracted: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in _INFOBOX_ROW.finditer(wikitext):
        raw_key = match.group("key").strip()
        key = raw_key.lower().replace(" ", "_")
        compact = raw_key.lower().replace(" ", "").replace("_", "")
        if compact.endswith("year") or compact.endswith("games"):
            continue
        if compact in _SKIP_INFOBOX_KEYS or compact in {
            "headcoachyear",
            "ocyear",
            "dcyear",
        }:
            continue
        role = (
            COACH_INFOBOX_KEYS.get(key)
            or COACH_INFOBOX_KEYS.get(raw_key.lower())
            or COACH_INFOBOX_KEYS.get(compact)
        )
        if not role:
            continue
        value = match.group("value").strip()
        if value.startswith("*"):
            continue
        person = wiki_display_name(value)
        games_note = ""
        games_key = None
        if compact in {"headcoach2", "head_coach2"}:
            games_key = r"hc_games2"
        elif compact in {"headcoach3", "head_coach3"}:
            games_key = r"hc_games3"
        elif compact in {"headcoach", "head_coach"}:
            games_key = r"hc_games"
        if games_key:
            games_match = re.search(
                rf"^\|\s*{games_key}\s*=\s*(.+)$", wikitext, re.I | re.M
            )
            games_note = str(games_match.group(1) if games_match else "")
        _append_wiki_episode(
            extracted,
            seen,
            person=person,
            title=raw_key,
            role=role,
            span_id=f"wikimedia:{page_title}:{revision_id}:{key}",
            revision_id=revision_id,
            co_role=_co_role_from_key(key),
            interim="interim" in games_note.casefold(),
        )
    for match in _MULTILINE_COACH_FIELD.finditer(wikitext):
        raw_key = match.group("key").strip()
        key = raw_key.lower().replace(" ", "_")
        infobox_role = (
            COACH_INFOBOX_KEYS.get(key)
            or COACH_INFOBOX_KEYS.get(raw_key.lower())
            or COACH_INFOBOX_KEYS.get(key.replace("_", ""))
        )
        for bullet in _STAFF_BULLET.finditer(match.group("body")):
            person, title = _wiki_title_from_bullet(bullet.group("body"))
            roles = observed_staff_roles_from_title(title)
            if not roles and infobox_role:
                roles = (infobox_role,)
            for role in roles:
                _append_wiki_episode(
                    extracted,
                    seen,
                    person=person,
                    title=title,
                    role=role,
                    span_id=(
                        f"wikimedia:{page_title}:{revision_id}:list:{person}:{role}"
                    ),
                    revision_id=revision_id,
                    co_role=_co_role_from_key(key) or " co-" in title.casefold(),
                )
    for match in _WIKI_TWO_CELL.finditer(wikitext):
        left = match.group("left").strip()
        title = match.group("title").strip()
        if "||" in left:
            continue
        families = observed_staff_roles_from_title(title)
        if not families:
            continue
        person = wiki_display_name(left)
        for role in families:
            _append_wiki_episode(
                extracted,
                seen,
                person=person,
                title=title,
                role=role,
                span_id=(f"wikimedia:{page_title}:{revision_id}:table:{person}:{role}"),
                revision_id=revision_id,
                co_role=" co-" in title.casefold()
                or title.casefold().startswith("co-"),
            )
    return extracted


def parse_infobox_college_coach(
    wikitext: str, *, revision_id: str, page_title: str
) -> list[dict[str, Any]]:
    """Career stops from Infobox college coach. Role UNKNOWN unless parenthetical."""

    wikitext = redact_personal_contact(wikitext)
    if not revision_id:
        raise CoachingError("Wikimedia evidence must be revision-bound")
    years = {
        match.group("n"): match.group("years").strip()
        for match in _COACH_YEARS_FIELD.finditer(wikitext)
    }
    teams = {
        match.group("n"): match.group("team").strip()
        for match in _COACH_TEAM_FIELD.finditer(wikitext)
    }
    episodes: list[dict[str, Any]] = []
    for index, raw_years in years.items():
        team_value = teams.get(index, "")
        if not team_value:
            continue
        span = expand_source_year_span(raw_years)
        team_text = re.sub(r"<[^>]+>", "", team_value)
        team_text = re.sub(r"\{\{[^}]+\}\}", "", team_text).strip()
        paren = re.search(r"\(([^)]+)\)\s*$", team_text)
        raw_role = paren.group(1).strip() if paren else "UNKNOWN"
        program = wiki_display_name(team_text[: paren.start()] if paren else team_text)
        if not program:
            continue
        roles = roles_from_career_parenthetical(raw_role) if paren else ("UNKNOWN",)
        for role in roles:
            episodes.append(
                {
                    "person": wiki_display_name(page_title),
                    "program_raw": program,
                    "role": role,
                    "raw_title": raw_role,
                    "source_title": raw_role,
                    "source_year_text": span["source_year_text"],
                    "start_year": span["start_year"],
                    "end_year": span["end_year"],
                    "ongoing": span["ongoing"],
                    "span_id": f"wikimedia:{page_title}:{revision_id}:career:{index}:{role}",
                    "wikimedia_revision": revision_id,
                    "pit_admitted": "false",
                    "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
                }
            )
    return episodes
