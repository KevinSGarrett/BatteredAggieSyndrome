"""Coaching schema, lattices, row-bound extraction, and attempt ledgers.

Equal-length name/title arrays are not a safe join. No DISPLAY: program IDs.
Coaching remains out of fitted models this cycle.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

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
