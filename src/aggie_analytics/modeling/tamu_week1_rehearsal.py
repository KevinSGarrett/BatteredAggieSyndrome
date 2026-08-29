"""Texas A&M Week One 2026 rehearsal against the unchanged national baseline.

The rehearsal deliberately owns no model. It reads the frozen Phase 8 snapshot
and forecast rows for one contest, restates the mandatory no-adjustment national
path exactly as it was frozen, and then answers a separate question: which Texas
A&M high-resolution evidence could in principle augment that national path, and
which evidence cannot, either because the project has no source for it or because
the only evidence that exists is postgame or carries an unknown known-at instant.

No specialization candidate was predeclared in the Phase 6 contract, so the
rehearsal has no specialization arm at all. That is recorded as a negative finding
rather than filled in with an improvised adjustment.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc

SCHEMA_VERSION = "aggie.shadow.tamu_2026_week1_rehearsal.v1"
CONTRACT_ID = "BAT-658-TAMU-2026-WEEK1-NATIONAL-BASELINE-REHEARSAL-V1"
CLASSIFICATION = "TAMU_2026_WEEK1_REHEARSAL_AGAINST_THE_UNCHANGED_NATIONAL_BASELINE"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_TAMU_2026_WEEK1_NATIONAL_BASELINE_REHEARSAL"

CONTRACT_RELATIVE = "configs/tamu_2026_week1_rehearsal_contract.json"
GATE_RELATIVE = "artifacts/shadow/tamu_2026_week1_rehearsal_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/tamu_2026_week1_rehearsal_replay.json"

TAMU_CANONICAL_TEAM_ID = "SRC-002:TEAM:245"

NATIONAL_BASELINE_INPUT = "NATIONAL_BASELINE_INPUT_ALREADY_CONSUMED"
COULD_AUGMENT = "COULD_AUGMENT_IF_ADMITTED_AND_TEMPORALLY_ELIGIBLE"
POSTGAME_ONLY = "TEMPORALLY_INELIGIBLE_POSTGAME_ONLY"
UNKNOWN_KNOWN_AT = "TEMPORALLY_INELIGIBLE_UNKNOWN_KNOWN_AT"
SOURCE_ABSENT = "UNAVAILABLE_SOURCE_ABSENT"
QUARANTINED = "UNAVAILABLE_QUARANTINED"
ROUTE_BLOCKED = "UNAVAILABLE_ROUTE_BLOCKED"

NON_AUTHORITATIVE_KEYS = frozenset({"issued_at_utc", "producer"})


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(Path(repo_root) / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("rehearsal contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("rehearsal contract schema mismatch")
    if contract.get("lane") != LANE:
        raise ValueError("the rehearsal lane must remain observation only")
    for field in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "forecast_publication",
        "canonical_entity_mutation",
        "immutable_raw_capture_mutation",
        "tamu_specialization_admission",
    ):
        if contract["authority"].get(field) is not False:
            raise ValueError(f"contract authority field must remain false: {field}")
    if contract["no_adjustment_path"].get("mandatory") is not True:
        raise ValueError("the no-adjustment national path is mandatory")
    if contract["no_adjustment_path"].get("tamu_adjustment_applied") is not False:
        raise ValueError("the no-adjustment path must not carry a Texas A&M adjustment")
    if contract["no_adjustment_path"].get("refit_performed") is not False:
        raise ValueError("the rehearsal must not refit the national candidates")
    specialization = contract["specialization"]
    if specialization.get("predeclared_specialization_candidate_exists") is not False:
        raise ValueError(
            "no specialization candidate was frozen in Phase 6, so the contract must say so"
        )
    if specialization.get("specialization_output_permitted") is not False:
        raise ValueError("a specialization output requires a predeclared candidate")
    if specialization.get("single_game_lift_claim_permitted") is not False:
        raise ValueError("a single-game lift claim is never permitted")
    if contract["target_contest"].get("outcome_access_permitted") is not False:
        raise ValueError("the rehearsal must not access the target-game outcome")
    if contract["feature_availability"].get("availability_inferred_from_participation") is not False:
        raise ValueError("availability may not be inferred from participation")
    if contract["scoring_plan"].get("may_promote_a_model") is not False:
        raise ValueError("the scoring plan must not permit promotion")
    return contract


# ---------------------------------------------------------------------------
# target contest identity
# ---------------------------------------------------------------------------


def select_target_contest(
    snapshots: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Locate exactly one frozen snapshot row matching the declared contest."""

    declared = contract["target_contest"]
    matches = [
        dict(row)
        for row in snapshots
        if str(row.get("home_source_display_name") or "")
        == declared["declared_home_source_display_name"]
        and str(row.get("away_source_display_name") or "")
        == declared["declared_away_source_display_name"]
        and str(row.get("source_published_game_date") or "")
        == declared["declared_source_published_game_date"]
    ]
    if len(matches) != 1:
        raise ValueError(
            "the declared Texas A&M Week One contest did not match exactly one frozen snapshot "
            f"row: matched {len(matches)}"
        )
    row = matches[0]
    if str(row.get("source_published_clock_text") or "") != declared[
        "declared_source_published_clock_text"
    ]:
        raise ValueError("the published kickoff clock drifted from the declared value")
    if str(row.get("home_canonical_team_id") or "") != TAMU_CANONICAL_TEAM_ID:
        raise ValueError("the home participant does not resolve to the Texas A&M canonical team")
    if row.get("forecast_state") != "SNAPSHOT_FROZEN":
        raise ValueError(
            f"the target contest carries no frozen pregame snapshot: {row.get('forecast_state')}"
        )
    snapshot = row.get("snapshot") or {}
    if snapshot.get("outcome_read_before_freeze") is not False:
        raise ValueError("the bound snapshot does not certify that no outcome was read")
    return row


def verified_identity(contest: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    declared = contract["target_contest"]
    snapshot = contest["snapshot"]
    return {
        "ncaa_contest_id": str(contest["ncaa_contest_id"]),
        "home_canonical_team_id": str(contest["home_canonical_team_id"]),
        "away_canonical_team_id": str(contest["away_canonical_team_id"]),
        "home_source_display_name": str(contest["home_source_display_name"]),
        "away_source_display_name": str(contest["away_source_display_name"]),
        "source_published_game_date": str(contest["source_published_game_date"]),
        "source_published_clock_text": str(contest["source_published_clock_text"]),
        "declared_local_kickoff_text": declared["declared_local_kickoff_text"],
        "declared_venue_text": declared["declared_venue_text"],
        "declared_broadcast_text": declared["declared_broadcast_text"],
        "venue_and_broadcast_independently_confirmed_from_the_bound_capture": False,
        "kickoff_utc_conservative_lower_bound": str(
            contest["kickoff_utc_conservative_lower_bound"]
        ),
        "kickoff_utc_independently_confirmed": False,
        "is_neutral_site": bool(contest.get("is_neutral_site")),
        "snapshot_identity": str(snapshot["snapshot_identity"]),
        "capture_sha256": str(snapshot["capture_sha256"]),
        "capture_retrieved_at_utc": str(snapshot["capture_retrieved_at_utc"]),
        "snapshot_frozen_at_utc": str(snapshot["snapshot_frozen_at_utc"]),
        "outcome_read_before_freeze": False,
        "target_game_outcome_excluded": True,
    }


# ---------------------------------------------------------------------------
# mandatory no-adjustment national path
# ---------------------------------------------------------------------------


def no_adjustment_path(
    forecasts: Sequence[Mapping[str, Any]],
    *,
    contest_id: str,
    contract: Mapping[str, Any],
    baseline_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Restate the frozen national forecast rows for the target contest."""

    frozen_candidate_ids = {str(item["candidate_id"]) for item in baseline_contract["candidates"]}
    rows = [dict(row) for row in forecasts if str(row["ncaa_contest_id"]) == str(contest_id)]
    if not rows:
        raise ValueError("the target contest carries no frozen Phase 8 forecast row")
    inserted = sorted({str(row["candidate_id"]) for row in rows} - frozen_candidate_ids)
    if inserted:
        raise ValueError(f"a candidate outside the Phase 6 frozen set appeared: {inserted}")
    forecast_rows: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: str(item["candidate_id"])):
        forecast_rows.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "candidate_admissibility": str(row["candidate_admissibility"]),
                "forecast_state": str(row["forecast_state"]),
                "probability_home_win": row.get("probability_home_win"),
                "orientation": str(row["orientation"]),
                "abstention_state": row.get("abstention_state"),
                "abstention_reason": row.get("abstention_reason"),
                "model_identity": str(row["model_identity"]),
                "feature_identity": str(row["feature_identity"]),
                "code_identity": str(row["code_identity"]),
                "snapshot_identity": row.get("snapshot_identity"),
                "created_at_utc": str(row["created_at_utc"]),
                "forecast_authority": str(row["forecast_authority"]),
                "tamu_adjustment_applied": False,
            }
        )
    frozen = [row for row in forecast_rows if row["forecast_state"] == "FORECAST_FROZEN"]
    minimum = int(contract["no_adjustment_path"]["minimum_frozen_candidate_rows"])
    if len(frozen) < minimum:
        raise ValueError(
            f"the mandatory no-adjustment path needs at least {minimum} frozen candidate row(s)"
        )
    for row in frozen:
        if not isinstance(row["probability_home_win"], (int, float)):
            raise ValueError("a frozen candidate row carried no probability")
        created = parse_utc(row["created_at_utc"])
        if created >= parse_utc(str(rows[0]["kickoff_utc_conservative_lower_bound"])):
            raise ValueError("a frozen forecast was created at or after kickoff")
    return {
        "candidate_rows": forecast_rows,
        "frozen_candidate_ids": sorted(row["candidate_id"] for row in frozen),
        "abstaining_candidate_ids": sorted(
            row["candidate_id"] for row in forecast_rows if row not in frozen
        ),
        "refit_performed": False,
        "tamu_adjustment_applied": False,
        "path_state": "NO_ADJUSTMENT_NATIONAL_PATH_PRESENT",
    }


# ---------------------------------------------------------------------------
# Texas A&M feature availability
# ---------------------------------------------------------------------------


def _classify_national_domain(
    domain: Mapping[str, Any], pregame_bases: Sequence[str]
) -> tuple[str, str]:
    decision = str(domain.get("decision") or "")
    known_at = str(domain.get("known_at_basis") or "")
    if decision == "ADMITTED":
        return (
            NATIONAL_BASELINE_INPUT,
            "The domain is already an admitted national input, so it is part of the unchanged "
            "baseline rather than a Texas A&M augmentation.",
        )
    if decision == "SOURCE_ABSENT":
        return (
            SOURCE_ABSENT,
            "The project holds no acquired evidence for this domain, nationally or for Texas A&M.",
        )
    if decision == "QUARANTINED":
        return (
            QUARANTINED,
            "The domain is quarantined, so it cannot enter a forecast path in any lane.",
        )
    if known_at == "POSTGAME_ONLY":
        return (
            POSTGAME_ONLY,
            "The only evidence for this domain is produced after the contest ends, so it can "
            "never be a pregame feature for the target contest.",
        )
    if known_at in set(pregame_bases):
        return (
            COULD_AUGMENT,
            "The domain carries a pregame known-at basis and would be an augmentation candidate "
            "once it is admitted nationally, which it is not yet.",
        )
    return (
        UNKNOWN_KNOWN_AT,
        "The domain has no established pregame known-at basis, so it cannot be admitted as a "
        "pregame feature without new timestamp evidence.",
    )


def feature_availability_matrix(
    *,
    domain_gate: Mapping[str, Any],
    tamu_gates: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Enumerate national domains plus the Texas A&M high-resolution routes."""

    pregame_bases = list(contract["feature_availability"]["pregame_known_at_bases"])
    rows: list[dict[str, Any]] = []
    for domain in domain_gate["admission_matrix"]:
        availability, reason = _classify_national_domain(domain, pregame_bases)
        share = domain.get("tamu_share") or {}
        rows.append(
            {
                "evidence_route": "NATIONAL_DOMAIN",
                "domain_id": str(domain["domain_id"]),
                "label": str(domain["label"]),
                "national_decision": str(domain["decision"]),
                "known_at_basis": str(domain["known_at_basis"]),
                "availability_class": availability,
                "availability_reason": reason,
                "domain_scope_games": domain.get("domain_scope_games"),
                "tamu_domain_scope_games": share.get("domain_scope_tamu_games"),
                "tamu_game_share_of_domain": share.get("tamu_game_share_of_domain"),
                "target_contest_feature_materialized": False,
            }
        )
    cross_source = tamu_gates["tamu_cross_source_domain_gate"]
    rows.append(
        {
            "evidence_route": "TAMU_OFFICIAL_STRUCTURED_ARCHIVE",
            "domain_id": "tamu_official_structured_domains",
            "label": "Texas A&M official structured game domains",
            "national_decision": str(cross_source["admissions"]["gate_admission"]),
            "known_at_basis": str(cross_source["admissions"]["historical_known_at"]),
            "availability_class": UNKNOWN_KNOWN_AT,
            "availability_reason": (
                "The archive is verified official postgame fact with only a capture-time "
                "timestamp, so it is high-resolution history rather than pregame evidence for a "
                "2026 contest."
            ),
            "domain_scope_games": cross_source["counts"]["scheduled_games"],
            "tamu_domain_scope_games": cross_source["counts"]["scheduled_games"],
            "tamu_game_share_of_domain": 1.0,
            "target_contest_feature_materialized": False,
        }
    )
    rows.append(
        {
            "evidence_route": "TAMU_PREGAME_AVAILABILITY",
            "domain_id": "tamu_pregame_availability",
            "label": "Texas A&M pregame availability evidence",
            "national_decision": str(cross_source["admissions"]["pregame_availability"]),
            "known_at_basis": "SOURCE_EVIDENCE_ABSENT",
            "availability_class": ROUTE_BLOCKED,
            "availability_reason": (
                "The pregame availability route is blocked and participation may not be read as "
                "availability, so the target contest carries no availability feature."
            ),
            "domain_scope_games": cross_source["counts"]["pregame_availability_true"],
            "tamu_domain_scope_games": cross_source["counts"]["pregame_availability_true"],
            "tamu_game_share_of_domain": None,
            "target_contest_feature_materialized": False,
        }
    )
    declared_classes = set(contract["feature_availability"]["classes"])
    unknown = sorted({row["availability_class"] for row in rows} - declared_classes)
    if unknown:
        raise ValueError(f"undeclared availability classes were produced: {unknown}")
    rows.sort(key=lambda row: (row["evidence_route"], row["domain_id"]))
    return rows


def augmentation_summary(matrix: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def ids(*classes: str) -> list[str]:
        return sorted(
            str(row["domain_id"]) for row in matrix if row["availability_class"] in set(classes)
        )

    could_augment = ids(COULD_AUGMENT)
    return {
        "already_consumed_by_the_national_baseline": ids(NATIONAL_BASELINE_INPUT),
        "could_augment_if_admitted_and_temporally_eligible": could_augment,
        "temporally_ineligible": ids(POSTGAME_ONLY, UNKNOWN_KNOWN_AT),
        "unavailable": ids(SOURCE_ABSENT, QUARANTINED, ROUTE_BLOCKED),
        "materialized_augmentation_features_for_the_target_contest": 0,
        "augmentation_applied_to_the_national_path": False,
    }


def specialization_state(contract: Mapping[str, Any]) -> dict[str, Any]:
    specialization = contract["specialization"]
    return {
        "predeclared_specialization_candidate_exists": False,
        "specialization_output_permitted": False,
        "specialization_output_state": str(specialization["specialization_output_state"]),
        "specialization_rows_emitted": 0,
        "adapter_or_specialization_feature_added_to_the_national_model": False,
        "comparator_is_mandatory_and_present": True,
        "single_game_lift_claimed": False,
    }


# ---------------------------------------------------------------------------
# checkpoints, commands, scoring plan
# ---------------------------------------------------------------------------


def checkpoint_plan(
    *, kickoff: datetime, execution_time: datetime, contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    offsets = contract["checkpoints"]["offsets_seconds"]
    cutoff = str(contract["checkpoints"]["snapshot_cutoff_checkpoint_id"])
    plan: list[dict[str, Any]] = []
    for checkpoint_id in contract["checkpoints"]["checkpoint_ids"]:
        deadline = kickoff - timedelta(seconds=int(offsets[checkpoint_id]))
        plan.append(
            {
                "checkpoint_id": checkpoint_id,
                "deadline_utc": iso_utc(deadline),
                "state": "OPEN" if execution_time <= deadline else "CLOSED",
                "is_snapshot_cutoff": checkpoint_id == cutoff,
                "backfill_permitted_after_the_deadline": False,
            }
        )
    return plan


def rehearsal_commands(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "step": "REACQUIRE_THE_OFFICIAL_SCHEDULE_SNAPSHOT",
            "command": "python tools/acquire_2026_prospective_schedule.py",
            "network_access": True,
            "immutable_output": True,
        },
        {
            "step": "FREEZE_THE_NO_ADJUSTMENT_NATIONAL_FORECAST",
            "command": "python tools/build_prospective_2026_shadow_forecasts.py",
            "network_access": False,
            "immutable_output": True,
        },
        {
            "step": "REBUILD_THE_REHEARSAL_GATE",
            "command": "python tools/build_tamu_2026_week1_rehearsal.py",
            "network_access": False,
            "immutable_output": True,
        },
        {
            "step": "SCORE_AFTER_AN_OFFICIAL_FINAL_EXISTS",
            "command": str(contract["scoring_plan"]["scorer"]),
            "network_access": False,
            "immutable_output": True,
        },
    ]


def scoring_plan(contract: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    plan = contract["scoring_plan"]
    return {
        "scorer": str(plan["scorer"]),
        "bound_snapshot_identity": str(identity["snapshot_identity"]),
        "official_final_required": True,
        "outcome_load_permitted_before_forecast_freeze": False,
        "earliest_permitted_outcome_read_utc": str(
            identity["kickoff_utc_conservative_lower_bound"]
        ),
        "current_state": str(plan["no_eligible_official_final_result"]),
        "single_game_metrics_are_diagnostic_only": True,
        "may_tune_a_model": False,
        "may_promote_a_model": False,
    }


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------


def build_rehearsal_bundle(
    *,
    contract: Mapping[str, Any],
    baseline_contract: Mapping[str, Any],
    snapshots: Sequence[Mapping[str, Any]],
    forecasts: Sequence[Mapping[str, Any]],
    domain_gate: Mapping[str, Any],
    tamu_gates: Mapping[str, Mapping[str, Any]],
    execution_time: datetime,
) -> dict[str, Any]:
    if execution_time > datetime.now(timezone.utc):
        raise ValueError("execution time must not be in the future")
    contest = select_target_contest(snapshots, contract)
    identity = verified_identity(contest, contract)
    path = no_adjustment_path(
        forecasts,
        contest_id=identity["ncaa_contest_id"],
        contract=contract,
        baseline_contract=baseline_contract,
    )
    matrix = feature_availability_matrix(
        domain_gate=domain_gate, tamu_gates=tamu_gates, contract=contract
    )
    kickoff = parse_utc(identity["kickoff_utc_conservative_lower_bound"])
    if execution_time >= kickoff:
        raise ValueError("the rehearsal may not be produced at or after the target kickoff bound")
    return {
        "execution_time_utc": iso_utc(execution_time),
        "target_contest_identity": identity,
        "no_adjustment_national_path": path,
        "tamu_feature_availability_matrix": matrix,
        "augmentation_summary": augmentation_summary(matrix),
        "specialization": specialization_state(contract),
        "checkpoint_plan": checkpoint_plan(
            kickoff=kickoff, execution_time=execution_time, contract=contract
        ),
        "commands": rehearsal_commands(contract),
        "scoring_plan": scoring_plan(contract, identity),
        "counts": {
            "target_contests": 1,
            "candidate_rows": len(path["candidate_rows"]),
            "frozen_candidate_rows": len(path["frozen_candidate_ids"]),
            "abstaining_candidate_rows": len(path["abstaining_candidate_ids"]),
            "availability_matrix_rows": len(matrix),
            "could_augment_domains": len(
                augmentation_summary(matrix)["could_augment_if_admitted_and_temporally_eligible"]
            ),
            "specialization_rows_emitted": 0,
        },
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    bundle: Mapping[str, Any],
    predecessor_sha256: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2026_WEEK1_NATIONAL_BASELINE_REHEARSAL_GATE",
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha256,
        "decision_unit": contract["decision_unit"],
        "local_issue_id": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "execution_time_utc": bundle["execution_time_utc"],
        "bound_predecessors": dict(sorted(predecessor_sha256.items())),
        "target_contest_identity": dict(bundle["target_contest_identity"]),
        "no_adjustment_national_path": dict(bundle["no_adjustment_national_path"]),
        "tamu_feature_availability_matrix": list(bundle["tamu_feature_availability_matrix"]),
        "augmentation_summary": dict(bundle["augmentation_summary"]),
        "specialization": dict(bundle["specialization"]),
        "checkpoint_plan": list(bundle["checkpoint_plan"]),
        "commands": list(bundle["commands"]),
        "scoring_plan": dict(bundle["scoring_plan"]),
        "counts": dict(bundle["counts"]),
        "authority": dict(contract["authority"]),
        "negative_findings": dict(contract["negative_findings"]),
        "scientific_nonclaims": dict(contract["scientific_nonclaims"]),
    }


def validate_artifact(repo_root: Path) -> dict[str, Any]:
    """Independently revalidate the published rehearsal gate."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    findings: list[str] = []
    if not gate_path.is_file():
        return {"result": "FAIL", "findings": ["the rehearsal gate is absent"]}
    gate = _read_json(gate_path)
    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    bound = contract["bound_predecessors"]
    for name, relative in (
        ("forecast", bound["forecast_gate_relative_path"]),
        ("cohort", bound["cohort_gate_relative_path"]),
        ("baseline", bound["baseline_gate_relative_path"]),
        ("domain_matrix", bound["domain_matrix_gate_relative_path"]),
    ):
        if gate["bound_predecessors"].get(f"{name}_gate_sha256") != sha256_file(
            repo_root / relative
        ):
            findings.append(f"bound predecessor hash drifted: {name}")
    identity = gate.get("target_contest_identity") or {}
    if identity.get("target_game_outcome_excluded") is not True:
        findings.append("the gate does not certify target-game outcome exclusion")
    if identity.get("outcome_read_before_freeze") is not False:
        findings.append("the gate does not certify that no outcome was read before the freeze")
    path = gate.get("no_adjustment_national_path") or {}
    if path.get("tamu_adjustment_applied") is not False or path.get("refit_performed") is not False:
        findings.append("the no-adjustment path is not certified unchanged")
    if not path.get("frozen_candidate_ids"):
        findings.append("the mandatory no-adjustment path carries no frozen candidate")
    specialization = gate.get("specialization") or {}
    if specialization.get("specialization_rows_emitted") != 0:
        findings.append("a specialization row was emitted without a predeclared candidate")
    if specialization.get("comparator_is_mandatory_and_present") is not True:
        findings.append("the mandatory comparator is not recorded as present")
    if specialization.get("single_game_lift_claimed") is not False:
        findings.append("a single-game lift claim appeared in the gate")
    matrix = gate.get("tamu_feature_availability_matrix") or []
    declared = set(contract["feature_availability"]["classes"])
    for row in matrix:
        if row.get("availability_class") not in declared:
            findings.append(f"undeclared availability class: {row.get('availability_class')}")
        if row.get("target_contest_feature_materialized") is not False:
            findings.append(f"a target-contest feature was materialized: {row.get('domain_id')}")
    if int((gate.get("counts") or {}).get("availability_matrix_rows", -1)) != len(matrix):
        findings.append("availability matrix row count drifted")
    kickoff = identity.get("kickoff_utc_conservative_lower_bound")
    for row in path.get("candidate_rows") or []:
        if row.get("tamu_adjustment_applied") is not False:
            findings.append("a candidate row carried a Texas A&M adjustment")
        if row.get("probability_home_win") is None:
            continue
        if kickoff and parse_utc(str(row["created_at_utc"])) >= parse_utc(str(kickoff)):
            findings.append("a candidate row was created at or after kickoff")
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate_identity_of(gate: Mapping[str, Any]) -> str:
    return stable_hash(
        {key: value for key, value in gate.items() if key not in NON_AUTHORITATIVE_KEYS}
    )
