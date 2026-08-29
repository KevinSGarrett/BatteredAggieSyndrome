"""Corrected 2026 Week Zero taxonomy and Texas A&M T-7D checkpoint authority.

Three separate facts were conflated by the predecessor cohort contract: the dates a
query was issued for, the dates the official host echoed back, and the dates that
actually carry Week Zero contests. This module keeps them apart. It also binds the
official athletics structured event record so the kickoff instant stops being an
unconfirmed conservative bound derived from a published local clock.

Nothing here revises a forecast. A checkpoint may add evidence and state only, so the
frozen probabilities are read and rehashed rather than recomputed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc

SCHEMA_VERSION = "aggie.shadow.week_zero_2026_calendar_and_t7d.v1"
CONTRACT_ID = "BAT-661-WEEK-ZERO-2026-CALENDAR-AND-TAMU-T7D-AUTHORITY-V1"
CLASSIFICATION = "WEEK_ZERO_2026_SEASON_TAXONOMY_CORRECTION_AND_TAMU_T7D_CHECKPOINT_AUTHORITY"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK_ZERO_2026_CALENDAR_AND_TAMU_T7D_AUTHORITY"
MISSED_RESULT = "MISSED_CUTOFF_NO_BACKFILL"

CONTRACT_RELATIVE = "configs/week_zero_2026_calendar_and_t7d_contract.json"
GATE_RELATIVE = "artifacts/shadow/week_zero_2026_calendar_and_t7d_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/week_zero_2026_calendar_and_t7d_replay.json"

WEEK_ZERO = "WEEK_ZERO"
WEEK_ZERO_TO_WEEK_ONE = "WEEK_ZERO_TO_WEEK_ONE_TRANSITION"
WEEK_ONE = "WEEK_ONE"
SOURCE_SUBSTITUTION_QUERY = "SOURCE_SUBSTITUTION_QUERY_DATE_NOT_A_WEEK_ZERO_DATE"

CHECKPOINT_CAPTURED = "CAPTURED_BEFORE_DEADLINE"
CHECKPOINT_MISSED = "MISSED_CUTOFF_NO_BACKFILL"
CHECKPOINT_OPEN = "OPEN_NOT_YET_EXECUTED"

_JSON_LD_EVENT_PATTERN = re.compile(
    r'\{"@context":"https://schema\.org/","@id":"[^"]*","@type":"(?:Sports)?Event",.*?'
    r'"location":\{"@type":"Place","name":"[^"]*","address":\{\}\}\}',
    re.DOTALL,
)


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(Path(repo_root) / CONTRACT_RELATIVE)
    if contract["contract_id"] != CONTRACT_ID:
        raise ValueError("contract identity drift")
    if contract["schema_version"] != SCHEMA_VERSION:
        raise ValueError("contract schema drift")
    if contract["lane"] != LANE or contract["protected_lane"] != PROTECTED_LANE:
        raise ValueError("contract lane drift")
    rules = contract["checkpoint_rules"]
    forbidden = (
        "backdated_capture_permitted",
        "backfill_after_the_deadline_permitted",
        "forecast_probability_revision_permitted",
        "candidate_set_change_permitted",
        "feature_shopping_permitted",
        "outcome_access_permitted",
        "early_execution_of_a_future_checkpoint_permitted",
    )
    for key in forbidden:
        if rules[key]:
            raise ValueError(f"contract must forbid {key}")
    authority = contract["authority"]
    for key in (
        "frozen_forecast_revision",
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "forecast_publication",
        "immutable_raw_capture_mutation",
    ):
        if authority[key]:
            raise ValueError(f"authority must not grant {key}")
    taxonomy = contract["corrected_season_taxonomy"]
    if taxonomy["membership_change_permitted"]:
        raise ValueError("a week label correction must not change contest membership")
    declared = (
        list(taxonomy["week_zero_dates"])
        + list(taxonomy["week_zero_to_week_one_transition_dates"])
        + list(taxonomy["week_one_dates"])
        + list(taxonomy["source_substitution_query_dates"])
    )
    if len(declared) != len(set(declared)):
        raise ValueError("a game date may carry exactly one taxonomy label")
    return contract


# ---------------------------------------------------------------------------
# corrected season taxonomy
# ---------------------------------------------------------------------------


def taxonomy_label(contract: Mapping[str, Any], game_date: str) -> str:
    taxonomy = contract["corrected_season_taxonomy"]
    if game_date in taxonomy["week_zero_dates"]:
        return WEEK_ZERO
    if game_date in taxonomy["week_zero_to_week_one_transition_dates"]:
        return WEEK_ZERO_TO_WEEK_ONE
    if game_date in taxonomy["week_one_dates"]:
        return WEEK_ONE
    if game_date in taxonomy["source_substitution_query_dates"]:
        return SOURCE_SUBSTITUTION_QUERY
    raise ValueError(f"game date outside the corrected taxonomy: {game_date}")


def predecessor_label(predecessor_window: Mapping[str, Any], game_date: str) -> str:
    if game_date in predecessor_window.get("week_zero_dates", ()):
        return "WEEK_ZERO"
    if game_date in predecessor_window.get("week_one_dates", ()):
        return "WEEK_ONE"
    return "UNLABELLED"


def build_calendar_correction(
    *,
    contract: Mapping[str, Any],
    predecessor_window: Mapping[str, Any],
    date_observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Relabel each declared date without moving any contest between dates."""

    rows: list[dict[str, Any]] = []
    for observation in sorted(date_observations, key=lambda row: str(row["game_date"])):
        game_date = str(observation["game_date"])
        corrected = taxonomy_label(contract, game_date)
        previous = predecessor_label(predecessor_window, game_date)
        echoed = observation.get("source_echoed_game_date")
        rows.append(
            {
                "game_date": game_date,
                "corrected_label": corrected,
                "predecessor_label": previous,
                "label_changed": corrected != previous,
                "date_observation_state": observation.get("date_observation_state"),
                "source_echoed_game_date": echoed,
                "official_contest_count": int(observation.get("parsed_card_count") or 0),
                "contest_membership_changed": False,
                "source_substituted": echoed is not None and echoed != game_date,
            }
        )
    return rows


def reconcile_membership(
    rows: Sequence[Mapping[str, Any]],
    *,
    predecessor_observations: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Relabelling must not move contests, but the official surface may still move.

    Two different things can change a per-date contest count. This unit relabelling a
    date must never change it, which is a defect. The official host later echoing a
    date it previously substituted is a source observation change, which is evidence and
    must be recorded rather than rejected. The observation state distinguishes them.
    """

    reconciled: list[dict[str, Any]] = []
    for row in rows:
        game_date = str(row["game_date"])
        previous = predecessor_observations.get(game_date)
        observed = int(row["official_contest_count"])
        if previous is None:
            reconciled.append({**dict(row), "membership_reconciliation": "NO_PREDECESSOR_OBSERVATION"})
            continue
        previous_count = int(previous.get("official_contests_enumerated") or 0)
        previous_state = str(previous.get("date_observation_state") or "")
        current_state = str(row["date_observation_state"] or "")
        if previous_state == current_state:
            if observed != previous_count:
                raise ValueError(
                    "contest membership changed under an unchanged observation state on "
                    f"{game_date}: {observed} != {previous_count}"
                )
            reconciliation = "UNCHANGED_UNDER_AN_UNCHANGED_OBSERVATION_STATE"
        else:
            reconciliation = "SOURCE_OBSERVATION_STATE_CHANGED_AT_THE_OFFICIAL_HOST"
        reconciled.append(
            {
                **dict(row),
                "predecessor_observation_state": previous_state or None,
                "predecessor_official_contest_count": previous_count,
                "official_contest_count_delta": observed - previous_count,
                "membership_reconciliation": reconciliation,
            }
        )
    return reconciled


# ---------------------------------------------------------------------------
# official Texas A&M structured event
# ---------------------------------------------------------------------------


def parse_tamu_official_events(document: str) -> list[dict[str, Any]]:
    """Extract the official schema.org event records from the athletics page."""

    events: list[dict[str, Any]] = []
    for match in _JSON_LD_EVENT_PATTERN.finditer(document):
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        schedule = payload.get("eventSchedule") or {}
        events.append(
            {
                "description": str(payload.get("description") or ""),
                "event_status": str(payload.get("eventStatus") or ""),
                "start_date_utc_text": str(payload.get("startDate") or ""),
                "local_start_date": str(schedule.get("startDate") or ""),
                "local_start_time": str(schedule.get("startTime") or ""),
                "schedule_timezone": str(schedule.get("scheduleTimezone") or ""),
                "location_name": str((payload.get("location") or {}).get("name") or ""),
            }
        )
    return events


def select_official_event(
    events: Sequence[Mapping[str, Any]], *, contract: Mapping[str, Any]
) -> dict[str, Any]:
    required = contract["official_tamu_source"]["required_event_description"]
    matches = [event for event in events if event["description"] == required]
    if not matches:
        raise ValueError(f"official athletics page did not carry the event {required!r}")
    if len(matches) > 1:
        raise ValueError(f"official athletics page carried {len(matches)} ambiguous event records")
    return dict(matches[0])


def _parse_structured_instant(value: str) -> datetime:
    text = value.strip()
    if not text.endswith("Z"):
        raise ValueError("official structured start instant must be expressed in UTC")
    body = text[:-1]
    if "." in body:
        head, fraction = body.split(".", 1)
        if not fraction.isdigit():
            raise ValueError("official structured start instant carried a malformed fraction")
        body = head
    return datetime.strptime(body, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def confirm_official_kickoff(
    *,
    contract: Mapping[str, Any],
    event: Mapping[str, Any],
    document: str,
) -> dict[str, Any]:
    """Confirm the kickoff instant only when a second official source truly agrees."""

    policy = contract["independent_confirmation_policy"]
    target = contract["target_contest"]
    bound = parse_utc(str(target["kickoff_utc_conservative_lower_bound"]))
    observed = _parse_structured_instant(str(event["start_date_utc_text"]))
    tokens = {
        token: token.casefold() in document.casefold()
        for token in contract["official_tamu_source"]["required_tokens"]
    }
    agrees = observed == bound
    if observed < bound:
        raise ValueError(
            "the official structured instant precedes the conservative bound, which would "
            "move a cutoff earlier without a new source identity"
        )
    if not agrees and policy["confirmation_requires_agreement_with_the_conservative_bound"]:
        confirmed = False
        state = "OFFICIAL_INSTANT_DISAGREES_WITH_THE_CONSERVATIVE_BOUND_SO_THE_BOUND_IS_RETAINED"
    elif not all(tokens.values()):
        confirmed = False
        state = "OFFICIAL_REQUIRED_TOKENS_ABSENT_SO_CONFIRMATION_IS_WITHHELD"
    else:
        confirmed = True
        state = "OFFICIAL_INSTANT_VENUE_AND_BROADCAST_INDEPENDENTLY_CONFIRMED"
    return {
        "kickoff_utc_conservative_lower_bound": iso_utc(bound),
        "official_structured_start_utc": iso_utc(observed),
        "official_local_start_date": event["local_start_date"],
        "official_local_start_time": event["local_start_time"],
        "official_schedule_timezone": event["schedule_timezone"],
        "official_event_status": event["event_status"],
        "official_location_name": event["location_name"],
        "required_token_presence": dict(sorted(tokens.items())),
        "agrees_with_conservative_bound": agrees,
        "kickoff_utc_independently_confirmed": confirmed,
        "confirmation_state": state,
        "retrieval_time_used_as_kickoff_time": False,
        "effective_kickoff_utc_for_eligibility": iso_utc(bound),
    }


# ---------------------------------------------------------------------------
# checkpoint evaluation
# ---------------------------------------------------------------------------


def evaluate_checkpoints(
    *,
    contract: Mapping[str, Any],
    capture_times: Mapping[str, datetime],
    execution_time: datetime,
) -> list[dict[str, Any]]:
    """Freeze executed checkpoints and leave future checkpoints untouched."""

    if execution_time > datetime.now(timezone.utc) + timedelta(seconds=90):
        raise ValueError("execution time must not be in the future")
    rows: list[dict[str, Any]] = []
    for checkpoint in contract["checkpoints"]:
        checkpoint_id = str(checkpoint["checkpoint_id"])
        deadline = parse_utc(str(checkpoint["deadline_utc"]))
        executed = bool(checkpoint["executed_by_this_unit"])
        if not executed:
            rows.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "deadline_utc": iso_utc(deadline),
                    "is_snapshot_cutoff": bool(checkpoint["is_snapshot_cutoff"]),
                    "executed_by_this_unit": False,
                    "state": CHECKPOINT_OPEN,
                    "captured_at_utc": None,
                    "backfill_permitted_after_the_deadline": False,
                    "early_execution_performed": False,
                }
            )
            continue
        captured_at = capture_times.get(checkpoint_id)
        if captured_at is None:
            state = CHECKPOINT_MISSED if execution_time >= deadline else CHECKPOINT_OPEN
            rows.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "deadline_utc": iso_utc(deadline),
                    "is_snapshot_cutoff": bool(checkpoint["is_snapshot_cutoff"]),
                    "executed_by_this_unit": True,
                    "state": state,
                    "captured_at_utc": None,
                    "backfill_permitted_after_the_deadline": False,
                    "early_execution_performed": False,
                }
            )
            continue
        if captured_at > execution_time:
            raise ValueError(
                f"checkpoint {checkpoint_id} capture claims a time after the execution instant"
            )
        state = CHECKPOINT_CAPTURED if captured_at < deadline else CHECKPOINT_MISSED
        rows.append(
            {
                "checkpoint_id": checkpoint_id,
                "deadline_utc": iso_utc(deadline),
                "is_snapshot_cutoff": bool(checkpoint["is_snapshot_cutoff"]),
                "executed_by_this_unit": True,
                "state": state,
                "captured_at_utc": iso_utc(captured_at),
                "seconds_before_deadline": int((deadline - captured_at).total_seconds()),
                "backfill_permitted_after_the_deadline": False,
                "early_execution_performed": False,
            }
        )
    return rows


def assert_no_backdated_capture(
    captures: Iterable[Mapping[str, Any]], *, earliest_permitted: datetime
) -> None:
    """A T-7D capture must be a real read taken during this checkpoint window."""

    for capture in captures:
        retrieved = parse_utc(str(capture["retrieved_at_utc"]))
        if retrieved < earliest_permitted:
            raise ValueError(
                "a checkpoint capture claimed a retrieval time before the checkpoint window "
                f"opened: {capture.get('source_uri')}"
            )


# ---------------------------------------------------------------------------
# frozen forecast preservation
# ---------------------------------------------------------------------------


def read_frozen_target_forecasts(
    *,
    forecast_rows: Iterable[Mapping[str, Any]],
    ncaa_contest_id: str,
) -> list[dict[str, Any]]:
    rows = [
        {
            "candidate_id": str(row["candidate_id"]),
            "forecast_state": str(row["forecast_state"]),
            "probability_home_win": row.get("probability_home_win"),
            "model_identity": row.get("model_identity"),
            "feature_identity": row.get("feature_identity"),
            "code_identity": row.get("code_identity"),
            "created_at_utc": row.get("created_at_utc"),
            "snapshot_identity": row.get("snapshot_identity"),
        }
        for row in forecast_rows
        if str(row.get("ncaa_contest_id")) == str(ncaa_contest_id)
    ]
    return sorted(rows, key=lambda row: row["candidate_id"])


def assert_forecasts_unrevised(
    *,
    rows: Sequence[Mapping[str, Any]],
    bound_snapshot_identity: str,
    kickoff_lower_bound: datetime,
) -> dict[str, Any]:
    for row in rows:
        if row["snapshot_identity"] != bound_snapshot_identity:
            raise ValueError("a frozen forecast row is bound to a different snapshot identity")
        created = parse_utc(str(row["created_at_utc"]))
        if created >= kickoff_lower_bound:
            raise ValueError("a frozen forecast row claims creation at or after kickoff")
    return {
        "rows": len(rows),
        "probability_identity": stable_hash(
            [
                {"candidate_id": row["candidate_id"], "probability": row["probability_home_win"]}
                for row in rows
            ]
        ),
        "revision_performed": False,
        "candidate_set_changed": False,
        "adjustment_applied": False,
    }


# ---------------------------------------------------------------------------
# domain observation ledger
# ---------------------------------------------------------------------------


def domain_observations(
    *,
    contract: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    domain_matrix: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Record what this checkpoint could and could not observe, and what moved."""

    decisions = {
        str(row["domain_id"]): str(row["decision"])
        for row in domain_matrix.get("admission_matrix", ())
    }
    rows: list[dict[str, Any]] = []
    for domain_id in contract["domain_observation_scope"]:
        if domain_id == "official_kickoff_instant":
            rows.append(
                {
                    "domain_id": domain_id,
                    "availability": "AVAILABLE_OFFICIAL_STRUCTURED_RECORD",
                    "value_changed_at_this_checkpoint": bool(
                        confirmation["kickoff_utc_independently_confirmed"]
                    ),
                    "changed_field": "kickoff_utc_independently_confirmed"
                    if confirmation["kickoff_utc_independently_confirmed"]
                    else None,
                    "observed_value": confirmation["official_structured_start_utc"],
                }
            )
            continue
        if domain_id in {"official_venue_designation", "official_broadcast_designation"}:
            token = "Kyle Field" if domain_id.endswith("venue_designation") else "ESPN"
            present = bool(confirmation["required_token_presence"].get(token))
            rows.append(
                {
                    "domain_id": domain_id,
                    "availability": "AVAILABLE_OFFICIAL_PAGE_TOKEN"
                    if present
                    else "UNAVAILABLE_TOKEN_ABSENT",
                    "value_changed_at_this_checkpoint": present,
                    "changed_field": f"{domain_id}_independently_confirmed" if present else None,
                    "observed_value": token if present else None,
                }
            )
            continue
        decision = decisions.get(domain_id, "SOURCE_ABSENT")
        if decision == "ADMITTED":
            availability = "AVAILABLE_ADMITTED_NATIONAL_INPUT_ALREADY_CONSUMED"
        elif decision == "CANDIDATE":
            availability = "UNAVAILABLE_CANDIDATE_ONLY_NOT_ADMITTED"
        elif decision == "QUARANTINED":
            availability = "UNAVAILABLE_QUARANTINED"
        else:
            availability = "UNAVAILABLE_SOURCE_ABSENT"
        rows.append(
            {
                "domain_id": domain_id,
                "availability": availability,
                "value_changed_at_this_checkpoint": False,
                "changed_field": None,
                "observed_value": None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# artifact assembly
# ---------------------------------------------------------------------------


def build_bundle(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    capture_inventory: Sequence[Mapping[str, Any]],
    calendar_rows: Sequence[Mapping[str, Any]],
    confirmation: Mapping[str, Any],
    checkpoint_rows: Sequence[Mapping[str, Any]],
    forecast_preservation: Mapping[str, Any],
    frozen_rows: Sequence[Mapping[str, Any]],
    domain_rows: Sequence[Mapping[str, Any]],
    execution_time: datetime,
    producer: str,
) -> dict[str, Any]:
    t7d = next(row for row in checkpoint_rows if row["checkpoint_id"] == "T_MINUS_7D")
    result = PASS_RESULT if t7d["state"] == CHECKPOINT_CAPTURED else MISSED_RESULT
    counts = {
        "declared_game_dates": len(calendar_rows),
        "week_zero_dates": sum(1 for row in calendar_rows if row["corrected_label"] == WEEK_ZERO),
        "week_one_dates": sum(1 for row in calendar_rows if row["corrected_label"] == WEEK_ONE),
        "transition_dates": sum(
            1 for row in calendar_rows if row["corrected_label"] == WEEK_ZERO_TO_WEEK_ONE
        ),
        "source_substitution_query_dates": sum(
            1 for row in calendar_rows if row["corrected_label"] == SOURCE_SUBSTITUTION_QUERY
        ),
        "relabelled_dates": sum(1 for row in calendar_rows if row["label_changed"]),
        "official_contests_observed": sum(
            int(row["official_contest_count"]) for row in calendar_rows
        ),
        "frozen_target_forecast_rows": len(frozen_rows),
        "checkpoints_executed": sum(
            1 for row in checkpoint_rows if row["state"] == CHECKPOINT_CAPTURED
        ),
        "checkpoints_open": sum(1 for row in checkpoint_rows if row["state"] == CHECKPOINT_OPEN),
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK_ZERO_2026_CALENDAR_AND_TAMU_T7D_AUTHORITY",
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha256,
        "decision_unit": contract["decision_unit"],
        "local_issue_id": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": result,
        "producer": producer,
        "execution_time_utc": iso_utc(execution_time),
        "supersession": contract["supersession"],
        "capture_inventory": [dict(sorted(row.items())) for row in capture_inventory],
        "corrected_calendar": [dict(sorted(row.items())) for row in calendar_rows],
        "counts": counts,
        "official_kickoff_confirmation": dict(sorted(confirmation.items())),
        "checkpoint_ledger": [dict(sorted(row.items())) for row in checkpoint_rows],
        "frozen_forecast_preservation": dict(sorted(forecast_preservation.items())),
        "frozen_target_forecasts": [dict(sorted(row.items())) for row in frozen_rows],
        "domain_observations": [dict(sorted(row.items())) for row in domain_rows],
        "authority": contract["authority"],
        "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
        "outcome_exclusion": {
            "outcome_fields_extracted": False,
            "outcome_accessible_before_forecast_freeze": False,
            "target_game_outcome_excluded": True,
        },
    }
    return {**core, "gate_identity": binding_identity(core, "gate_identity")}


def gate_identity_of(gate: Mapping[str, Any]) -> str:
    """Identity over the whole gate.

    The gate deliberately carries no wall-clock issue stamp, so two runs from the same
    capture manifest and the same execution instant produce byte-identical output.
    """

    core = {key: value for key, value in gate.items() if key != "gate_identity"}
    return binding_identity(core, "gate_identity")


def validate_artifact(repo_root: Path) -> dict[str, Any]:
    """Independently revalidate the merged gate without touching the network."""

    root = Path(repo_root)
    contract = load_contract(root)
    gate_path = root / GATE_RELATIVE
    if not gate_path.is_file():
        return {"result": "FAIL", "findings": [f"missing gate: {GATE_RELATIVE}"]}
    gate = _read_json(gate_path)
    findings: list[str] = []

    if gate["contract_id"] != CONTRACT_ID:
        findings.append("gate contract identity drift")
    if gate["contract_sha256"] != sha256_file(root / CONTRACT_RELATIVE):
        findings.append("gate contract hash drift")
    if gate_identity_of(gate) != gate["gate_identity"]:
        findings.append("gate identity drift")
    if gate["lane"] != LANE or gate["protected_lane"] != PROTECTED_LANE:
        findings.append("gate lane drift")
    if gate["result"] not in {PASS_RESULT, MISSED_RESULT}:
        findings.append(f"unsupported gate result {gate['result']!r}")

    for predecessor in gate["supersession"]["predecessors"]:
        path = root / predecessor["artifact_relative_path"]
        if not path.is_file():
            findings.append(f"missing predecessor gate: {predecessor['artifact_relative_path']}")
            continue
        recorded = _read_json(path).get("gate_identity")
        if recorded != predecessor["gate_identity"]:
            findings.append(
                f"predecessor gate identity drift: {predecessor['artifact_relative_path']}"
            )

    labels = {row["game_date"]: row["corrected_label"] for row in gate["corrected_calendar"]}
    for game_date, label in labels.items():
        if taxonomy_label(contract, game_date) != label:
            findings.append(f"corrected label drift on {game_date}")
    for row in gate["corrected_calendar"]:
        if row["contest_membership_changed"]:
            findings.append(f"contest membership changed on {row['game_date']}")

    confirmation = gate["official_kickoff_confirmation"]
    if confirmation["retrieval_time_used_as_kickoff_time"]:
        findings.append("a retrieval time was used as a kickoff time")
    if confirmation["effective_kickoff_utc_for_eligibility"] != str(
        contract["target_contest"]["kickoff_utc_conservative_lower_bound"]
    ):
        findings.append("the effective eligibility instant drifted from the conservative bound")

    for row in gate["checkpoint_ledger"]:
        if row["backfill_permitted_after_the_deadline"]:
            findings.append(f"checkpoint {row['checkpoint_id']} permits backfill")
        if row["early_execution_performed"]:
            findings.append(f"checkpoint {row['checkpoint_id']} was executed early")
        if row["state"] == CHECKPOINT_CAPTURED:
            captured = parse_utc(str(row["captured_at_utc"]))
            if captured >= parse_utc(str(row["deadline_utc"])):
                findings.append(f"checkpoint {row['checkpoint_id']} captured after its deadline")
        if row["checkpoint_id"] != "T_MINUS_7D" and row["state"] != CHECKPOINT_OPEN:
            findings.append(f"future checkpoint {row['checkpoint_id']} is not open")

    preservation = gate["frozen_forecast_preservation"]
    for key in ("revision_performed", "candidate_set_changed", "adjustment_applied"):
        if preservation[key]:
            findings.append(f"frozen forecast preservation violated: {key}")
    expected = stable_hash(
        [
            {"candidate_id": row["candidate_id"], "probability": row["probability_home_win"]}
            for row in gate["frozen_target_forecasts"]
        ]
    )
    if expected != preservation["probability_identity"]:
        findings.append("frozen probability identity drift")

    if gate["outcome_exclusion"]["outcome_fields_extracted"]:
        findings.append("an outcome field was extracted")
    for key, value in gate["scientific_nonclaims"].items():
        if value:
            findings.append(f"scientific nonclaim asserted: {key}")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate["gate_identity"],
        "gate_result": gate["result"],
    }
