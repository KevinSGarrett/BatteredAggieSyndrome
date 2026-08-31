"""Official 2026 Week 1 national contest universe with bound identities.

The universe is every Division I football contest the official NCAA scoreboard
published for the declared Week 1 dates. Each contest carries its official contest
identifier, its ordered away/home participants, a conservative kickoff bound, the
published site annotation, and one disposition.

Three identity rules are load bearing. A participant is bound to a canonical team
only through evidence the predecessor entity benchmark already established, so a
display name never resolves an entity here. Subdivision and conference come from
the official 2026-27 institution lists rather than from a historical row, so a
realignment cannot be inherited from a prior season. And a contest whose published
header date disagrees with the requested date is refused rather than admitted,
so a source date substitution can never be presented as the requested schedule.
"""

from __future__ import annotations

import json
import platform
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import (
    assert_no_outcome_evidence,
    iso_utc,
    kickoff_bound,
    parse_scoreboard_document,
    parse_utc,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_official_schedule_identity.v1"
CONTRACT_ID = "BAT-676-WEEK1-2026-OFFICIAL-SCHEDULE-IDENTITY-V1"
JIRA_KEY = "BAT-676"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-OFFICIAL-SCHEDULE-IDENTITY-001"
CLASSIFICATION = "WEEK1_2026_NATIONAL_OFFICIAL_SCHEDULE_AND_IDENTITY_UNIVERSE"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_OFFICIAL_SCHEDULE_IDENTITY"

CONTRACT_RELATIVE = "configs/week1_2026_official_schedule_identity_contract.json"
GATE_RELATIVE = "artifacts/schedule/week1_2026_official_schedule_identity_gate.json"

CONTEST_PAYLOAD_NAME = "week1_2026_contest_identity.jsonl"
PARTICIPANT_PAYLOAD_NAME = "week1_2026_participant_identity.jsonl"
PAYLOAD_SLUG = "week1_2026_official_schedule_identity"

NON_AUTHORITATIVE_MANIFEST_KEYS = frozenset({"issued_at_utc", "producer"})

ADMITTED_MODEL_ELIGIBLE = "ADMITTED_MODEL_ELIGIBLE"
ADMITTED_FEATURE_SPINE_ONLY = "ADMITTED_FEATURE_SPINE_ONLY"
UNSUPPORTED_ENTITY = "UNSUPPORTED_ENTITY"
AMBIGUOUS_KICKOFF = "AMBIGUOUS_KICKOFF"
CONFLICT_QUARANTINED = "CONFLICT_QUARANTINED"
SOURCE_DATE_SUBSTITUTION = "SOURCE_DATE_SUBSTITUTION"
CANCELED_OR_POSTPONED = "CANCELED_OR_POSTPONED"
OUTSIDE_FBS_TARGET = "OUTSIDE_FBS_TARGET"
SOURCE_EVIDENCE_ABSENT = "SOURCE_EVIDENCE_ABSENT"

DISPOSITIONS = (
    ADMITTED_MODEL_ELIGIBLE,
    ADMITTED_FEATURE_SPINE_ONLY,
    UNSUPPORTED_ENTITY,
    AMBIGUOUS_KICKOFF,
    CONFLICT_QUARANTINED,
    SOURCE_DATE_SUBSTITUTION,
    CANCELED_OR_POSTPONED,
    OUTSIDE_FBS_TARGET,
    SOURCE_EVIDENCE_ABSENT,
)

PERMITTED_RESOLUTION_EVIDENCE = (
    "OFFICIAL_NCAA_ORGANIZATION_RECORD_TUPLE",
    "EXACT_NORMALIZED_NAME_RESOLVED_IN_PREDECESSOR_BENCHMARK",
    "RESOLVED_BY_OFFICIAL_RECORD_TUPLE_SHORT_HISTORY",
)

VENUE_IDENTITY_ABSENT = "SOURCE_EVIDENCE_ABSENT"
VENUE_IDENTITY_NEUTRAL_ANNOTATION = "NEUTRAL_SITE_ANNOTATION_ONLY"


class Week1ScheduleIdentityViolation(RuntimeError):
    """Raised when Week 1 schedule identity evidence fails a declared rule."""


def load_contract(repo_root: Path) -> dict[str, Any]:
    return validate_contract(
        json.loads((Path(repo_root) / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
    )


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse a contract that relaxes an identity, lane, or outcome protection."""

    if contract.get("contract_id") != CONTRACT_ID:
        raise Week1ScheduleIdentityViolation("contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise Week1ScheduleIdentityViolation("contract schema mismatch")
    if contract.get("lane") != LANE:
        raise Week1ScheduleIdentityViolation("contract lane must remain observation only")
    for field, expected in (
        ("prospective_shadow_observation", True),
        ("historical_pit_admission", False),
        ("protected_training_admission", False),
        ("protected_evaluation_admission", False),
        ("model_selection_or_tuning", False),
        ("champion_or_production_promotion", False),
        ("forecast_publication", False),
        ("canonical_entity_mutation", False),
        ("immutable_raw_capture_mutation", False),
    ):
        if contract["authority"].get(field) is not expected:
            raise Week1ScheduleIdentityViolation(
                f"contract authority field must remain {expected}: {field}"
            )
    if contract["outcome_exclusion"].get("outcome_fields_extracted") is not False:
        raise Week1ScheduleIdentityViolation("contract must forbid outcome extraction")
    identity_rules = contract["identity_rules"]
    if identity_rules.get("name_only_resolution_permitted") is not False:
        raise Week1ScheduleIdentityViolation("contract must forbid name-only resolution")
    if identity_rules.get("fuzzy_auto_accept_enabled") is not False:
        raise Week1ScheduleIdentityViolation("contract must keep fuzzy auto-accept disabled")
    if identity_rules.get("fuzzy_threshold_reduction_permitted") is not False:
        raise Week1ScheduleIdentityViolation("contract must forbid threshold reduction")
    if contract["sources"]["team_season_authority"].get(
        "historical_conference_inference_permitted"
    ) is not False:
        raise Week1ScheduleIdentityViolation(
            "contract must forbid inheriting a conference from a historical row"
        )
    if tuple(contract["dispositions"]) != DISPOSITIONS:
        raise Week1ScheduleIdentityViolation("contract disposition vocabulary mismatch")
    return dict(contract)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def index_team_season_authority(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index official 2026-27 subdivision and conference membership by source team.

    A team that the official lists place in more than one conference is refused
    rather than arbitrated, because arbitrating it would fabricate an affiliation.
    """

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in manifest["memberships"]:
        grouped.setdefault(str(row["source_team_id"]), []).append(row)
    indexed: dict[str, dict[str, Any]] = {}
    for source_team_id, rows in grouped.items():
        distinct = {(row["subdivision"], row["conference_id"]) for row in rows}
        if len(distinct) != 1:
            raise Week1ScheduleIdentityViolation(
                f"official season authority is ambiguous for team {source_team_id}"
            )
        row = rows[0]
        indexed[source_team_id] = {
            "subdivision": str(row["subdivision"]),
            "division_code": str(row["division_code"]),
            "conference_id": str(row["conference_id"]),
            "conference_name": str(row["conference_name"]),
            "season_authority_capture_sha256": str(row["source_capture_sha256"]),
            "season_authority_retrieved_at_utc": str(row["retrieved_at_utc"]),
            "season_authority_source_uri": str(row["source_uri"]),
        }
    return indexed


def index_predecessor_identities(
    cohort_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index the predecessor entity benchmark's participant identities by source team."""

    indexed: dict[str, dict[str, Any]] = {}
    for row in cohort_rows:
        for participant in row.get("participants", []):
            source_team_id = str(participant["source_team_id"])
            resolved = participant.get("canonical_team_id")
            evidence = participant.get("resolution_evidence")
            if resolved and evidence is None:
                evidence = "EXACT_NORMALIZED_NAME_RESOLVED_IN_PREDECESSOR_BENCHMARK"
            if resolved and evidence not in PERMITTED_RESOLUTION_EVIDENCE:
                raise Week1ScheduleIdentityViolation(
                    f"participant {source_team_id} carried unpermitted resolution evidence"
                )
            indexed[source_team_id] = {
                "canonical_team_id": resolved,
                "official_organization_id": participant.get("official_organization_id"),
                "normalized_name_key": participant.get("normalized_name_key"),
                "predecessor_source_display_name": participant.get("source_display_name"),
                "resolution_state": participant.get("resolution_state"),
                "resolution_evidence": evidence,
            }
    return indexed


def _participant_identity(
    participant: Mapping[str, Any],
    orientation: str,
    *,
    predecessor: Mapping[str, Mapping[str, Any]],
    authority: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source_team_id = str(participant["source_team_id"])
    resolved = dict(predecessor.get(source_team_id) or {})
    season = dict(authority.get(source_team_id) or {})
    if resolved.get("predecessor_source_display_name") and resolved[
        "predecessor_source_display_name"
    ] != participant["source_display_name"]:
        resolved["source_display_name_alias_observed"] = True
    return {
        "orientation": orientation,
        "source_team_id": source_team_id,
        "source_display_name": participant["source_display_name"],
        "source_label_carried_prior_record": bool(
            participant.get("source_label_carried_prior_record")
        ),
        "canonical_team_id": resolved.get("canonical_team_id"),
        "official_organization_id": resolved.get("official_organization_id"),
        "normalized_name_key": resolved.get("normalized_name_key"),
        "resolution_state": resolved.get("resolution_state") or "UNRESOLVED_SOURCE_ENTITY",
        "resolution_evidence": resolved.get("resolution_evidence"),
        "source_display_name_alias_observed": bool(
            resolved.get("source_display_name_alias_observed")
        ),
        "subdivision": season.get("subdivision"),
        "division_code": season.get("division_code"),
        "conference_id": season.get("conference_id"),
        "conference_name": season.get("conference_name"),
        "season_authority_state": (
            "OFFICIAL_2026_SEASON_AUTHORITY_BOUND" if season else SOURCE_EVIDENCE_ABSENT
        ),
        "season_authority_capture_sha256": season.get("season_authority_capture_sha256"),
        "season_authority_retrieved_at_utc": season.get("season_authority_retrieved_at_utc"),
    }


def _disposition_for(
    *,
    parse_state: str,
    parse_reason: str,
    participants: Sequence[Mapping[str, Any]],
    kickoff_state: str,
    fbs_target: bool,
) -> tuple[str, str]:
    if parse_state != "PARSED":
        if parse_reason == "CARD_HEADER_DATE_DOES_NOT_MATCH_REQUESTED_DATE":
            return SOURCE_DATE_SUBSTITUTION, parse_reason
        return CONFLICT_QUARANTINED, parse_reason
    unresolved = [row for row in participants if not row["canonical_team_id"]]
    if unresolved:
        return (
            UNSUPPORTED_ENTITY,
            "AT_LEAST_ONE_PARTICIPANT_HAS_NO_CANONICAL_IDENTITY_UNDER_PERMITTED_EVIDENCE",
        )
    if any(row["season_authority_state"] != "OFFICIAL_2026_SEASON_AUTHORITY_BOUND" for row in participants):
        return (
            SOURCE_EVIDENCE_ABSENT,
            "AT_LEAST_ONE_PARTICIPANT_HAS_NO_OFFICIAL_2026_SUBDIVISION_AUTHORITY",
        )
    if kickoff_state != "KICKOFF_TIME_PUBLISHED":
        return AMBIGUOUS_KICKOFF, f"OFFICIAL_KICKOFF_TIME_{kickoff_state}"
    if not fbs_target:
        return OUTSIDE_FBS_TARGET, "NO_PARTICIPANT_IS_A_2026_FBS_PROGRAM"
    return (
        ADMITTED_MODEL_ELIGIBLE,
        "CANONICAL_IDENTITIES_SEASON_AUTHORITY_AND_KICKOFF_BOUND_ALL_RESOLVE",
    )


def build_contest_rows(
    *,
    contract: Mapping[str, Any],
    captures: Sequence[Mapping[str, Any]],
    documents: Mapping[str, str],
    predecessor: Mapping[str, Mapping[str, Any]],
    authority: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    declared_dates = list(contract["requested_game_dates"])
    captured_dates = sorted({capture["requested_game_date"] for capture in captures})
    if captured_dates != sorted(declared_dates):
        raise Week1ScheduleIdentityViolation(
            "captured schedule dates do not match the declared Week 1 window"
        )
    by_date = {capture["requested_game_date"]: capture for capture in captures}
    offset = int(contract["kickoff_time_basis"]["declared_offset_seconds_for_window"])
    season = int(contract["season"])

    rows: list[dict[str, Any]] = []
    for game_date in declared_dates:
        capture = by_date[game_date]
        for record in parse_scoreboard_document(documents[game_date], game_date=game_date):
            parse_state = str(record.get("parse_state"))
            parse_reason = str(record.get("parse_reason") or "")
            participants = [
                _participant_identity(
                    participant,
                    orientation,
                    predecessor=predecessor,
                    authority=authority,
                )
                for participant, orientation in zip(
                    record.get("participants", []), ("AWAY", "HOME")
                )
            ]
            lower_bound, kickoff_state = kickoff_bound(
                game_date=str(record.get("source_published_game_date") or game_date),
                clock_text=str(record.get("source_published_clock_text") or ""),
                offset_seconds=offset,
            )
            fbs_target = any(row["subdivision"] == "FBS" for row in participants)
            disposition, reason = _disposition_for(
                parse_state=parse_state,
                parse_reason=parse_reason,
                participants=participants,
                kickoff_state=kickoff_state,
                fbs_target=fbs_target,
            )
            neutral_site_text = str(record.get("neutral_site_text") or "")
            row: dict[str, Any] = {
                "ncaa_contest_id": str(record.get("ncaa_contest_id") or ""),
                "season": season,
                "week_label": str(contract["week_label"]),
                "requested_game_date": game_date,
                "source_published_game_date": record.get("source_published_game_date"),
                "source_published_clock_text": record.get("source_published_clock_text"),
                "source_published_broadcast_text": record.get("source_published_broadcast_text"),
                "kickoff_utc_conservative_lower_bound": lower_bound,
                "kickoff_time_state": kickoff_state,
                "kickoff_utc_independently_confirmed": False,
                "kickoff_timezone_authority": str(
                    contract["kickoff_time_basis"]["published_clock_timezone_authority"]
                ),
                "kickoff_offset_seconds_declared": offset,
                "neutral_site_text": neutral_site_text,
                "site_state": "NEUTRAL" if neutral_site_text else "HOME_TEAM_SITE",
                "venue_identity_state": (
                    VENUE_IDENTITY_NEUTRAL_ANNOTATION if neutral_site_text else VENUE_IDENTITY_ABSENT
                ),
                "venue_identity": None,
                "away_team": participants[0] if len(participants) > 0 else None,
                "home_team": participants[1] if len(participants) > 1 else None,
                "participants": participants,
                "unresolved_participant_source_team_ids": sorted(
                    row_["source_team_id"] for row_ in participants if not row_["canonical_team_id"]
                ),
                "universe_membership": sorted(
                    membership
                    for membership, present in (
                        ("WEEK1_SOURCE_UNIVERSE", True),
                        ("WEEK1_FBS_TARGET", fbs_target),
                        ("WEEK1_MODEL_ELIGIBLE", disposition == ADMITTED_MODEL_ELIGIBLE),
                        (
                            "WEEK1_UNSUPPORTED",
                            disposition
                            in (UNSUPPORTED_ENTITY, AMBIGUOUS_KICKOFF, SOURCE_EVIDENCE_ABSENT),
                        ),
                    )
                    if present
                ),
                "disposition": disposition,
                "disposition_reason": reason,
                "parse_state": parse_state,
                "parse_reason": parse_reason,
                "outcome_fields_extracted": False,
                "source_capture_sha256": str(capture["raw_sha256"]),
                "request_identity_sha256": str(capture["request_identity_sha256"]),
                "retrieved_at_utc": str(capture["retrieved_at_utc"]),
                "route_id": str(capture["route_id"]),
            }
            row["contest_identity"] = stable_hash(
                {
                    "ncaa_contest_id": row["ncaa_contest_id"],
                    "season": row["season"],
                    "source_published_game_date": row["source_published_game_date"],
                    "kickoff_utc_conservative_lower_bound": row[
                        "kickoff_utc_conservative_lower_bound"
                    ],
                    "site_state": row["site_state"],
                    "ordered_source_team_ids": [
                        item["source_team_id"] for item in participants
                    ],
                    "ordered_canonical_team_ids": [
                        item["canonical_team_id"] for item in participants
                    ],
                    "source_capture_sha256": row["source_capture_sha256"],
                }
            )
            rows.append(row)

    duplicates = sorted(
        contest_id
        for contest_id, count in Counter(row["ncaa_contest_id"] for row in rows).items()
        if count > 1
    )
    if duplicates:
        raise Week1ScheduleIdentityViolation(
            f"official contest identifiers repeated across the Week 1 window: {duplicates}"
        )
    identities = {row["contest_identity"] for row in rows}
    if len(identities) != len(rows):
        raise Week1ScheduleIdentityViolation("contest identities are not unique")
    rows.sort(key=lambda row: (str(row["requested_game_date"]), int(row["ncaa_contest_id"])))
    assert_no_outcome_evidence(rows)
    return rows


def build_participant_rows(contests: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One row per distinct Week 1 participant with its truthful identity result."""

    indexed: dict[str, dict[str, Any]] = {}
    for contest in contests:
        for participant in contest["participants"]:
            entry = indexed.setdefault(
                participant["source_team_id"],
                {
                    "source_team_id": participant["source_team_id"],
                    "source_display_names": [],
                    "canonical_team_id": participant["canonical_team_id"],
                    "official_organization_id": participant["official_organization_id"],
                    "resolution_state": participant["resolution_state"],
                    "resolution_evidence": participant["resolution_evidence"],
                    "subdivision": participant["subdivision"],
                    "conference_id": participant["conference_id"],
                    "conference_name": participant["conference_name"],
                    "season_authority_state": participant["season_authority_state"],
                    "season_authority_capture_sha256": participant[
                        "season_authority_capture_sha256"
                    ],
                    "contest_ids": [],
                },
            )
            if participant["source_display_name"] not in entry["source_display_names"]:
                entry["source_display_names"].append(participant["source_display_name"])
            entry["contest_ids"].append(contest["ncaa_contest_id"])
    rows = []
    for entry in indexed.values():
        entry["source_display_names"] = sorted(entry["source_display_names"])
        entry["contest_ids"] = sorted(set(entry["contest_ids"]), key=int)
        entry["contest_count"] = len(entry["contest_ids"])
        entry["participant_identity"] = stable_hash(
            {
                "source_team_id": entry["source_team_id"],
                "canonical_team_id": entry["canonical_team_id"],
                "official_organization_id": entry["official_organization_id"],
                "subdivision": entry["subdivision"],
                "conference_id": entry["conference_id"],
                "season_authority_capture_sha256": entry["season_authority_capture_sha256"],
            }
        )
        rows.append(entry)
    rows.sort(key=lambda row: int(row["source_team_id"]))
    return rows


def summarize(
    contests: Sequence[Mapping[str, Any]], participants: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    disposition_counts = {name: 0 for name in DISPOSITIONS}
    for contest in contests:
        disposition_counts[contest["disposition"]] += 1
    by_date: dict[str, int] = {}
    for contest in contests:
        by_date[contest["requested_game_date"]] = by_date.get(contest["requested_game_date"], 0) + 1
    subdivision_counts = dict(
        sorted(Counter(str(row["subdivision"]) for row in participants).items())
    )
    conference_counts = dict(
        sorted(Counter(str(row["conference_name"]) for row in participants).items())
    )
    return {
        "contest_count": len(contests),
        "participant_count": len(participants),
        "contests_by_requested_date": dict(sorted(by_date.items())),
        "disposition_counts": disposition_counts,
        "universe_counts": {
            "WEEK1_SOURCE_UNIVERSE": len(contests),
            "WEEK1_FBS_TARGET": sum(
                1 for row in contests if "WEEK1_FBS_TARGET" in row["universe_membership"]
            ),
            "WEEK1_MODEL_ELIGIBLE": sum(
                1 for row in contests if "WEEK1_MODEL_ELIGIBLE" in row["universe_membership"]
            ),
            "WEEK1_UNSUPPORTED": sum(
                1 for row in contests if "WEEK1_UNSUPPORTED" in row["universe_membership"]
            ),
        },
        "participant_subdivision_counts": subdivision_counts,
        "participant_conference_counts": conference_counts,
        "participants_with_canonical_identity": sum(
            1 for row in participants if row["canonical_team_id"]
        ),
        "participants_unresolved": sum(1 for row in participants if not row["canonical_team_id"]),
        "participants_with_official_organization_id": sum(
            1 for row in participants if row["official_organization_id"] is not None
        ),
        "participants_with_official_season_authority": sum(
            1
            for row in participants
            if row["season_authority_state"] == "OFFICIAL_2026_SEASON_AUTHORITY_BOUND"
        ),
        "contests_with_published_kickoff_clock": sum(
            1 for row in contests if row["kickoff_time_state"] == "KICKOFF_TIME_PUBLISHED"
        ),
        "contests_with_independently_confirmed_kickoff": sum(
            1 for row in contests if row["kickoff_utc_independently_confirmed"]
        ),
        "contests_with_neutral_site_annotation": sum(
            1 for row in contests if row["site_state"] == "NEUTRAL"
        ),
        "contests_with_bound_venue_identity": sum(
            1 for row in contests if row["venue_identity"] is not None
        ),
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    contests: Sequence[Mapping[str, Any]],
    participants: Sequence[Mapping[str, Any]],
    capture_inventory: Sequence[Mapping[str, Any]],
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
    payloads: Sequence[Mapping[str, Any]],
    bound_predecessors: Mapping[str, Any],
    execution_time: datetime,
) -> dict[str, Any]:
    summary = summarize(contests, participants)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_OFFICIAL_SCHEDULE_IDENTITY_GATE",
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "contract_sha256": contract_sha256,
        "season": int(contract["season"]),
        "week_label": str(contract["week_label"]),
        "requested_game_dates": list(contract["requested_game_dates"]),
        "kickoff_time_basis": dict(contract["kickoff_time_basis"]),
        "identity_rules": dict(contract["identity_rules"]),
        "venue_policy": dict(contract["venue_policy"]),
        "universe_definitions": dict(contract["universe_definitions"]),
        "bound_predecessors": dict(bound_predecessors),
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
            "dataset_identity": dataset_identity,
            "bulk_payloads_in_git": False,
        },
        "payloads": [dict(payload) for payload in payloads],
        "payload_root_sha256": stable_hash(
            [
                {"name": payload["name"], "rows": payload["rows"], "sha256": payload["sha256"]}
                for payload in payloads
            ]
        ),
        "capture_inventory": [dict(row) for row in capture_inventory],
        "summary": summary,
        "unresolved_participants": [
            {
                "source_team_id": row["source_team_id"],
                "source_display_names": row["source_display_names"],
                "official_organization_id": row["official_organization_id"],
                "subdivision": row["subdivision"],
                "conference_name": row["conference_name"],
                "resolution_state": row["resolution_state"],
                "contest_ids": row["contest_ids"],
            }
            for row in participants
            if not row["canonical_team_id"]
        ],
        "contest_dispositions": [
            {
                "ncaa_contest_id": row["ncaa_contest_id"],
                "disposition": row["disposition"],
                "disposition_reason": row["disposition_reason"],
                "contest_identity": row["contest_identity"],
            }
            for row in contests
        ],
        "authority": {**dict(contract["authority"]), "protected_lane_admission": False},
        "predecessor_identity": str(
            bound_predecessors["national_entity_identity_benchmark_gate_identity"]
        ),
        "backfill_performed": False,
        "outcome_exclusion": {
            "outcome_fields_extracted": False,
            "prior_record_suffix_discarded": True,
            "forbidden_outcome_markers_absent": True,
        },
        "scientific_nonclaims": {
            "bas_or_aggie_excess": False,
            "champion_or_production_selection": False,
            "forecast_published": False,
            "model_tuning_or_promotion": False,
            "protected_performance": False,
            "specialization_lift": False,
            "tamu_specific_adjustment_applied": False,
        },
        "declared_nonclaims": list(contract["scientific_nonclaims"]),
        "execution_time_utc": iso_utc(execution_time),
    }


def dataset_manifest(
    *,
    contract: Mapping[str, Any],
    summary: Mapping[str, Any],
    capture_inventory: Sequence[Mapping[str, Any]],
    payloads: Sequence[Mapping[str, Any]],
    execution_time: datetime,
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_OFFICIAL_SCHEDULE_IDENTITY_MANIFEST",
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "season": int(contract["season"]),
        "requested_game_dates": list(contract["requested_game_dates"]),
        "summary": dict(summary),
        "capture_inventory": [dict(row) for row in capture_inventory],
        "payloads": [dict(payload) for payload in payloads],
        "authority": dict(contract["authority"]),
        "execution_time_utc": iso_utc(execution_time),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def validate_artifact(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Revalidate the published gate against external evidence without writing."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    findings: list[str] = []
    if not gate_path.is_file():
        return {"result": "FAIL", "findings": ["gate artifact is absent"]}
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    if gate.get("requested_game_dates") != list(contract["requested_game_dates"]):
        findings.append("gate window disagrees with the contract")

    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        findings.append("dataset manifest is absent from the external data root")
        return {"result": "FAIL", "findings": findings}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("dataset manifest hash drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("dataset_identity") != gate["manifest"]["dataset_identity"]:
        findings.append("dataset identity disagrees with the gate binding")

    payload_rows: dict[str, list[dict[str, Any]]] = {}
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        rows = read_jsonl(payload_path)
        if len(rows) != int(payload["rows"]):
            findings.append(f"payload row count drifted: {payload['name']}")
        payload_rows[payload["name"]] = rows

    contests = payload_rows.get(CONTEST_PAYLOAD_NAME, [])
    participants = payload_rows.get(PARTICIPANT_PAYLOAD_NAME, [])
    if contests:
        assert_no_outcome_evidence(contests)
        if summarize(contests, participants) != gate["summary"]:
            findings.append("payload summary disagrees with the gate")
        if len({row["ncaa_contest_id"] for row in contests}) != len(contests):
            findings.append("payload carries duplicate contest identifiers")
        for row in contests:
            if row["disposition"] not in DISPOSITIONS:
                findings.append(f"contest {row['ncaa_contest_id']} carries an undeclared disposition")
            if row["requested_game_date"] != row["source_published_game_date"]:
                findings.append(
                    f"contest {row['ncaa_contest_id']} was admitted under a substituted source date"
                )
            if row["disposition"] == ADMITTED_MODEL_ELIGIBLE and (
                not all(item["canonical_team_id"] for item in row["participants"])
                or row["kickoff_utc_conservative_lower_bound"] is None
            ):
                findings.append(
                    f"contest {row['ncaa_contest_id']} was admitted without a resolved input"
                )
            if row["kickoff_utc_conservative_lower_bound"] is not None:
                bound = parse_utc(row["kickoff_utc_conservative_lower_bound"])
                if bound <= parse_utc(row["retrieved_at_utc"]):
                    findings.append(
                        f"contest {row['ncaa_contest_id']} kickoff bound is not after its capture"
                    )
    for row in participants:
        if row["canonical_team_id"] and row["resolution_evidence"] not in PERMITTED_RESOLUTION_EVIDENCE:
            findings.append(
                f"participant {row['source_team_id']} was bound without permitted evidence"
            )

    for capture in gate["capture_inventory"]:
        capture_path = data_root / capture["raw_relative_path"]
        if not capture_path.is_file():
            findings.append(f"immutable capture absent: {capture['requested_game_date']}")
        elif sha256_file(capture_path) != capture["raw_sha256"]:
            findings.append(f"immutable capture hash drifted: {capture['requested_game_date']}")

    if gate["authority"].get("protected_evaluation_admission") is not False:
        findings.append("gate opened protected evaluation")
    if gate["identity_rules"].get("fuzzy_auto_accept_enabled") is not False:
        findings.append("gate enabled fuzzy auto-accept")
    if gate["outcome_exclusion"].get("outcome_fields_extracted") is not False:
        findings.append("gate claimed outcome extraction")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "summary": gate.get("summary"),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
