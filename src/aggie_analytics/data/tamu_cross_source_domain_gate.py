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


SCHEMA_VERSION = "aggie.data.tamu_cross_source_domain_gate.v1"
CONTRACT_RELATIVE = "configs/tamu_cross_source_domain_gate_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_cross_source_domain_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CROSS-SOURCE-DOMAIN-GATE-001.json"
CONTRACT_ID = "BAT-572-TAMU-CROSS-SOURCE-DOMAIN-GATE-V1"
PASS_RESULT = "PASS_IDENTITY_BOUND_DOMAIN_GATE_NO_VERIFIED_OFFICIAL"
PASS_CLASSIFICATION = "TAMU_2010_2011_CROSS_SOURCE_DOMAIN_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PHASE3_MATRIX_IDENTITY = "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa"
PHASE3_GATE_IDENTITY = "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93"
PHASE4_ACQUISITION_IDENTITY = "349654307f5d46b979e65b12128da50f99e91c1f75627b9bd94ed6b83f21ae8f"
PHASE4_DISPOSITION = "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ENDPOINTS"
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
    "counts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "remaining_blockers",
    "bat_429",
    "protected_lane",
    "row_identities",
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
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("cross-source domain-gate contract identity drift")
    if contract.get("jira_key") != "BAT-572":
        raise AuthorityViolation("contract jira key drift")
    identities = contract["identities"]
    expected = {
        "phase3_matrix_identity": PHASE3_MATRIX_IDENTITY,
        "phase3_gate_identity": PHASE3_GATE_IDENTITY,
        "phase4_acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
        "phase4_disposition": PHASE4_DISPOSITION,
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


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
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
        "wmt_gamebook": "SOURCE_EVIDENCE_ABSENT_GAP_SEASONS",
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
        "WMT_GAMEBOOK_ABSENT_FOR_2010_2011",
        "NO_VERIFIED_OFFICIAL_POSTGAME_FACT",
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
        "verified_official": False,
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
    if domain == "pregame_availability":
        return _decision(
            decision="SOURCE_EVIDENCE_ABSENT",
            reason="NO_TIMESTAMPED_PREGAME_EVIDENCE",
            sources=["none"],
        )
    if domain == "participation":
        return _decision(
            decision="SOURCE_EVIDENCE_ABSENT",
            reason="NO_2010_2011_GAMEBOOK_PARTICIPATION",
            sources=["wmt_gap"],
        )
    if domain == "roster_membership":
        return _decision(
            decision="CANDIDATE_ONLY",
            reason="SEASON_MEMBERSHIP_NOT_GAME_AVAILABILITY",
            sources=["bat567_roster_gate"],
        )
    if domain == "linescore_game_info":
        if "DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT" in conflicts:
            return _decision(
                decision="CONFLICT_REVIEW_REQUIRED",
                reason="DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT",
                sources=["sidearm", "ncaa_legacy"],
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
            if admitted["decision"] in VERIFIED_DECISIONS:
                raise AuthorityViolation("verified official inflation")
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
    return games


def expected_input_identities() -> dict[str, str]:
    return {
        "phase3_matrix_identity": PHASE3_MATRIX_IDENTITY,
        "phase3_gate_identity": PHASE3_GATE_IDENTITY,
        "phase4_acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
        "ncaa_official_national_acquisition_identity": NCAA_NATIONAL_IDENTITY,
        "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
        "wmt_reconciliation_dataset_identity": WMT_RECONCILIATION_IDENTITY,
        "team_box_snapshot_dataset_identity": TEAM_BOX_IDENTITY,
        "player_box_snapshot_dataset_identity": PLAYER_BOX_IDENTITY,
        "roster_gate_identity": ROSTER_GATE_IDENTITY,
        "protected_split_registry_sha256": REGISTRY_SHA256,
    }


def expected_gate_document(
    *,
    contract: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
    bat_429: Mapping[str, Any],
) -> dict[str, Any]:
    counts = summarize_rows(rows)
    if counts["scheduled_games"] != 26:
        raise AuthorityViolation("not every 2010-2011 scheduled game was classified")
    if counts["domain_rows"] != 26 * len(DOMAIN_COLUMNS):
        raise AuthorityViolation("domain-row cardinality drifted")
    if counts["verified_official"] or counts["verified_cross_source"]:
        raise AuthorityViolation("verified official inflation")
    if counts["technical_route_blocked"]:
        raise AuthorityViolation("TECHNICAL_ROUTE_BLOCKED claimed without HTTP evidence")
    if counts["contest_ids_present"]:
        raise AuthorityViolation("contest IDs were fabricated")
    if counts["pregame_availability_true"]:
        raise AuthorityViolation("participation must not be relabeled availability")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_CROSS_SOURCE_DOMAIN_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": "BAT-572",
        "input_identities": expected_input_identities(),
        "phase4_disposition": PHASE4_DISPOSITION,
        "counts": counts,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
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
    gate = expected_gate_document(contract=contract, rows=rows, bat_429=bat_429)
    return {"contract": contract, "games": games, "rows": rows, "gate": gate, "bat_429": bat_429}


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
    write_json(repo_root / EVIDENCE_RELATIVE, _evidence_packet(repo_root, gate))
    return {
        "gate_path": str(repo_root / GATE_RELATIVE),
        "gate_identity": gate["gate_identity"],
        "counts": gate["counts"],
        "payload": gate["payload"],
    }


def _evidence_packet(repo_root: Path, gate: Mapping[str, Any]) -> dict[str, Any]:
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
    recovered = ["linescore_game_info", "venue", "roster_membership"]
    missing = [domain for domain in DOMAIN_COLUMNS if domain not in recovered]
    return {
        "schema_version": "2.1.0",
        "evidence_manifest_type": "jira_issue_completion_evidence",
        "jira_key": "BAT-572",
        "local_issue_id": "POST-TASK-CROSS-SOURCE-DOMAIN-GATE-001",
        "parent_jira_key": "BAT-523",
        "related_jira_keys": [
            "BAT-570",
            "BAT-571",
            "BAT-523",
            "BAT-429",
            "BAT-548",
            "BAT-550",
            "BAT-554",
            "BAT-567",
        ],
        "new_issue_decision": "CREATE",
        "workflow_state": "IN_PROGRESS",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "completeness_claimed": False,
        "verified_official_claimed": False,
        "observable_outcome": (
            "Cycle #7 Phase 5 produced an identity-bound 2010-2011 Texas A&M field-grain domain "
            "admission gate over 26 scheduled games. Phase 4 remains "
            f"{PHASE4_DISPOSITION} with contest counts 0/0. No VERIFIED_OFFICIAL rows. "
            "Protected lane stays RETAIN_PROTECTED_LANE_BLOCKED. BAT-429 stays blocked. "
            "BAT-523 stays In Progress."
        ),
        "outputs": outputs,
        "gate_identity": gate["gate_identity"],
        "phase3_identities": {
            "matrix_identity": PHASE3_MATRIX_IDENTITY,
            "gate_identity": PHASE3_GATE_IDENTITY,
        },
        "phase4_identities": {
            "acquisition_identity": PHASE4_ACQUISITION_IDENTITY,
            "disposition": PHASE4_DISPOSITION,
        },
        "ncaa_official_national_acquisition_identity": NCAA_NATIONAL_IDENTITY,
        "coverage": {
            "seasons": [2010, 2011],
            "games": gate["counts"]["scheduled_games"],
            "domain_rows": gate["counts"]["domain_rows"],
            "recovered_domains": recovered,
            "missing_domains": missing,
            "by_decision": gate["counts"]["by_decision"],
        },
        "admissions": gate["admissions"],
        "protected_nonclaims": gate["scientific_nonclaims"],
        "bat_429": gate["bat_429"],
    }


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
    if gate.get("counts", {}).get("verified_official"):
        raise AuthorityViolation("verified official inflation")
    if gate.get("scientific_nonclaims", {}).get("verified_official_claimed"):
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
    if identities.get("ncaa_official_national_acquisition_identity") != NCAA_NATIONAL_IDENTITY:
        raise AuthorityViolation("missing BAT-554 national NCAA bind")
    if gate.get("phase4_disposition") != PHASE4_DISPOSITION:
        raise AuthorityViolation("Phase 4 disposition drift")
    if require_rebuild and expected["gate"]["gate_identity"] != rebuilt["gate_identity"]:
        raise AuthorityViolation("gate identity rebuild mismatch")
    return {
        "result": "PASS",
        "gate_identity": rebuilt["gate_identity"],
        "counts": rebuilt["counts"],
        "protected_lane": PROTECTED_LANE,
    }
