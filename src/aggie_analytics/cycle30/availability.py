"""Official public availability-report policy inventory.

No report means UNKNOWN, not healthy. Roster membership and game
participation are not availability. These fields stay out of fitted models.
Existing owner BAT-414 retains health evidence after duplicate audit.
"""

from __future__ import annotations

import re
import urllib.parse
from io import BytesIO
from typing import Any, Mapping, Sequence

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]

CONFERENCE_POLICY_ROUTES: dict[str, dict[str, str]] = {
    "SEC": {
        "source_id": "SRC-017",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "SEC football student-athlete availability reports",
    },
    "Big Ten": {
        "source_id": "SRC-018",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Big Ten gameday availability reports",
    },
    "ACC": {
        "source_id": "SRC-019",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "ACC availability reporting",
    },
    "Big 12": {
        "source_id": "SRC-020",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Big 12 player availability reporting",
    },
    "American Athletic": {
        "source_id": "SRC-021",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "American Conference football player availability reports",
    },
    "Sun Belt": {
        "source_id": "SRC-022",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Sun Belt football availability reporting",
    },
    "Conference USA": {
        "source_id": "SRC-023",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Conference USA football availability reports",
    },
    "Mid-American": {
        "source_id": "SRC-024",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "MAC football availability reports",
    },
    "Pac-12": {
        "source_id": "SRC-C30-PAC12",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Pac-12 football player availability reporting",
    },
    "Mountain West": {
        "source_id": "SRC-026",
        "policy_status": "KNOWN_PUBLIC_POLICY",
        "route_label": "Mountain West football player availability reporting",
    },
}

PUBLIC_AVAILABILITY_ROUTES: tuple[dict[str, str], ...] = (
    {
        "source_id": "SRC-017",
        "conference": "SEC",
        "uri": "https://www.secsports.com/fbreports-archive",
    },
    {
        "source_id": "SRC-018",
        "conference": "Big Ten",
        "uri": "https://bigten.org/fb/article/blt2856785fb75ee868/",
    },
    {
        "source_id": "SRC-019",
        "conference": "ACC",
        "uri": "https://theacc.com/sports/2025/8/28/availability-reporting-football.aspx",
    },
    {
        "source_id": "SRC-019-POLICY",
        "conference": "ACC",
        "uri": "https://theacc.com/sports/2025/8/28/availability-reporting.aspx",
    },
    {
        "source_id": "SRC-020",
        "conference": "Big 12",
        "uri": "https://big12sports.com/news/2025/8/13/general-big-12-conference-to-begin-player-availability-reporting-for-football-womens-and-mens-basketball.aspx",
    },
    {
        "source_id": "SRC-021",
        "conference": "American Athletic",
        "uri": "https://theamerican.org/sports/2025/8/5/fbavail.aspx",
    },
    {
        "source_id": "SRC-022",
        "conference": "Sun Belt",
        "uri": "https://sunbeltsports.org/news/2025/8/20/sun-belt-to-institute-availability-reporting-for-2025-football-season.aspx",
    },
    {
        "source_id": "SRC-023",
        "conference": "Conference USA",
        "uri": "https://conferenceusa.com/sports/2025/8/23/FB_0823254134.aspx",
    },
    {
        "source_id": "SRC-024",
        "conference": "Mid-American",
        "uri": "https://getsomemaction.com/news/2024/8/22/mac-to-launch-gameday-student-athlete-availability-report-for-2024-football-season.aspx",
    },
    {
        "source_id": "SRC-025",
        "conference": "CFP",
        "uri": "https://collegefootballplayoff.com/sports/2025/11/12/reports.aspx",
    },
    {
        "source_id": "SRC-026",
        "conference": "Mountain West",
        "uri": "https://themw.com/news/2026/9/1/2026-mw-football-weekly-release-week-1.aspx",
    },
    {
        "source_id": "SRC-026-HOME",
        "conference": "Mountain West",
        "uri": "https://themw.com/",
    },
    {
        "source_id": "SRC-C30-PAC12",
        "conference": "Pac-12",
        "uri": "https://pac-12.com/news/2026/9/3/pac-12-announces-commercial-and-operational-updates-ahead-of-its-2026-football-season-kickoff.aspx",
    },
)


class AvailabilityError(ValueError):
    """Raised when availability inventory contracts fail."""


def conference_policy(conference: str, *, classification: str) -> dict[str, str]:
    known = CONFERENCE_POLICY_ROUTES.get(str(conference or ""))
    if known:
        return dict(known)
    if str(classification or "").lower() == "fcs":
        return {
            "source_id": "SRC-UNASSIGNED-FCS",
            "policy_status": "FCS_VARIES_BY_PROGRAM",
            "route_label": "FCS official availability policy varies by program",
        }
    return {
        "source_id": "SRC-UNASSIGNED",
        "policy_status": "UNKNOWN_POLICY",
        "route_label": "no independently inventoried public availability route",
    }


def program_availability_row(
    program: Mapping[str, Any], *, season: int = 2026
) -> dict[str, Any]:
    policy = conference_policy(
        str(program.get("conference") or ""),
        classification=str(program.get("classification") or ""),
    )
    return {
        "program_id": program.get("program_id"),
        "display_name": program.get("display_name"),
        "conference": program.get("conference"),
        "classification": program.get("classification"),
        "season": season,
        "source_id": policy["source_id"],
        "policy_status": policy["policy_status"],
        "route_label": policy["route_label"],
        "attempt_count": 0,
        "disposition": "NOT_ATTEMPTED",
        "no_report_means": "UNKNOWN",
        "roster_or_participation_is_not_availability": True,
        "joined_to_verified_roster": False,
        "private_medical_detail_ingested": False,
        "out_of_fitted_models": True,
        "owner": "BAT-414",
        "artifact_class": "BLOCKER_METADATA",
    }


def inventory_availability_policies(
    programs: Sequence[Mapping[str, Any]],
    *,
    season: int = 2026,
    route_attempts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not programs:
        raise AvailabilityError(
            "availability inventory requires the current national parent"
        )
    attempts_by_source = {
        str(row.get("source_id")): row for row in (route_attempts or [])
    }
    rows = []
    for program in programs:
        row = program_availability_row(program, season=season)
        attempt = attempts_by_source.get(str(row["source_id"]))
        if attempt:
            count = int(attempt.get("attempt_count") or 0)
            if count < 1 or not attempt.get("receipt_identity"):
                raise AvailabilityError(
                    "availability attempt claimed without request evidence"
                )
            row["attempt_count"] = count
            row["disposition"] = str(
                attempt.get("disposition") or "ATTEMPTED_WITH_EVIDENCE"
            )
            row["http_status"] = attempt.get("http_status")
            row["receipt_identity"] = attempt.get("receipt_identity")
            row["route_uri"] = attempt.get("uri")
            row["player_rows_joined_to_verified_roster"] = False
            row["artifact_class"] = "REAL_EVIDENCE"
        rows.append(row)
    attempted_programs = sum(1 for row in rows if int(row["attempt_count"]) > 0)
    attempted_routes = len(attempts_by_source)
    return {
        "artifact_type": "AVAILABILITY_POLICY_INVENTORY",
        "artifact_class": "REAL_EVIDENCE" if attempted_routes else "BLOCKER_METADATA",
        "season": season,
        "current_national_programs_in_denominator": len(rows),
        "attempted_official_report_routes": attempted_routes,
        "programs_covered_by_attempted_routes": attempted_programs,
        "not_attempted": sum(1 for row in rows if int(row["attempt_count"]) == 0),
        "no_report_means_unknown_not_healthy": True,
        "roster_or_participation_is_not_availability": True,
        "out_of_fitted_models": True,
        "owner": "BAT-414",
        "status": "ROUTES_ATTEMPTED"
        if attempted_routes
        else "INVENTORIED_NOT_ACQUIRED",
        "policy_status_counts": _counts(rows, "policy_status"),
        "conference_counts": _counts(rows, "conference"),
        "rows": rows,
    }


_CANDIDATE_NAME = re.compile(
    r"<t[dh][^>]*>\s*([A-Z][a-z]+(?:[-\s][A-Z][a-z'.]+){1,3})\s*</t[dh]>",
)
_CANDIDATE_COMMA = re.compile(
    r"<t[dh][^>]*>\s*([A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*</t[dh]>",
)
_JSON_PLAYER_NAME = re.compile(
    r'"(?:player(?:Name)?|athleteName|fullName|displayName)"\s*:\s*"([^"]{3,80})"',
    re.I,
)
_PDF_HREF = re.compile(r"""href=["']([^"'#]+\.pdf[^"']*)["']""", re.I)
_PLAIN_COMMA_NAME = re.compile(r"\b([A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b")
_LINE_STATUS_NAME = re.compile(
    r"^\s*([A-Z][a-z]+(?:-[A-Z][a-z]+)?),\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[-–]",
    re.MULTILINE,
)


def availability_pdf_hrefs(html: str, *, page_uri: str, limit: int = 4) -> list[str]:
    """Absolute PDF links from a public availability page. Not health status."""

    out: list[str] = []
    seen: set[str] = set()
    for match in _PDF_HREF.finditer(html or ""):
        href = match.group(1).strip()
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            parsed = urllib.parse.urlparse(page_uri)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            href = urllib.parse.urljoin(page_uri, href)
        key = href.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(href)
        if len(out) >= limit:
            break
    return out


def pdf_plaintext(body: bytes, *, page_limit: int = 20) -> str:
    """Extract name-bearing text from a public PDF. Not a health status."""

    if not body.startswith(b"%PDF"):
        return ""
    if PdfReader is None:
        return body.decode("latin-1", "replace")
    try:
        reader = PdfReader(BytesIO(body))
        parts: list[str] = []
        for page in list(reader.pages)[:page_limit]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:  # noqa: BLE001
        return body.decode("latin-1", "replace")


def extract_candidate_player_rows(
    html: str, *, source_id: str, uri: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Name-only public-page candidates. Not roster-joined. Not health status."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    names: list[str] = []
    for match in _CANDIDATE_NAME.finditer(html or ""):
        names.append(match.group(1))
    for match in _CANDIDATE_COMMA.finditer(html or ""):
        last, first = [part.strip() for part in match.group(1).split(",", 1)]
        names.append(f"{first} {last}")
    for match in _JSON_PLAYER_NAME.finditer(html or ""):
        names.append(match.group(1))
    for match in _LINE_STATUS_NAME.finditer(html or ""):
        names.append(f"{match.group(2).strip()} {match.group(1).strip()}")
    if "<t" not in (html or "").casefold():
        for match in _PLAIN_COMMA_NAME.finditer(html or ""):
            last, first = [part.strip() for part in match.group(1).split(",", 1)]
            names.append(f"{first} {last}")
    for raw in names:
        name = " ".join((raw or "").split())
        key = name.casefold()
        if key in seen:
            continue
        if any(
            token in key
            for token in (
                "availability",
                "conference",
                "football",
                "report",
                "student",
                "athlete",
                "discretion",
                "handbook",
                "sportsmanship",
                "timeliness",
            )
        ):
            continue
        if len(name.split()) < 2:
            continue
        seen.add(key)
        rows.append(
            {
                "source_id": source_id,
                "uri": uri,
                "candidate_name": name,
                "disposition": "CANDIDATE_NOT_JOINED",
                "joined_to_verified_roster": False,
                "no_report_means": "UNKNOWN",
                "private_medical_detail_ingested": False,
                "health_status_inferred": False,
                "out_of_fitted_models": True,
                "owner": "BAT-414",
                "artifact_class": "REAL_EVIDENCE",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _normalize_person_name(value: str) -> str:
    return re.sub(r"[^a-z ]", "", str(value or "").casefold())


def join_candidates_to_roster(
    candidates: Sequence[Mapping[str, Any]],
    roster_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Join public name-only candidates to verified roster identities.

    No report still means UNKNOWN. Roster membership is not availability.
    """

    roster_index: dict[str, Mapping[str, Any]] = {}
    for row in roster_rows:
        name = _normalize_person_name(
            str(
                row.get("full_name")
                or row.get("display_name")
                or " ".join(
                    str(part)
                    for part in (
                        row.get("first_name") or row.get("firstName"),
                        row.get("last_name") or row.get("lastName"),
                    )
                    if part
                )
                or row.get("name")
                or ""
            )
        )
        if name:
            roster_index.setdefault(name, row)
    joined: list[dict[str, Any]] = []
    unmatched = 0
    for candidate in candidates:
        key = _normalize_person_name(str(candidate.get("candidate_name") or ""))
        roster = roster_index.get(key)
        if roster is None:
            unmatched += 1
            joined.append({**dict(candidate), "joined_to_verified_roster": False})
            continue
        joined.append(
            {
                **dict(candidate),
                "joined_to_verified_roster": True,
                "roster_identity": str(
                    roster.get("canonical_person_id")
                    or roster.get("id")
                    or roster.get("athlete_id")
                    or ""
                ),
                "disposition": "JOINED_NAME_ONLY_STATUS_UNKNOWN",
                "health_status_inferred": False,
                "no_report_means": "UNKNOWN",
                "roster_or_participation_is_not_availability": True,
                "out_of_fitted_models": True,
                "owner": "BAT-414",
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    return {
        "artifact_type": "AVAILABILITY_CANDIDATE_PLAYER_SUMMARY",
        "candidate_rows": len(candidates),
        "joined_to_verified_roster": sum(
            1 for row in joined if row.get("joined_to_verified_roster")
        ),
        "unmatched_name_only": unmatched,
        "no_report_means": "UNKNOWN",
        "roster_or_participation_is_not_availability": True,
        "out_of_fitted_models": True,
        "rows": joined,
        "artifact_class": "REAL_EVIDENCE" if candidates else "BLOCKER_METADATA",
        "owner": "BAT-414",
    }


def _counts(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key) or "UNKNOWN")
        out[label] = out.get(label, 0) + 1
    return dict(sorted(out.items()))
