"""Materialize the corrected BAT-674 Week Zero official-final scoring successor.

Every artifact this tool writes is a pure function of the raw NCAA HTML plus the
immutable BAT-663/BAT-664/BAT-665 predecessors, so
``tools/validate_week_zero_2026_official_final_scoring_successor.py`` can rebuild
all of it offline and compare byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.modeling.week_zero_official_final_scoring import (  # noqa: E402
    AWAITING,
    MISSED_CUTOFF,
    PROOF_COMPLETE,
    QUARANTINED,
    RECONCILIATION_ABSTAIN,
    RECONCILIATION_CFBD_QUOTA,
    RECONCILIATION_EXACT,
    RECONCILIATION_MISSED,
    RECONCILIATION_QUARANTINED,
    SCORED,
    UNSUPPORTED_ENTITY_FAILURE,
    OfficialFinalScoringViolation,
    brier_contribution,
    build_official_capture_manifest,
    candidate_metrics,
    failure_is_conflict,
    favorite_direction,
    frozen_forecast_row_identity,
    identity_excluding_identity_field,
    iso_utc,
    log_loss_contribution,
    parse_utc,
    pooled_model_row_diagnostics,
    prove_contest_orientation,
    scoring_row_identity,
    sha256_of,
    state_counts,
    temporal_verdict_row_identity,
    unique_contest_outcome_diagnostics,
)

CONTRACT_RELATIVE = "configs/week_zero_2026_official_final_scoring_successor_contract.json"
PREDECESSOR_GATE_RELATIVE = "artifacts/shadow/week_zero_2026_live_execution_gate.json"
FORECAST_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_forecast_gate.json"
TEMPORAL_AUDIT_RELATIVE = "artifacts/shadow/prospective_2026_shadow_temporal_audit_gate.json"
CFBD_PROBE_RELATIVE = "artifacts/shadow/week_zero_2026_cfbd_route_probe.json"
PRODUCER_RELATIVE = "tools/build_week_zero_2026_official_final_scoring_successor.py"
VALIDATOR_RELATIVE = "tools/validate_week_zero_2026_official_final_scoring_successor.py"
CORE_RELATIVE = "src/aggie_analytics/modeling/week_zero_official_final_scoring.py"

GATE_RELATIVE = "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"
REPLAY_RELATIVE = "artifacts/shadow/week_zero_2026_official_final_scoring_successor_replay.json"
TRANSITIONS_RELATIVE = (
    "artifacts/shadow/week_zero_2026_official_final_scoring_successor_state_transitions.json"
)
SCORING_RELATIVE = "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json"
RESIDUAL_RELATIVE = "artifacts/shadow/week_zero_2026_prospective_residual_successor_payload.json"
CROSSWALK_RELATIVE = "artifacts/shadow/week_zero_2026_cfbd_crosswalk.json"
RECONCILIATION_RELATIVE = "artifacts/shadow/week_zero_2026_result_reconciliation_gate.json"

CAPTURE_MANIFEST_NAME = "week_zero_2026_official_final_capture_manifest.json"
CAPTURE_MANIFEST_FAMILY = "manifests/shadow/week_zero_2026_official_final_capture/sha256"

OFFICIAL_SOURCE_LABEL = "NCAA_OFFICIAL_SCOREBOARD_VIA_DECLARED_TRANSPORT"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise OfficialFinalScoringViolation(f"{path.as_posix()} is not a JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_raw_captures(*, data_root: Path, acquisition_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Resolve the raw bytes behind each declared acquisition capture."""
    captures: list[dict[str, Any]] = []
    for row in acquisition_manifest.get("captures", []):
        if str(row.get("state")) != "CAPTURED":
            continue
        raw_path = data_root / str(row["raw_relative_path"])
        raw_bytes = raw_path.read_bytes()
        captures.append(
            {
                "requested_game_date": str(row["game_date"]),
                "raw_bytes": raw_bytes,
                "document": raw_bytes.decode("utf-8", errors="replace"),
                "raw_sha256": str(row["raw_sha256"]),
                "raw_relative_path": str(row["raw_relative_path"]),
                "request_identity_sha256": str(row["request_identity_sha256"]),
                "retrieved_at_utc": str(row["retrieved_at_utc"]),
                "route_id": str(row["route_id"]),
                "source_uri": str(row["source_uri"]),
            }
        )
    return captures


def predecessor_participants_by_contest(
    predecessor_capture_manifest: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Ordered away-then-home source participants published by BAT-665."""
    ordered: dict[str, list[dict[str, Any]]] = {}
    for row in predecessor_capture_manifest.get("refreshed_contests", []):
        if str(row.get("requested_game_date")) != str(row.get("source_published_game_date")):
            continue
        ordered.setdefault(str(row["ncaa_contest_id"]), list(row.get("participants") or []))
    return ordered


def build_successor(
    *,
    repo_root: Path,
    data_root: Path,
    execution_time_utc: str,
    acquisition_capture_identity: str,
) -> dict[str, Any]:
    contract_path = repo_root / CONTRACT_RELATIVE
    contract = read_json(contract_path)
    contract_sha256 = file_sha256(contract_path)
    predecessor = contract["predecessor_authority"]

    predecessor_gate_path = repo_root / PREDECESSOR_GATE_RELATIVE
    predecessor_gate = read_json(predecessor_gate_path)
    for field in ("gate_identity", "capture_identity", "execution_time_utc"):
        contract_field = field if field != "gate_identity" else "gate_identity"
        if predecessor_gate.get(field) != predecessor[contract_field]:
            raise OfficialFinalScoringViolation(f"BAT-665 predecessor {field} mismatch")
    if predecessor_gate.get("contest_state_counts") != predecessor["contest_state_counts"]:
        raise OfficialFinalScoringViolation("BAT-665 predecessor contest counts mismatch")
    if predecessor_gate.get("forecast_state_counts") != predecessor["forecast_state_counts"]:
        raise OfficialFinalScoringViolation("BAT-665 predecessor forecast counts mismatch")
    if len(predecessor_gate.get("append_only_transitions", [])) != int(
        predecessor["transition_count"]
    ):
        raise OfficialFinalScoringViolation("BAT-665 predecessor transition count mismatch")

    temporal_audit_path = repo_root / TEMPORAL_AUDIT_RELATIVE
    temporal_audit = read_json(temporal_audit_path)
    temporal_by_key = {
        (str(row["ncaa_contest_id"]), str(row["candidate_id"])): row
        for row in temporal_audit.get("row_verdicts", [])
    }

    forecast_gate_path = repo_root / FORECAST_GATE_RELATIVE
    forecast_gate = read_json(forecast_gate_path)
    forecast_manifest = read_json(data_root / forecast_gate["manifest"]["relative_path"])
    snapshot_payload = next(
        row
        for row in forecast_manifest["payloads"]
        if row["role"] == "PROSPECTIVE_2026_SHADOW_SNAPSHOT_ROWS"
    )
    snapshot_records = {
        str(row["ncaa_contest_id"]): row
        for row in read_jsonl(data_root / snapshot_payload["relative_path"])
    }

    predecessor_capture_manifest = read_json(
        data_root
        / "manifests/shadow/week_zero_2026_live_execution/sha256"
        / str(predecessor["capture_identity"])
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    ordered_participants = predecessor_participants_by_contest(predecessor_capture_manifest)

    acquisition_manifest = read_json(
        data_root
        / "manifests/shadow/week_zero_2026_live_execution/sha256"
        / acquisition_capture_identity
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    raw_captures = load_raw_captures(data_root=data_root, acquisition_manifest=acquisition_manifest)

    capture_manifest = build_official_capture_manifest(
        captures=raw_captures,
        contract_sha256=contract_sha256,
        issued_at_utc=execution_time_utc,
    )
    capture_identity = str(capture_manifest["capture_identity"])
    finals_by_contest = {
        str(row["ncaa_contest_id"]): row for row in capture_manifest["official_finals"]
    }

    execution_time = parse_utc(execution_time_utc)
    if execution_time is None:
        raise OfficialFinalScoringViolation("execution time is not a UTC instant")

    cfbd_probe_path = repo_root / CFBD_PROBE_RELATIVE
    cfbd_probe = read_json(cfbd_probe_path) if cfbd_probe_path.is_file() else {}
    cfbd_state = str(cfbd_probe.get("acquisition_result") or "NOT_ATTEMPTED")
    cfbd_quota_exhausted = "QUOTA" in cfbd_state.upper()

    predecessor_contests = {
        str(row["ncaa_contest_id"]): dict(row) for row in predecessor_gate.get("contest_rows", [])
    }
    frozen_forecasts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in predecessor_gate.get("forecast_rows", []):
        frozen_forecasts[str(row["ncaa_contest_id"])].append(dict(row))

    contest_rows: list[dict[str, Any]] = []
    forecast_rows: list[dict[str, Any]] = []
    scored_rows: list[dict[str, Any]] = []
    orientation_proofs: list[dict[str, Any]] = []
    crosswalk_rows: list[dict[str, Any]] = []
    appended_transitions: list[dict[str, Any]] = []

    for contest_id in sorted(predecessor_contests):
        prior = predecessor_contests[contest_id]
        snapshot = snapshot_records.get(contest_id, {})
        kickoff = parse_utc(prior.get("kickoff_bound_utc"))
        kickoff_elapsed = kickoff is not None and execution_time >= kickoff
        frozen_rows = frozen_forecasts.get(contest_id, [])
        final_card = finals_by_contest.get(contest_id)

        proof: dict[str, Any] | None = None
        if final_card is not None:
            proof = prove_contest_orientation(
                final_card=final_card,
                frozen_contest_row=prior,
                snapshot_record=snapshot,
                predecessor_participants=ordered_participants.get(contest_id, []),
                capture_identity=capture_identity,
            )
            orientation_proofs.append(proof)

        proven = proof is not None and proof["proof_state"] == "ORIENTATION_PROVEN"
        conflict_reasons = sorted(
            reason
            for reason in (proof["failure_reasons"] if proof else [])
            if failure_is_conflict(reason)
        )
        unsupported_entity = bool(
            proof and UNSUPPORTED_ENTITY_FAILURE in proof["failure_reasons"]
        )

        if conflict_reasons:
            contest_state = QUARANTINED
            reason = "ORIENTATION_OR_ADMISSIBILITY_PROOF_FAILED_CLOSED"
        elif kickoff_elapsed and not frozen_rows:
            contest_state = MISSED_CUTOFF
            reason = (
                "UNRESOLVED_PARTICIPANT_IDENTITY_LEFT_NO_FROZEN_FORECAST_BEFORE_THE_KICKOFF_BOUND"
                if unsupported_entity
                else "NO_FROZEN_FORECAST_EXISTS_AFTER_KICKOFF_BOUND"
            )
        elif proven and frozen_rows:
            contest_state = SCORED
            reason = "OFFICIAL_NCAA_FINAL_OBSERVED_AND_ORIENTATION_PROVEN"
        else:
            contest_state = AWAITING
            reason = "NO_ADMISSIBLE_OFFICIAL_FINAL_EXISTS"

        current = dict(prior)
        current["contest_state"] = contest_state
        current["state_reason"] = reason
        current["timing_state"] = (
            "KICKOFF_BOUND_HAS_ELAPSED"
            if kickoff_elapsed
            else "CONTEST_HAS_NOT_REACHED_ITS_KICKOFF_BOUND"
        )
        current["final_capture_after_kickoff"] = bool(
            proof and proof.get("final_capture_after_kickoff")
        )
        current["unsupported_entity"] = unsupported_entity
        current["conflict_reasons"] = conflict_reasons
        if proof is not None:
            current["official_final_status_state"] = (
                "OFFICIAL_FINAL_OBSERVED" if proven else "OFFICIAL_FINAL_QUARANTINED"
            )
            current["official_final_status_text"] = proof.get("final_status_text")
            current["official_status_capture_sha256"] = proof.get("official_raw_response_sha256")
            current["official_status_retrieved_at_utc"] = proof.get(
                "final_capture_retrieved_at_utc"
            )
            current["home_points"] = proof.get("home_points")
            current["away_points"] = proof.get("away_points")
            current["official_final_source"] = OFFICIAL_SOURCE_LABEL
            current["contest_orientation_identity"] = proof["contest_orientation_identity"]
            current["official_capture_identity"] = capture_identity
        contest_rows.append(current)

        if contest_state != str(prior.get("contest_state")):
            appended_transitions.append(
                {
                    "entity_id": contest_id,
                    "entity_kind": "CONTEST",
                    "from_state": str(prior.get("contest_state")),
                    "to_state": contest_state,
                    "observed_at_utc": iso_utc(execution_time),
                    "reason": reason,
                }
            )

        if contest_state == SCORED:
            disposition = RECONCILIATION_EXACT
        elif contest_state == QUARANTINED:
            disposition = RECONCILIATION_QUARANTINED
        elif contest_state == MISSED_CUTOFF:
            disposition = RECONCILIATION_MISSED
        else:
            disposition = RECONCILIATION_ABSTAIN

        crosswalk_rows.append(
            {
                "ncaa_contest_id": contest_id,
                "season": 2026,
                "kickoff_date": snapshot.get("source_published_game_date"),
                "kickoff_bound_utc": prior.get("kickoff_bound_utc"),
                "ncaa_identity_disposition": disposition,
                "cfbd_enrichment_disposition": (
                    RECONCILIATION_CFBD_QUOTA if cfbd_quota_exhausted else cfbd_state
                ),
                "cfbd_game_id": None,
                "cfbd_absence_is_enrichment_limitation_not_identity_failure": True,
                "ordered_source_team_identifiers": ordered_participants.get(contest_id, []),
                "canonical_team_identifiers": {
                    "away_canonical_team_id": snapshot.get("away_canonical_team_id"),
                    "home_canonical_team_id": snapshot.get("home_canonical_team_id"),
                },
                "contest_orientation_identity": (
                    proof["contest_orientation_identity"] if proof else None
                ),
                "official_capture_identity": capture_identity if proof else None,
                "official_raw_response_sha256": (
                    proof.get("official_raw_response_sha256") if proof else None
                ),
                "matched_fields": (
                    ["ncaa_contest_id", "ordered_source_team_ids", "canonical_team_ids"]
                    if proven
                    else []
                ),
                "conflicting_fields": conflict_reasons,
                "unsupported_entity": unsupported_entity,
            }
        )

        for frozen in sorted(frozen_rows, key=lambda row: str(row["candidate_id"])):
            candidate_id = str(frozen["candidate_id"])
            verdict_row = temporal_by_key.get((contest_id, candidate_id))
            temporal_complete = (
                verdict_row is not None and str(verdict_row.get("verdict")) == PROOF_COMPLETE
            )
            out = dict(frozen)
            out["frozen_forecast_row_identity"] = frozen_forecast_row_identity(frozen)
            out["forecast_gate_identity"] = str(predecessor_gate["gate_identity"])
            out["bat664_temporal_audit_gate_identity"] = str(temporal_audit["gate_identity"])
            out["temporal_verdict_row_identity"] = (
                temporal_verdict_row_identity(verdict_row) if verdict_row else None
            )
            out["bat665_gate_identity"] = str(predecessor["gate_identity"])

            if contest_state == SCORED and temporal_complete and proof is not None:
                probability = float(frozen["probability_home_win"])
                home_win = int(proof["home_win"])
                residual = home_win - probability
                brier = brier_contribution(probability, home_win)
                loss = log_loss_contribution(probability, home_win)
                direction = favorite_direction(probability)

                out["forecast_state"] = SCORED
                out["state_reason"] = "OFFICIAL_FINAL_ORIENTATION_PROVEN_AND_TEMPORAL_PROOF_COMPLETE"
                out["home_win"] = home_win
                out["home_points"] = proof["home_points"]
                out["away_points"] = proof["away_points"]
                out["result_residual"] = residual
                out["brier_contribution"] = brier
                out["log_loss_contribution"] = loss
                out["favorite_direction"] = direction
                out["official_final_source"] = OFFICIAL_SOURCE_LABEL

                scoring_row: dict[str, Any] = {
                    "ncaa_contest_id": contest_id,
                    "candidate_id": candidate_id,
                    "frozen_probability_home_win": probability,
                    "home_win": home_win,
                    "home_points": proof["home_points"],
                    "away_points": proof["away_points"],
                    "result_residual": residual,
                    "brier_contribution": brier,
                    "log_loss_contribution": loss,
                    "favorite_direction": direction,
                    "directional_correct": (
                        None
                        if direction == "NO_DIRECTION"
                        else int((direction == "HOME") == bool(home_win))
                    ),
                    "official_final_source": OFFICIAL_SOURCE_LABEL,
                    "frozen_forecast_row_identity": out["frozen_forecast_row_identity"],
                    "forecast_gate_identity": out["forecast_gate_identity"],
                    "bat664_temporal_audit_gate_identity": out[
                        "bat664_temporal_audit_gate_identity"
                    ],
                    "temporal_verdict_row_identity": out["temporal_verdict_row_identity"],
                    "bat665_gate_identity": out["bat665_gate_identity"],
                    "official_capture_identity": capture_identity,
                    "official_raw_response_sha256": proof["official_raw_response_sha256"],
                    "contest_orientation_identity": proof["contest_orientation_identity"],
                }
                scoring_row["reconciliation_identity"] = sha256_of(
                    {
                        "ncaa_contest_id": contest_id,
                        "disposition": RECONCILIATION_EXACT,
                        "contest_orientation_identity": proof["contest_orientation_identity"],
                        "official_capture_identity": capture_identity,
                    }
                )
                scoring_row["scoring_row_identity"] = scoring_row_identity(scoring_row)
                scored_rows.append(scoring_row)
                out["scoring_row_identity"] = scoring_row["scoring_row_identity"]

                appended_transitions.append(
                    {
                        "entity_id": f"{contest_id}::{candidate_id}",
                        "entity_kind": "FORECAST",
                        "from_state": str(frozen.get("forecast_state")),
                        "to_state": SCORED,
                        "observed_at_utc": iso_utc(execution_time),
                        "reason": "OFFICIAL_FINAL_ORIENTATION_PROVEN_AND_TEMPORAL_PROOF_COMPLETE",
                    }
                )
            elif contest_state == QUARANTINED:
                out["forecast_state"] = QUARANTINED
                out["state_reason"] = "CONTEST_ORIENTATION_PROOF_FAILED_CLOSED"
            forecast_rows.append(out)

    scored_rows.sort(key=lambda row: (str(row["ncaa_contest_id"]), str(row["candidate_id"])))
    orientation_proofs.sort(key=lambda row: str(row["ncaa_contest_id"]))

    contest_state_counts = state_counts(contest_rows, "contest_state")
    forecast_state_counts = state_counts(forecast_rows, "forecast_state")

    scored_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored_rows:
        scored_by_candidate[str(row["candidate_id"])].append(row)

    candidates = sorted({str(row["candidate_id"]) for row in predecessor_gate["forecast_rows"]})
    missed_cutoff_contests = [
        str(row["ncaa_contest_id"]) for row in contest_rows if row["contest_state"] == MISSED_CUTOFF
    ]
    unsupported_contests = [
        str(row["ncaa_contest_id"]) for row in contest_rows if row.get("unsupported_entity")
    ]

    metrics_by_candidate: dict[str, Any] = {}
    for candidate in candidates:
        candidate_frozen = [
            row
            for row in predecessor_gate["forecast_rows"]
            if str(row["candidate_id"]) == candidate
        ]
        eligible = [
            row
            for row in candidate_frozen
            if str(
                (
                    temporal_by_key.get((str(row["ncaa_contest_id"]), candidate)) or {}
                ).get("verdict")
            )
            == PROOF_COMPLETE
        ]
        candidate_scored = scored_by_candidate.get(candidate, [])
        temporal_exclusions = len(candidate_frozen) - len(eligible)
        quarantined_contests = {
            str(row["ncaa_contest_id"]) for row in contest_rows if row["contest_state"] == QUARANTINED
        }
        pending = sum(
            1
            for row in eligible
            if str(row["ncaa_contest_id"]) not in {r["ncaa_contest_id"] for r in candidate_scored}
            and str(row["ncaa_contest_id"]) not in quarantined_contests
        )
        metrics_by_candidate[candidate] = candidate_metrics(
            scored_rows=candidate_scored,
            predeclared_eligible_opportunity_count=len(eligible),
            pending_row_count=pending,
            temporal_exclusion_count=temporal_exclusions,
            unsupported_count=len(unsupported_contests),
            missed_cutoff_with_no_forecast_count=len(missed_cutoff_contests),
        )

    pooled = pooled_model_row_diagnostics(scored_rows)
    unique_contest = unique_contest_outcome_diagnostics(scored_rows)

    scoring_payload = {
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_SCORING_SUCCESSOR_PAYLOAD",
        "contract_id": contract["contract_id"],
        "forecast_rows": forecast_rows,
        "forecast_state_counts": forecast_state_counts,
        "metrics_by_candidate": metrics_by_candidate,
        "official_capture_identity": capture_identity,
        "orientation_proofs": orientation_proofs,
        "pooled_model_row_diagnostics": pooled,
        "result": "SCORED_FROM_ADMISSIBLE_OFFICIAL_FINALS"
        if scored_rows
        else "NO_ADMISSIBLE_OFFICIAL_FINALS_SCOREABLE",
        "scientific_nonclaims": {
            "no_bas_or_aggie_excess_claim": True,
            "no_production_or_specialization_claim": True,
            "no_tuning_selection_or_promotion_from_these_results": True,
            "tiny_population_no_calibration_or_champion_claim": True,
        },
        "scored_rows": scored_rows,
        "unique_contest_outcome_diagnostics": unique_contest,
    }
    scoring_payload["payload_identity"] = sha256_of(scoring_payload)

    residual_rows = [
        {
            "ncaa_contest_id": row["ncaa_contest_id"],
            "candidate_id": row["candidate_id"],
            "frozen_probability_home_win": row["frozen_probability_home_win"],
            "home_win": row["home_win"],
            "result_residual": row["result_residual"],
            "frozen_forecast_row_identity": row["frozen_forecast_row_identity"],
            "temporal_verdict_row_identity": row["temporal_verdict_row_identity"],
            "contest_orientation_identity": row["contest_orientation_identity"],
            "official_capture_identity": row["official_capture_identity"],
            "official_raw_response_sha256": row["official_raw_response_sha256"],
            "reconciliation_identity": row["reconciliation_identity"],
            "scoring_row_identity": row["scoring_row_identity"],
        }
        for row in scored_rows
    ]
    residual_payload = {
        "artifact_type": "WEEK_ZERO_2026_PROSPECTIVE_RESIDUAL_SUCCESSOR_PAYLOAD",
        "admitted_row_count": len(residual_rows),
        "admitted_rows": residual_rows,
        "residual_only_on_scored_rows": True,
        "result": "RESIDUAL_ROWS_AVAILABLE_FROM_OFFICIAL_FINAL_SCORING"
        if residual_rows
        else "NO_RESIDUAL_ROWS_WITHOUT_OFFICIAL_FINAL_SCORING",
        "unscored_row_count": len(forecast_rows) - len(residual_rows),
    }
    residual_payload["payload_identity"] = sha256_of(residual_payload)

    crosswalk_payload = {
        "artifact_type": "WEEK_ZERO_2026_NCAA_CFBD_CROSSWALK",
        "cfbd_acquisition_state": cfbd_state,
        "cfbd_route_probe_present": cfbd_probe_path.is_file(),
        "counts": dict(
            sorted(Counter(str(row["ncaa_identity_disposition"]) for row in crosswalk_rows).items())
        ),
        "official_capture_identity": capture_identity,
        "rows": crosswalk_rows,
    }
    crosswalk_payload["crosswalk_identity"] = sha256_of(crosswalk_payload)

    reconciliation_gate = {
        "artifact_type": "WEEK_ZERO_2026_RESULT_RECONCILIATION_GATE",
        "cfbd_source_label": "CFBD_STRUCTURED_FINAL_EVIDENCE",
        "contest_state_counts": contest_state_counts,
        "crosswalk_identity": crosswalk_payload["crosswalk_identity"],
        "disposition_counts": crosswalk_payload["counts"],
        "official_capture_identity": capture_identity,
        "official_final_source_label": OFFICIAL_SOURCE_LABEL,
        "orientation_proven_contest_count": sum(
            1 for row in orientation_proofs if row["proof_state"] == "ORIENTATION_PROVEN"
        ),
        "pending_contest_count": contest_state_counts.get(AWAITING, 0),
        "quarantine_contest_count": contest_state_counts.get(QUARANTINED, 0),
        "result": "PASS_RECONCILIATION",
        "scored_row_count": len(scored_rows),
    }
    reconciliation_gate["gate_identity"] = identity_excluding_identity_field(reconciliation_gate)

    successor_transitions = list(predecessor_gate.get("append_only_transitions", [])) + (
        appended_transitions
    )
    transition_ledger = {
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_SCORING_SUCCESSOR_STATE_TRANSITIONS",
        "append_only": True,
        "bound_predecessor_transition_count": predecessor["transition_count"],
        "new_transition_count": len(appended_transitions),
        "new_transitions": appended_transitions,
        "total_transition_count": len(successor_transitions),
        "transitions": successor_transitions,
    }
    transition_ledger["ledger_identity"] = sha256_of(transition_ledger)

    external_manifest_relative = (
        f"{CAPTURE_MANIFEST_FAMILY}/{capture_identity}/{CAPTURE_MANIFEST_NAME}"
    )

    gate: dict[str, Any] = {
        "acquisition_capture_identity": acquisition_capture_identity,
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_SCORING_SUCCESSOR_GATE",
        "bound_child_artifact_identities": {
            "contract_sha256": contract_sha256,
            "core_module_sha256": file_sha256(repo_root / CORE_RELATIVE),
            "crosswalk_identity": crosswalk_payload["crosswalk_identity"],
            "official_capture_identity": capture_identity,
            "official_capture_manifest_relative_path": external_manifest_relative,
            "producer_sha256": file_sha256(repo_root / PRODUCER_RELATIVE),
            "reconciliation_gate_identity": reconciliation_gate["gate_identity"],
            "residual_payload_identity": residual_payload["payload_identity"],
            "scoring_payload_identity": scoring_payload["payload_identity"],
            "temporal_audit_gate_identity": str(temporal_audit["gate_identity"]),
            "temporal_audit_sha256": file_sha256(temporal_audit_path),
            "transition_ledger_identity": transition_ledger["ledger_identity"],
            "validator_sha256": file_sha256(repo_root / VALIDATOR_RELATIVE),
        },
        "bound_predecessor_identities": {
            "bat665_capture_identity": predecessor["capture_identity"],
            "bat665_gate_identity": predecessor["gate_identity"],
            "bat665_gate_sha256": file_sha256(predecessor_gate_path),
            "bat665_transition_count": predecessor["transition_count"],
            "forecast_gate_identity": str(predecessor_gate["gate_identity"]),
        },
        "classification": contract["classification"],
        "contest_rows": contest_rows,
        "contest_state_counts": contest_state_counts,
        "contract_id": contract["contract_id"],
        "contract_sha256": contract_sha256,
        "execution_time_utc": iso_utc(execution_time),
        "forecast_state_counts": forecast_state_counts,
        "jira_key": contract["jira_key"],
        "lane": contract["lane"],
        "local_issue_id": contract["local_issue_id"],
        "metrics_by_candidate": metrics_by_candidate,
        "official_capture_summary": {
            "admissible_final_capture_count": capture_manifest["admissible_final_capture_count"],
            "capture_count": capture_manifest["capture_count"],
            "source_substitution_capture_count": capture_manifest[
                "source_substitution_capture_count"
            ],
            "source_substitution_observation_count": len(
                capture_manifest["source_substitution_observations"]
            ),
            "unique_official_final_count": capture_manifest["unique_official_final_count"],
        },
        "parent_jira_key": contract["parent_jira_key"],
        "pooled_model_row_diagnostics": pooled,
        "predecessor_identity": predecessor["gate_identity"],
        "protected_lane": contract["protected_lane"],
        "result": "PASS_WEEK_ZERO_2026_OFFICIAL_FINAL_SCORING_SUCCESSOR",
        "schema_version": contract["schema_version"],
        "scientific_nonclaims": scoring_payload["scientific_nonclaims"],
        "unique_contest_outcome_diagnostics": unique_contest,
    }
    gate["gate_identity"] = identity_excluding_identity_field(gate)

    replay = {
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_SCORING_SUCCESSOR_REPLAY",
        "bound_predecessor_gate_identity": predecessor["gate_identity"],
        "gate_identity": gate["gate_identity"],
        "official_capture_identity": capture_identity,
        "replay_command": (
            "python -B tools/build_week_zero_2026_official_final_scoring_successor.py "
            "--repo-root . --data-root <data-root> --execution-time-utc <utc> "
            "--acquisition-capture-identity <sha256>"
        ),
        "reconciliation_gate_identity": reconciliation_gate["gate_identity"],
        "residual_payload_identity": residual_payload["payload_identity"],
        "scoring_payload_identity": scoring_payload["payload_identity"],
        "state_transition_count": len(successor_transitions),
        "validation_command": (
            "python -B tools/validate_week_zero_2026_official_final_scoring_successor.py "
            "--repo-root . --data-root <data-root>"
        ),
    }

    return {
        "capture_manifest": capture_manifest,
        "capture_manifest_relative_path": external_manifest_relative,
        "crosswalk": crosswalk_payload,
        "gate": gate,
        "reconciliation_gate": reconciliation_gate,
        "replay": replay,
        "residual": residual_payload,
        "scoring": scoring_payload,
        "transition_ledger": transition_ledger,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--execution-time-utc", required=True)
    parser.add_argument("--acquisition-capture-identity", required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()

    bundle = build_successor(
        repo_root=repo_root,
        data_root=data_root,
        execution_time_utc=args.execution_time_utc,
        acquisition_capture_identity=args.acquisition_capture_identity,
    )

    write_json(
        data_root / bundle["capture_manifest_relative_path"], bundle["capture_manifest"]
    )
    write_json(repo_root / GATE_RELATIVE, bundle["gate"])
    write_json(repo_root / REPLAY_RELATIVE, bundle["replay"])
    write_json(repo_root / SCORING_RELATIVE, bundle["scoring"])
    write_json(repo_root / RESIDUAL_RELATIVE, bundle["residual"])
    write_json(repo_root / TRANSITIONS_RELATIVE, bundle["transition_ledger"])
    write_json(repo_root / CROSSWALK_RELATIVE, bundle["crosswalk"])
    write_json(repo_root / RECONCILIATION_RELATIVE, bundle["reconciliation_gate"])

    print(
        json.dumps(
            {
                "contest_state_counts": bundle["gate"]["contest_state_counts"],
                "forecast_state_counts": bundle["gate"]["forecast_state_counts"],
                "gate_identity": bundle["gate"]["gate_identity"],
                "official_capture_summary": bundle["gate"]["official_capture_summary"],
                "result": bundle["gate"]["result"],
                "scored_row_count": len(bundle["scoring"]["scored_rows"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
