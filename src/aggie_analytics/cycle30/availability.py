"""Official public availability-report policy inventory.

No report means UNKNOWN, not healthy. Roster membership and game
participation are not availability. These fields stay out of fitted models.
Existing owner BAT-414 retains health evidence after duplicate audit.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

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
        "source_id": "SRC-UNASSIGNED-PAC12",
        "policy_status": "POLICY_ROUTE_UNVERIFIED_THIS_CYCLE",
        "route_label": "Pac-12 availability reporting (route not independently fetched)",
    },
    "Mountain West": {
        "source_id": "SRC-UNASSIGNED-MW",
        "policy_status": "POLICY_ROUTE_UNVERIFIED_THIS_CYCLE",
        "route_label": "Mountain West availability reporting (route not independently fetched)",
    },
}


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
    programs: Sequence[Mapping[str, Any]], *, season: int = 2026
) -> dict[str, Any]:
    if not programs:
        raise AvailabilityError(
            "availability inventory requires the current national parent"
        )
    rows = [program_availability_row(program, season=season) for program in programs]
    attempted = sum(int(row["attempt_count"]) for row in rows)
    if attempted:
        raise AvailabilityError(
            "inventory cannot claim attempts without request evidence"
        )
    return {
        "artifact_type": "AVAILABILITY_POLICY_INVENTORY",
        "artifact_class": "BLOCKER_METADATA",
        "season": season,
        "current_national_programs_in_denominator": len(rows),
        "attempted_official_report_routes": attempted,
        "not_attempted": len(rows),
        "no_report_means_unknown_not_healthy": True,
        "roster_or_participation_is_not_availability": True,
        "out_of_fitted_models": True,
        "owner": "BAT-414",
        "status": "INVENTORIED_NOT_ACQUIRED",
        "policy_status_counts": _counts(rows, "policy_status"),
        "conference_counts": _counts(rows, "conference"),
        "rows": rows,
    }


def _counts(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key) or "UNKNOWN")
        out[label] = out.get(label, 0) + 1
    return dict(sorted(out.items()))
