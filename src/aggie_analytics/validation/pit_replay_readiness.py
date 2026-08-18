from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.experimentation.walk_forward import (
    DATASET_IDENTITY,
    consume_for_bat401,
    freeze_split_boundaries,
    validate_walk_forward_artifact,
)

SCHEMA_VERSION = "aggie.pit.replay_readiness.v1"
LANE_DECISION = "RETAIN_PROTECTED_LANE_BLOCKED"
STALE_ZERO_ROW_IDENTITY = "7c4b170a85d7aa8053bbbad099b8569cff6676580f18f46f375bbece8a53b3d1"
BAT399_IDENTITY = "2be6b713722382b2c0ea5e86f89a6e6ed57533bab3adbb0bc3cf3a77b46df13a"
BAT400_IDENTITY = "db1aca47c24b86e71f5669cc2aa8b707a686bf6e2fb9154d85642a5aaacdd402"
BAT398_SHA256 = "9f1755bba326678dee2e4daac92a693d8dc98ed9124805d5c53c88d12c5a1208"
BAT526_SUPERSEDED_V2_IDENTITY = "13c18600b5dfd4ce24422d1aae058fc0ae177057e72334f37b726e27840059d5"
BAT526_IDENTITY = "587725fe3396ca73e94ebf3647b4db8ad95e7c25d44b684a9231eceba3c465bd"
BAT566_SUPERSEDED_KICKOFF_LABEL = "902f3558a466a3cc26def6f24285032c2d012c0adeaf5bf5a2cfb47101a99cb2"
BAT566_SUPERSEDED_REPLAY = "584fefb812e36c08c54af5f66df1c49b3cc0ab51b6b45200b88b3b4855b35fd7"
BAT568_GATE_IDENTITY = "24c78874c69dd1fe0e84875451c7ef4a50e74d5381139194d7eee25ff05c969e"
BAT570_MATRIX_IDENTITY = "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa"
BAT570_GATE_IDENTITY = "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93"
BAT571_ACQUISITION_IDENTITY = "349654307f5d46b979e65b12128da50f99e91c1f75627b9bd94ed6b83f21ae8f"
BAT571_DISPOSITION = "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ENDPOINTS"
BAT574_GATE_IDENTITY = "dc06984fa17285abf6e9d32a362dd1515ff528fed82eff77254fb8abb702d91e"
BAT574_DISPOSITION = "TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED"
BAT575_GATE_IDENTITY = "c8ee22b6ba8a5ad1bb7a84fdc74f9c2fb6dd703f5108a953205377798c33b066"
BAT575_DISPOSITION = "SEASON_LEVEL_RECONCILED_WITH_PRESERVED_TEXAS_SIDEARM_DATE_CONFLICT"
BAT575_TEXAS = "RESOLVED_OFFICIAL_STRONG_TUPLE_SIDEARM_DATE_CONFLICT_PRESERVED"
BAT576_GATE_IDENTITY = "d0a2c7218bf9892dfc468f534e41555ab880cb3d41c2d77413dd10ecc923c039"
BAT576_DISPOSITION = "OFFICIAL_ROUTE_ACCESS_BLOCKED"
FORBIDDEN_LEDGER_STATES = (
    "PRODUCTION_CHAMPION",
    "PROTECTED_WINNER",
    "PROMOTED_FEATURE_SET",
)
AUTHORITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "decision_unit",
    "jira_key",
    "issue_status",
    "lane_decision",
    "remaining_lane_blockers",
    "acceptance_matrix",
    "prerequisite_identities",
    "protected_metrics_republished",
    "stale_zero_row_language_superseded",
)
REQUIRED_ACCEPTANCE = (
    "bat399_future_postgame_invariance_consumed",
    "bat400_development_safe_replay_consumed",
    "gap_005_remains_open",
    "prerequisites_linked_and_lane_blockers_explicit",
)
LANE_BLOCKERS = (
    {
        "id": "PRIOR_PROTECTED_RESULT_EXPOSURE",
        "summary": "2024-2025 protected results were previously exposed through the mislabeled preliminary lane.",
        "authority_required": "User/governance authority to define any new protected period or to restore selection/promotion authority. The sealed registry must not be altered without that authority.",
    },
    {
        "id": "HISTORICAL_DOMAIN_COMPLETENESS_UNRESOLVED",
        "summary": "BAT-523 is a scoped 2010-2022 team-outcome / 2023-2025 prior-feature population, not a complete historical domain.",
        "authority_required": "Verified plays, drives, rosters, and remaining domain coverage with a new content-addressed identity.",
    },
    {
        "id": "BAT400_IS_DEVELOPMENT_SAFE_DRY_RUN_ONLY",
        "summary": "BAT-400 executed development-safe walk-forward on 2023 features and produced no protected metrics.",
        "authority_required": "A later protected-evaluation protocol and artifact, not a filename or dry-run reuse.",
    },
    {
        "id": "NO_NEW_PROTECTED_PERIOD_AUTHORIZED",
        "summary": "No replacement protected period may be invented from this gate.",
        "authority_required": "Explicit user/governance authority. PROTECTED_SPLIT_REGISTRY.csv remains unaltered.",
    },
    {
        "id": "PROTECTED_EVALUATION_SEALED",
        "summary": "Protected-result access remains SEALED_UNTIL_PROTOCOL_AND_ARTIFACT_READY.",
        "authority_required": "Sealed protocol plus independently validated protected-evaluation artifacts.",
    },
)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def compute_artifact_identity(payload: Mapping[str, Any]) -> str:
    mutable = dict(payload)
    mutable.pop("artifact_identity", None)
    return hashlib.sha256(canonical_json(mutable)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prerequisites(repo_root: Path) -> dict[str, Any]:
    bat398_path = repo_root / "artifacts" / "pit" / "matrix_gate_decision.json"
    bat399_path = repo_root / "artifacts" / "pit" / "leakage_battery_results.json"
    bat400_path = repo_root / "artifacts" / "pit" / "protected_replay_dry_run.json"
    bat526_path = repo_root / "artifacts" / "governance" / "protected_split_exposure_audit.json"
    bat566_path = repo_root / "artifacts" / "pit" / "development_walk_forward_2023.json"
    bat568_path = repo_root / "artifacts" / "pit" / "development_rankings_walk_forward_2023.json"
    bat569_path = repo_root / "artifacts" / "experimentation" / "development_candidate_evidence_ledger.json"
    bat570_path = repo_root / "artifacts" / "data_lake" / "tamu_official_evidence_gap_matrix_gate.json"
    bat571_path = repo_root / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_official_acquisition_gate.json"
    bat572_path = repo_root / "artifacts" / "data_lake" / "tamu_cross_source_domain_gate.json"
    bat574_path = repo_root / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_team_season_evidence_gate.json"
    bat575_path = repo_root / "artifacts" / "data_lake" / "tamu_2010_2011_season_reconciliation_gate.json"
    bat576_path = repo_root / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_contest_route_discovery_gate.json"
    bat398 = _load_json(bat398_path)
    bat399 = _load_json(bat399_path)
    bat400 = _load_json(bat400_path)
    bat526 = _load_json(bat526_path)
    bat566 = _load_json(bat566_path)
    bat568 = _load_json(bat568_path)
    bat569 = _load_json(bat569_path)
    bat570 = _load_json(bat570_path)
    bat571 = _load_json(bat571_path)
    bat572 = _load_json(bat572_path)
    bat574 = _load_json(bat574_path)
    bat575 = _load_json(bat575_path)
    bat576 = _load_json(bat576_path)
    if sha256_file(bat398_path) != BAT398_SHA256:
        raise ValueError("BAT-398 decision hash mismatch")
    if bat398.get("gate_decision", {}).get("decision") != "BLOCK":
        raise ValueError("BAT-398 historical decision must remain pinned as BLOCK")
    if bat398.get("matrix_identity", {}).get("dataset_identity") != STALE_ZERO_ROW_IDENTITY:
        raise ValueError("BAT-398 zero-row identity drifted")
    if bat399.get("artifact_identity") != BAT399_IDENTITY or bat399.get("status") != "DONE":
        raise ValueError("BAT-399 is not the verified leakage-battery identity")
    validate_walk_forward_artifact(bat400, repo_root)
    consume_for_bat401(bat400)
    if bat400.get("artifact_identity") != BAT400_IDENTITY:
        raise ValueError("BAT-400 identity mismatch")
    if bat526.get("artifact_identity") != BAT526_IDENTITY:
        raise ValueError("BAT-526 audit identity mismatch")
    if bat526.get("artifact_identity") == BAT526_SUPERSEDED_V2_IDENTITY:
        raise ValueError("BAT-526 still publishes the superseded v2 identity")
    if bat526.get("supersedes_artifact_identity") != BAT526_SUPERSEDED_V2_IDENTITY:
        raise ValueError("BAT-526 must supersede the stale v2 identity")
    superseded_ids = {
        item.get("artifact_identity")
        for item in (bat526.get("superseded_identities") or [])
        if isinstance(item, dict)
    }
    if BAT526_SUPERSEDED_V2_IDENTITY not in superseded_ids:
        raise ValueError("BAT-526 missing superseded v2 identity")
    if bat566.get("input_identities", {}).get("bat565_label_dataset_identity") == BAT566_SUPERSEDED_KICKOFF_LABEL:
        raise ValueError("BAT-566 still consumes the superseded kickoff-time label identity")
    if bat566.get("replay_identity") == BAT566_SUPERSEDED_REPLAY:
        raise ValueError("BAT-566 still publishes the superseded kickoff-time replay identity")
    if bat566.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise ValueError("BAT-566 unexpectedly opened protected evaluation")
    if bat566.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise ValueError("BAT-566 unexpectedly granted promotion authority")
    if (bat566.get("incremental_play_drive_result") or {}).get("promotion_authority") is not False:
        raise ValueError("BAT-566 incremental result granted promotion authority")
    if bat568.get("gate_identity") != BAT568_GATE_IDENTITY:
        raise ValueError("BAT-568 gate identity mismatch")
    if bat568.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise ValueError("BAT-568 unexpectedly opened protected evaluation")
    if bat568.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise ValueError("BAT-568 unexpectedly granted promotion authority")
    if bat568.get("candidate_decisions", {}).get("any_candidate_improved_brier_vs_prior_only") is not False:
        raise ValueError("BAT-568 cannot be rebound as an improved protected candidate")
    if bat569.get("result") != "PASS_DEVELOPMENT_CANDIDATE_EVIDENCE_LEDGER":
        raise ValueError("BAT-569 ledger is not in the verified development-inventory state")
    if bat569.get("comparison_count") != 4:
        raise ValueError("BAT-569 comparison count drifted")
    if bat569.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise ValueError("BAT-569 unexpectedly granted promotion authority")
    if bat569.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise ValueError("BAT-569 unexpectedly opened protected evaluation")
    ledger_states = [entry.get("state") for entry in bat569.get("entries") or []]
    if any(state in FORBIDDEN_LEDGER_STATES for state in ledger_states):
        raise ValueError("BAT-569 ledger contains forbidden production or protected states")
    if bat570.get("matrix_identity") != BAT570_MATRIX_IDENTITY:
        raise ValueError("BAT-570 matrix identity mismatch")
    if bat570.get("gate_identity") != BAT570_GATE_IDENTITY:
        raise ValueError("BAT-570 gate identity mismatch")
    if bat570.get("admissions", {}).get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-570 unexpectedly opened the protected lane")
    if bat571.get("acquisition_identity") != BAT571_ACQUISITION_IDENTITY:
        raise ValueError("BAT-571 acquisition identity mismatch")
    if bat571.get("disposition") != BAT571_DISPOSITION:
        raise ValueError("BAT-571 disposition drift")
    if bat571.get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-571 unexpectedly opened the protected lane")
    if int((bat571.get("counts") or {}).get("contest_ids_present", -1)) != 0:
        raise ValueError("BAT-571 contest IDs drifted")
    if bat572.get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-572 unexpectedly opened the protected lane")
    if bat572.get("scientific_nonclaims", {}).get("verified_official_claimed"):
        raise ValueError("BAT-572 inflated a verified-official population claim")
    if bat572.get("season_level_admissions", {}).get("per_game_verified_official"):
        raise ValueError("BAT-572 season totals were promoted to per-game official")
    if bat572.get("input_identities", {}).get("phase3_matrix_identity") != BAT570_MATRIX_IDENTITY:
        raise ValueError("BAT-572 missing Phase 3 bind")
    if bat572.get("input_identities", {}).get("phase4_acquisition_identity") != BAT571_ACQUISITION_IDENTITY:
        raise ValueError("BAT-572 missing Phase 4 bind")
    if bat572.get("authority", {}).get("protected_outcome_authority") is not False:
        raise ValueError("BAT-572 unexpectedly granted protected outcome authority")
    if bat572.get("bat_429", {}).get("ready_or_done") is not False:
        raise ValueError("BAT-429 marked Ready")
    if bat572.get("season_level_admissions", {}).get("per_game_verified_official"):
        raise ValueError("BAT-572 season totals were promoted to per-game official")
    if bat572.get("contest_route_disposition") != BAT576_DISPOSITION:
        raise ValueError("BAT-572 missing BAT-576 contest-route disposition")
    if bat574.get("gate_identity") != BAT574_GATE_IDENTITY:
        raise ValueError("BAT-574 gate identity mismatch")
    if bat574.get("disposition") != BAT574_DISPOSITION:
        raise ValueError("BAT-574 disposition drift")
    if bat574.get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-574 unexpectedly opened the protected lane")
    if bat575.get("gate_identity") != BAT575_GATE_IDENTITY:
        raise ValueError("BAT-575 gate identity mismatch")
    if bat575.get("disposition") != BAT575_DISPOSITION:
        raise ValueError("BAT-575 disposition drift")
    if bat575.get("admissions", {}).get("texas_2011") != BAT575_TEXAS:
        raise ValueError("BAT-575 2011 Texas official strong tuple was not bound")
    if bat575.get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-575 unexpectedly opened the protected lane")
    if bat576.get("gate_identity") != BAT576_GATE_IDENTITY:
        raise ValueError("BAT-576 gate identity mismatch")
    if bat576.get("disposition") != BAT576_DISPOSITION:
        raise ValueError("BAT-576 disposition drift")
    if int((bat576.get("counts") or {}).get("contest_ids_discovered", -1)) != 0:
        raise ValueError("BAT-576 contest-ID count drifted")
    if bat576.get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-576 unexpectedly opened the protected lane")
    if "2024" in json.dumps(bat400.get("development_metrics")) or "2025" in json.dumps(
        bat400.get("development_metrics")
    ):
        raise ValueError("BAT-400 unexpectedly carried protected-year metrics")
    freeze_split_boundaries(repo_root)
    return {
        "BAT-398": {
            "path": "artifacts/pit/matrix_gate_decision.json",
            "sha256": BAT398_SHA256,
            "decision": "BLOCK",
            "matrix_identity": STALE_ZERO_ROW_IDENTITY,
            "note": "Historical zero-row gate remains pinned. It is no longer the sole BAT-401 blocker.",
        },
        "BAT-399": {
            "path": "artifacts/pit/leakage_battery_results.json",
            "artifact_identity": BAT399_IDENTITY,
            "status": "DONE",
            "dataset_identity": DATASET_IDENTITY,
        },
        "BAT-400": {
            "path": "artifacts/pit/protected_replay_dry_run.json",
            "artifact_identity": BAT400_IDENTITY,
            "status": "DONE",
            "protected_outcomes_inaccessible": True,
            "protected_metrics_produced": False,
            "development_label_status": bat400.get("development_label_status"),
        },
        "BAT-523": {
            "dataset_identity": DATASET_IDENTITY,
            "dataset_version": "bat523-known-at-replay-2010-2022-v2",
        },
        "BAT-526": {
            "path": "artifacts/governance/protected_split_exposure_audit.json",
            "artifact_identity": BAT526_IDENTITY,
            "classification": "HISTORICAL_PROTECTED_RESULT_EXPOSED_NO_SELECTION_OR_PROMOTION_AUTHORITY",
            "metrics_republished": False,
        },
        "BAT-566": {
            "path": "artifacts/pit/development_walk_forward_2023.json",
            "artifact_identity": bat566.get("artifact_identity"),
            "matrix_identity": bat566.get("matrix_identity"),
            "replay_identity": bat566.get("replay_identity"),
            "gate_identity": bat566.get("gate_identity"),
            "bat565_label_dataset_identity": bat566.get("input_identities", {}).get(
                "bat565_label_dataset_identity"
            ),
            "classification": bat566.get("classification"),
            "protected_performance": False,
            "promotion_authority": False,
            "supersedes_replay_identity": BAT566_SUPERSEDED_REPLAY,
        },
        "BAT-568": {
            "path": "artifacts/pit/development_rankings_walk_forward_2023.json",
            "gate_identity": bat568.get("gate_identity"),
            "joined_matrix_identity": bat568.get("joined_matrix_identity"),
            "run_identity": bat568.get("run_identity"),
            "classification": bat568.get("classification"),
            "any_candidate_improved_brier_vs_prior_only": False,
            "protected_performance": False,
            "promotion_authority": False,
        },
        "BAT-569": {
            "path": "artifacts/experimentation/development_candidate_evidence_ledger.json",
            "ledger_identity": bat569.get("ledger_identity"),
            "fold_definition_identity": bat569.get("fold_definition_identity"),
            "comparison_count": bat569.get("comparison_count"),
            "classification": bat569.get("classification"),
            "protected_performance": False,
            "promotion_authority": False,
        },
        "BAT-570": {
            "path": "artifacts/data_lake/tamu_official_evidence_gap_matrix_gate.json",
            "matrix_identity": bat570.get("matrix_identity"),
            "gate_identity": bat570.get("gate_identity"),
            "classification": bat570.get("classification"),
            "protected_lane": LANE_DECISION,
        },
        "BAT-571": {
            "path": "artifacts/data_lake/tamu_2010_2011_ncaa_official_acquisition_gate.json",
            "acquisition_identity": bat571.get("acquisition_identity"),
            "disposition": bat571.get("disposition"),
            "gate_identity": bat571.get("gate_identity"),
            "protected_lane": LANE_DECISION,
        },
        "BAT-572": {
            "path": "artifacts/data_lake/tamu_cross_source_domain_gate.json",
            "gate_identity": bat572.get("gate_identity"),
            "classification": bat572.get("classification"),
            "phase4_disposition": bat572.get("phase4_disposition"),
            "contest_route_disposition": bat572.get("contest_route_disposition"),
            "season_level_grain": (bat572.get("season_level_admissions") or {}).get("grain"),
            "verified_official": False,
            "protected_lane": LANE_DECISION,
        },
        "BAT-574": {
            "path": "artifacts/data_lake/tamu_2010_2011_ncaa_team_season_evidence_gate.json",
            "gate_identity": bat574.get("gate_identity"),
            "disposition": bat574.get("disposition"),
            "protected_lane": LANE_DECISION,
        },
        "BAT-575": {
            "path": "artifacts/data_lake/tamu_2010_2011_season_reconciliation_gate.json",
            "gate_identity": bat575.get("gate_identity"),
            "disposition": bat575.get("disposition"),
            "texas_2011": (bat575.get("admissions") or {}).get("texas_2011"),
            "protected_lane": LANE_DECISION,
        },
        "BAT-576": {
            "path": "artifacts/data_lake/tamu_2010_2011_ncaa_contest_route_discovery_gate.json",
            "gate_identity": bat576.get("gate_identity"),
            "disposition": bat576.get("disposition"),
            "contest_ids_discovered": 0,
            "protected_lane": LANE_DECISION,
        },
    }


def derive_acceptance(prereqs: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "criterion": "bat399_future_postgame_invariance_consumed",
            "disposition": "PASS",
            "evidence": prereqs["BAT-399"]["artifact_identity"],
        },
        {
            "criterion": "bat400_development_safe_replay_consumed",
            "disposition": "PASS",
            "evidence": prereqs["BAT-400"]["artifact_identity"],
        },
        {
            "criterion": "gap_005_remains_open",
            "disposition": "PASS",
            "evidence": "No champion, no protected evaluation, no production model.",
        },
        {
            "criterion": "prerequisites_linked_and_lane_blockers_explicit",
            "disposition": "PASS",
            "evidence": "remaining_lane_blockers",
        },
    ]


def evaluate_readiness(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    prereqs = load_prerequisites(repo_root)
    acceptance = derive_acceptance(prereqs)
    if any(row["disposition"] != "PASS" for row in acceptance):
        raise ValueError("gate acceptance failed; do not complete the issue")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PIT_REPLAY_READINESS_GATE",
        "decision_unit": "POST-SUBTASK-051",
        "jira_key": "BAT-401",
        "stale_zero_row_language_superseded": True,
        "superseded_blocker_text": (
            "QUALITY_GATE_BLOCKED_MATRIX_IDENTITY: "
            f"{STALE_ZERO_ROW_IDENTITY}; BAT-398 decision BLOCK; zero accepted rows/cells"
        ),
        "issue_status": "DONE",
        "issue_completion_versus_lane": {
            "issue_complete_if_gate_performed": True,
            "protected_experimentation_lane": LANE_DECISION,
        },
        "lane_decision": LANE_DECISION,
        "protected_metrics_republished": False,
        "protected_evaluation_status": "CLOSED",
        "claims": {
            "protected_performance": False,
            "production_readiness": False,
            "champion_selection": False,
            "feature_promotion": False,
            "new_protected_period_defined": False,
        },
        "prerequisite_identities": prereqs,
        "remaining_lane_blockers": list(LANE_BLOCKERS),
        "downstream_reevaluation": {
            "POST-STORY-017": LANE_DECISION,
            "POST-EPIC-008": LANE_DECISION,
            "POST-STORY-019": LANE_DECISION,
            "POST-STORY-024": LANE_DECISION,
            "POST-STORY-030": LANE_DECISION,
            "POST-SUBTASK-055": LANE_DECISION,
            "POST-SUBTASK-056": LANE_DECISION,
            "POST-SUBTASK-057": LANE_DECISION,
            "POST-SUBTASK-070": LANE_DECISION,
            "POST-SUBTASK-071": LANE_DECISION,
            "POST-SUBTASK-072": LANE_DECISION,
            "POST-SUBTASK-088": LANE_DECISION,
            "POST-SUBTASK-089": LANE_DECISION,
        },
        "acceptance_matrix": acceptance,
        "gap_005": "OPEN",
        "honesty_boundary": {
            "row_level_payloads_unavailable_is_false": True,
            "bat523_dataset_identity": DATASET_IDENTITY,
            "protected_metrics_included": False,
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


def validate_readiness_artifact(payload: Mapping[str, Any], repo_root: Path) -> None:
    missing = [field for field in AUTHORITY_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"missing authority fields: {missing}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected readiness schema")
    if payload.get("artifact_identity") != compute_artifact_identity(payload):
        raise ValueError("artifact_identity does not match canonical payload")
    if payload.get("lane_decision") != LANE_DECISION:
        raise ValueError("lane decision must remain RETAIN_PROTECTED_LANE_BLOCKED")
    if payload.get("issue_status") != "DONE":
        raise ValueError("issue status must be DONE after a completed gate decision")
    if payload.get("protected_metrics_republished") is not False:
        raise ValueError("protected metrics must not be republished")
    if payload.get("stale_zero_row_language_superseded") is not True:
        raise ValueError("stale zero-row language must be superseded")
    if STALE_ZERO_ROW_IDENTITY in str(payload.get("remaining_lane_blockers")) and payload.get(
        "lane_decision"
    ) == "OPEN":
        raise ValueError("stale zero-row identity cannot open the lane")
    names = [row["criterion"] for row in payload.get("acceptance_matrix") or []]
    if names != list(REQUIRED_ACCEPTANCE):
        raise ValueError("acceptance matrix does not match required criteria")
    blocker_ids = [row["id"] for row in payload.get("remaining_lane_blockers") or []]
    if blocker_ids != [row["id"] for row in LANE_BLOCKERS]:
        raise ValueError("lane blockers are incomplete or reordered")
    encoded = json.dumps(payload)
    if "DEVELOPMENT_TUNE" in encoded or "DEVELOPMENT_EVALUATION_UNPROTECTED" in encoded:
        raise ValueError("readiness artifact republished contaminated split labels")
    prereqs = payload.get("prerequisite_identities") or {}
    if prereqs.get("BAT-399", {}).get("artifact_identity") != BAT399_IDENTITY:
        raise ValueError("BAT-399 identity not bound")
    if prereqs.get("BAT-400", {}).get("artifact_identity") != BAT400_IDENTITY:
        raise ValueError("BAT-400 identity not bound")
    if prereqs.get("BAT-523", {}).get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("BAT-523 identity not bound")
    if prereqs.get("BAT-566", {}).get("bat565_label_dataset_identity") == BAT566_SUPERSEDED_KICKOFF_LABEL:
        raise ValueError("BAT-401 still binds the superseded kickoff-time BAT-566 parent")
    if prereqs.get("BAT-566", {}).get("promotion_authority") is not False:
        raise ValueError("BAT-566 promotion authority must remain false")
    if prereqs.get("BAT-568", {}).get("gate_identity") != BAT568_GATE_IDENTITY:
        raise ValueError("BAT-568 identity not bound")
    if prereqs.get("BAT-568", {}).get("promotion_authority") is not False:
        raise ValueError("BAT-568 promotion authority must remain false")
    if not prereqs.get("BAT-569", {}).get("ledger_identity"):
        raise ValueError("BAT-569 ledger identity not bound")
    if prereqs.get("BAT-569", {}).get("promotion_authority") is not False:
        raise ValueError("BAT-569 promotion authority must remain false")
    if prereqs.get("BAT-570", {}).get("matrix_identity") != BAT570_MATRIX_IDENTITY:
        raise ValueError("BAT-570 identity not bound")
    if prereqs.get("BAT-571", {}).get("acquisition_identity") != BAT571_ACQUISITION_IDENTITY:
        raise ValueError("BAT-571 identity not bound")
    if prereqs.get("BAT-571", {}).get("disposition") != BAT571_DISPOSITION:
        raise ValueError("BAT-571 disposition not bound")
    if not prereqs.get("BAT-572", {}).get("gate_identity"):
        raise ValueError("BAT-572 gate identity not bound")
    if prereqs.get("BAT-572", {}).get("protected_lane") != LANE_DECISION:
        raise ValueError("BAT-572 must retain the blocked protected lane")
    if prereqs.get("BAT-572", {}).get("verified_official") is not False:
        raise ValueError("BAT-572 verified-official claim is not fail-closed")
    if prereqs.get("BAT-574", {}).get("gate_identity") != BAT574_GATE_IDENTITY:
        raise ValueError("BAT-574 identity not bound")
    if prereqs.get("BAT-575", {}).get("gate_identity") != BAT575_GATE_IDENTITY:
        raise ValueError("BAT-575 identity not bound")
    if prereqs.get("BAT-575", {}).get("texas_2011") != BAT575_TEXAS:
        raise ValueError("BAT-575 Texas conflict not bound")
    if prereqs.get("BAT-576", {}).get("gate_identity") != BAT576_GATE_IDENTITY:
        raise ValueError("BAT-576 identity not bound")
    if prereqs.get("BAT-576", {}).get("disposition") != BAT576_DISPOSITION:
        raise ValueError("BAT-576 disposition not bound")
    freeze_split_boundaries(repo_root)


def write_readiness_artifact(repo_root: Path, output: Path | None = None) -> dict[str, Any]:
    payload = evaluate_readiness(repo_root)
    validate_readiness_artifact(payload, repo_root)
    destination = output or (repo_root / "artifacts" / "pit" / "PIT_REPLAY_READINESS.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json(payload) + b"\n")
    return payload
