"""Week 1 2026 feature coverage, temporal eligibility and forecast-input adequacy.

This unit reads the materialized spine and states, per contest and per frozen
candidate, whether the inputs that candidate declared are actually present as
admitted prospective evidence. It produces no forecast and promotes no model: an
adequacy state is a statement about evidence, not about expected accuracy. A
contest whose required features are missing abstains explicitly rather than
receiving a default, and the Texas A&M contest is discovered from the universe and
reported through the same path as every other contest.
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
from aggie_analytics.data.prospective_shadow_cohort import iso_utc
from aggie_analytics.data.week1_2026_current_feature_spine import (
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CANDIDATE_ONLY_NOT_CONSUMED,
    FEATURE_DOMAINS,
    QUARANTINED_CONFLICT,
    SPINE_ROW_ADMITTED,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_feature_coverage_adequacy.v1"
CONTRACT_ID = "BAT-678-WEEK1-2026-FEATURE-COVERAGE-ADEQUACY-V1"
JIRA_KEY = "BAT-678"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-FEATURE-COVERAGE-ADEQUACY-001"
CLASSIFICATION = (
    "WEEK1_2026_FEATURE_COVERAGE_TEMPORAL_ELIGIBILITY_AND_FORECAST_INPUT_ADEQUACY"
)
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_FEATURE_COVERAGE_ADEQUACY"

CONTRACT_RELATIVE = "configs/week1_2026_feature_coverage_adequacy_contract.json"
GATE_RELATIVE = "artifacts/spine/week1_2026_feature_coverage_adequacy_gate.json"
CONTEST_PAYLOAD_NAME = "week1_2026_contest_adequacy.jsonl"
CANDIDATE_PAYLOAD_NAME = "week1_2026_candidate_adequacy.jsonl"
PAYLOAD_SLUG = "week1_2026_feature_coverage_adequacy"

READY = "READY_FOR_PREDECLARED_MODEL_INPUT"
PARTIAL = "PARTIAL_MODEL_INPUT"
ABSTAIN_MISSING = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_UNSUPPORTED = "ABSTAIN_UNSUPPORTED_ENTITY"
QUARANTINED = "QUARANTINED_CONFLICT"
NOT_IN_TARGET = "NOT_IN_MODEL_TARGET"

ADEQUACY_STATES = (
    READY,
    PARTIAL,
    ABSTAIN_MISSING,
    ABSTAIN_UNSUPPORTED,
    QUARANTINED,
    NOT_IN_TARGET,
)

TAMU_CANONICAL_TEAM_ID = None


class Week1AdequacyViolation(RuntimeError):
    """Raised when an adequacy claim is not supported by the spine evidence."""


def load_contract(repo_root: Path) -> dict[str, Any]:
    return validate_contract(
        json.loads(
            (Path(repo_root) / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )
    )


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse a contract that would let this gate forecast, promote, or hardcode."""

    if contract.get("contract_id") != CONTRACT_ID:
        raise Week1AdequacyViolation("contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise Week1AdequacyViolation("contract schema mismatch")
    if contract.get("lane") != LANE:
        raise Week1AdequacyViolation("contract lane must remain observation only")
    for field in (
        "forecast_publication",
        "forecast_produced",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "protected_training_admission",
        "protected_evaluation_admission",
    ):
        if contract["authority"].get(field) is not False:
            raise Week1AdequacyViolation(
                f"contract authority field must remain False: {field}"
            )
    if (
        contract["sources"]["frozen_candidates"].get("post_hoc_candidate_insertion")
        is not False
    ):
        raise Week1AdequacyViolation(
            "contract must forbid post hoc candidate insertion"
        )
    if (
        contract["sources"]["frozen_candidates"].get("candidate_set_is_frozen")
        is not True
    ):
        raise Week1AdequacyViolation("contract must keep the candidate set frozen")
    checkpoints = contract["checkpoints"]
    for field, expected in (
        ("t_minus_24h_state", "OPEN"),
        ("t_minus_90m_state", "OPEN"),
        ("t_minus_7d_packet_state", "PRESERVED_UNCHANGED"),
    ):
        if checkpoints.get(field) != expected:
            raise Week1AdequacyViolation(
                f"contract must keep checkpoint state {expected}: {field}"
            )
    for field in ("executed_early", "pregame_result_access"):
        if checkpoints.get(field) is not False:
            raise Week1AdequacyViolation(
                f"contract must refuse checkpoint field: {field}"
            )
    if contract["tamu_policy"].get("tamu_specific_adjustment_applied") is not False:
        raise Week1AdequacyViolation(
            "contract must forbid a Texas A&M specific adjustment"
        )
    if (
        contract["tamu_policy"].get(
            "tamu_ncaa_contest_id_is_discovered_from_the_universe_not_hardcoded"
        )
        is not True
    ):
        raise Week1AdequacyViolation(
            "contract must forbid a hardcoded Texas A&M contest identifier"
        )
    if tuple(contract["adequacy_states"]) != ADEQUACY_STATES:
        raise Week1AdequacyViolation("contract adequacy vocabulary mismatch")
    for requirement in contract["candidate_feature_requirements"]:
        for domain in list(requirement["required_domains"]) + list(
            requirement["optional_domains"]
        ):
            if domain not in FEATURE_DOMAINS:
                raise Week1AdequacyViolation(
                    f"candidate requires an undeclared domain: {domain}"
                )
    return dict(contract)


def _cells_by_row(
    cells: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for cell in cells:
        indexed.setdefault(cell["row_identity"], {})[cell["domain"]] = cell
    return indexed


def build_adequacy_rows(
    *,
    contract: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """State adequacy per contest and per frozen candidate from spine evidence only."""

    admitted_states = set(contract["admission_counts_as_required"])
    indexed = _cells_by_row(cells)
    by_contest: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_contest.setdefault(row["ncaa_contest_id"], []).append(row)

    contest_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for contest_id in sorted(by_contest):
        pair = sorted(by_contest[contest_id], key=lambda row: row["orientation"])
        if len(pair) != 2:
            raise Week1AdequacyViolation(
                f"contest {contest_id} does not carry two spine rows"
            )
        pair_cells = [indexed[row["row_identity"]] for row in pair]
        entity_supported = all(
            row["spine_row_state"] == SPINE_ROW_ADMITTED for row in pair
        )
        conflicted_domains = sorted(
            {
                domain
                for cell_map in pair_cells
                for domain, cell in cell_map.items()
                if cell["admission_disposition"] == QUARANTINED_CONFLICT
            }
        )
        kickoff = pair[0]["kickoff_utc_conservative_lower_bound"]

        contest_candidates: list[dict[str, Any]] = []
        for requirement in contract["candidate_feature_requirements"]:
            required = list(requirement["required_domains"])
            optional = list(requirement["optional_domains"])
            admitted_required = sorted(
                domain
                for domain in required
                if all(
                    cell_map[domain]["admission_disposition"] in admitted_states
                    for cell_map in pair_cells
                )
            )
            missing_required = sorted(set(required) - set(admitted_required))
            optional_candidates = sorted(
                domain
                for domain in optional
                if any(
                    cell_map[domain]["admission_disposition"]
                    in admitted_states | {CANDIDATE_ONLY_NOT_CONSUMED}
                    for cell_map in pair_cells
                )
            )
            if not entity_supported:
                state = ABSTAIN_UNSUPPORTED
                reason = "AT_LEAST_ONE_PARTICIPANT_HAS_NO_CANONICAL_IDENTITY"
            elif conflicted_domains:
                state = QUARANTINED
                reason = f"CONFLICTED_DOMAINS:{','.join(conflicted_domains)}"
            elif kickoff is None:
                state = ABSTAIN_MISSING
                reason = "THE_TARGET_KICKOFF_BOUND_IS_UNRESOLVED"
            elif missing_required:
                state = PARTIAL if admitted_required else ABSTAIN_MISSING
                reason = f"MISSING_REQUIRED_DOMAINS:{','.join(missing_required)}"
            else:
                state = READY
                reason = "EVERY_REQUIRED_DOMAIN_IS_ADMITTED_PROSPECTIVE_EVIDENCE_FOR_BOTH_TEAMS"
            candidate_row = {
                "ncaa_contest_id": contest_id,
                "contest_identity": pair[0]["contest_identity"],
                "candidate_id": requirement["candidate_id"],
                "feature_scope": requirement["feature_scope"],
                "required_feature_count": len(required),
                "admitted_required_count": len(admitted_required),
                "missing_required_count": len(missing_required),
                "optional_candidate_count": len(optional_candidates),
                "required_domains": required,
                "admitted_required_domains": admitted_required,
                "missing_required_domains": missing_required,
                "optional_candidate_domains": optional_candidates,
                "adequacy_state": state,
                "adequacy_reason": reason,
                "forecast_produced": False,
            }
            candidate_row["candidate_adequacy_identity"] = stable_hash(candidate_row)
            candidate_rows.append(candidate_row)
            contest_candidates.append(candidate_row)

        states = {row["adequacy_state"] for row in contest_candidates}
        if not entity_supported:
            contest_state = ABSTAIN_UNSUPPORTED
        elif conflicted_domains:
            contest_state = QUARANTINED
        elif READY in states:
            contest_state = READY if states == {READY} else PARTIAL
        elif PARTIAL in states:
            contest_state = PARTIAL
        else:
            contest_state = ABSTAIN_MISSING

        contest_row = {
            "ncaa_contest_id": contest_id,
            "contest_identity": pair[0]["contest_identity"],
            "requested_game_date": pair[0]["requested_game_date"],
            "kickoff_utc_conservative_lower_bound": kickoff,
            "kickoff_time_state": pair[0]["kickoff_time_state"],
            "contest_disposition": pair[0]["contest_disposition"],
            "away_source_team_id": next(
                row["source_team_id"] for row in pair if row["orientation"] == "AWAY"
            ),
            "home_source_team_id": next(
                row["source_team_id"] for row in pair if row["orientation"] == "HOME"
            ),
            "away_canonical_team_id": next(
                row["canonical_team_id"] for row in pair if row["orientation"] == "AWAY"
            ),
            "home_canonical_team_id": next(
                row["canonical_team_id"] for row in pair if row["orientation"] == "HOME"
            ),
            "subdivisions": sorted({str(row["subdivision"]) for row in pair}),
            "conferences": sorted({str(row["conference_name"]) for row in pair}),
            "site_state": "NEUTRAL" if pair[0]["is_neutral_site"] else "HOME_TEAM_SITE",
            "unsupported_entity_count": sum(
                1 for row in pair if not row["canonical_team_id"]
            ),
            "temporal_exclusion_count": sum(
                1
                for cell_map in pair_cells
                for cell in cell_map.values()
                if cell["admission_disposition"] == "TEMPORALLY_INELIGIBLE"
            ),
            "conflict_count": len(conflicted_domains),
            "conflicted_domains": conflicted_domains,
            "weather_available": all(
                cell_map["WEATHER_VINTAGE"]["value"] is not None
                for cell_map in pair_cells
            ),
            "roster_membership_available": any(
                cell_map["ROSTER_MEMBERSHIP"]["value"] is not None
                for cell_map in pair_cells
            ),
            "verified_availability_count": sum(
                row["availability_feature_count"] for row in pair
            ),
            "ranked_participant_count": sum(
                1 for row in pair if row["ranked_state"] == "RANKED"
            ),
            "admitted_domain_count": sum(
                1
                for cell_map in pair_cells
                for cell in cell_map.values()
                if cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
            ),
            "candidate_only_domain_count": sum(
                1
                for cell_map in pair_cells
                for cell in cell_map.values()
                if cell["admission_disposition"] == CANDIDATE_ONLY_NOT_CONSUMED
            ),
            "missing_domain_count": sum(
                1
                for cell_map in pair_cells
                for cell in cell_map.values()
                if cell["admission_disposition"]
                in (
                    "SOURCE_EVIDENCE_ABSENT",
                    "TEMPORALLY_INELIGIBLE",
                    "UNRESOLVED_ENTITY",
                )
            ),
            "candidate_states": {
                row["candidate_id"]: row["adequacy_state"] for row in contest_candidates
            },
            "ready_candidate_ids": sorted(
                row["candidate_id"]
                for row in contest_candidates
                if row["adequacy_state"] == READY
            ),
            "forecast_input_readiness": contest_state,
            "adequacy_state": contest_state,
            "forecast_produced": False,
        }
        contest_row["contest_adequacy_identity"] = stable_hash(contest_row)
        contest_rows.append(contest_row)

    return contest_rows, candidate_rows


def summarize(
    contest_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_candidate: dict[str, dict[str, int]] = {}
    for row in candidate_rows:
        bucket = by_candidate.setdefault(
            row["candidate_id"], {state: 0 for state in ADEQUACY_STATES}
        )
        bucket[row["adequacy_state"]] += 1
    return {
        "contest_count": len(contest_rows),
        "candidate_row_count": len(candidate_rows),
        "team_row_count": len(spine_rows),
        "contest_adequacy_counts": {
            state: sum(1 for row in contest_rows if row["adequacy_state"] == state)
            for state in ADEQUACY_STATES
        },
        "candidate_adequacy_counts": by_candidate,
        "coverage_by_requested_date": dict(
            sorted(Counter(row["requested_game_date"] for row in contest_rows).items())
        ),
        "coverage_by_subdivision_pair": dict(
            sorted(
                Counter("+".join(row["subdivisions"]) for row in contest_rows).items()
            )
        ),
        "coverage_by_conference": dict(
            sorted(
                Counter(
                    conference
                    for row in contest_rows
                    for conference in row["conferences"]
                ).items()
            )
        ),
        "coverage_by_contest_disposition": dict(
            sorted(Counter(row["contest_disposition"] for row in contest_rows).items())
        ),
        "coverage_by_site_state": dict(
            sorted(Counter(row["site_state"] for row in contest_rows).items())
        ),
        "contests_with_weather": sum(
            1 for row in contest_rows if row["weather_available"]
        ),
        "contests_with_roster_membership": sum(
            1 for row in contest_rows if row["roster_membership_available"]
        ),
        "contests_with_a_ranked_participant": sum(
            1 for row in contest_rows if row["ranked_participant_count"] > 0
        ),
        "contests_with_unsupported_entities": sum(
            1 for row in contest_rows if row["unsupported_entity_count"] > 0
        ),
        "contests_with_conflicts": sum(
            1 for row in contest_rows if row["conflict_count"] > 0
        ),
        "temporal_exclusion_total": sum(
            row["temporal_exclusion_count"] for row in contest_rows
        ),
        "verified_availability_total": sum(
            row["verified_availability_count"] for row in contest_rows
        ),
    }


def compare_contest_to_national_distribution(
    *,
    contest_row: Mapping[str, Any],
    contest_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Report one contest against the national distribution without correcting it."""

    national_admitted = [row["admitted_domain_count"] for row in contest_rows]
    ranked = sorted(national_admitted)
    position = sum(
        1 for value in ranked if value < contest_row["admitted_domain_count"]
    )
    return {
        "ncaa_contest_id": contest_row["ncaa_contest_id"],
        "contest_identity": contest_row["contest_identity"],
        "adequacy_state": contest_row["adequacy_state"],
        "candidate_states": dict(contest_row["candidate_states"]),
        "admitted_domain_count": contest_row["admitted_domain_count"],
        "national_admitted_domain_count_min": min(national_admitted),
        "national_admitted_domain_count_max": max(national_admitted),
        "national_admitted_domain_count_mean": round(
            sum(national_admitted) / len(national_admitted), 6
        ),
        "national_percentile_position": round(position / len(national_admitted), 6),
        "matches_national_modal_state": contest_row["adequacy_state"]
        == Counter(row["adequacy_state"] for row in contest_rows).most_common(1)[0][0],
        "candidate_rows": [
            {
                "candidate_id": row["candidate_id"],
                "adequacy_state": row["adequacy_state"],
                "missing_required_domains": row["missing_required_domains"],
            }
            for row in candidate_rows
            if row["ncaa_contest_id"] == contest_row["ncaa_contest_id"]
        ],
        "custom_correction_applied": False,
        "hardcoded_feature_applied": False,
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    contest_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
    focus_report: Mapping[str, Any] | None,
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
    payloads: Sequence[Mapping[str, Any]],
    bound_predecessors: Mapping[str, Any],
    execution_time: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_FEATURE_COVERAGE_ADEQUACY_GATE",
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
        "adequacy_states": list(ADEQUACY_STATES),
        "candidate_feature_requirements": [
            dict(requirement)
            for requirement in contract["candidate_feature_requirements"]
        ],
        "checkpoints": dict(contract["checkpoints"]),
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
                {
                    "name": payload["name"],
                    "rows": payload["rows"],
                    "sha256": payload["sha256"],
                }
                for payload in payloads
            ]
        ),
        "summary": summarize(contest_rows, candidate_rows, spine_rows),
        "focus_contest_report": dict(focus_report) if focus_report else None,
        "authority": {**dict(contract["authority"]), "protected_lane_admission": False},
        "predecessor_identity": str(bound_predecessors["feature_spine_gate_identity"]),
        "tamu_policy": dict(contract["tamu_policy"]),
        "scientific_nonclaims": {
            "bas_or_aggie_excess": False,
            "calibration_or_performance_claim": False,
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
    payloads: Sequence[Mapping[str, Any]],
    bound_predecessors: Mapping[str, Any],
    execution_time: datetime,
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_FEATURE_COVERAGE_ADEQUACY_MANIFEST",
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "season": int(contract["season"]),
        "summary": dict(summary),
        "bound_predecessors": dict(bound_predecessors),
        "payloads": [dict(payload) for payload in payloads],
        "authority": dict(contract["authority"]),
        "execution_time_utc": iso_utc(execution_time),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_artifact(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Revalidate the adequacy gate against the spine evidence without writing."""

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
    if gate.get("checkpoints") != dict(contract["checkpoints"]):
        findings.append("gate checkpoints disagree with the contract")
    if gate["checkpoints"].get("t_minus_24h_state") != "OPEN":
        findings.append("gate closed the T-24H checkpoint")
    if gate["checkpoints"].get("t_minus_90m_state") != "OPEN":
        findings.append("gate closed the T-90M checkpoint")

    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        return {"result": "FAIL", "findings": findings + ["dataset manifest is absent"]}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("dataset manifest hash drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

    payload_rows: dict[str, list[dict[str, Any]]] = {}
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        payload_rows[payload["name"]] = read_jsonl(payload_path)

    contest_rows = payload_rows.get(CONTEST_PAYLOAD_NAME, [])
    candidate_rows = payload_rows.get(CANDIDATE_PAYLOAD_NAME, [])
    for row in contest_rows:
        if row["adequacy_state"] not in ADEQUACY_STATES:
            findings.append(
                f"contest {row['ncaa_contest_id']} carries an undeclared adequacy state"
            )
        if row["forecast_produced"]:
            findings.append(f"contest {row['ncaa_contest_id']} claimed a forecast")
        if row["adequacy_state"] == READY and row["unsupported_entity_count"]:
            findings.append(
                f"contest {row['ncaa_contest_id']} is ready with an unsupported entity"
            )
    for row in candidate_rows:
        if row["adequacy_state"] == READY and row["missing_required_count"]:
            findings.append(
                f"candidate {row['candidate_id']} is ready while missing a required domain"
            )
        if (
            row["admitted_required_count"] + row["missing_required_count"]
            != row["required_feature_count"]
        ):
            findings.append(
                f"candidate {row['candidate_id']} coverage counts do not reconcile"
            )

    if gate["authority"].get("forecast_produced") is not False:
        findings.append("gate claimed a forecast")
    if gate["tamu_policy"].get("tamu_specific_adjustment_applied") is not False:
        findings.append("gate claimed a Texas A&M specific adjustment")
    focus = gate.get("focus_contest_report")
    if focus and (
        focus.get("custom_correction_applied") or focus.get("hardcoded_feature_applied")
    ):
        findings.append("focus contest report applied a custom correction")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "summary": gate.get("summary"),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }


__all__ = [
    "ADEQUACY_STATES",
    "CANDIDATE_PAYLOAD_NAME",
    "CONTEST_PAYLOAD_NAME",
    "CONTRACT_RELATIVE",
    "GATE_RELATIVE",
    "PASS_RESULT",
    "PAYLOAD_SLUG",
    "Week1AdequacyViolation",
    "build_adequacy_rows",
    "build_gate",
    "compare_contest_to_national_distribution",
    "dataset_manifest",
    "load_contract",
    "read_jsonl",
    "summarize",
    "validate_artifact",
    "validate_contract",
]
