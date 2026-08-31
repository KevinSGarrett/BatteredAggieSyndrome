from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# Cycle #24 semantic successor to the Cycle #23 Week 1 current-feature spine.
#
# The predecessor is bound, never rewritten. Six semantic defects are corrected
# here, and each correction is emitted as an explicit, independently checkable
# record rather than as a silent change of meaning:
#
#   A  VENUE_AND_SITE is split into SITE_ORIENTATION, VENUE_IDENTITY and
#      VENUE_COORDINATES, so an unknown venue can no longer ride into an
#      "admitted" state on the back of a known kickoff time.
#   B  "no knowable prior" becomes an exact prior-state classification. Allowed
#      through-2023 history is knowable and stale, not absent.
#   C  PARTIAL_MODEL_INPUT stays a diagnostic state but becomes terminal at
#      forecast time.
#   D  the ambiguous pair-level admitted_domain_count is replaced by five
#      unambiguous counters.
#   E  the leakage invariant is restated as "no target outcome enters its own
#      feature row" rather than the false "no outcome field exists anywhere".
#   F  the Week Zero report language is corrected to two scored candidates.

SCHEMA_VERSION = "aggie.shadow.week1_2026_spine_semantic_successor.v1"
CONTRACT_ID = "CYCLE24-WEEK1-2026-SPINE-SEMANTIC-SUCCESSOR-V1"
JIRA_KEY = "BAT-682"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-SPINE-SEMANTIC-SUCCESSOR-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_SPINE_SEMANTIC_SUCCESSOR_AND_FORECAST_READINESS_CORRECTION"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_SPINE_SEMANTIC_SUCCESSOR"

CONTRACT_RELATIVE = "configs/week1_2026_spine_semantic_successor_contract.json"
GATE_RELATIVE = "artifacts/spine/week1_2026_spine_semantic_successor_gate.json"
PAYLOAD_SLUG = "week1_2026_spine_semantic_successor"

CELL_PAYLOAD_NAME = "week1_2026_successor_admission_cells.jsonl"
ROW_PAYLOAD_NAME = "week1_2026_successor_spine_rows.jsonl"
PAIR_PAYLOAD_NAME = "week1_2026_successor_pair_counts.jsonl"
READINESS_PAYLOAD_NAME = "week1_2026_successor_forecast_readiness.jsonl"
CORRECTION_PAYLOAD_NAME = "week1_2026_semantic_correction_records.jsonl"

# ---------------------------------------------------------------------------
# successor domain vocabulary
# ---------------------------------------------------------------------------

TEAM_STRENGTH_PRIOR = "TEAM_STRENGTH_PRIOR"
WEEK_ZERO_CURRENT_RESULT = "WEEK_ZERO_CURRENT_RESULT"
CURRENT_RANKING = "CURRENT_RANKING"
CONFERENCE_AND_SUBDIVISION = "CONFERENCE_AND_SUBDIVISION"
SITE_ORIENTATION = "SITE_ORIENTATION"
VENUE_IDENTITY = "VENUE_IDENTITY"
VENUE_COORDINATES = "VENUE_COORDINATES"
WEATHER_VINTAGE = "WEATHER_VINTAGE"
ROSTER_MEMBERSHIP = "ROSTER_MEMBERSHIP"
PREGAME_AVAILABILITY = "PREGAME_AVAILABILITY"

SUCCESSOR_DOMAINS = (
    TEAM_STRENGTH_PRIOR,
    WEEK_ZERO_CURRENT_RESULT,
    CURRENT_RANKING,
    CONFERENCE_AND_SUBDIVISION,
    SITE_ORIENTATION,
    VENUE_IDENTITY,
    VENUE_COORDINATES,
    WEATHER_VINTAGE,
    ROSTER_MEMBERSHIP,
    PREGAME_AVAILABILITY,
)

PREDECESSOR_COMPOSITE_DOMAIN = "VENUE_AND_SITE"
SPLIT_DOMAINS = (SITE_ORIENTATION, VENUE_IDENTITY, VENUE_COORDINATES)

ADMITTED_PROSPECTIVE_PREKICKOFF = "ADMITTED_PROSPECTIVE_PREKICKOFF"
CANDIDATE_ONLY_NOT_CONSUMED = "CANDIDATE_ONLY_NOT_CONSUMED"
TEMPORALLY_INELIGIBLE = "TEMPORALLY_INELIGIBLE"
SOURCE_EVIDENCE_ABSENT = "SOURCE_EVIDENCE_ABSENT"
UNRESOLVED_ENTITY = "UNRESOLVED_ENTITY"
QUARANTINED_CONFLICT = "QUARANTINED_CONFLICT"
NOT_APPLICABLE = "NOT_APPLICABLE"

ADMISSION_DISPOSITIONS = (
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CANDIDATE_ONLY_NOT_CONSUMED,
    TEMPORALLY_INELIGIBLE,
    SOURCE_EVIDENCE_ABSENT,
    UNRESOLVED_ENTITY,
    QUARANTINED_CONFLICT,
    NOT_APPLICABLE,
)

SITE_ORIENTATION_VALUES = ("HOME", "AWAY", "NEUTRAL", "UNKNOWN")

# ---------------------------------------------------------------------------
# corrected prior vocabulary
# ---------------------------------------------------------------------------

RETIRED_PRIOR_CLASSIFICATION = (
    "NO_PRIOR_STRENGTH_VALUE_IS_KNOWABLE_FOR_THIS_TEAM_BEFORE_KICKOFF"
)

CURRENT_PRIOR_NOT_MATERIALIZED = "CURRENT_2026_FROZEN_PRIOR_NOT_MATERIALIZED"
STALE_ALLOWED_HISTORY_AVAILABLE = "STALE_ALLOWED_HISTORY_AVAILABLE"
COLD_START_INSUFFICIENT_TEAM_HISTORY = "COLD_START_INSUFFICIENT_TEAM_HISTORY"
PRIOR_UNRESOLVED_ENTITY = "UNRESOLVED_ENTITY"
CURRENT_PRIOR_ADMITTED = "CURRENT_PRIOR_ADMITTED"
CURRENT_PRIOR_QUARANTINED = "CURRENT_PRIOR_QUARANTINED"

PRIOR_CLASSIFICATIONS = (
    CURRENT_PRIOR_NOT_MATERIALIZED,
    STALE_ALLOWED_HISTORY_AVAILABLE,
    COLD_START_INSUFFICIENT_TEAM_HISTORY,
    PRIOR_UNRESOLVED_ENTITY,
    CURRENT_PRIOR_ADMITTED,
    CURRENT_PRIOR_QUARANTINED,
)

# ---------------------------------------------------------------------------
# forecast readiness vocabulary
# ---------------------------------------------------------------------------

FORECAST_READY = "FORECAST_READY_ALL_REQUIRED_FEATURES_ADMITTED"
ABSTAIN_MISSING_REQUIRED_FEATURES = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_UNSUPPORTED_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"
READINESS_QUARANTINED_CONFLICT = "QUARANTINED_CONFLICT"
NOT_IN_MODEL_TARGET = "NOT_IN_MODEL_TARGET"

READINESS_STATES = (
    FORECAST_READY,
    ABSTAIN_MISSING_REQUIRED_FEATURES,
    ABSTAIN_UNSUPPORTED_ENTITY,
    READINESS_QUARANTINED_CONFLICT,
    NOT_IN_MODEL_TARGET,
)

PARTIAL_MODEL_INPUT = "PARTIAL_MODEL_INPUT"

CORRECT_LEAKAGE_INVARIANT = "NO_TARGET_CONTEST_OUTCOME_ENTERS_ITS_OWN_FEATURE_ROW"

SPINE_ROW_UNSUPPORTED_ENTITY = "SPINE_ROW_UNSUPPORTED_ENTITY"
ADMITTED_MODEL_ELIGIBLE = "ADMITTED_MODEL_ELIGIBLE"

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "bound_predecessors",
    "candidate_feature_requirements",
    "classification",
    "contract_id",
    "contract_sha256",
    "corrections",
    "count_semantics",
    "dataset_identity",
    "decision_unit",
    "domain_split",
    "focus_contest_report",
    "forecast_readiness",
    "jira_key",
    "lane",
    "local_issue_id",
    "manifest",
    "parent_jira_key",
    "payloads",
    "prior_semantics",
    "protected_lane",
    "record_hashes",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "season",
    "summary",
    "tamu_policy",
    "week_label",
)


class SemanticSuccessorViolation(ValueError):
    """Raised when a successor invariant is violated."""


# ---------------------------------------------------------------------------
# io helpers
# ---------------------------------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [field for field in GATE_IDENTITY_FIELDS if field not in gate]
    if missing:
        raise SemanticSuccessorViolation(f"gate is missing identity fields: {missing}")
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise SemanticSuccessorViolation("semantic successor contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise SemanticSuccessorViolation("semantic successor schema drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise SemanticSuccessorViolation("protected lane must remain blocked")
    if contract.get("lane") != LANE:
        raise SemanticSuccessorViolation("successor lane drift")
    if contract.get("local_issue_id") != LOCAL_ISSUE_ID:
        raise SemanticSuccessorViolation("local issue identity drift")
    if contract.get("parent_jira_key") != PARENT_JIRA_KEY:
        raise SemanticSuccessorViolation("parent issue drift")
    if contract.get("jira_key") != JIRA_KEY:
        raise SemanticSuccessorViolation("owning issue drift")

    authority = contract["authority"]
    for key in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "forecast_publication",
        "forecast_produced",
        "canonical_entity_mutation",
        "immutable_raw_capture_mutation",
        "protected_split_registry_mutation",
        "judging_rule_seal_mutation",
    ):
        if authority.get(key) is not False:
            raise SemanticSuccessorViolation(f"successor authority is open: {key}")
    for key in ("prospective_shadow_observation", "semantic_successor_authoring"):
        if authority.get(key) is not True:
            raise SemanticSuccessorViolation(f"successor authority is missing: {key}")

    policy = contract["predecessor_policy"]
    if policy.get("predecessor_artifacts_are_rewritten_in_place") is not False:
        raise SemanticSuccessorViolation(
            "the predecessor must not be rewritten in place"
        )
    if policy.get("predecessor_gate_identities_are_bound") is not True:
        raise SemanticSuccessorViolation(
            "the predecessor gate identities must be bound"
        )
    if policy.get("done_issues_reopened") is not False:
        raise SemanticSuccessorViolation("Done issues must not be reopened")

    split = contract["domain_split"]
    if tuple(split["successor_domain_set"]) != SUCCESSOR_DOMAINS:
        raise SemanticSuccessorViolation("successor domain set drift")
    if split["predecessor_domain"] != PREDECESSOR_COMPOSITE_DOMAIN:
        raise SemanticSuccessorViolation("predecessor composite domain drift")
    by_domain = {item["domain"]: item for item in split["successor_domains"]}
    if (
        by_domain[VENUE_IDENTITY].get("may_be_admitted_from_site_orientation_alone")
        is not False
    ):
        raise SemanticSuccessorViolation(
            "venue identity must not be admissible from site orientation alone"
        )
    if by_domain[VENUE_COORDINATES].get("may_be_admitted_from_inference") is not False:
        raise SemanticSuccessorViolation(
            "venue coordinates must not be admissible from inference"
        )
    if (
        by_domain[SITE_ORIENTATION].get("may_be_admitted_without_venue_identity")
        is not True
    ):
        raise SemanticSuccessorViolation(
            "site orientation must be admissible on its own"
        )
    weather = split["weather_rule"]
    if (
        weather.get("weather_may_become_admitted_model_input_from_inferred_coordinates")
        is not False
    ):
        raise SemanticSuccessorViolation(
            "weather must not be admitted from inferred coordinates"
        )

    prior = contract["prior_semantics"]
    if prior.get("retired_classification") != RETIRED_PRIOR_CLASSIFICATION:
        raise SemanticSuccessorViolation("retired prior classification drift")
    if tuple(prior["successor_classifications"]) != PRIOR_CLASSIFICATIONS:
        raise SemanticSuccessorViolation("successor prior classification drift")
    if prior.get("stale_history_is_current_prior") is not False:
        raise SemanticSuccessorViolation(
            "stale history must not be represented as current"
        )
    if prior.get("stale_history_admissible_as_current_model_input") is not False:
        raise SemanticSuccessorViolation(
            "stale history must not be admitted as current input"
        )

    readiness = contract["forecast_readiness"]
    if readiness.get("partial_model_input_may_emit_a_forecast") is not False:
        raise SemanticSuccessorViolation("PARTIAL_MODEL_INPUT must not emit a forecast")
    if readiness.get("partial_model_input_forecast_time_mapping") != (
        ABSTAIN_MISSING_REQUIRED_FEATURES
    ):
        raise SemanticSuccessorViolation(
            "PARTIAL_MODEL_INPUT must map to a missing-feature abstention"
        )
    if tuple(readiness["readiness_states"]) != READINESS_STATES:
        raise SemanticSuccessorViolation("readiness state vocabulary drift")

    wording = contract["outcome_wording"]
    if wording.get("correct_invariant") != CORRECT_LEAKAGE_INVARIANT:
        raise SemanticSuccessorViolation("leakage invariant wording drift")
    if wording.get("week_zero_finals_legitimately_appear_as_prior_results") is not True:
        raise SemanticSuccessorViolation(
            "Week Zero finals legitimately appear as prior results for later targets"
        )

    week_zero = contract["week_zero_report_correction"]
    if int(week_zero["scored_candidate_count"]) != 2:
        raise SemanticSuccessorViolation("Week Zero scored-candidate count must be two")
    if int(week_zero["eligible_opportunities_per_candidate"]) != 6:
        raise SemanticSuccessorViolation("Week Zero opportunity count drift")
    if int(week_zero["pooled_candidate_rows"]) != 12:
        raise SemanticSuccessorViolation("Week Zero pooled candidate row count drift")
    if week_zero.get("scientific_artifact_identity_rewritten") is not False:
        raise SemanticSuccessorViolation(
            "no scientific artifact identity may be rewritten"
        )

    audit = contract["jira_comment_audit"]
    if audit.get("reconstruct_body_from_model_memory") is not False:
        raise SemanticSuccessorViolation(
            "a deleted comment body must not be reconstructed"
        )
    if audit.get("post_second_cycle23_parent_comment") is not False:
        raise SemanticSuccessorViolation(
            "a second Cycle #23 parent comment must not be posted"
        )
    if audit.get("cycle23_comment_14718_mutated") is not False:
        raise SemanticSuccessorViolation("Cycle #23 comment 14718 must not be mutated")

    checkpoints = contract["checkpoints"]
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if checkpoints.get(key) != "OPEN":
            raise SemanticSuccessorViolation(f"{key} must remain OPEN in this cycle")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if checkpoints.get(key) is not False:
            raise SemanticSuccessorViolation(f"forbidden checkpoint behaviour: {key}")

    tamu = contract["tamu_policy"]
    for key in (
        "tamu_specific_adjustment_applied",
        "custom_correction_applied",
    ):
        if tamu.get(key) is not False:
            raise SemanticSuccessorViolation(
                f"an A&M-specific adjustment is declared: {key}"
            )

    declared = [
        item["candidate_id"] for item in contract["candidate_feature_requirements"]
    ]
    if len(declared) != len(set(declared)):
        raise SemanticSuccessorViolation("duplicate candidate requirement rows")
    if len(declared) != 5:
        raise SemanticSuccessorViolation(
            "the Cycle #24 candidate set is exactly five candidates"
        )
    for item in contract["candidate_feature_requirements"]:
        unknown = set(item["required_domains"]) | set(item["optional_domains"])
        unknown -= set(SUCCESSOR_DOMAINS)
        if unknown:
            raise SemanticSuccessorViolation(
                f"unknown successor domain requested: {sorted(unknown)}"
            )
        if PREDECESSOR_COMPOSITE_DOMAIN in item["required_domains"]:
            raise SemanticSuccessorViolation(
                "a successor candidate must not require the retired composite domain"
            )
        if VENUE_IDENTITY in item["required_domains"]:
            raise SemanticSuccessorViolation(
                "no Cycle #24 candidate consumes an authoritative venue identity as a required input"
            )
    return contract


# ---------------------------------------------------------------------------
# predecessor loading
# ---------------------------------------------------------------------------


def _payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise SemanticSuccessorViolation(f"predecessor payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Resolve every pinned predecessor surface and verify its bound identity."""
    contract = load_contract(repo_root)
    sources = contract["sources"]

    gates: dict[str, dict[str, Any]] = {}
    for name in (
        "feature_spine",
        "feature_coverage_adequacy",
        "schedule_identity",
        "frozen_candidates",
        "week_zero_scoring",
    ):
        source = sources[name]
        path = repo_root / source["gate_relative_path"]
        if not path.is_file():
            raise SemanticSuccessorViolation(
                f"missing predecessor gate: {source['gate_relative_path']}"
            )
        gate = read_json(path)
        expected = source["gate_identity"]
        if gate.get("gate_identity") != expected:
            raise SemanticSuccessorViolation(
                f"predecessor gate identity drift for {name}: {gate.get('gate_identity')} != {expected}"
            )
        gates[name] = gate

    spine_gate = gates["feature_spine"]
    spine_rows = _payload_rows(
        data_root, spine_gate, sources["feature_spine"]["row_payload_name"]
    )
    spine_cells = _payload_rows(
        data_root, spine_gate, sources["feature_spine"]["cell_payload_name"]
    )

    matrix_source = sources["chronological_development_matrix"]
    matrix_gate_path = repo_root / matrix_source["gate_relative_path"]
    if sha256_file(matrix_gate_path) != matrix_source["gate_sha256"]:
        raise SemanticSuccessorViolation("chronological development matrix gate drift")
    matrix_gate = read_json(matrix_gate_path)
    if matrix_gate["dataset_identity"] != matrix_source["dataset_identity"]:
        raise SemanticSuccessorViolation(
            "chronological development matrix dataset drift"
        )
    chronology = matrix_gate["chronology"]
    if int(chronology["development_evaluation_season"]) != int(
        matrix_source["allowed_season_max"]
    ):
        raise SemanticSuccessorViolation("allowed evidence window drift")
    if sorted(chronology["excluded_protected_seasons"]) != sorted(
        matrix_source["excluded_protected_seasons"]
    ):
        raise SemanticSuccessorViolation("protected seasons are no longer excluded")
    matrix_rows = _payload_rows(
        data_root, matrix_gate, matrix_source["feature_payload_name"]
    )
    protected = {
        int(row["season"])
        for row in matrix_rows
        if int(row["season"]) in set(matrix_source["excluded_protected_seasons"])
    }
    if protected:
        raise SemanticSuccessorViolation(
            f"protected seasons present in allowed evidence: {protected}"
        )

    return {
        "contract": contract,
        "gates": gates,
        "matrix_gate": matrix_gate,
        "spine_rows": spine_rows,
        "spine_cells": spine_cells,
        "matrix_rows": matrix_rows,
    }


def team_history_index(
    matrix_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Count allowed through-2023 chronological evidence per canonical team."""
    counts: defaultdict[str, int] = defaultdict(int)
    latest_season: dict[str, int] = {}
    for row in matrix_rows:
        team = row["canonical_team_id"]
        season = int(row["season"])
        counts[team] += 1
        if season > latest_season.get(team, 0):
            latest_season[team] = season
    return {
        team: {
            "allowed_history_row_count": counts[team],
            "latest_allowed_season": latest_season[team],
        }
        for team in counts
    }


# ---------------------------------------------------------------------------
# correction A: split the composite venue/site domain
# ---------------------------------------------------------------------------


def split_site_and_venue_cells(cell: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Turn one predecessor VENUE_AND_SITE cell into three successor cells."""
    if cell["domain"] != PREDECESSOR_COMPOSITE_DOMAIN:
        raise SemanticSuccessorViolation("only the composite domain may be split")
    value = cell.get("value") or {}
    orientation = value.get("site_orientation") or "UNKNOWN"
    if orientation not in SITE_ORIENTATION_VALUES:
        orientation = "UNKNOWN"
    venue_identity = value.get("venue_identity")
    venue_state = value.get("venue_identity_state") or SOURCE_EVIDENCE_ABSENT
    candidate_only_attributes = bool(value.get("venue_attributes_are_candidate_only"))

    base = {
        key: cell[key]
        for key in (
            "canonical_team_id",
            "contest_identity",
            "ncaa_contest_id",
            "orientation",
            "row_identity",
            "snapshot_issuance_utc",
            "source_id",
            "source_team_id",
            "target_kickoff_bound_utc",
            "observed_at_utc",
            "published_at_utc",
            "raw_capture_sha256",
            "source_observation_identity",
        )
        if key in cell
    }

    site_cell = {
        **base,
        "domain": SITE_ORIENTATION,
        "admission_disposition": (
            ADMITTED_PROSPECTIVE_PREKICKOFF
            if orientation != "UNKNOWN"
            else SOURCE_EVIDENCE_ABSENT
        ),
        "conflict_state": cell.get("conflict_state", "NONE"),
        "known_at_classification": "OFFICIAL_PUBLISHED_SITE_ORIENTATION_OBSERVED_AT_CAPTURE",
        "missingness_reason": None
        if orientation != "UNKNOWN"
        else "SITE_ORIENTATION_NOT_PUBLISHED",
        "value": {
            "site_orientation": orientation,
            "site_state": value.get("site_state"),
            "neutral_site_text": value.get("neutral_site_text", ""),
            "derived_from_predecessor_domain": PREDECESSOR_COMPOSITE_DOMAIN,
        },
        "successor_of": PREDECESSOR_COMPOSITE_DOMAIN,
    }

    identity_admitted = (
        venue_identity is not None and venue_state != SOURCE_EVIDENCE_ABSENT
    )
    identity_cell = {
        **base,
        "domain": VENUE_IDENTITY,
        "admission_disposition": (
            ADMITTED_PROSPECTIVE_PREKICKOFF
            if identity_admitted
            else SOURCE_EVIDENCE_ABSENT
        ),
        "conflict_state": cell.get("conflict_state", "NONE"),
        "known_at_classification": (
            "AUTHORITATIVE_VENUE_IDENTITY_OBSERVED_AT_CAPTURE"
            if identity_admitted
            else "NO_AUTHORITATIVE_VENUE_IDENTITY_IN_SOURCE_CAPTURE"
        ),
        "missingness_reason": None
        if identity_admitted
        else "VENUE_IDENTITY_ABSENT_FROM_SOURCE",
        "value": {
            "venue_identity": venue_identity,
            "venue_identity_state": venue_state
            if identity_admitted
            else SOURCE_EVIDENCE_ABSENT,
            "admitted_from_site_orientation_alone": False,
            "derived_from_predecessor_domain": PREDECESSOR_COMPOSITE_DOMAIN,
        },
        "successor_of": PREDECESSOR_COMPOSITE_DOMAIN,
    }

    # Coordinates can never outrank the venue identity that would justify them.
    if identity_admitted and not candidate_only_attributes:
        coordinate_disposition = ADMITTED_PROSPECTIVE_PREKICKOFF
        coordinate_state = "AUTHORITATIVE_COORDINATES"
        coordinate_reason = None
    elif candidate_only_attributes:
        coordinate_disposition = CANDIDATE_ONLY_NOT_CONSUMED
        coordinate_state = "CANDIDATE_ONLY"
        coordinate_reason = "VENUE_ATTRIBUTES_ARE_CANDIDATE_ONLY"
    else:
        coordinate_disposition = SOURCE_EVIDENCE_ABSENT
        coordinate_state = SOURCE_EVIDENCE_ABSENT
        coordinate_reason = "NO_AUTHORITATIVE_VENUE_COORDINATE_SOURCE"

    coordinate_cell = {
        **base,
        "domain": VENUE_COORDINATES,
        "admission_disposition": coordinate_disposition,
        "conflict_state": cell.get("conflict_state", "NONE"),
        "known_at_classification": (
            "AUTHORITATIVE_VENUE_COORDINATES_OBSERVED_AT_CAPTURE"
            if coordinate_disposition == ADMITTED_PROSPECTIVE_PREKICKOFF
            else "NO_AUTHORITATIVE_VENUE_COORDINATE_EVIDENCE"
        ),
        "missingness_reason": coordinate_reason,
        "value": {
            "venue_coordinate_state": coordinate_state,
            "latitude": None,
            "longitude": None,
            "requires_authoritative_venue_identity": True,
            "authoritative_venue_identity_present": identity_admitted,
            "admitted_from_inference": False,
            "derived_from_predecessor_domain": PREDECESSOR_COMPOSITE_DOMAIN,
        },
        "successor_of": PREDECESSOR_COMPOSITE_DOMAIN,
    }
    return [site_cell, identity_cell, coordinate_cell]


def enforce_weather_rule(
    cells_by_team_contest: Mapping[tuple[str, str], Mapping[str, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Demote any weather cell whose coordinate authority is not established."""
    demotions: list[dict[str, Any]] = []
    for key, by_domain in cells_by_team_contest.items():
        weather = by_domain.get(WEATHER_VINTAGE)
        if weather is None:
            continue
        coordinates = by_domain.get(VENUE_COORDINATES)
        coordinate_admitted = (
            coordinates is not None
            and coordinates["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
        )
        if (
            weather["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
            and not coordinate_admitted
        ):
            demotions.append(
                {
                    "contest_identity": key[0],
                    "canonical_team_id": key[1],
                    "from_disposition": ADMITTED_PROSPECTIVE_PREKICKOFF,
                    "to_disposition": CANDIDATE_ONLY_NOT_CONSUMED,
                    "reason": "WEATHER_REQUIRES_AUTHORITATIVE_VENUE_COORDINATES",
                }
            )
    return demotions


def build_successor_cells(
    spine_cells: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Rebuild the admission-cell surface over the successor domain vocabulary."""
    successor: list[dict[str, Any]] = []
    for cell in spine_cells:
        if cell["domain"] == PREDECESSOR_COMPOSITE_DOMAIN:
            successor.extend(split_site_and_venue_cells(cell))
            continue
        carried = dict(cell)
        carried["successor_of"] = cell["domain"]
        successor.append(carried)

    index: defaultdict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for cell in successor:
        index[(cell["contest_identity"], cell["canonical_team_id"])][cell["domain"]] = (
            cell
        )

    demotions = enforce_weather_rule(index)
    demoted = {
        (item["contest_identity"], item["canonical_team_id"]) for item in demotions
    }
    for cell in successor:
        if (
            cell["domain"] == WEATHER_VINTAGE
            and (
                cell["contest_identity"],
                cell["canonical_team_id"],
            )
            in demoted
        ):
            cell["admission_disposition"] = CANDIDATE_ONLY_NOT_CONSUMED
            cell["missingness_reason"] = (
                "WEATHER_REQUIRES_AUTHORITATIVE_VENUE_COORDINATES"
            )

    for cell in successor:
        if cell["domain"] not in SUCCESSOR_DOMAINS:
            raise SemanticSuccessorViolation(
                f"unknown successor domain emitted: {cell['domain']}"
            )
        if cell["admission_disposition"] not in ADMISSION_DISPOSITIONS:
            raise SemanticSuccessorViolation(
                f"unknown admission disposition: {cell['admission_disposition']}"
            )
        if cell["domain"] == VENUE_IDENTITY:
            value = cell["value"]
            if (
                cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
                and value.get("venue_identity") is None
            ):
                raise SemanticSuccessorViolation(
                    "venue identity admitted without an authoritative venue id"
                )
        if cell["domain"] == VENUE_COORDINATES:
            value = cell["value"]
            if cell[
                "admission_disposition"
            ] == ADMITTED_PROSPECTIVE_PREKICKOFF and not value.get(
                "authoritative_venue_identity_present"
            ):
                raise SemanticSuccessorViolation(
                    "venue coordinates admitted without an authoritative venue identity"
                )

    successor.sort(
        key=lambda row: (
            row["contest_identity"],
            row["orientation"],
            row["canonical_team_id"] or "",
            row["domain"],
        )
    )
    return successor, demotions


# ---------------------------------------------------------------------------
# correction B: exact prior classification
# ---------------------------------------------------------------------------


def classify_prior(
    *,
    spine_row: Mapping[str, Any],
    prior_cell: Mapping[str, Any] | None,
    history: Mapping[str, Mapping[str, Any]],
    minimum_games: int,
) -> dict[str, Any]:
    """State exactly why a current prior is unavailable, never that none is knowable.

    The classification keys on this row's own canonical identity. A resolved team
    that merely shares a contest with an unresolved opponent still has knowable
    history, so contest-level blocking is reported separately rather than being
    folded into this team's prior state.
    """
    team = spine_row.get("canonical_team_id")
    if not team or spine_row.get("team_identity_state") == "UNRESOLVED_SOURCE_ENTITY":
        return {
            "classification": PRIOR_UNRESOLVED_ENTITY,
            "allowed_history_row_count": 0,
            "latest_allowed_season": None,
            "current_frozen_prior_materialized": False,
            "stale_history_available": False,
            "retired_classification_asserted": False,
            "contest_blocked_by_an_unresolved_participant": spine_row.get(
                "spine_row_state"
            )
            == SPINE_ROW_UNSUPPORTED_ENTITY,
            "reason": "THIS_ROWS_PARTICIPANT_IDENTITY_IS_UNRESOLVED",
        }

    blocked = spine_row.get("spine_row_state") == SPINE_ROW_UNSUPPORTED_ENTITY

    if (
        prior_cell is not None
        and prior_cell["admission_disposition"] == QUARANTINED_CONFLICT
    ):
        return {
            "classification": CURRENT_PRIOR_QUARANTINED,
            "allowed_history_row_count": history.get(team, {}).get(
                "allowed_history_row_count", 0
            ),
            "latest_allowed_season": history.get(team, {}).get("latest_allowed_season"),
            "current_frozen_prior_materialized": False,
            "stale_history_available": False,
            "retired_classification_asserted": False,
            "contest_blocked_by_an_unresolved_participant": blocked,
            "reason": "CONFLICTING_PRIOR_EVIDENCE_IS_QUARANTINED",
        }

    if prior_cell is not None and prior_cell["admission_disposition"] == (
        ADMITTED_PROSPECTIVE_PREKICKOFF
    ):
        entry = history.get(team, {})
        return {
            "classification": CURRENT_PRIOR_ADMITTED,
            "allowed_history_row_count": entry.get("allowed_history_row_count", 0),
            "latest_allowed_season": entry.get("latest_allowed_season"),
            "current_frozen_prior_materialized": True,
            "stale_history_available": True,
            "retired_classification_asserted": False,
            "contest_blocked_by_an_unresolved_participant": blocked,
            "reason": "CURRENT_FROZEN_PRIOR_IS_ADMITTED",
        }

    entry = history.get(team)
    rows = int(entry["allowed_history_row_count"]) if entry else 0
    latest = entry["latest_allowed_season"] if entry else None
    if rows >= int(minimum_games):
        classification = STALE_ALLOWED_HISTORY_AVAILABLE
        reason = "ALLOWED_THROUGH_2023_HISTORY_IS_KNOWABLE_BUT_NO_CURRENT_2026_FROZEN_PRIOR_EXISTS_YET"
    elif rows > 0:
        classification = COLD_START_INSUFFICIENT_TEAM_HISTORY
        reason = "ALLOWED_HISTORY_IS_BELOW_THE_PREDECLARED_MINIMUM_SUPPORT"
    else:
        classification = CURRENT_PRIOR_NOT_MATERIALIZED
        reason = "NO_ALLOWED_CHRONOLOGICAL_HISTORY_AND_NO_CURRENT_FROZEN_PRIOR"

    return {
        "classification": classification,
        "allowed_history_row_count": rows,
        "latest_allowed_season": latest,
        "current_frozen_prior_materialized": False,
        "stale_history_available": classification == STALE_ALLOWED_HISTORY_AVAILABLE,
        "retired_classification_asserted": False,
        "contest_blocked_by_an_unresolved_participant": blocked,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# correction D: unambiguous counting
# ---------------------------------------------------------------------------


def count_team_domain_cells(
    cells: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count one oriented team row's admission cells without pair-level ambiguity."""
    admitted = [
        c
        for c in cells
        if c["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
    ]
    candidate_only = [
        c for c in cells if c["admission_disposition"] == CANDIDATE_ONLY_NOT_CONSUMED
    ]
    missing = [
        c
        for c in cells
        if c["admission_disposition"]
        in {SOURCE_EVIDENCE_ABSENT, UNRESOLVED_ENTITY, TEMPORALLY_INELIGIBLE}
    ]
    conflicted = [
        c for c in cells if c["admission_disposition"] == QUARANTINED_CONFLICT
    ]
    return {
        "admitted_team_domain_cell_count": len(admitted),
        "admitted_domains": sorted(c["domain"] for c in admitted),
        "candidate_only_team_domain_cell_count": len(candidate_only),
        "missing_team_domain_cell_count": len(missing),
        "conflicted_team_domain_cell_count": len(conflicted),
        "missing_domains": sorted(c["domain"] for c in missing),
    }


def build_pair_counts(
    *,
    successor_cells: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit the five successor counters at contest level, each explicitly named."""
    by_contest: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for cell in successor_cells:
        by_contest[cell["contest_identity"]].append(cell)

    row_by_contest: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in spine_rows:
        row_by_contest[row["contest_identity"]].append(row)

    pairs: list[dict[str, Any]] = []
    for contest_identity in sorted(by_contest):
        cells = by_contest[contest_identity]
        rows = row_by_contest.get(contest_identity, [])
        admitted = [
            c
            for c in cells
            if c["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
        ]
        by_orientation: defaultdict[str, int] = defaultdict(int)
        for cell in admitted:
            by_orientation[cell["orientation"]] += 1
        distinct = sorted({cell["domain"] for cell in admitted})
        candidate_only = sum(
            1
            for c in cells
            if c["admission_disposition"] == CANDIDATE_ONLY_NOT_CONSUMED
        )
        missing = sum(
            1
            for c in cells
            if c["admission_disposition"]
            in {SOURCE_EVIDENCE_ABSENT, UNRESOLVED_ENTITY, TEMPORALLY_INELIGIBLE}
        )
        pairs.append(
            {
                "contest_identity": contest_identity,
                "ncaa_contest_id": cells[0]["ncaa_contest_id"],
                "oriented_team_row_count": len(rows),
                "admitted_team_domain_cell_count": len(admitted),
                "distinct_admitted_domain_count": len(distinct),
                "distinct_admitted_domains": distinct,
                "admitted_domain_count_by_orientation": dict(
                    sorted(by_orientation.items())
                ),
                "candidate_only_team_domain_cell_count": candidate_only,
                "missing_team_domain_cell_count": missing,
                "retired_ambiguous_field_emitted": False,
            }
        )
    return pairs


# ---------------------------------------------------------------------------
# correction C: forecast readiness
# ---------------------------------------------------------------------------


def resolve_forecast_readiness(
    *,
    requirement: Mapping[str, Any],
    contest_cells: Sequence[Mapping[str, Any]],
    contest_rows: Sequence[Mapping[str, Any]],
    ranking_surface_complete: bool,
) -> dict[str, Any]:
    """Map coverage to a terminal forecast-time state. Partial input never forecasts."""
    candidate_id = requirement["candidate_id"]
    required = list(requirement["required_domains"])

    unsupported = [
        row
        for row in contest_rows
        if row.get("spine_row_state") == SPINE_ROW_UNSUPPORTED_ENTITY
    ]
    conflicted = [
        cell
        for cell in contest_cells
        if cell["admission_disposition"] == QUARANTINED_CONFLICT
    ]

    admitted_by_team: defaultdict[str, set[str]] = defaultdict(set)
    for cell in contest_cells:
        if cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF:
            admitted_by_team[cell["canonical_team_id"] or ""].add(cell["domain"])

    teams = [row.get("canonical_team_id") or "" for row in contest_rows]
    missing_required: list[str] = []
    for domain in required:
        for team in teams:
            if domain not in admitted_by_team.get(team, set()):
                missing_required.append(domain)
                break

    kickoff_known = all(
        row.get("kickoff_utc_conservative_lower_bound") for row in contest_rows
    )
    not_target = any(
        row.get("contest_disposition") != ADMITTED_MODEL_ELIGIBLE
        for row in contest_rows
    )

    ranking_blocked = bool(
        requirement.get("requires_complete_ranking_semantics")
        and not ranking_surface_complete
    )

    # Fail-closed precedence: identity, then conflict, then target scope, then
    # required-feature coverage. A diagnostic PARTIAL_MODEL_INPUT is never a
    # terminal forecast state.
    if unsupported:
        state = ABSTAIN_UNSUPPORTED_ENTITY
        reasons = ["PARTICIPANT_IDENTITY_IS_UNRESOLVED"]
    elif conflicted:
        state = READINESS_QUARANTINED_CONFLICT
        reasons = ["CONFLICTING_SOURCE_EVIDENCE_IS_QUARANTINED"]
    elif not_target:
        state = NOT_IN_MODEL_TARGET
        reasons = ["CONTEST_IS_NOT_MODEL_ELIGIBLE_AT_THE_ENTITY_LAYER"]
    elif not kickoff_known:
        state = ABSTAIN_MISSING_REQUIRED_FEATURES
        reasons = ["KICKOFF_BOUND_IS_NOT_ESTABLISHED"]
    elif missing_required or ranking_blocked:
        state = ABSTAIN_MISSING_REQUIRED_FEATURES
        reasons = [
            f"REQUIRED_DOMAIN_NOT_ADMITTED:{domain}"
            for domain in sorted(set(missing_required))
        ]
        if ranking_blocked:
            reasons.append(
                "RANKING_SURFACE_IS_INCOMPLETE_FOR_A_RANKING_DEPENDENT_CANDIDATE"
            )
    else:
        state = FORECAST_READY
        reasons = []

    if state not in READINESS_STATES:
        raise SemanticSuccessorViolation(f"unknown readiness state: {state}")

    return {
        "candidate_id": candidate_id,
        "contest_identity": contest_rows[0]["contest_identity"]
        if contest_rows
        else None,
        "ncaa_contest_id": contest_rows[0]["ncaa_contest_id"] if contest_rows else None,
        "forecast_readiness_state": state,
        "required_domains": required,
        "missing_required_domains": sorted(set(missing_required)),
        "requires_complete_ranking_semantics": bool(
            requirement.get("requires_complete_ranking_semantics")
        ),
        "ranking_surface_complete": ranking_surface_complete,
        "abstention_reasons": reasons,
        "partial_model_input_mapped_to_abstention": bool(missing_required)
        and state == (ABSTAIN_MISSING_REQUIRED_FEATURES),
        "forecast_emitted_by_this_gate": False,
    }


def map_partial_model_input(diagnostic_state: str) -> str:
    """The single authority for turning a diagnostic state into a forecast-time state."""
    if diagnostic_state == PARTIAL_MODEL_INPUT:
        return ABSTAIN_MISSING_REQUIRED_FEATURES
    if diagnostic_state == "READY_FOR_PREDECLARED_MODEL_INPUT":
        return FORECAST_READY
    if diagnostic_state in READINESS_STATES:
        return diagnostic_state
    raise SemanticSuccessorViolation(
        f"unmappable diagnostic adequacy state: {diagnostic_state}"
    )


# ---------------------------------------------------------------------------
# corrections E, F and G: durable correction records
# ---------------------------------------------------------------------------


def build_correction_records(
    *,
    contract: Mapping[str, Any],
    spine_gate: Mapping[str, Any],
    adequacy_gate: Mapping[str, Any],
    week_zero_gate: Mapping[str, Any],
    demotions: Sequence[Mapping[str, Any]],
    focus_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """One immutable record per Cycle #23 semantic finding."""
    split = contract["domain_split"]
    prior = contract["prior_semantics"]
    readiness = contract["forecast_readiness"]
    counts = contract["count_semantics"]
    wording = contract["outcome_wording"]
    week_zero = contract["week_zero_report_correction"]
    audit = contract["jira_comment_audit"]

    predecessor_venue = spine_gate["summary"]["domain_admission_counts"][
        PREDECESSOR_COMPOSITE_DOMAIN
    ]

    records: list[dict[str, Any]] = [
        {
            "correction_id": "CYCLE24-CORRECTION-A-SITE-VENUE-SEPARATION",
            "cycle23_finding": "SITE_ORIENTATION_AND_VENUE_IDENTITY_WERE_CONFLATED",
            "severity": "SEMANTIC_OVERSTATEMENT_OF_ADMITTED_EVIDENCE",
            "predecessor_gate_identity": spine_gate["gate_identity"],
            "predecessor_domain": PREDECESSOR_COMPOSITE_DOMAIN,
            "predecessor_admitted_cell_count": predecessor_venue[
                ADMITTED_PROSPECTIVE_PREKICKOFF
            ],
            "predecessor_defect": split["predecessor_defect"],
            "successor_domains": list(SPLIT_DOMAINS),
            "site_orientation_may_be_admitted_without_venue_identity": True,
            "venue_identity_may_be_admitted_from_site_orientation_alone": False,
            "venue_coordinates_may_be_admitted_from_inference": False,
            "weather_demotions_applied": len(demotions),
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-B-PRIOR-KNOWABLE-VERSUS-CURRENT",
            "cycle23_finding": "A_MISSING_CURRENT_PRIOR_WAS_DESCRIBED_AS_NO_KNOWABLE_PRIOR",
            "severity": "FALSE_UNKNOWABILITY_CLAIM",
            "predecessor_gate_identity": spine_gate["gate_identity"],
            "predecessor_absence_reason": spine_gate["prior_domain_evidence"][
                "absence_reason"
            ],
            "retired_classification": RETIRED_PRIOR_CLASSIFICATION,
            "retired_classification_defect": prior["retired_classification_defect"],
            "successor_classifications": list(PRIOR_CLASSIFICATIONS),
            "allowed_evidence_window": "THROUGH_2023_CHRONOLOGICAL_OUTCOMES",
            "stale_history_is_knowable": True,
            "stale_history_is_current": False,
            "stale_history_minimum_games": int(prior["stale_history_minimum_games"]),
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-C-PARTIAL-INPUT-IS-TERMINAL",
            "cycle23_finding": "PARTIAL_MODEL_INPUT_WAS_A_NONTERMINAL_PRE_FORECAST_STATE",
            "severity": "FORECAST_READINESS_LOOPHOLE",
            "predecessor_gate_identity": adequacy_gate["gate_identity"],
            "predecessor_partial_contest_count": adequacy_gate["summary"][
                "contest_adequacy_counts"
            ][PARTIAL_MODEL_INPUT],
            "diagnostic_state_retained": True,
            "forecast_time_mapping": readiness[
                "partial_model_input_forecast_time_mapping"
            ],
            "partial_model_input_may_emit_a_forecast": False,
            "enforced_by": "map_partial_model_input",
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-D-PAIR-CELL-VERSUS-DISTINCT-DOMAIN",
            "cycle23_finding": "PAIR_LEVEL_ADMITTED_DOMAIN_COUNT_WAS_AMBIGUOUS",
            "severity": "COUNT_SEMANTIC_AMBIGUITY",
            "predecessor_gate_identity": adequacy_gate["gate_identity"],
            "retired_field": counts["retired_field"],
            "retired_field_defect": counts["retired_field_defect"],
            "successor_fields": list(counts["successor_fields"]),
            "focus_contest_predecessor_reported_value": adequacy_gate[
                "focus_contest_report"
            ]["admitted_domain_count"],
            "focus_contest_admitted_team_domain_cell_count": focus_report[
                "admitted_team_domain_cell_count"
            ],
            "focus_contest_distinct_admitted_domain_count": focus_report[
                "distinct_admitted_domain_count"
            ],
            "focus_contest_interpretation": focus_report["reported_four_means"],
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-E-TARGET-OUTCOME-WORDING",
            "cycle23_finding": "THE_LEAKAGE_INVARIANT_WAS_STATED_AS_NO_OUTCOME_FIELD_ANYWHERE",
            "severity": "INVARIANT_MISSTATEMENT",
            "predecessor_gate_identity": spine_gate["gate_identity"],
            "retired_wording": wording["retired_wording"],
            "correct_invariant": CORRECT_LEAKAGE_INVARIANT,
            "week_zero_finals_legitimately_appear_as_prior_results": True,
            "week_zero_completed_contest_count": int(
                wording["week_zero_completed_contest_count"]
            ),
            "target_outcome_enters_its_own_feature_row": False,
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-F-WEEK-ZERO-CANDIDATE-COUNT",
            "cycle23_finding": "THE_WEEK_ZERO_REPORT_DESCRIBED_SIX_SCORED_CANDIDATES",
            "severity": "REPORT_LANGUAGE_ERROR_WITHOUT_ARTIFACT_DRIFT",
            "predecessor_gate_identity": week_zero_gate["gate_identity"],
            "incorrect_statement": week_zero["incorrect_statement"],
            "correct_statement": week_zero["correct_statement"],
            "scored_candidate_count": int(week_zero["scored_candidate_count"]),
            "eligible_opportunities_per_candidate": int(
                week_zero["eligible_opportunities_per_candidate"]
            ),
            "pooled_candidate_rows": int(week_zero["pooled_candidate_rows"]),
            "scientific_artifact_identity_rewritten": False,
            "predecessor_rewritten_in_place": False,
        },
        {
            "correction_id": "CYCLE24-CORRECTION-G-JIRA-COMMENT-14717-AUDIT",
            "cycle23_finding": "A_CYCLE23_JIRA_COMMENT_IS_MALFORMED_OR_DELETED",
            "severity": "AUTHORITY_TRACEABILITY_INCIDENT",
            "comment_id": int(audit["comment_id"]),
            "audit_performed": True,
            "body_disposition": audit["unavailable_body_disposition"],
            "body_reconstructed_from_model_memory": False,
            "second_cycle23_parent_comment_posted": False,
            "cycle23_comment_14718_mutated": False,
            "predecessor_rewritten_in_place": False,
        },
    ]

    for record in records:
        if record.get("predecessor_rewritten_in_place") is not False:
            raise SemanticSuccessorViolation(
                "a correction record claims an in-place rewrite"
            )
    records.sort(key=lambda row: row["correction_id"])
    return records


# ---------------------------------------------------------------------------
# successor rows and focus report
# ---------------------------------------------------------------------------


def build_successor_rows(
    *,
    spine_rows: Sequence[Mapping[str, Any]],
    successor_cells: Sequence[Mapping[str, Any]],
    history: Mapping[str, Mapping[str, Any]],
    minimum_games: int,
) -> list[dict[str, Any]]:
    """One corrected row per oriented team row, carrying only unambiguous fields."""
    cells_by_row: defaultdict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for cell in successor_cells:
        cells_by_row[
            (cell["contest_identity"], cell["canonical_team_id"] or "")
        ].append(cell)

    rows: list[dict[str, Any]] = []
    for spine_row in spine_rows:
        key = (spine_row["contest_identity"], spine_row.get("canonical_team_id") or "")
        cells = cells_by_row.get(key, [])
        by_domain = {cell["domain"]: cell for cell in cells}
        counts = count_team_domain_cells(cells)
        prior_state = classify_prior(
            spine_row=spine_row,
            prior_cell=by_domain.get(TEAM_STRENGTH_PRIOR),
            history=history,
            minimum_games=minimum_games,
        )

        site_cell = by_domain.get(SITE_ORIENTATION) or {}
        identity_cell = by_domain.get(VENUE_IDENTITY) or {}
        coordinate_cell = by_domain.get(VENUE_COORDINATES) or {}

        row: dict[str, Any] = {
            "contest_identity": spine_row["contest_identity"],
            "ncaa_contest_id": spine_row["ncaa_contest_id"],
            "canonical_team_id": spine_row.get("canonical_team_id"),
            "opponent_canonical_team_id": spine_row.get("opponent_canonical_team_id"),
            "source_team_id": spine_row["source_team_id"],
            "orientation": spine_row["orientation"],
            "season": spine_row["season"],
            "week_label": spine_row["week_label"],
            "requested_game_date": spine_row["requested_game_date"],
            "kickoff_utc_conservative_lower_bound": spine_row[
                "kickoff_utc_conservative_lower_bound"
            ],
            "kickoff_time_state": spine_row["kickoff_time_state"],
            "kickoff_utc_independently_confirmed": spine_row[
                "kickoff_utc_independently_confirmed"
            ],
            "contest_disposition": spine_row["contest_disposition"],
            "spine_row_state": spine_row["spine_row_state"],
            "team_identity_state": spine_row["team_identity_state"],
            "subdivision": spine_row["subdivision"],
            "conference_name": spine_row["conference_name"],
            "site_orientation": site_cell.get("value", {}).get(
                "site_orientation", "UNKNOWN"
            ),
            "site_orientation_state": site_cell.get(
                "admission_disposition", SOURCE_EVIDENCE_ABSENT
            ),
            "venue_identity": identity_cell.get("value", {}).get("venue_identity"),
            "venue_identity_state": identity_cell.get(
                "admission_disposition", SOURCE_EVIDENCE_ABSENT
            ),
            "venue_coordinate_state": coordinate_cell.get("value", {}).get(
                "venue_coordinate_state", SOURCE_EVIDENCE_ABSENT
            ),
            "venue_coordinates_admitted": coordinate_cell.get("admission_disposition")
            == ADMITTED_PROSPECTIVE_PREKICKOFF,
            "weather_state": (by_domain.get(WEATHER_VINTAGE) or {}).get(
                "admission_disposition", SOURCE_EVIDENCE_ABSENT
            ),
            "current_ranking_state": (by_domain.get(CURRENT_RANKING) or {}).get(
                "admission_disposition", SOURCE_EVIDENCE_ABSENT
            ),
            "poll_rank": spine_row.get("poll_rank"),
            "week_zero_result_state": (
                by_domain.get(WEEK_ZERO_CURRENT_RESULT) or {}
            ).get("admission_disposition", SOURCE_EVIDENCE_ABSENT),
            "retired_composite_domain_emitted": False,
            "retired_prior_classification_emitted": False,
            "target_outcome_enters_its_own_feature_row": False,
            "tamu_specific_adjustment_applied": False,
        }
        row.update({f"prior_{key}": value for key, value in prior_state.items()})
        row.update(counts)
        row["row_identity"] = stable_hash(row)
        rows.append(row)

    rows.sort(key=lambda row: (row["contest_identity"], row["orientation"]))
    return rows


def build_focus_contest_report(
    *,
    successor_rows: Sequence[Mapping[str, Any]],
    pair_counts: Sequence[Mapping[str, Any]],
    readiness_rows: Sequence[Mapping[str, Any]],
    adequacy_gate: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove what the predecessor's reported admitted-domain count actually counted."""
    predecessor = adequacy_gate["focus_contest_report"]
    contest_identity = predecessor["contest_identity"]
    pair = next(
        (item for item in pair_counts if item["contest_identity"] == contest_identity),
        None,
    )
    if pair is None:
        raise SemanticSuccessorViolation(
            "the focus contest is absent from the successor surface"
        )
    rows = [
        row for row in successor_rows if row["contest_identity"] == contest_identity
    ]
    if len(rows) != 2:
        raise SemanticSuccessorViolation(
            "the focus contest does not carry exactly two oriented rows"
        )

    reported = int(predecessor["admitted_domain_count"])
    cells = int(pair["admitted_team_domain_cell_count"])
    distinct = int(pair["distinct_admitted_domain_count"])
    if reported == cells and reported != distinct:
        interpretation = "FOUR_ADMITTED_TEAM_DOMAIN_CELLS_ACROSS_TWO_ORIENTED_ROWS"
    elif reported == distinct and reported != cells:
        interpretation = "FOUR_DISTINCT_ADMITTED_DOMAINS"
    elif reported == distinct == cells:
        interpretation = "AMBIGUOUS_BOTH_COUNTERS_COINCIDE_AT_THIS_CONTEST"
    else:
        interpretation = "PREDECESSOR_VALUE_MATCHES_NEITHER_SUCCESSOR_COUNTER"

    return {
        "contest_identity": contest_identity,
        "ncaa_contest_id": predecessor["ncaa_contest_id"],
        "discovered_from_the_predecessor_focus_report_not_hardcoded": True,
        "predecessor_reported_admitted_domain_count": reported,
        "admitted_team_domain_cell_count": cells,
        "distinct_admitted_domain_count": distinct,
        "distinct_admitted_domains": pair["distinct_admitted_domains"],
        "admitted_domain_count_by_orientation": pair[
            "admitted_domain_count_by_orientation"
        ],
        "candidate_only_team_domain_cell_count": pair[
            "candidate_only_team_domain_cell_count"
        ],
        "missing_team_domain_cell_count": pair["missing_team_domain_cell_count"],
        "reported_four_means": interpretation,
        "oriented_rows": [
            {
                "orientation": row["orientation"],
                "canonical_team_id": row["canonical_team_id"],
                "site_orientation": row["site_orientation"],
                "venue_identity_state": row["venue_identity_state"],
                "venue_coordinate_state": row["venue_coordinate_state"],
                "prior_classification": row["prior_classification"],
                "admitted_team_domain_cell_count": row[
                    "admitted_team_domain_cell_count"
                ],
                "admitted_domains": row["admitted_domains"],
            }
            for row in sorted(rows, key=lambda item: item["orientation"])
        ],
        "candidate_readiness": {
            item["candidate_id"]: item["forecast_readiness_state"]
            for item in sorted(
                (
                    r
                    for r in readiness_rows
                    if r["contest_identity"] == contest_identity
                ),
                key=lambda item: item["candidate_id"],
            )
        },
        "predecessor_candidate_states": predecessor["candidate_states"],
        "custom_correction_applied": False,
        "tamu_specific_adjustment_applied": False,
    }


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically rebuild every successor surface from pinned predecessors."""
    resolved = dict(inputs if inputs is not None else load_inputs(repo_root, data_root))
    contract = resolved["contract"]
    gates = resolved["gates"]
    spine_gate = gates["feature_spine"]
    adequacy_gate = gates["feature_coverage_adequacy"]
    week_zero_gate = gates["week_zero_scoring"]
    spine_rows = resolved["spine_rows"]
    spine_cells = resolved["spine_cells"]

    history = team_history_index(resolved["matrix_rows"])
    minimum_games = int(contract["prior_semantics"]["stale_history_minimum_games"])

    successor_cells, demotions = build_successor_cells(spine_cells)
    successor_rows = build_successor_rows(
        spine_rows=spine_rows,
        successor_cells=successor_cells,
        history=history,
        minimum_games=minimum_games,
    )
    pair_counts = build_pair_counts(
        successor_cells=successor_cells, spine_rows=spine_rows
    )

    ranking_surface_complete = bool(
        spine_gate["ranking_evidence"]["poll_coverage_complete"]
    )

    rows_by_contest: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in successor_rows:
        rows_by_contest[row["contest_identity"]].append(row)
    cells_by_contest: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for cell in successor_cells:
        cells_by_contest[cell["contest_identity"]].append(cell)

    readiness_rows: list[dict[str, Any]] = []
    for requirement in contract["candidate_feature_requirements"]:
        for contest_identity in sorted(rows_by_contest):
            readiness_rows.append(
                resolve_forecast_readiness(
                    requirement=requirement,
                    contest_cells=cells_by_contest[contest_identity],
                    contest_rows=rows_by_contest[contest_identity],
                    ranking_surface_complete=ranking_surface_complete,
                )
            )
    readiness_rows.sort(key=lambda row: (row["candidate_id"], row["contest_identity"]))

    focus_report = build_focus_contest_report(
        successor_rows=successor_rows,
        pair_counts=pair_counts,
        readiness_rows=readiness_rows,
        adequacy_gate=adequacy_gate,
    )
    corrections = build_correction_records(
        contract=contract,
        spine_gate=spine_gate,
        adequacy_gate=adequacy_gate,
        week_zero_gate=week_zero_gate,
        demotions=demotions,
        focus_report=focus_report,
    )

    summary = build_summary(
        successor_cells=successor_cells,
        successor_rows=successor_rows,
        pair_counts=pair_counts,
        readiness_rows=readiness_rows,
        ranking_surface_complete=ranking_surface_complete,
        demotions=demotions,
    )

    record_hashes = {
        "cells": stable_hash(successor_cells),
        "rows": stable_hash(successor_rows),
        "pair_counts": stable_hash(pair_counts),
        "readiness": stable_hash(readiness_rows),
        "corrections": stable_hash(corrections),
    }
    contract_sha256 = hashlib.sha256(
        (repo_root / CONTRACT_RELATIVE).read_bytes()
    ).hexdigest()
    code_identity = sha256_file(Path(__file__).resolve())
    dataset_identity = stable_hash(
        {
            "classification": CLASSIFICATION,
            "code_identity": code_identity,
            "contract_sha256": contract_sha256,
            "predecessor_spine_gate_identity": spine_gate["gate_identity"],
            "predecessor_adequacy_gate_identity": adequacy_gate["gate_identity"],
            "record_hashes": record_hashes,
        }
    )

    return {
        "contract": contract,
        "contract_sha256": contract_sha256,
        "code_identity": code_identity,
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "cells": successor_cells,
        "rows": successor_rows,
        "pair_counts": pair_counts,
        "readiness": readiness_rows,
        "corrections": corrections,
        "summary": summary,
        "focus_contest_report": focus_report,
        "weather_demotions": demotions,
        "ranking_surface_complete": ranking_surface_complete,
        "gates": gates,
        "matrix_gate": resolved["matrix_gate"],
    }


def build_summary(
    *,
    successor_cells: Sequence[Mapping[str, Any]],
    successor_rows: Sequence[Mapping[str, Any]],
    pair_counts: Sequence[Mapping[str, Any]],
    readiness_rows: Sequence[Mapping[str, Any]],
    ranking_surface_complete: bool,
    demotions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    domain_counts: dict[str, dict[str, int]] = {}
    for domain in SUCCESSOR_DOMAINS:
        cells = [cell for cell in successor_cells if cell["domain"] == domain]
        counter = Counter(cell["admission_disposition"] for cell in cells)
        domain_counts[domain] = {
            disposition: int(counter.get(disposition, 0))
            for disposition in ADMISSION_DISPOSITIONS
        }

    readiness_counts: dict[str, dict[str, int]] = {}
    for candidate_id in sorted({row["candidate_id"] for row in readiness_rows}):
        counter = Counter(
            row["forecast_readiness_state"]
            for row in readiness_rows
            if row["candidate_id"] == candidate_id
        )
        readiness_counts[candidate_id] = {
            state: int(counter.get(state, 0)) for state in READINESS_STATES
        }

    prior_counter = Counter(row["prior_classification"] for row in successor_rows)
    return {
        "cell_count": len(successor_cells),
        "row_count": len(successor_rows),
        "contest_count": len(pair_counts),
        "readiness_row_count": len(readiness_rows),
        "successor_domain_count": len(SUCCESSOR_DOMAINS),
        "domain_admission_counts": domain_counts,
        "forecast_readiness_counts": readiness_counts,
        "prior_classification_counts": {
            classification: int(prior_counter.get(classification, 0))
            for classification in PRIOR_CLASSIFICATIONS
        },
        "ranking_surface_complete": ranking_surface_complete,
        "weather_demotion_count": len(demotions),
        "site_orientation_admitted_without_venue_identity": sum(
            1
            for row in successor_rows
            if row["site_orientation_state"] == ADMITTED_PROSPECTIVE_PREKICKOFF
            and row["venue_identity_state"] != ADMITTED_PROSPECTIVE_PREKICKOFF
        ),
        "venue_identity_admitted_count": sum(
            1
            for row in successor_rows
            if row["venue_identity_state"] == ADMITTED_PROSPECTIVE_PREKICKOFF
        ),
        "venue_coordinates_admitted_count": sum(
            1 for row in successor_rows if row["venue_coordinates_admitted"]
        ),
        "rows_by_orientation": dict(
            sorted(Counter(row["orientation"] for row in successor_rows).items())
        ),
        "retired_composite_domain_emitted": False,
        "retired_prior_classification_emitted": False,
        "retired_ambiguous_count_field_emitted": False,
        "forecast_emitted": False,
    }


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
    execution_time_utc: str,
) -> dict[str, Any]:
    contract = expected["contract"]
    gates = expected["gates"]
    gate: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_SPINE_SEMANTIC_SUCCESSOR_GATE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "season": int(contract["season"]),
        "week_label": contract["week_label"],
        "execution_time_utc": execution_time_utc,
        "dataset_identity": expected["dataset_identity"],
        "record_hashes": expected["record_hashes"],
        "manifest": dict(manifest_entry),
        "payloads": [dict(item) for item in payloads],
        "bound_predecessors": {
            "feature_spine_gate_identity": gates["feature_spine"]["gate_identity"],
            "feature_coverage_adequacy_gate_identity": gates[
                "feature_coverage_adequacy"
            ]["gate_identity"],
            "week1_schedule_identity_gate_identity": gates["schedule_identity"][
                "gate_identity"
            ],
            "frozen_candidate_gate_identity": gates["frozen_candidates"][
                "gate_identity"
            ],
            "week_zero_official_final_scoring_gate_identity": gates[
                "week_zero_scoring"
            ]["gate_identity"],
            "chronological_development_matrix_dataset_identity": expected[
                "matrix_gate"
            ]["dataset_identity"],
            "predecessor_artifacts_rewritten_in_place": False,
        },
        "predecessor_identity": gates["feature_spine"]["gate_identity"],
        "domain_split": contract["domain_split"],
        "prior_semantics": contract["prior_semantics"],
        "forecast_readiness": contract["forecast_readiness"],
        "count_semantics": contract["count_semantics"],
        "candidate_feature_requirements": contract["candidate_feature_requirements"],
        "corrections": expected["corrections"],
        "focus_contest_report": expected["focus_contest_report"],
        "summary": expected["summary"],
        "authority": contract["authority"],
        "checkpoints": contract["checkpoints"],
        "tamu_policy": contract["tamu_policy"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    gate["payload_root_sha256"] = stable_hash(
        [
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")}
            for item in payloads
        ]
    )
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


PAYLOAD_ROLES = (
    (CELL_PAYLOAD_NAME, "WEEK1_2026_SUCCESSOR_ADMISSION_CELLS", "cells"),
    (ROW_PAYLOAD_NAME, "WEEK1_2026_SUCCESSOR_SPINE_ROWS", "rows"),
    (PAIR_PAYLOAD_NAME, "WEEK1_2026_SUCCESSOR_PAIR_COUNTS", "pair_counts"),
    (READINESS_PAYLOAD_NAME, "WEEK1_2026_SUCCESSOR_FORECAST_READINESS", "readiness"),
    (CORRECTION_PAYLOAD_NAME, "WEEK1_2026_SEMANTIC_CORRECTION_RECORDS", "corrections"),
)


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    execution_time: datetime,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = dict(
        expected
        if expected is not None
        else build_expected(repo_root=repo_root, data_root=data_root)
    )
    execution_time_utc = (
        execution_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if execution_time.microsecond
        else execution_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    identity = resolved["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    manifest_root = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / identity

    payloads: list[dict[str, Any]] = []
    for name, role, key in PAYLOAD_ROLES:
        rows = resolved[key]
        payload_bytes = jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_SPINE_SEMANTIC_SUCCESSOR_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": resolved["contract"]["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "dataset_identity": identity,
        "issued_at_utc": execution_time_utc,
        "classification": CLASSIFICATION,
        "record_hashes": resolved["record_hashes"],
        "summary": resolved["summary"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": resolved["code_identity"],
            "contract_sha256": resolved["contract_sha256"],
        },
    }
    manifest_path = manifest_root / f"{PAYLOAD_SLUG}_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "dataset_identity": identity,
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate = build_gate(
        expected=resolved,
        manifest_entry=manifest_entry,
        payloads=[
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")}
            for item in payloads
        ],
        execution_time_utc=execution_time_utc,
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"gate": gate, "manifest": manifest, "expected": resolved}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    """Independently reconstruct the successor and refuse any semantic regression."""
    gate = read_json(repo_root / GATE_RELATIVE)
    if gate.get("result") != PASS_RESULT:
        raise SemanticSuccessorViolation(
            f"successor gate is not passing: {gate.get('result')}"
        )
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise SemanticSuccessorViolation("successor gate opened the protected lane")
    if gate.get("lane") != LANE:
        raise SemanticSuccessorViolation("successor gate lane drift")
    if (
        gate["bound_predecessors"].get("predecessor_artifacts_rewritten_in_place")
        is not False
    ):
        raise SemanticSuccessorViolation(
            "the gate admits an in-place predecessor rewrite"
        )
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if gate["checkpoints"].get(key) != "OPEN":
            raise SemanticSuccessorViolation(f"{key} is no longer OPEN")
    if gate["summary"].get("forecast_emitted") is not False:
        raise SemanticSuccessorViolation("the successor gate emitted a forecast")
    for key in ("tamu_specific_adjustment_applied", "custom_correction_applied"):
        if gate["tamu_policy"].get(key) is not False:
            raise SemanticSuccessorViolation(
                f"an A&M-specific adjustment is declared: {key}"
            )

    if compute_gate_identity(gate) != gate.get("gate_identity"):
        raise SemanticSuccessorViolation(
            "gate identity does not match its identity-bearing fields"
        )
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        raise SemanticSuccessorViolation("cross-surface binding identity drift")

    if not require_rebuild:
        return {
            "result": "PASS",
            "mode": "SCHEMA_ONLY",
            "gate_identity": gate["gate_identity"],
        }

    expected = build_expected(repo_root=repo_root, data_root=data_root)
    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("record_hashes", gate["record_hashes"], expected["record_hashes"], errors)
    _compare("summary", gate["summary"], expected["summary"], errors)
    _compare("corrections", gate["corrections"], expected["corrections"], errors)
    _compare(
        "focus_contest_report",
        gate["focus_contest_report"],
        expected["focus_contest_report"],
        errors,
    )

    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    if (
        manifest_authoritative_sha256(manifest)
        != gate["manifest"]["authoritative_sha256"]
    ):
        errors.append("manifest authoritative content drift")
    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest["payloads"] if item["name"] == payload["name"]),
            None,
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    for row in expected["rows"]:
        if row["retired_composite_domain_emitted"] is not False:
            errors.append("a successor row emitted the retired composite domain")
        if row["prior_classification"] not in PRIOR_CLASSIFICATIONS:
            errors.append(
                f"unknown prior classification: {row['prior_classification']}"
            )
        if (
            row["venue_identity_state"] == ADMITTED_PROSPECTIVE_PREKICKOFF
            and row["venue_identity"] is None
        ):
            errors.append("venue identity admitted without an authoritative venue id")
    for readiness in expected["readiness"]:
        if readiness["forecast_readiness_state"] not in READINESS_STATES:
            errors.append(
                f"unknown readiness state: {readiness['forecast_readiness_state']}"
            )
        if readiness["forecast_emitted_by_this_gate"] is not False:
            errors.append("a readiness row emitted a forecast")

    if errors:
        raise SemanticSuccessorViolation(
            "independent successor validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
        "summary": gate["summary"],
        "focus_contest_report": gate["focus_contest_report"],
    }
