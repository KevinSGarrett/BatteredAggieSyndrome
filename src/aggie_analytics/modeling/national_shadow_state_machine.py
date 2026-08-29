"""Append-only national shadow state machine and GAP-002..009 reevaluation.

Every 2026 contest and every frozen forecast row already carries a state that was
decided by an earlier phase. This module is the place where those states become a
ledger with rules: an entity moves forward through the declared progress states or
into exactly one declared side state, and it can never move back, skip, leave a
terminal state, gain a second probability under one forecast identity, gain a new
kickoff without a new source identity, or reach ``SCORED`` from an outcome that was
observed before the forecast was frozen.

The same artifact reevaluates the gap register. The verdicts are not prose: each
gap declares a verification kind that is evaluated against the merged gates, so a
gap cannot be silently closed by editing a sentence.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc

SCHEMA_VERSION = "aggie.shadow.national_shadow_operations.v1"
CONTRACT_ID = "BAT-659-NATIONAL-SHADOW-OPERATIONS-AND-GAP-REEVALUATION-V1"
CLASSIFICATION = "APPEND_ONLY_NATIONAL_SHADOW_STATE_MACHINE_AND_GAP_REEVALUATION"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_NATIONAL_SHADOW_OPERATIONS_AND_GAP_REEVALUATION"

CONTRACT_RELATIVE = "configs/national_shadow_operations_contract.json"
GATE_RELATIVE = "artifacts/shadow/national_shadow_operations_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/national_shadow_operations_replay.json"

PROGRESS_STATES = (
    "PRECOMMITTED",
    "SNAPSHOT_ELIGIBLE",
    "SNAPSHOT_FROZEN",
    "FORECAST_FROZEN",
    "AWAITING_OFFICIAL_FINAL",
    "SCORED",
)
SIDE_STATES = (
    "MISSED_CUTOFF_NO_BACKFILL",
    "UNSUPPORTED_ENTITY",
    "MISSING_REQUIRED_FEATURES_ABSTAIN",
    "CANCELED_OR_SUSPENDED",
    "OFFICIAL_FINAL_UNAVAILABLE",
    "FAIL_CLOSED_IDENTITY_MISMATCH",
)
PROGRESS_ORDER = {state: index for index, state in enumerate(PROGRESS_STATES)}

NON_AUTHORITATIVE_KEYS = frozenset({"issued_at_utc", "producer"})


class StateMachineRejection(ValueError):
    """Raised whenever an appended transition would violate the ledger rules."""


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(Path(repo_root) / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("shadow operations contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("shadow operations contract schema mismatch")
    if contract.get("lane") != LANE:
        raise ValueError("the shadow operations lane must remain observation only")
    for field_name in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "forecast_publication",
        "canonical_entity_mutation",
        "immutable_raw_capture_mutation",
        "gap_closure_forced",
    ):
        if contract["authority"].get(field_name) is not False:
            raise ValueError(f"contract authority field must remain false: {field_name}")
    machine = contract["state_machine"]
    if machine.get("append_only") is not True:
        raise ValueError("the ledger must be append only")
    if tuple(machine["progress_states"]) != PROGRESS_STATES:
        raise ValueError("declared progress states do not match the implementation")
    if tuple(machine["terminal_or_side_states"]) != SIDE_STATES:
        raise ValueError("declared side states do not match the implementation")
    for rejection, value in machine["rejections"].items():
        if value is not True:
            raise ValueError(f"a declared rejection was disabled: {rejection}")
    if not contract["gap_reevaluation"]:
        raise ValueError("the contract declares no gap reevaluation")
    return contract


# ---------------------------------------------------------------------------
# ledger
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Transition:
    entity_id: str
    entity_kind: str
    sequence: int
    from_state: str
    to_state: str
    at_utc: str
    source_identity: str
    kickoff_utc: str | None = None
    snapshot_identity: str | None = None
    forecast_identity: str | None = None
    probability_home_win: float | None = None
    candidate_id: str | None = None
    outcome_observed_at_utc: str | None = None
    reason: str = ""


@dataclass
class ShadowStateLedger:
    """An append-only ledger of shadow transitions with fail-closed rules."""

    frozen_candidate_ids: frozenset[str]
    entries: list[dict[str, Any]] = field(default_factory=list)
    _state: dict[str, str] = field(default_factory=dict)
    _sequence: dict[str, int] = field(default_factory=dict)
    _kickoff: dict[str, tuple[str, str]] = field(default_factory=dict)
    _probability: dict[tuple[str, str], float] = field(default_factory=dict)
    _forecast_frozen_at: dict[str, str] = field(default_factory=dict)

    def current_state(self, entity_id: str) -> str:
        return self._state.get(entity_id, "PRECOMMITTED")

    def append(self, transition: Transition) -> dict[str, Any]:
        entity = transition.entity_id
        current = self.current_state(entity)
        expected_sequence = self._sequence.get(entity, 0) + 1

        if transition.sequence != expected_sequence:
            raise StateMachineRejection(
                f"nonmonotonic sequence for {entity}: expected {expected_sequence}"
            )
        if transition.from_state != current:
            raise StateMachineRejection(
                f"declared origin state does not match the ledger for {entity}: {current}"
            )
        if current in SIDE_STATES:
            raise StateMachineRejection(f"{entity} already reached the terminal state {current}")
        if transition.to_state in SIDE_STATES:
            pass
        elif transition.to_state in PROGRESS_ORDER:
            if PROGRESS_ORDER[transition.to_state] < PROGRESS_ORDER[current]:
                raise StateMachineRejection(
                    f"backward transition for {entity}: {current} -> {transition.to_state}"
                )
            if PROGRESS_ORDER[transition.to_state] != PROGRESS_ORDER[current] + 1:
                raise StateMachineRejection(
                    f"state skip for {entity}: {current} -> {transition.to_state}"
                )
        else:
            raise StateMachineRejection(f"undeclared target state: {transition.to_state}")

        if transition.candidate_id is not None:
            if transition.candidate_id not in self.frozen_candidate_ids:
                raise StateMachineRejection(
                    f"post-hoc candidate insertion rejected: {transition.candidate_id}"
                )

        if transition.kickoff_utc is not None:
            previous = self._kickoff.get(entity)
            if (
                previous is not None
                and previous[0] != transition.kickoff_utc
                and previous[1] == transition.source_identity
            ):
                raise StateMachineRejection(
                    f"kickoff changed without a new source identity for {entity}"
                )
            self._kickoff[entity] = (transition.kickoff_utc, transition.source_identity)

        if transition.to_state == "FORECAST_FROZEN":
            if transition.probability_home_win is None:
                raise StateMachineRejection(f"a frozen forecast needs a probability for {entity}")
            if transition.kickoff_utc is None:
                raise StateMachineRejection(f"a frozen forecast needs a kickoff bound for {entity}")
            if parse_utc(transition.at_utc) >= parse_utc(transition.kickoff_utc):
                raise StateMachineRejection(f"retroactive forecast rejected for {entity}")
            key = (entity, str(transition.forecast_identity))
            if key in self._probability and self._probability[key] != float(
                transition.probability_home_win
            ):
                raise StateMachineRejection(
                    f"changed probability under one forecast identity for {entity}"
                )
            self._probability[key] = float(transition.probability_home_win)
            self._forecast_frozen_at[entity] = transition.at_utc

        if transition.outcome_observed_at_utc is not None:
            frozen_at = self._forecast_frozen_at.get(entity)
            if frozen_at is None:
                raise StateMachineRejection(
                    f"an outcome was offered before any forecast was frozen for {entity}"
                )
            observed = parse_utc(transition.outcome_observed_at_utc)
            if observed < parse_utc(frozen_at):
                raise StateMachineRejection(
                    f"outcome access before the forecast freeze rejected for {entity}"
                )
            kickoff = self._kickoff.get(entity)
            if kickoff is not None and observed < parse_utc(kickoff[0]):
                raise StateMachineRejection(f"outcome observed before kickoff for {entity}")

        if transition.to_state == "SCORED" and transition.outcome_observed_at_utc is None:
            raise StateMachineRejection(f"a scored entity needs an official final for {entity}")

        entry = {
            "entity_id": entity,
            "entity_kind": transition.entity_kind,
            "sequence": transition.sequence,
            "from_state": transition.from_state,
            "to_state": transition.to_state,
            "at_utc": transition.at_utc,
            "source_identity": transition.source_identity,
            "kickoff_utc": transition.kickoff_utc,
            "snapshot_identity": transition.snapshot_identity,
            "forecast_identity": transition.forecast_identity,
            "probability_home_win": transition.probability_home_win,
            "candidate_id": transition.candidate_id,
            "outcome_observed_at_utc": transition.outcome_observed_at_utc,
            "reason": transition.reason,
            "lane": LANE,
            "protected_lane": PROTECTED_LANE,
            "promotion_performed": False,
            "publication_performed": False,
            "availability_inferred": False,
        }
        self.entries.append(entry)
        self._state[entity] = transition.to_state
        self._sequence[entity] = transition.sequence
        return entry

    def state_counts(self) -> dict[str, int]:
        counts = Counter(self._state.values())
        for state in PROGRESS_STATES + SIDE_STATES:
            counts.setdefault(state, 0)
        return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# replay of the merged shadow evidence
# ---------------------------------------------------------------------------


def replay_cohort(
    *,
    snapshots: Sequence[Mapping[str, Any]],
    forecasts: Sequence[Mapping[str, Any]],
    frozen_candidate_ids: Sequence[str],
    capture_identity: str,
) -> ShadowStateLedger:
    """Drive every merged contest and forecast row through the ledger."""

    ledger = ShadowStateLedger(frozen_candidate_ids=frozenset(frozen_candidate_ids))
    forecasts_by_contest: dict[str, list[Mapping[str, Any]]] = {}
    for row in forecasts:
        forecasts_by_contest.setdefault(str(row["ncaa_contest_id"]), []).append(row)

    for snapshot in sorted(
        snapshots, key=lambda row: (str(row["source_published_game_date"]), str(row["ncaa_contest_id"]))
    ):
        contest_id = str(snapshot["ncaa_contest_id"])
        state = str(snapshot["forecast_state"])
        kickoff = snapshot.get("kickoff_utc_conservative_lower_bound")
        frozen = snapshot.get("snapshot") or {}
        observed_at = str(frozen.get("snapshot_frozen_at_utc") or frozen.get("capture_retrieved_at_utc") or "")
        if state == "SNAPSHOT_FROZEN":
            ledger.append(
                Transition(
                    entity_id=contest_id,
                    entity_kind="CONTEST",
                    sequence=1,
                    from_state="PRECOMMITTED",
                    to_state="SNAPSHOT_ELIGIBLE",
                    at_utc=observed_at,
                    source_identity=str(frozen["capture_sha256"]),
                    kickoff_utc=str(kickoff),
                    reason="THE_CONTEST_WAS_STILL_BEFORE_THE_DECLARED_PREGAME_CUTOFF",
                )
            )
            ledger.append(
                Transition(
                    entity_id=contest_id,
                    entity_kind="CONTEST",
                    sequence=2,
                    from_state="SNAPSHOT_ELIGIBLE",
                    to_state="SNAPSHOT_FROZEN",
                    at_utc=str(frozen["snapshot_frozen_at_utc"]),
                    source_identity=str(frozen["capture_sha256"]),
                    kickoff_utc=str(kickoff),
                    snapshot_identity=str(frozen["snapshot_identity"]),
                    reason=str(snapshot.get("state_reason") or ""),
                )
            )
        else:
            ledger.append(
                Transition(
                    entity_id=contest_id,
                    entity_kind="CONTEST",
                    sequence=1,
                    from_state="PRECOMMITTED",
                    to_state=state,
                    at_utc=observed_at or iso_utc(datetime.now(timezone.utc)),
                    source_identity=capture_identity,
                    kickoff_utc=str(kickoff) if kickoff else None,
                    reason=str(snapshot.get("state_reason") or ""),
                )
            )

    for contest_id in sorted(forecasts_by_contest):
        for row in sorted(forecasts_by_contest[contest_id], key=lambda item: str(item["candidate_id"])):
            entity_id = f"{contest_id}::{row['candidate_id']}"
            state = str(row["forecast_state"])
            kickoff = row.get("kickoff_utc_conservative_lower_bound")
            if state == "FORECAST_FROZEN":
                ledger.append(
                    Transition(
                        entity_id=entity_id,
                        entity_kind="FORECAST",
                        sequence=1,
                        from_state="PRECOMMITTED",
                        to_state="SNAPSHOT_ELIGIBLE",
                        at_utc=str(row["created_at_utc"]),
                        source_identity=str(row["snapshot_identity"]),
                        kickoff_utc=str(kickoff),
                        candidate_id=str(row["candidate_id"]),
                        reason="THE_BOUND_CONTEST_CARRIED_A_FROZEN_PREGAME_SNAPSHOT",
                    )
                )
                ledger.append(
                    Transition(
                        entity_id=entity_id,
                        entity_kind="FORECAST",
                        sequence=2,
                        from_state="SNAPSHOT_ELIGIBLE",
                        to_state="SNAPSHOT_FROZEN",
                        at_utc=str(row["created_at_utc"]),
                        source_identity=str(row["snapshot_identity"]),
                        kickoff_utc=str(kickoff),
                        snapshot_identity=str(row["snapshot_identity"]),
                        candidate_id=str(row["candidate_id"]),
                        reason="THE_SNAPSHOT_IDENTITY_WAS_BOUND_TO_THE_FORECAST",
                    )
                )
                ledger.append(
                    Transition(
                        entity_id=entity_id,
                        entity_kind="FORECAST",
                        sequence=3,
                        from_state="SNAPSHOT_FROZEN",
                        to_state="FORECAST_FROZEN",
                        at_utc=str(row["created_at_utc"]),
                        source_identity=str(row["snapshot_identity"]),
                        kickoff_utc=str(kickoff),
                        snapshot_identity=str(row["snapshot_identity"]),
                        forecast_identity=stable_hash(
                            {
                                "candidate_id": str(row["candidate_id"]),
                                "model_identity": str(row["model_identity"]),
                                "ncaa_contest_id": contest_id,
                                "snapshot_identity": str(row["snapshot_identity"]),
                            }
                        ),
                        probability_home_win=float(row["probability_home_win"]),
                        candidate_id=str(row["candidate_id"]),
                        reason="THE_PROBABILITY_WAS_FROZEN_BEFORE_THE_CONSERVATIVE_KICKOFF_BOUND",
                    )
                )
                ledger.append(
                    Transition(
                        entity_id=entity_id,
                        entity_kind="FORECAST",
                        sequence=4,
                        from_state="FORECAST_FROZEN",
                        to_state="AWAITING_OFFICIAL_FINAL",
                        at_utc=str(row["created_at_utc"]),
                        source_identity=str(row["snapshot_identity"]),
                        kickoff_utc=str(kickoff),
                        snapshot_identity=str(row["snapshot_identity"]),
                        candidate_id=str(row["candidate_id"]),
                        reason="NO_OFFICIAL_FINAL_EXISTS_YET_FOR_THIS_CONTEST",
                    )
                )
            else:
                ledger.append(
                    Transition(
                        entity_id=entity_id,
                        entity_kind="FORECAST",
                        sequence=1,
                        from_state="PRECOMMITTED",
                        to_state=state,
                        at_utc=str(row["created_at_utc"]),
                        source_identity=str(row.get("snapshot_identity") or capture_identity),
                        kickoff_utc=str(kickoff) if kickoff else None,
                        candidate_id=str(row["candidate_id"]),
                        reason=str(row.get("abstention_reason") or ""),
                    )
                )
    return ledger


# ---------------------------------------------------------------------------
# gap reevaluation
# ---------------------------------------------------------------------------


def _no_promotion(gates: Mapping[str, Mapping[str, Any]]) -> bool:
    for gate in gates.values():
        authority = gate.get("authority") or {}
        if authority.get("champion_or_production_promotion") not in (None, False):
            return False
        nonclaims = gate.get("scientific_nonclaims") or {}
        if nonclaims.get("claims_production_champion") not in (None, False):
            return False
    return True


def evaluate_gap(
    declaration: Mapping[str, Any], gates: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Evaluate one declared gap verdict against the merged gates."""

    kind = str(declaration["verification"]["kind"])
    if kind == "FOUNDATION_PIT_FEATURE_ELIGIBLE_IS_ZERO":
        census = gates["foundation"]["eligibility_census"]
        holds = int(census.get("PIT_FEATURE_ELIGIBLE", -1)) == 0
        observed = {"PIT_FEATURE_ELIGIBLE": census.get("PIT_FEATURE_ELIGIBLE")}
    elif kind == "PROTECTED_LANE_REMAINS_BLOCKED_EVERYWHERE":
        blocked = {
            name: gate.get("protected_lane") for name, gate in gates.items() if "protected_lane" in gate
        }
        holds = all(value == PROTECTED_LANE for value in blocked.values()) and bool(blocked)
        observed = blocked
    elif kind == "NO_PRODUCTION_PROMOTION_IN_ANY_GATE":
        holds = _no_promotion(gates)
        observed = {"gates_checked": sorted(gates)}
    elif kind == "REHEARSAL_EMITS_NO_SPECIALIZATION_ROW":
        specialization = gates["rehearsal"]["specialization"]
        holds = (
            int(specialization["specialization_rows_emitted"]) == 0
            and specialization["single_game_lift_claimed"] is False
            and specialization["comparator_is_mandatory_and_present"] is True
        )
        observed = dict(specialization)
    elif kind == "NO_BAS_CLAIM_IN_ANY_GATE":
        claims = {
            name: (gate.get("scientific_nonclaims") or {}).get("claims_bas_or_aggie_excess")
            for name, gate in gates.items()
        }
        holds = all(value in (None, False) for value in claims.values())
        observed = {name: value for name, value in claims.items() if value is not None}
    elif kind == "AVAILABILITY_IS_NOT_ADMITTED_AND_NOT_INFERRED":
        domain = next(
            (
                row
                for row in gates["domain_matrix"]["admission_matrix"]
                if str(row["domain_id"]) == "pregame_availability"
            ),
            None,
        )
        rehearsal = next(
            (
                row
                for row in gates["rehearsal"]["tamu_feature_availability_matrix"]
                if str(row["domain_id"]) == "tamu_pregame_availability"
            ),
            None,
        )
        holds = (
            domain is not None
            and str(domain["decision"]) != "ADMITTED"
            and rehearsal is not None
            and str(rehearsal["availability_class"]).startswith("UNAVAILABLE")
            and gates["rehearsal"]["scientific_nonclaims"]["claims_availability_from_participation"]
            is False
        )
        observed = {
            "national_decision": None if domain is None else domain["decision"],
            "tamu_availability_class": None if rehearsal is None else rehearsal["availability_class"],
        }
    elif kind == "UNRESOLVED_ENTITIES_ABSTAIN_RATHER_THAN_MATCH":
        counts = gates["forecast"]["contest_state_counts"]
        unsupported = int(counts.get("UNSUPPORTED_ENTITY", 0))
        forecast_states = gates["forecast"]["forecast_state_counts"]
        frozen_contests = len(gates["forecast"]["frozen_forecast_contest_ids"])
        eligible = int(counts.get("SNAPSHOT_FROZEN", 0))
        holds = (
            unsupported > 0
            and int(forecast_states.get("UNSUPPORTED_ENTITY", 0)) > 0
            and frozen_contests == eligible
        )
        observed = {
            "unsupported_contests": unsupported,
            "unsupported_forecast_rows": forecast_states.get("UNSUPPORTED_ENTITY"),
            "frozen_forecast_contests": frozen_contests,
            "snapshot_frozen_contests": eligible,
        }
    else:
        raise ValueError(f"unsupported gap verification kind: {kind}")

    if not holds:
        raise ValueError(
            f"{declaration['gap_id']} verification did not hold against the merged evidence"
        )
    if str(declaration["state"]) != str(declaration["verification"]["expected_state"]):
        raise ValueError(f"{declaration['gap_id']} declared state disagrees with its verification")
    return {
        "gap_id": str(declaration["gap_id"]),
        "title": str(declaration["title"]),
        "state": str(declaration["state"]),
        "materially_advanced": bool(declaration["materially_advanced"]),
        "advance": str(declaration["advance"]),
        "why_still_open": str(declaration["why_still_open"]),
        "closure_requires": list(declaration["closure_requires"]),
        "verification_kind": kind,
        "verification_holds": True,
        "observed": observed,
        "closure_forced": False,
    }


def reevaluate_gaps(
    contract: Mapping[str, Any], gates: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    verdicts = [evaluate_gap(item, gates) for item in contract["gap_reevaluation"]]
    if any(verdict["state"] != "OPEN" for verdict in verdicts):
        raise ValueError("no gap may be closed by this artifact")
    return verdicts


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------


def build_bundle(
    *,
    contract: Mapping[str, Any],
    gates: Mapping[str, Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
    forecasts: Sequence[Mapping[str, Any]],
    frozen_candidate_ids: Sequence[str],
    capture_identity: str,
    execution_time: datetime,
) -> dict[str, Any]:
    if execution_time > datetime.now(timezone.utc):
        raise ValueError("execution time must not be in the future")
    ledger = replay_cohort(
        snapshots=snapshots,
        forecasts=forecasts,
        frozen_candidate_ids=frozen_candidate_ids,
        capture_identity=capture_identity,
    )
    verdicts = reevaluate_gaps(contract, gates)
    entity_kinds = Counter(entry["entity_kind"] for entry in ledger.entries)
    return {
        "execution_time_utc": iso_utc(execution_time),
        "ledger_entries": ledger.entries,
        "terminal_state_counts": ledger.state_counts(),
        "gap_reevaluation": verdicts,
        "counts": {
            "ledger_entries": len(ledger.entries),
            "contest_entities": len(
                {entry["entity_id"] for entry in ledger.entries if entry["entity_kind"] == "CONTEST"}
            ),
            "forecast_entities": len(
                {
                    entry["entity_id"]
                    for entry in ledger.entries
                    if entry["entity_kind"] == "FORECAST"
                }
            ),
            "contest_transitions": entity_kinds.get("CONTEST", 0),
            "forecast_transitions": entity_kinds.get("FORECAST", 0),
            "scored_entities": ledger.state_counts().get("SCORED", 0),
            "gaps_reevaluated": len(verdicts),
            "gaps_closed": 0,
        },
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    bundle: Mapping[str, Any],
    predecessor_sha256: Mapping[str, str],
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_SHADOW_OPERATIONS_AND_GAP_REEVALUATION_GATE",
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
        "state_machine": {
            "append_only": True,
            "progress_states": list(PROGRESS_STATES),
            "terminal_or_side_states": list(SIDE_STATES),
            "rejections": dict(contract["state_machine"]["rejections"]),
        },
        "terminal_state_counts": dict(bundle["terminal_state_counts"]),
        "gap_reevaluation": list(bundle["gap_reevaluation"]),
        "preserved_states": dict(contract["preserved_states"]),
        "counts": dict(bundle["counts"]),
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
            "dataset_identity": dataset_identity,
            "bulk_payloads_in_git": False,
        },
        "authority": dict(contract["authority"]),
        "negative_findings": dict(contract["negative_findings"]),
        "scientific_nonclaims": dict(contract["scientific_nonclaims"]),
    }


def dataset_manifest(
    *,
    contract: Mapping[str, Any],
    bundle: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_SHADOW_OPERATIONS_LEDGER_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": CLASSIFICATION,
        "lane": LANE,
        "execution_time_utc": bundle["execution_time_utc"],
        "counts": dict(bundle["counts"]),
        "terminal_state_counts": dict(bundle["terminal_state_counts"]),
        "payloads": [dict(item) for item in payloads],
        "authority": dict(contract["authority"]),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def validate_artifact(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Independently revalidate the published shadow operations gate."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    if not gate_path.is_file():
        return {"result": "FAIL", "findings": ["the shadow operations gate is absent"]}
    gate = _read_json(gate_path)
    findings: list[str] = []
    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    for name, relative in contract["bound_predecessors"].items():
        if not name.endswith("_relative_path"):
            continue
        key = name.replace("_relative_path", "_sha256")
        if gate["bound_predecessors"].get(key) != sha256_file(repo_root / relative):
            findings.append(f"bound predecessor hash drifted: {key}")
    for verdict in gate.get("gap_reevaluation") or []:
        if verdict.get("state") != "OPEN":
            findings.append(f"a gap was closed by this artifact: {verdict.get('gap_id')}")
        if verdict.get("closure_forced") is not False:
            findings.append(f"gap closure was forced: {verdict.get('gap_id')}")
        if verdict.get("verification_holds") is not True:
            findings.append(f"gap verification did not hold: {verdict.get('gap_id')}")
    if int((gate.get("counts") or {}).get("gaps_closed", -1)) != 0:
        findings.append("the gate reports a closed gap")
    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        findings.append("the ledger manifest is absent from the external data root")
        return {"result": "FAIL", "findings": findings}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("ledger manifest hash drifted")
    manifest = _read_json(manifest_path)
    if manifest.get("dataset_identity") != gate["manifest"]["dataset_identity"]:
        findings.append("dataset identity disagrees with the gate binding")
    for payload in manifest.get("payloads") or []:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        rows = [
            json.loads(line)
            for line in payload_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(rows) != int(payload["rows"]):
            findings.append(f"payload row count drifted: {payload['name']}")
        for row in rows:
            if row.get("protected_lane") != PROTECTED_LANE or row.get("lane") != LANE:
                findings.append("a ledger row left the shadow lane")
                break
            if row.get("promotion_performed") or row.get("publication_performed"):
                findings.append("a ledger row claimed promotion or publication")
                break
            if row.get("availability_inferred"):
                findings.append("a ledger row inferred availability")
                break
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}
