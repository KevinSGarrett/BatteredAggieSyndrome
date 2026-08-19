"""Identity-bound 2010-2011 Texas A&M cross-source domain admission gate."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import (
    canonical_json_bytes,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.tamu_official_gamebook_union import (
    TEXAS_DISPOSITION,
    attach_official_boxes,
    load_official_compact_games,
    official_domain_present,
)


SCHEMA_VERSION = "aggie.data.tamu_cross_source_domain_gate.v2"
CONTRACT_SCHEMA_VERSION = "2.0.0"
EVIDENCE_SCHEMA_VERSION = "2.2.0"
CONTRACT_RELATIVE = "configs/tamu_cross_source_domain_gate_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_cross_source_domain_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CROSS-SOURCE-DOMAIN-GATE-001.json"
CONTRACT_ID = "BAT-572-TAMU-CROSS-SOURCE-DOMAIN-GATE-V1"
CORRECTION_JIRA_KEY = "BAT-583"
CORRECTION_LOCAL_ID = "POST-TASK-CYCLE-10-BAT572-EVIDENCE-REPRODUCIBILITY-001"
PASS_RESULT = "PASS_IDENTITY_BOUND_DOMAIN_GATE_SRC014_POSTGAME_FACTS_NO_NCAA_CONTEST"
PASS_CLASSIFICATION = "TAMU_2010_2011_CROSS_SOURCE_DOMAIN_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PHASE3_MATRIX_IDENTITY = "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa"
PHASE3_GATE_IDENTITY = "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93"
PHASE4_ACQUISITION_IDENTITY = "349654307f5d46b979e65b12128da50f99e91c1f75627b9bd94ed6b83f21ae8f"
PHASE4_DISPOSITION = "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ENDPOINTS"
TEAM_SEASON_GATE_IDENTITY = "dc06984fa17285abf6e9d32a362dd1515ff528fed82eff77254fb8abb702d91e"
TEAM_SEASON_DISPOSITION = "TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED"
SEASON_RECON_GATE_IDENTITY = "c8ee22b6ba8a5ad1bb7a84fdc74f9c2fb6dd703f5108a953205377798c33b066"
SEASON_RECON_DISPOSITION = "SEASON_LEVEL_RECONCILED_WITH_PRESERVED_TEXAS_SIDEARM_DATE_CONFLICT"
OFFICIAL_BOXSCORE_GATE_IDENTITY = "29e76b1e264387b2195e2fd4c1d04bbb375d448789b4ac64aec701a61eceb1e5"
OFFICIAL_BOXSCORE_DATASET_IDENTITY = "46841fcd9e3c3d18be55a7e098b52e089bc1a307a9779783cf4192f1324ba2aa"
CONTEST_ROUTE_GATE_IDENTITY = "d0a2c7218bf9892dfc468f534e41555ab880cb3d41c2d77413dd10ecc923c039"
CONTEST_ROUTE_DISPOSITION = "OFFICIAL_ROUTE_ACCESS_BLOCKED"
CONTEST_ROUTE_MANIFEST_IDENTITY = "0af578e834efdb78cc1710d3a2690311315f829f9b7f0bfb3353dd4ab2abf9cb"
CYCLE7_GATE_IDENTITY = "418995882f3c2aa7951b38672a3cf0b8dd93ddd883f682b08683b8777aeef3f3"
CYCLE8_GATE_IDENTITY = "b13f4d8954d660211a2393303fbb118dc459455f854ef31a757e3c16476da678"
UNION_GATE_IDENTITY = "dd0d0f32c499b4863551a9ab6649cbef7638c3916228661262fbd5a71909c106"
UNION_IDENTITY = "050fb22e733f3dc296a5bafed9f89a20281efb06860dc220264d074a7e9b7672"
NCAA_NATIONAL_IDENTITY = "3e7163624cb05c77a9ac6e8ec089c8bacd4d8bd360693aa8b473ca1ec174bebf"
WMT_ACQUISITION_IDENTITY = "d227b6cfca71ad0e6d514fa707f7d23a4a6a59374142352a016202c3bd2f25b3"
WMT_RECONCILIATION_IDENTITY = "76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010"
TEAM_BOX_IDENTITY = "f2e8fae89ca3659adad710b4b9b952cdb391a1b3c0c44956803b0e29c219a733"
PLAYER_BOX_IDENTITY = "3df499e8f6d448624fc62af2a95505546483cc01aba84f19078ad72fd0d36af5"
ROSTER_GATE_IDENTITY = "53fd14a5ea8f43aaf51c9998141c90d13ac371e43c3f1ec502e871a185c35aa9"
REGISTRY_SHA256 = "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
STALE_429_MATRIX = "7c4b170a85d7aa8053bbbad099b8569cff6676580f18f46f375bbece8a53b3d1"
BAT429_BLOCKED_REASON = (
    "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-063;POST-SUBTASK-066;POST-SUBTASK-069"
)
BAT429_UNBLOCK = "Complete and verify all hard dependencies at required maturity/evidence."
BAT429_JSON = (
    "jira/records/issues/subtasks/"
    "POST-SUBTASK-079_acquire_approved_a_and_m_schedules_rosters_depth_staff_media_guide_participation.json"
)
BAT429_MD = (
    "jira/issues/subtasks/"
    "POST-SUBTASK-079_acquire_approved_a_and_m_schedules_rosters_depth_staff_media_guide_participation.md"
)
BAT429_SIBLING_MD = (
    "jira/issues/subtasks/"
    "POST-SUBTASK-063_validate_player_state_coverage_uncertainty_double_counting_controls_and_producti.md",
    "jira/issues/subtasks/"
    "POST-SUBTASK-069_validate_context_correctness_forecast_versus_realized_isolation_fallback_behavio.md",
)
DOMAIN_COLUMNS = (
    "linescore_game_info",
    "venue",
    "attendance",
    "officials",
    "team_statistics",
    "team_statistics_by_period",
    "player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
    "participation",
    "roster_membership",
    "pregame_availability",
)
ADMITTED_DECISIONS = (
    "VERIFIED_OFFICIAL_POSTGAME_FACT",
    "VERIFIED_CROSS_SOURCE_POSTGAME_FACT",
    "CANDIDATE_ONLY",
    "CONFLICT_REVIEW_REQUIRED",
    "TECHNICAL_ROUTE_BLOCKED",
    "SOURCE_EVIDENCE_ABSENT",
    "NOT_APPLICABLE",
)
VERIFIED_DECISIONS = frozenset(
    {"VERIFIED_OFFICIAL_POSTGAME_FACT", "VERIFIED_CROSS_SOURCE_POSTGAME_FACT"}
)
NCAA_CONTEST_DOMAINS = frozenset(
    {
        "attendance",
        "officials",
        "team_statistics",
        "team_statistics_by_period",
        "player_statistics",
        "drives",
        "play_by_play",
        "scoring_summary",
    }
)
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "input_identities",
    "phase4_disposition",
    "contest_route_disposition",
    "counts",
    "admissions",
    "season_level_admissions",
    "rebound_jira_key",
    "authority",
    "official_fact_scope",
    "scientific_nonclaims",
    "remaining_blockers",
    "bat_429",
    "protected_lane",
    "row_identities",
)
DEPRECATED_VERIFIED_OFFICIAL_CLAIMED_MEANING = (
    "FALSE means full historical official completeness and NCAA contest official "
    "evidence are not claimed. It does not deny admitted VERIFIED_OFFICIAL_POSTGAME_FACT rows."
)


class AuthorityViolation(ValueError):
    """Raised when the gate is asked to inflate admission or open a sealed lane."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise AuthorityViolation("cross-source domain-gate contract schema drift")
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("cross-source domain-gate contract identity drift")
    if contract.get("jira_key") != "BAT-572":
        raise AuthorityViolation("contract jira key drift")
    if contract.get("correction_jira_key") != CORRECTION_JIRA_KEY:
        raise AuthorityViolation("contract correction owner drift")
    if contract.get("correction_local_issue_id") != CORRECTION_LOCAL_ID:
        raise AuthorityViolation("contract correction local-id drift")
    _validate_owner_inputs(contract)
    identities = contract["identities"]
    expected = {
        "phase3_matrix_identity": PHASE3_MATRIX_IDENTITY,
        "phase3_gate_identity": PHASE3_GATE_IDENTITY,
        "phase4_acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
        "phase4_disposition": PHASE4_DISPOSITION,
        "team_season_gate_identity": TEAM_SEASON_GATE_IDENTITY,
        "team_season_disposition": TEAM_SEASON_DISPOSITION,
        "season_reconciliation_gate_identity": SEASON_RECON_GATE_IDENTITY,
        "season_reconciliation_disposition": SEASON_RECON_DISPOSITION,
        "contest_route_gate_identity": CONTEST_ROUTE_GATE_IDENTITY,
        "contest_route_disposition": CONTEST_ROUTE_DISPOSITION,
        "official_boxscore_gate_identity": OFFICIAL_BOXSCORE_GATE_IDENTITY,
        "official_boxscore_dataset_identity": OFFICIAL_BOXSCORE_DATASET_IDENTITY,
        "union_gate_identity": UNION_GATE_IDENTITY,
        "union_identity": UNION_IDENTITY,
        "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
        "wmt_reconciliation_dataset_identity": WMT_RECONCILIATION_IDENTITY,
        "team_box_snapshot_dataset_identity": TEAM_BOX_IDENTITY,
        "player_box_snapshot_dataset_identity": PLAYER_BOX_IDENTITY,
        "ncaa_official_national_acquisition_identity": NCAA_NATIONAL_IDENTITY,
        "roster_gate_identity": ROSTER_GATE_IDENTITY,
        "protected_split_registry_sha256": REGISTRY_SHA256,
    }
    for key, digest in expected.items():
        if identities.get(key) != digest:
            raise AuthorityViolation(f"contract identity drift: {key}")
    authority = contract.get("authority") or {}
    for key in (
        "completeness_claim",
        "verified_official_inflation",
        "full_historical_official_completeness",
        "ncaa_contest_official_evidence",
        "blanket_gamebook_admission",
        "same_lineage_as_independent_corroboration",
        "name_only_promotion",
        "participation_as_availability",
        "membership_as_availability",
        "postgame_as_pregame_feature",
        "protected_outcome_authority",
        "bat_429_ready_or_done",
    ):
        if authority.get(key) is not False:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    return contract


def _validate_owner_inputs(contract: Mapping[str, Any]) -> dict[str, Any]:
    rebound = str(contract.get("rebound_jira_key") or "")
    related = list(contract.get("related_jira_keys") or [])
    current = list(contract.get("current_relationship_set") or [])
    superseded = list(contract.get("superseded_rebound_owners") or [])
    history = list(contract.get("supersession_history") or [])
    if not rebound:
        raise AuthorityViolation("current rebound owner is missing")
    if rebound in superseded:
        raise AuthorityViolation("superseded owner presented as current")
    if rebound not in current:
        raise AuthorityViolation("current rebound owner missing from current relationship set")
    missing_current = [key for key in current if key not in related]
    if missing_current:
        raise AuthorityViolation(f"current relationship missing from related keys: {missing_current}")
    if any(key in related for key in superseded):
        raise AuthorityViolation("superseded owner presented as current")
    for row in history:
        if row.get("current") is True:
            raise AuthorityViolation("superseded owner presented as current")
        if row.get("jira_key") == rebound:
            raise AuthorityViolation("current rebound owner listed as superseded")
    if CORRECTION_JIRA_KEY not in related:
        raise AuthorityViolation("correction owner missing from current relationship set")
    return {
        "gate_jira_key": contract["jira_key"],
        "local_issue_id": contract["decision_unit"],
        "parent_jira_key": contract["parent_jira_key"],
        "correction_jira_key": contract["correction_jira_key"],
        "correction_local_issue_id": contract["correction_local_issue_id"],
        "related_jira_keys": related,
        "current_relationship_set": current,
        "superseded_rebound_owners": superseded,
        "rebound_jira_key": rebound,
        "supersession_history": history,
    }


def current_evidence_owner(contract: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_owner_inputs(contract)


def verify_file(path: Path, expected_sha256: str, context: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{context} is missing: {path}")
    digest = sha256_file(path)
    if digest.lower() != expected_sha256.lower():
        raise ValueError(f"{context} hash drift: {digest}")


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "verified_official_inflation": False,
        "full_historical_official_completeness": False,
        "ncaa_contest_official_evidence": False,
        "blanket_gamebook_admission": False,
        "same_lineage_as_independent_corroboration": False,
        "name_only_promotion": False,
        "contest_id_fabrication": False,
        "historical_known_at_from_capture_time": False,
        "participation_as_availability": False,
        "membership_as_availability": False,
        "postgame_as_pregame_feature": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_429_ready_or_done": False,
        "bat_523_closed": False,
    }


def expected_official_fact_scope(counts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    verified_official = int((counts or {}).get("verified_official") or 0)
    verified_cross = int((counts or {}).get("verified_cross_source") or 0)
    present = verified_official > 0
    return {
        "verified_official_postgame_facts_present": present,
        "verified_official_postgame_fact_count": verified_official,
        "verified_cross_source_postgame_facts_present": verified_cross > 0,
        "verified_cross_source_postgame_fact_count": verified_cross,
        "full_historical_official_completeness_claimed": False,
        "ncaa_contest_official_evidence_claimed": False,
        "historical_population_ready": False,
        "historical_known_at_established": False,
        "deprecated_verified_official_claimed": False,
        "deprecated_verified_official_claimed_meaning": DEPRECATED_VERIFIED_OFFICIAL_CLAIMED_MEANING,
    }


def expected_scientific_nonclaims(counts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    scope = expected_official_fact_scope(counts)
    return {
        "completeness_claimed": False,
        "verified_official_postgame_facts_present": scope["verified_official_postgame_facts_present"],
        "verified_official_postgame_fact_count": scope["verified_official_postgame_fact_count"],
        "verified_cross_source_postgame_facts_present": scope["verified_cross_source_postgame_facts_present"],
        "verified_cross_source_postgame_fact_count": scope["verified_cross_source_postgame_fact_count"],
        "full_historical_official_completeness_claimed": False,
        "ncaa_contest_official_evidence_claimed": False,
        "verified_official_claimed": False,
        "verified_cross_source_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "participation_used_as_availability": False,
        "membership_used_as_availability": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_outcome_authority": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "contest_ids_fabricated": False,
        "name_only_promoted": False,
        "bat_429_ready_or_done": False,
        "bat_523_closed": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "gate_admission": "CANDIDATE_ONLY",
        "ncaa_official": "SOURCE_EVIDENCE_ABSENT_NO_CONTEST_IDS",
        "ncaa_official_per_game": "SOURCE_EVIDENCE_ABSENT_NO_CONTEST_IDS",
        "ncaa_team_season": TEAM_SEASON_DISPOSITION,
        "season_reconciliation": SEASON_RECON_DISPOSITION,
        "contest_route": CONTEST_ROUTE_DISPOSITION,
        "wmt_gamebook": "SOURCE_EVIDENCE_ABSENT_GAP_SEASONS",
        "official_src014": "VERIFIED_OFFICIAL_POSTGAME_FACT_PER_DOMAIN",
        "sidearm_schedule": "CANDIDATE_ONLY",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
    }


def expected_remaining_blockers() -> list[str]:
    return [
        "NCAA_CONTEST_IDS_EMPTY_FOR_TAMU_2010_2011",
        "NCAA_CONTEST_ENDPOINTS_NOT_ATTEMPTED",
        "NCAA_CONTEST_ROUTE_ACCESS_BLOCKED",
        "SEASON_LEVEL_NOT_PER_GAME_OFFICIAL",
        "WMT_GAMEBOOK_ABSENT_FOR_2010_2011",
        "OFFICIAL_SCHOOL_BOXSCORES_ARE_NOT_NCAA_CONTEST_IDS",
        "NO_PREGAME_AVAILABILITY_EVIDENCE",
        "MEMBERSHIP_IS_NOT_AVAILABILITY",
        "PARTICIPATION_IS_NOT_AVAILABILITY",
        "NAME_ONLY_PROMOTION_FORBIDDEN",
        "TEAM_BOX_PLAYER_BOX_NOT_JOINED_WITHOUT_CANONICAL_GAME_ID",
        "PROTECTED_LANE_REMAINS_BLOCKED",
        "BAT_429_HARD_DEPENDENCIES_UNSATISFIED",
    ]


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def verify_protected_registry(repo_root: Path, contract: Mapping[str, Any]) -> None:
    relative = contract["identities"]["protected_split_registry_relative_path"]
    verify_file(repo_root / relative, REGISTRY_SHA256, "protected split registry")


def verify_upstream_gates(repo_root: Path) -> dict[str, Any]:
    phase3 = load_json(repo_root / "artifacts/data_lake/tamu_official_evidence_gap_matrix_gate.json")
    phase4 = load_json(repo_root / "artifacts/data_lake/tamu_2010_2011_ncaa_official_acquisition_gate.json")
    team_season = load_json(repo_root / "artifacts/data_lake/tamu_2010_2011_ncaa_team_season_evidence_gate.json")
    season_recon = load_json(repo_root / "artifacts/data_lake/tamu_2010_2011_season_reconciliation_gate.json")
    contest_route = load_json(repo_root / "artifacts/data_lake/tamu_2010_2011_ncaa_contest_route_discovery_gate.json")
    ncaa = load_json(repo_root / "artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json")
    roster = load_json(repo_root / "artifacts/pit/roster_domain_completeness_gate.json")
    team_box = load_json(repo_root / "artifacts/pit/historical_team_box_snapshot_gate.json")
    player_box = load_json(repo_root / "artifacts/pit/historical_player_box_snapshot_gate.json")
    if phase3.get("matrix_identity") != PHASE3_MATRIX_IDENTITY:
        raise AuthorityViolation("missing Phase 3 matrix bind")
    if phase3.get("gate_identity") != PHASE3_GATE_IDENTITY:
        raise AuthorityViolation("missing Phase 3 gate bind")
    if phase4.get("acquisition_identity") != PHASE4_ACQUISITION_IDENTITY:
        raise AuthorityViolation("missing Phase 4 acquisition bind")
    if phase4.get("disposition") != PHASE4_DISPOSITION:
        raise AuthorityViolation("Phase 4 disposition drift")
    if int((phase4.get("counts") or {}).get("contest_ids_2010", -1)) != 0:
        raise AuthorityViolation("Phase 4 2010 contest count drifted")
    if int((phase4.get("counts") or {}).get("contest_ids_2011", -1)) != 0:
        raise AuthorityViolation("Phase 4 2011 contest count drifted")
    if team_season.get("gate_identity") != TEAM_SEASON_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-574 team-season bind")
    if team_season.get("disposition") != TEAM_SEASON_DISPOSITION:
        raise AuthorityViolation("BAT-574 disposition drift")
    if season_recon.get("gate_identity") != SEASON_RECON_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-575 season-reconciliation bind")
    if season_recon.get("disposition") != SEASON_RECON_DISPOSITION:
        raise AuthorityViolation("BAT-575 disposition drift")
    if season_recon.get("admissions", {}).get("texas_2011") != TEXAS_DISPOSITION:
        raise AuthorityViolation("2011 Texas official strong tuple was not bound")
    if contest_route.get("gate_identity") != CONTEST_ROUTE_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-576 contest-route bind")
    if contest_route.get("disposition") != CONTEST_ROUTE_DISPOSITION:
        raise AuthorityViolation("BAT-576 disposition drift")
    if int((contest_route.get("counts") or {}).get("contest_ids_discovered", -1)) != 0:
        raise AuthorityViolation("BAT-576 contest-ID count drifted")
    if int((contest_route.get("counts") or {}).get("contest_endpoint_attempts", -1)) != 0:
        raise AuthorityViolation("BAT-576 contest-endpoint attempt count drifted")
    ncaa_identity = (ncaa.get("manifest") or {}).get("acquisition_identity") or ncaa.get(
        "acquisition_identity"
    )
    if ncaa_identity != NCAA_NATIONAL_IDENTITY:
        raise AuthorityViolation("missing BAT-554 national NCAA bind")
    if roster.get("gate_identity") != ROSTER_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-567 roster-gate bind")
    if (team_box.get("output_identities") or {}).get("dataset") != TEAM_BOX_IDENTITY:
        raise AuthorityViolation("missing BAT-548 team-box bind")
    if (player_box.get("output_identities") or {}).get("dataset") != PLAYER_BOX_IDENTITY:
        raise AuthorityViolation("missing BAT-550 player-box bind")
    return {
        "phase3": phase3,
        "phase4": phase4,
        "team_season": team_season,
        "season_recon": season_recon,
        "contest_route": contest_route,
        "ncaa": ncaa,
        "roster": roster,
        "team_box": team_box,
        "player_box": player_box,
    }


def inspect_bat429(repo_root: Path) -> dict[str, Any]:
    record = load_json(repo_root / BAT429_JSON)
    markdown = (repo_root / BAT429_MD).read_text(encoding="utf-8")
    queue_path = repo_root / "jira/index/BLOCKED_QUEUE.csv"
    queue_row = None
    with queue_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("issue_id") == "POST-SUBTASK-079":
                queue_row = row
                break
    if queue_row is None:
        raise AuthorityViolation("POST-SUBTASK-079 missing from BLOCKED_QUEUE")
    ready_states = {"READY", "Ready", "DONE", "Done"}
    workflow = str(record.get("workflow_state") or "")
    if workflow in ready_states or workflow.upper() in {"READY", "DONE"}:
        raise AuthorityViolation("BAT-429 marked Ready")
    if record.get("blocked_reason") != BAT429_BLOCKED_REASON:
        raise AuthorityViolation("BAT-429 blocked_reason is not the live hard-dependency classification")
    if record.get("unblock_condition") != BAT429_UNBLOCK:
        raise AuthorityViolation("BAT-429 unblock_condition drift")
    if STALE_429_MATRIX in str(record.get("blocked_reason") or ""):
        raise AuthorityViolation("BAT-429 still cites the stale QUALITY_GATE_BLOCKED_MATRIX_IDENTITY")
    if BAT429_BLOCKED_REASON not in markdown or BAT429_UNBLOCK not in markdown:
        raise AuthorityViolation("BAT-429 markdown classification drift")
    if STALE_429_MATRIX in markdown:
        raise AuthorityViolation("BAT-429 markdown still cites the stale matrix identity")
    if queue_row.get("reason") != BAT429_BLOCKED_REASON:
        raise AuthorityViolation("BLOCKED_QUEUE POST-SUBTASK-079 reason drift")
    if queue_row.get("unblock_condition") != BAT429_UNBLOCK:
        raise AuthorityViolation("BLOCKED_QUEUE POST-SUBTASK-079 unblock_condition drift")
    for sibling in BAT429_SIBLING_MD:
        text = (repo_root / sibling).read_text(encoding="utf-8")
        if STALE_429_MATRIX not in text:
            raise AuthorityViolation(f"sibling {sibling} was rewritten")
    return {
        "local_id": "POST-SUBTASK-079",
        "jira_key": "BAT-429",
        "workflow_state": workflow,
        "blocked_reason": record["blocked_reason"],
        "unblock_condition": record["unblock_condition"],
        "ready_or_done": False,
    }


def _decision(
    *,
    decision: str,
    reason: str,
    sources: list[str],
    ncaa_http: str = "NOT_APPLICABLE",
) -> dict[str, Any]:
    if decision not in ADMITTED_DECISIONS:
        raise AuthorityViolation(f"unknown domain decision {decision}")
    return {
        "decision": decision,
        "reason": reason,
        "sources": sources,
        "ncaa_http": ncaa_http,
        "verified_official": decision in VERIFIED_DECISIONS,
        "pregame_available": False,
    }


def decide_domain(game: Mapping[str, Any], domain: str) -> dict[str, Any]:
    if domain not in DOMAIN_COLUMNS:
        raise AuthorityViolation(f"unknown domain {domain}")
    if game.get("name_only_promotion"):
        raise AuthorityViolation("silent name-only merge")
    if game.get("contest_id") or game.get("contest_id_fabricated"):
        raise AuthorityViolation("invented contest IDs are forbidden")
    if game.get("pregame_availability") is True:
        raise AuthorityViolation("participation must not be relabeled availability")
    conflicts = list(game.get("conflicts") or [])
    recon = str(game.get("reconciliation_state") or "")
    official = game.get("official_box")
    official_status = str(game.get("official_match_status") or "")
    if domain == "pregame_availability":
        return _decision(
            decision="SOURCE_EVIDENCE_ABSENT",
            reason="NO_TIMESTAMPED_PREGAME_EVIDENCE",
            sources=["none"],
        )
    if domain == "roster_membership":
        return _decision(
            decision="CANDIDATE_ONLY",
            reason="SEASON_MEMBERSHIP_NOT_GAME_AVAILABILITY",
            sources=["bat567_roster_gate"],
        )
    if domain == "participation" and official_domain_present(official, "participation"):
        return _decision(
            decision="VERIFIED_OFFICIAL_POSTGAME_FACT",
            reason="OFFICIAL_SCHOOL_PARTICIPATION_IS_NOT_AVAILABILITY",
            sources=["official_src014"],
        )
    if domain == "participation":
        return _decision(
            decision="SOURCE_EVIDENCE_ABSENT",
            reason="NO_2010_2011_GAMEBOOK_PARTICIPATION",
            sources=["wmt_gap"],
        )
    if domain == "linescore_game_info":
        if "DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT" in conflicts:
            return _decision(
                decision="CONFLICT_REVIEW_REQUIRED",
                reason="DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT",
                sources=["sidearm", "ncaa_legacy"],
            )
        if official_status == TEXAS_DISPOSITION and official_domain_present(official, domain):
            return _decision(
                decision="VERIFIED_CROSS_SOURCE_POSTGAME_FACT",
                reason="OFFICIAL_SCHOOL_BOX_PLUS_NCAA_LEGACY_SIDEARM_DATE_LOST_AUTHORITY",
                sources=["official_src014", "ncaa_legacy", "sidearm"],
            )
        if official_domain_present(official, domain):
            return _decision(
                decision="VERIFIED_OFFICIAL_POSTGAME_FACT",
                reason="OFFICIAL_SCHOOL_BOXSCORE_LINESCORE",
                sources=["official_src014"],
            )
        if recon == "UNRESOLVED_NAME_ONLY_NOT_PROMOTED":
            return _decision(
                decision="CANDIDATE_ONLY",
                reason="SIDEARM_SCHEDULE_ONLY_NAME_ONLY_NCAA_NOT_PROMOTED",
                sources=["sidearm"],
            )
        return _decision(
            decision="CANDIDATE_ONLY",
            reason="SIDEARM_SCHEDULE_METADATA_NOT_POSTGAME_GAMEBOOK",
            sources=["sidearm"],
        )
    if domain == "venue":
        if official_domain_present(official, domain):
            return _decision(
                decision="VERIFIED_OFFICIAL_POSTGAME_FACT",
                reason="OFFICIAL_SCHOOL_BOXSCORE_VENUE",
                sources=["official_src014"],
            )
        if "NCAA_SITE_HINT_AWAY_CONFLICTS_WITH_SIDEARM_VENUE" in conflicts:
            return _decision(
                decision="CONFLICT_REVIEW_REQUIRED",
                reason="NCAA_SITE_HINT_AWAY_CONFLICTS_WITH_SIDEARM_VENUE",
                sources=["sidearm", "ncaa_legacy"],
            )
        return _decision(
            decision="CANDIDATE_ONLY",
            reason="SIDEARM_VS_OR_AT_ONLY",
            sources=["sidearm"],
        )
    if domain in NCAA_CONTEST_DOMAINS:
        if official_domain_present(official, domain):
            reason = "OFFICIAL_SCHOOL_BOXSCORE_POSTGAME_FACT"
            if domain == "team_statistics_by_period":
                reason = "OFFICIAL_QUARTER_SCORES_NOT_FULL_PERIOD_TEAM_STATS"
            if domain == "player_statistics":
                reason = "OFFICIAL_PLAYER_STAT_CANDIDATES_IDENTITY_NOT_CANONICAL"
            return _decision(
                decision="VERIFIED_OFFICIAL_POSTGAME_FACT",
                reason=reason,
                sources=["official_src014"],
                ncaa_http="NOT_ATTEMPTED_NO_CONTEST_ID",
            )
        return _decision(
            decision="SOURCE_EVIDENCE_ABSENT",
            reason="NCAA_CONTEST_ID_ABSENT_AND_WMT_GAMEBOOK_GAP",
            sources=["ncaa_contest_absent", "wmt_gap"],
            ncaa_http="NOT_ATTEMPTED_NO_CONTEST_ID",
        )
    raise AuthorityViolation(f"unhandled domain {domain}")


def build_domain_rows(games: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for game in games:
        season = int(game["season"])
        if season not in {2010, 2011}:
            raise AuthorityViolation("gate population is 2010-2011 only")
        for domain in DOMAIN_COLUMNS:
            admitted = decide_domain(game, domain)
            if admitted["pregame_available"]:
                raise AuthorityViolation("participation must not be relabeled availability")
            row = {
                "row_identity": stable_hash(
                    {
                        "game_row_identity": game.get("row_identity"),
                        "season": season,
                        "game_date": game.get("game_date"),
                        "opponent_name": game.get("opponent_name"),
                        "domain": domain,
                    }
                ),
                "season": season,
                "game_date": game.get("game_date"),
                "opponent_name": game.get("opponent_name"),
                "game_row_identity": game.get("row_identity"),
                "reconciliation_state": game.get("reconciliation_state"),
                "name_only_unpromoted": game.get("reconciliation_state")
                == "UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
                "domain": domain,
                **admitted,
            }
            rows.append(row)
    rows.sort(key=lambda item: (item["season"], str(item["game_date"]), str(item["domain"]), item["row_identity"]))
    if len(rows) != len(games) * len(DOMAIN_COLUMNS):
        raise AuthorityViolation("game-domain cardinality drifted")
    return rows


def summarize_rows(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_decision = {key: 0 for key in ADMITTED_DECISIONS}
    for row in rows:
        by_decision[str(row["decision"])] += 1
    return {
        "games_2010": len({row["game_row_identity"] for row in rows if int(row["season"]) == 2010}),
        "games_2011": len({row["game_row_identity"] for row in rows if int(row["season"]) == 2011}),
        "scheduled_games": len({row["game_row_identity"] for row in rows}),
        "domains": len(DOMAIN_COLUMNS),
        "domain_rows": len(rows),
        "contest_ids_2010": 0,
        "contest_ids_2011": 0,
        "contest_ids_present": 0,
        "verified_official": by_decision["VERIFIED_OFFICIAL_POSTGAME_FACT"],
        "verified_cross_source": by_decision["VERIFIED_CROSS_SOURCE_POSTGAME_FACT"],
        "candidate_only": by_decision["CANDIDATE_ONLY"],
        "conflict_review_required": by_decision["CONFLICT_REVIEW_REQUIRED"],
        "technical_route_blocked": by_decision["TECHNICAL_ROUTE_BLOCKED"],
        "source_evidence_absent": by_decision["SOURCE_EVIDENCE_ABSENT"],
        "not_applicable": by_decision["NOT_APPLICABLE"],
        "name_only_promotions": 0,
        "pregame_availability_true": 0,
        "by_decision": by_decision,
    }


def load_phase3_games(data_root: Path, repo_root: Path) -> list[dict[str, Any]]:
    upstream = verify_upstream_gates(repo_root)
    phase3 = upstream["phase3"]
    parquet = Path(phase3["payload"]["payload"])
    if not parquet.is_file():
        parquet = (
            data_root
            / "features"
            / "tamu_official_evidence_gap_matrix"
            / "sha256"
            / PHASE3_MATRIX_IDENTITY
            / "game_rows.parquet"
        )
    if not parquet.is_file():
        raise FileNotFoundError("Phase 3 matrix payload is not mounted")
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("cross-source domain gate requires the optional data-engineering environment") from exc
    frame = polars.read_parquet(parquet).filter(polars.col("season").is_in([2010, 2011]))
    games = frame.to_dicts()
    if len(games) != 26:
        raise AuthorityViolation(f"expected 26 Phase 3 2010-2011 games, found {len(games)}")
    for game in games:
        game["conflicts"] = json.loads(game.get("conflicts_json") or "[]")
        if game.get("name_only_promotion"):
            raise AuthorityViolation("silent name-only merge")
        if game.get("contest_id") or game.get("contest_id_fabricated"):
            raise AuthorityViolation("Phase 3 row unexpectedly carries a contest ID")
    official_games = load_official_compact_games(repo_root)
    return attach_official_boxes(games, official_games)


def expected_season_level_admissions(season_recon: Mapping[str, Any]) -> dict[str, Any]:
    domains: dict[str, dict[str, str]] = {}
    for domain, rows in (season_recon.get("domains") or {}).items():
        by_season: dict[str, str] = {}
        for row in rows:
            season = str(row.get("season"))
            classification = str(row.get("classification") or "")
            if classification == "VERIFIED_OFFICIAL":
                raise AuthorityViolation("season summary promoted to per-game VERIFIED_OFFICIAL")
            if bool(row.get("pregame_availability_eligible")):
                raise AuthorityViolation("retrospective season evidence marked pregame-eligible")
            by_season[season] = classification
        domains[str(domain)] = by_season
    by_classification = dict((season_recon.get("counts") or {}).get("by_classification") or {})
    admissions = {
        "grain": "SEASON_LEVEL_NOT_PER_GAME",
        "disposition": SEASON_RECON_DISPOSITION,
        "texas_2011": TEXAS_DISPOSITION,
        "by_classification": by_classification,
        "domains": domains,
        "per_game_verified_official": False,
        "development_pit_eligible_season_dates_2010": True,
        "pregame_availability_admitted": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
    }
    if admissions["texas_2011"] != TEXAS_DISPOSITION:
        raise AuthorityViolation("2011 Texas official strong tuple was not bound")
    if admissions["per_game_verified_official"]:
        raise AuthorityViolation("season total falsely promoted to per-game official")
    if admissions["pregame_availability_admitted"]:
        raise AuthorityViolation("participation must not be relabeled availability")
    return admissions


def expected_input_identities() -> dict[str, str]:
    return {
        "phase3_matrix_identity": PHASE3_MATRIX_IDENTITY,
        "phase3_gate_identity": PHASE3_GATE_IDENTITY,
        "phase4_acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
        "team_season_gate_identity": TEAM_SEASON_GATE_IDENTITY,
        "season_reconciliation_gate_identity": SEASON_RECON_GATE_IDENTITY,
        "contest_route_gate_identity": CONTEST_ROUTE_GATE_IDENTITY,
        "contest_route_manifest_identity": CONTEST_ROUTE_MANIFEST_IDENTITY,
        "official_boxscore_gate_identity": OFFICIAL_BOXSCORE_GATE_IDENTITY,
        "official_boxscore_dataset_identity": OFFICIAL_BOXSCORE_DATASET_IDENTITY,
        "union_gate_identity": UNION_GATE_IDENTITY,
        "union_identity": UNION_IDENTITY,
        "ncaa_official_national_acquisition_identity": NCAA_NATIONAL_IDENTITY,
        "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
        "wmt_reconciliation_dataset_identity": WMT_RECONCILIATION_IDENTITY,
        "team_box_snapshot_dataset_identity": TEAM_BOX_IDENTITY,
        "player_box_snapshot_dataset_identity": PLAYER_BOX_IDENTITY,
        "roster_gate_identity": ROSTER_GATE_IDENTITY,
        "protected_split_registry_sha256": REGISTRY_SHA256,
        "supersedes_cycle7_gate_identity": CYCLE7_GATE_IDENTITY,
    }


def expected_gate_document(
    *,
    contract: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
    bat_429: Mapping[str, Any],
    season_recon: Mapping[str, Any],
) -> dict[str, Any]:
    counts = summarize_rows(rows)
    if counts["scheduled_games"] != 26:
        raise AuthorityViolation("not every 2010-2011 scheduled game was classified")
    if counts["domain_rows"] != 26 * len(DOMAIN_COLUMNS):
        raise AuthorityViolation("domain-row cardinality drifted")
    if counts["verified_official"] and not any(
        row.get("sources") and "official_src014" in row.get("sources") for row in rows
    ):
        raise AuthorityViolation("verified official inflation without official-school evidence")
    if counts["technical_route_blocked"]:
        raise AuthorityViolation("TECHNICAL_ROUTE_BLOCKED claimed without HTTP evidence")
    if counts["contest_ids_present"]:
        raise AuthorityViolation("contest IDs were fabricated")
    if counts["pregame_availability_true"]:
        raise AuthorityViolation("participation must not be relabeled availability")
    season_level = expected_season_level_admissions(season_recon)
    owner = current_evidence_owner(contract)
    official_scope = expected_official_fact_scope(counts)
    nonclaims = expected_scientific_nonclaims(counts)
    if official_scope["verified_official_postgame_facts_present"] != (
        counts["verified_official"] > 0
    ):
        raise AuthorityViolation("official-fact presence drifted from admitted count")
    if official_scope["verified_official_postgame_fact_count"] != counts["verified_official"]:
        raise AuthorityViolation("official-fact count drifted from admitted rows")
    if official_scope["full_historical_official_completeness_claimed"]:
        raise AuthorityViolation("full historical official completeness forged")
    if official_scope["ncaa_contest_official_evidence_claimed"]:
        raise AuthorityViolation("NCAA contest official evidence forged")
    if nonclaims["verified_official_claimed"] or official_scope["deprecated_verified_official_claimed"]:
        raise AuthorityViolation("deprecated verified-official claim opened")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_CROSS_SOURCE_DOMAIN_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": "BAT-572",
        "rebound_jira_key": owner["rebound_jira_key"],
        "input_identities": expected_input_identities(),
        "phase4_disposition": PHASE4_DISPOSITION,
        "contest_route_disposition": CONTEST_ROUTE_DISPOSITION,
        "counts": counts,
        "admissions": expected_admissions(),
        "season_level_admissions": season_level,
        "authority": expected_authority(),
        "official_fact_scope": official_scope,
        "scientific_nonclaims": nonclaims,
        "remaining_blockers": expected_remaining_blockers(),
        "bat_429": dict(bat_429),
        "protected_lane": PROTECTED_LANE,
        "row_identities": [row["row_identity"] for row in rows],
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    verify_protected_registry(repo_root, contract)
    games = load_phase3_games(data_root, repo_root)
    rows = build_domain_rows(games)
    bat_429 = inspect_bat429(repo_root)
    season_recon = load_json(repo_root / "artifacts/data_lake/tamu_2010_2011_season_reconciliation_gate.json")
    gate = expected_gate_document(
        contract=contract,
        rows=rows,
        bat_429=bat_429,
        season_recon=season_recon,
    )
    return {
        "contract": contract,
        "games": games,
        "rows": rows,
        "gate": gate,
        "bat_429": bat_429,
        "season_recon": season_recon,
    }


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    payload_root = (
        data_root
        / "features"
        / "tamu_cross_source_domain_gate"
        / "sha256"
        / expected["gate"]["gate_identity"]
    )
    payload_path = payload_root / "domain_rows.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_CROSS_SOURCE_DOMAIN_ROWS",
        "gate_identity": expected["gate"]["gate_identity"],
        "phase4_disposition": PHASE4_DISPOSITION,
        "contest_route_disposition": CONTEST_ROUTE_DISPOSITION,
        "rows": expected["rows"],
        "protected_lane": PROTECTED_LANE,
    }
    payload_root.mkdir(parents=True, exist_ok=True)
    temporary = payload_path.with_name(payload_path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(canonical_json_bytes(payload) + b"\n")
        os.replace(temporary, payload_path)
    finally:
        temporary.unlink(missing_ok=True)
    gate = dict(expected["gate"])
    gate["issued_at_utc"] = issued_at_utc
    gate["payload"] = {
        "rows": str(payload_path),
        "sha256": sha256_file(payload_path),
        "row_count": len(expected["rows"]),
    }
    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        build_evidence_packet(
            repo_root=repo_root,
            gate=gate,
            owner=current_evidence_owner(expected["contract"]),
            contract=expected["contract"],
        ),
    )
    return {
        "gate_path": str(repo_root / GATE_RELATIVE),
        "gate_identity": gate["gate_identity"],
        "counts": gate["counts"],
        "payload": gate["payload"],
    }


def _evidence_outputs(repo_root: Path) -> list[dict[str, Any]]:
    outputs = []
    for relative in (
        GATE_RELATIVE,
        CONTRACT_RELATIVE,
        "src/aggie_analytics/data/tamu_cross_source_domain_gate.py",
        "tools/build_tamu_cross_source_domain_gate.py",
        "tools/validate_tamu_cross_source_domain_gate.py",
        "tests/test_tamu_cross_source_domain_gate.py",
    ):
        path = repo_root / relative
        if path.is_file():
            outputs.append(
                {
                    "path": relative.replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return outputs


def _recovered_domains(gate: Mapping[str, Any]) -> list[str]:
    by_decision = (gate.get("counts") or {}).get("by_decision") or {}
    recovered: list[str] = []
    if int(by_decision.get("VERIFIED_OFFICIAL_POSTGAME_FACT") or 0) or int(
        by_decision.get("VERIFIED_CROSS_SOURCE_POSTGAME_FACT") or 0
    ):
        recovered.extend(
            [
                "linescore_game_info",
                "venue",
                "attendance",
                "officials",
                "team_statistics",
                "team_statistics_by_period",
                "player_statistics",
                "drives",
                "play_by_play",
                "scoring_summary",
                "participation",
            ]
        )
    if "roster_membership" not in recovered:
        recovered.append("roster_membership")
    return recovered


def build_observable_outcome(gate: Mapping[str, Any], owner: Mapping[str, Any]) -> str:
    counts = gate["counts"]
    identities = gate.get("input_identities") or {}
    outcome = (
        f"BAT-572 evidence is derived from the current domain gate {gate['gate_identity']} "
        f"with current rebound owner {owner['rebound_jira_key']}. Correction owner "
        f"{owner['correction_jira_key']} binds current relationships "
        f"{','.join(owner['current_relationship_set'])}. "
        f"Counts: {counts['verified_official']} VERIFIED_OFFICIAL_POSTGAME_FACT, "
        f"{counts['verified_cross_source']} VERIFIED_CROSS_SOURCE_POSTGAME_FACT, "
        f"{counts['candidate_only']} CANDIDATE_ONLY, "
        f"{counts['source_evidence_absent']} SOURCE_EVIDENCE_ABSENT. "
        f"NCAA contest IDs remain {counts['contest_ids_present']}. "
        f"Contest-route disposition remains {gate['contest_route_disposition']} "
        f"with manifest identity {identities.get('contest_route_manifest_identity')}. "
        f"Superseded owners remain only in supersession_history. "
        f"Protected lane stays {gate['protected_lane']}. BAT-429 stays blocked. "
        f"BAT-523 stays In Progress."
    )
    if "Cycle #8" in outcome:
        raise AuthorityViolation("stale Cycle #8 narrative")
    return outcome


def build_evidence_packet(
    *,
    repo_root: Path,
    gate: Mapping[str, Any],
    owner: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if contract is not None:
        owner = current_evidence_owner(contract)
    rebound = str(gate.get("rebound_jira_key") or "")
    if rebound != owner["rebound_jira_key"]:
        raise AuthorityViolation("current gate/evidence ownership mismatch")
    if rebound in owner["superseded_rebound_owners"]:
        raise AuthorityViolation("superseded owner presented as current")
    missing_current = [
        key for key in owner["current_relationship_set"] if key not in owner["related_jira_keys"]
    ]
    if missing_current:
        raise AuthorityViolation("BAT-581 removed from the current relationship set")
    recovered = _recovered_domains(gate)
    missing = [domain for domain in DOMAIN_COLUMNS if domain not in recovered]
    packet = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "evidence_manifest_type": "jira_issue_completion_evidence",
        "jira_key": owner["gate_jira_key"],
        "local_issue_id": owner["local_issue_id"],
        "parent_jira_key": owner["parent_jira_key"],
        "correction_jira_key": owner["correction_jira_key"],
        "correction_local_issue_id": owner["correction_local_issue_id"],
        "related_jira_keys": list(owner["related_jira_keys"]),
        "current_relationship_set": list(owner["current_relationship_set"]),
        "rebound_jira_key": rebound,
        "supersession_history": list(owner["supersession_history"]),
        "new_issue_decision": "CREATE",
        "workflow_state": "DONE",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "completeness_claimed": False,
        "verified_official_claimed": False,
        "official_fact_scope": dict(gate["official_fact_scope"]),
        "observable_outcome": build_observable_outcome(gate, owner),
        "outputs": _evidence_outputs(repo_root),
        "gate_identity": gate["gate_identity"],
        "phase3_identities": {
            "matrix_identity": PHASE3_MATRIX_IDENTITY,
            "gate_identity": PHASE3_GATE_IDENTITY,
        },
        "phase4_identities": {
            "acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
            "disposition": PHASE4_DISPOSITION,
        },
        "current_identities": {
            "team_season_gate_identity": TEAM_SEASON_GATE_IDENTITY,
            "season_reconciliation_gate_identity": SEASON_RECON_GATE_IDENTITY,
            "contest_route_gate_identity": CONTEST_ROUTE_GATE_IDENTITY,
            "contest_route_disposition": CONTEST_ROUTE_DISPOSITION,
            "contest_route_manifest_identity": CONTEST_ROUTE_MANIFEST_IDENTITY,
            "official_boxscore_gate_identity": OFFICIAL_BOXSCORE_GATE_IDENTITY,
            "official_boxscore_dataset_identity": OFFICIAL_BOXSCORE_DATASET_IDENTITY,
            "union_gate_identity": UNION_GATE_IDENTITY,
            "union_identity": UNION_IDENTITY,
        },
        "ncaa_official_national_acquisition_identity": NCAA_NATIONAL_IDENTITY,
        "coverage": {
            "seasons": [2010, 2011],
            "games": gate["counts"]["scheduled_games"],
            "domain_rows": gate["counts"]["domain_rows"],
            "recovered_domains": recovered,
            "missing_domains": missing,
            "ncaa_contest_domains_still_absent": ["ncaa_contest_identity"],
            "roster_membership": "CANDIDATE_ONLY_NOT_AVAILABILITY",
            "by_decision": gate["counts"]["by_decision"],
        },
        "admissions": gate["admissions"],
        "protected_nonclaims": gate["scientific_nonclaims"],
        "bat_429": gate["bat_429"],
    }
    if "Cycle #8" in packet["observable_outcome"]:
        raise AuthorityViolation("stale Cycle #8 narrative")
    return packet


def validate_evidence(
    *,
    repo_root: Path,
    gate: Mapping[str, Any],
    evidence: Mapping[str, Any] | None = None,
    owner: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if contract is None:
        contract = load_contract(repo_root)
    if owner is None:
        owner = current_evidence_owner(contract)
    rebuilt = build_evidence_packet(repo_root=repo_root, gate=gate, owner=owner, contract=contract)
    live = evidence
    if live is None:
        live = load_json(repo_root / EVIDENCE_RELATIVE)
    if live.get("rebound_jira_key") != rebuilt["rebound_jira_key"]:
        raise AuthorityViolation("current gate/evidence ownership mismatch")
    if live.get("rebound_jira_key") in owner["superseded_rebound_owners"]:
        raise AuthorityViolation("superseded owner presented as current")
    if "Cycle #8" in str(live.get("observable_outcome") or ""):
        raise AuthorityViolation("stale Cycle #8 narrative")
    for key in owner["current_relationship_set"]:
        if key not in (live.get("related_jira_keys") or []) and key not in (
            live.get("current_relationship_set") or []
        ):
            raise AuthorityViolation(f"{key} removed from the current relationship set")
    if live.get("official_fact_scope") != rebuilt["official_fact_scope"]:
        raise AuthorityViolation("official-fact scope drifted from current gate")
    if live.get("gate_identity") != gate.get("gate_identity"):
        raise AuthorityViolation("current gate/evidence ownership mismatch")
    comparable_live = {key: live[key] for key in rebuilt if key != "outputs"}
    comparable_rebuilt = {key: rebuilt[key] for key in rebuilt if key != "outputs"}
    if comparable_live != comparable_rebuilt:
        raise AuthorityViolation("evidence packet drifted from current gate and owner inputs")
    return {"result": "PASS", "rebound_jira_key": rebuilt["rebound_jira_key"]}


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    verify_protected_registry(repo_root, contract)
    inspect_bat429(repo_root)
    if expected is None and require_rebuild:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    if expected is None:
        raise AuthorityViolation("expected document required when rebuild is skipped")
    rebuilt = expected_gate_document(
        contract=expected["contract"],
        rows=expected["rows"],
        bat_429=expected["bat_429"],
        season_recon=expected["season_recon"],
    )
    live_artifact = gate is None
    if live_artifact:
        gate = load_json(repo_root / GATE_RELATIVE)
    observed = {key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate}
    desired = {key: rebuilt[key] for key in GATE_IDENTITY_FIELDS}
    if observed != desired:
        raise AuthorityViolation("domain gate drifted from rebuilt identity-bound document")
    if gate.get("gate_identity") != compute_gate_identity(gate):
        raise AuthorityViolation("forged terminal state after rehash")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane must remain blocked")
    owner = current_evidence_owner(contract)
    if gate.get("rebound_jira_key") != owner["rebound_jira_key"]:
        raise AuthorityViolation("current gate/evidence ownership mismatch")
    if gate.get("rebound_jira_key") in owner["superseded_rebound_owners"]:
        raise AuthorityViolation("superseded owner presented as current")
    scope = gate.get("official_fact_scope") or {}
    counts = gate.get("counts") or {}
    if scope.get("verified_official_postgame_fact_count") != counts.get("verified_official"):
        raise AuthorityViolation("official-fact count drifted from admitted rows")
    if bool(scope.get("verified_official_postgame_facts_present")) != (
        int(counts.get("verified_official") or 0) > 0
    ):
        raise AuthorityViolation("official-fact presence drifted from admitted count")
    if scope.get("full_historical_official_completeness_claimed"):
        raise AuthorityViolation("full historical official completeness forged")
    if scope.get("ncaa_contest_official_evidence_claimed"):
        raise AuthorityViolation("NCAA contest official evidence forged")
    nonclaims = gate.get("scientific_nonclaims") or {}
    if nonclaims.get("full_historical_official_completeness_claimed"):
        raise AuthorityViolation("full historical official completeness forged")
    if nonclaims.get("ncaa_contest_official_evidence_claimed"):
        raise AuthorityViolation("NCAA contest official evidence forged")
    if nonclaims.get("verified_official_claimed"):
        raise AuthorityViolation("verified official inflation")
    if gate.get("scientific_nonclaims", {}).get("pregame_availability_admitted"):
        raise AuthorityViolation("participation must not be relabeled availability")
    if gate.get("scientific_nonclaims", {}).get("participation_used_as_availability"):
        raise AuthorityViolation("participation must not be relabeled availability")
    if gate.get("authority", {}).get("participation_as_availability"):
        raise AuthorityViolation("participation must not be relabeled availability")
    if gate.get("authority", {}).get("bat_429_ready_or_done"):
        raise AuthorityViolation("BAT-429 marked Ready")
    if gate.get("bat_429", {}).get("ready_or_done"):
        raise AuthorityViolation("BAT-429 marked Ready")
    identities = gate.get("input_identities") or {}
    if identities.get("phase3_matrix_identity") != PHASE3_MATRIX_IDENTITY:
        raise AuthorityViolation("missing Phase 3 matrix bind")
    if identities.get("phase3_gate_identity") != PHASE3_GATE_IDENTITY:
        raise AuthorityViolation("missing Phase 3 gate bind")
    if identities.get("phase4_acquisition_identity") != PHASE4_ACQUISITION_IDENTITY:
        raise AuthorityViolation("missing Phase 4 acquisition bind")
    if identities.get("team_season_gate_identity") != TEAM_SEASON_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-574 team-season bind")
    if identities.get("season_reconciliation_gate_identity") != SEASON_RECON_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-575 season-reconciliation bind")
    if identities.get("contest_route_gate_identity") != CONTEST_ROUTE_GATE_IDENTITY:
        raise AuthorityViolation("missing BAT-576 contest-route bind")
    if identities.get("ncaa_official_national_acquisition_identity") != NCAA_NATIONAL_IDENTITY:
        raise AuthorityViolation("missing BAT-554 national NCAA bind")
    if gate.get("phase4_disposition") != PHASE4_DISPOSITION:
        raise AuthorityViolation("Phase 4 disposition drift")
    if gate.get("contest_route_disposition") != CONTEST_ROUTE_DISPOSITION:
        raise AuthorityViolation("contest-route disposition drift")
    season_level = gate.get("season_level_admissions") or {}
    if season_level.get("grain") != "SEASON_LEVEL_NOT_PER_GAME":
        raise AuthorityViolation("season-level grain missing")
    if season_level.get("per_game_verified_official"):
        raise AuthorityViolation("season total falsely promoted to per-game official")
    if season_level.get("texas_2011") != TEXAS_DISPOSITION:
        raise AuthorityViolation("2011 Texas official strong tuple was not bound")
    if season_level.get("pregame_availability_admitted"):
        raise AuthorityViolation("participation must not be relabeled availability")
    if season_level.get("membership_as_availability"):
        raise AuthorityViolation("membership must not be relabeled availability")
    if require_rebuild and expected["gate"]["gate_identity"] != rebuilt["gate_identity"]:
        raise AuthorityViolation("gate identity rebuild mismatch")
    if live_artifact:
        validate_evidence(repo_root=repo_root, gate=gate, contract=contract, owner=owner)
    return {
        "result": "PASS",
        "gate_identity": rebuilt["gate_identity"],
        "counts": rebuilt["counts"],
        "protected_lane": PROTECTED_LANE,
        "rebound_jira_key": owner["rebound_jira_key"],
    }
