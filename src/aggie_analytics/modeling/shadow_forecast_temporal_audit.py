"""Independent temporal-proof audit of the frozen 2026 prospective shadow forecasts.

The audit reconstructs the Cycle 20 prospective population read-only and proves, row by
row, that every frozen probability was issued strictly before its kickoff bound and no
later than its declared pregame cutoff. It never regenerates a forecast, never revises a
probability and never reads an outcome field.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.shadow.prospective_2026_temporal_audit.v1"
CONTRACT_ID = "BAT-664-PROSPECTIVE-2026-SHADOW-FORECAST-TEMPORAL-AUDIT-V1"
CLASSIFICATION = "INDEPENDENT_TEMPORAL_PROOF_AUDIT_OF_FROZEN_2026_SHADOW_FORECASTS"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-664"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-SHADOW-FORECAST-TEMPORAL-AUDIT-001"
PRODUCER = "tools/build_prospective_2026_shadow_temporal_audit.py"

CONTRACT_RELATIVE = "configs/prospective_2026_shadow_temporal_audit_contract.json"
GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_temporal_audit_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_temporal_audit_replay.json"
COHORT_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_cohort_gate.json"
FORECAST_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_forecast_gate.json"
CALENDAR_GATE_RELATIVE = "artifacts/shadow/week_zero_2026_calendar_and_t7d_gate.json"

PASS_RESULT = "PASS_PROSPECTIVE_2026_SHADOW_FORECAST_TEMPORAL_AUDIT"

PROOF_COMPLETE = "TEMPORAL_PROOF_COMPLETE"
MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
FAIL_CLOSED = "FAIL_CLOSED_INSUFFICIENT_TEMPORAL_PROOF"
VERDICTS = (PROOF_COMPLETE, MISSED_CUTOFF, FAIL_CLOSED)

FROZEN_STATE = "FORECAST_FROZEN"
ROUND_DIGITS = 8

REQUIRED_BINDINGS = (
    "official_contest_identity",
    "official_game_date",
    "kickoff_bound_utc",
    "snapshot_identity",
    "snapshot_frozen_at_utc",
    "forecast_issued_at_utc",
    "candidate_identity",
    "model_identity",
    "probability_identity",
)

# Keys excluded from the gate identity because they describe the run, not the finding.
NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


class TemporalAuditViolation(RuntimeError):
    """Raised when the audit input or the audit artifact is not admissible."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise TemporalAuditViolation(f"the temporal audit contract is not present at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise TemporalAuditViolation("the temporal audit contract identifier does not match")
    return contract


def reconstruct_population(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Read the predecessor gates and their off-repo payloads without mutating anything."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    cohort_gate = read_json(repo_root / COHORT_GATE_RELATIVE)
    forecast_gate = read_json(repo_root / FORECAST_GATE_RELATIVE)
    calendar_gate = read_json(repo_root / CALENDAR_GATE_RELATIVE)

    manifest_path = data_root / forecast_gate["manifest"]["relative_path"]
    if not manifest_path.exists():
        raise TemporalAuditViolation(
            f"the frozen forecast manifest is not present under the data root: {manifest_path}"
        )
    manifest = read_json(manifest_path)

    payloads: dict[str, list[dict[str, Any]]] = {}
    for payload in manifest.get("payloads", []):
        payload_path = data_root / payload["relative_path"]
        if not payload_path.exists():
            raise TemporalAuditViolation(
                f"a declared forecast payload is missing: {payload['relative_path']}"
            )
        payloads[payload["name"]] = read_jsonl(payload_path)

    snapshots = payloads.get("prospective_2026_shadow_snapshots.jsonl", [])
    forecasts = payloads.get("prospective_2026_shadow_forecasts.jsonl", [])
    if not snapshots or not forecasts:
        raise TemporalAuditViolation("the reconstructed population is missing a required payload")

    return {
        "cohort_gate": cohort_gate,
        "forecast_gate": forecast_gate,
        "calendar_gate": calendar_gate,
        "manifest": manifest,
        "snapshot_records": snapshots,
        "forecast_rows": forecasts,
    }


def corrected_label_index(calendar_gate: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(entry["game_date"]): str(entry["corrected_label"])
        for entry in calendar_gate.get("corrected_calendar", [])
    }


def snapshot_index(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for record in records:
        contest_id = record.get("ncaa_contest_id")
        if contest_id is None:
            continue
        index[str(contest_id)] = record
    return index


def probability_identity(row: Mapping[str, Any]) -> str | None:
    probability = row.get("probability_home_win")
    if not isinstance(probability, (int, float)) or isinstance(probability, bool):
        return None
    return sha256_of(
        {
            "candidate_id": row.get("candidate_id"),
            "code_identity": row.get("code_identity"),
            "feature_identity": row.get("feature_identity"),
            "model_identity": row.get("model_identity"),
            "ncaa_contest_id": row.get("ncaa_contest_id"),
            "probability_home_win": round(float(probability), ROUND_DIGITS),
            "snapshot_identity": row.get("snapshot_identity"),
        }
    )


def declared_cutoff(snapshot: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Return the declared pregame cutoff checkpoint identifier and its deadline."""

    detail = snapshot.get("snapshot") or {}
    cutoff_id = detail.get("cutoff_checkpoint_id")
    if not cutoff_id:
        return None, None
    for checkpoint in snapshot.get("checkpoints", []):
        if checkpoint.get("checkpoint_id") == cutoff_id:
            return str(cutoff_id), checkpoint.get("deadline_utc")
    return str(cutoff_id), None


def audit_frozen_row(
    row: Mapping[str, Any],
    *,
    snapshot: Mapping[str, Any] | None,
    contest_ids: frozenset[str],
    gate_identities: Mapping[str, Any],
    labels: Mapping[str, str],
) -> dict[str, Any]:
    """Bind every required proof field for one frozen row and return its verdict."""

    contest_id = row.get("ncaa_contest_id")
    game_date = row.get("source_published_game_date")
    detail = (snapshot or {}).get("snapshot") or {}

    kickoff = parse_utc(row.get("kickoff_utc_conservative_lower_bound"))
    issued = parse_utc(row.get("created_at_utc"))
    frozen_at = parse_utc(detail.get("snapshot_frozen_at_utc"))
    captured_at = parse_utc(detail.get("capture_retrieved_at_utc"))
    cutoff_id, cutoff_text = declared_cutoff(snapshot or {})
    cutoff = parse_utc(cutoff_text)
    identity = probability_identity(row)

    missing: list[str] = []
    if contest_id is None or str(contest_id) not in contest_ids:
        missing.append("official_contest_identity")
    if not game_date or (snapshot is not None and snapshot.get("source_published_game_date") != game_date):
        missing.append("official_game_date")
    if kickoff is None:
        missing.append("kickoff_bound_utc")
    if not row.get("snapshot_identity") or row.get("snapshot_identity") != detail.get(
        "snapshot_identity"
    ):
        missing.append("snapshot_identity")
    if frozen_at is None:
        missing.append("snapshot_frozen_at_utc")
    if issued is None:
        missing.append("forecast_issued_at_utc")
    if not row.get("candidate_id"):
        missing.append("candidate_identity")
    if (
        row.get("model_identity") != gate_identities.get("model_identity")
        or row.get("code_identity") != gate_identities.get("code_identity")
        or row.get("feature_identity") != gate_identities.get("feature_identity")
    ):
        missing.append("model_identity")
    if identity is None:
        missing.append("probability_identity")

    ordering: dict[str, bool | None] = {
        "capture_precedes_snapshot_freeze": (
            None if captured_at is None or frozen_at is None else captured_at <= frozen_at
        ),
        "snapshot_freeze_precedes_issuance": (
            None if frozen_at is None or issued is None else frozen_at <= issued
        ),
        "issuance_within_declared_cutoff": (
            None if cutoff is None or issued is None else issued <= cutoff
        ),
        "issuance_strictly_precedes_kickoff": (
            None if kickoff is None or issued is None else issued < kickoff
        ),
    }

    if missing or any(value is None for value in ordering.values()):
        verdict = FAIL_CLOSED
        reason = "AT_LEAST_ONE_REQUIRED_TEMPORAL_BINDING_IS_ABSENT_OR_INCONSISTENT"
    elif not ordering["issuance_strictly_precedes_kickoff"]:
        verdict = MISSED_CUTOFF
        reason = "THE_PROBABILITY_WAS_ISSUED_AT_OR_AFTER_THE_KICKOFF_BOUND"
    elif not ordering["issuance_within_declared_cutoff"]:
        verdict = MISSED_CUTOFF
        reason = "THE_PROBABILITY_WAS_ISSUED_AFTER_THE_DECLARED_PREGAME_CUTOFF_DEADLINE"
    elif not ordering["capture_precedes_snapshot_freeze"] or not ordering[
        "snapshot_freeze_precedes_issuance"
    ]:
        verdict = FAIL_CLOSED
        reason = "THE_CAPTURE_SNAPSHOT_AND_ISSUANCE_INSTANTS_ARE_NOT_IN_CHRONOLOGICAL_ORDER"
    else:
        verdict = PROOF_COMPLETE
        reason = "EVERY_REQUIRED_BINDING_IS_PRESENT_AND_ISSUANCE_STRICTLY_PRECEDES_KICKOFF"

    margin_seconds = (
        None if kickoff is None or issued is None else int((kickoff - issued).total_seconds())
    )

    return {
        "candidate_id": row.get("candidate_id"),
        "corrected_week_label": labels.get(str(game_date), "LABEL_NOT_PUBLISHED_BY_THE_CALENDAR_GATE"),
        "declared_cutoff_checkpoint_id": cutoff_id,
        "declared_cutoff_deadline_utc": cutoff_text,
        "forecast_issued_at_utc": row.get("created_at_utc"),
        "kickoff_bound_utc": row.get("kickoff_utc_conservative_lower_bound"),
        "lead_seconds_before_kickoff_bound": margin_seconds,
        "missing_bindings": sorted(missing),
        "model_identity": row.get("model_identity"),
        "ncaa_contest_id": None if contest_id is None else str(contest_id),
        "official_game_date": game_date,
        "ordering_checks": ordering,
        "probability_identity": identity,
        "snapshot_frozen_at_utc": detail.get("snapshot_frozen_at_utc"),
        "snapshot_identity": row.get("snapshot_identity"),
        "verdict": verdict,
        "verdict_reason": reason,
    }


def explain_non_frozen_rows(
    rows: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Group every non-frozen candidate row by its declared abstention state."""

    explanations = contract.get("non_frozen_row_explanations", {})
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        state = str(row.get("forecast_state"))
        if state == FROZEN_STATE:
            continue
        reason = str(row.get("abstention_reason") or "NO_ABSTENTION_REASON_RECORDED")
        key = (state, reason)
        entry = grouped.setdefault(
            key,
            {
                "abstention_reason": reason,
                "contract_explanation": explanations.get(
                    state, "NO_CONTRACT_EXPLANATION_IS_DECLARED_FOR_THIS_STATE"
                ),
                "distinct_contests": set(),
                "forecast_state": state,
                "row_count": 0,
                "rows_carrying_a_probability": 0,
            },
        )
        entry["row_count"] += 1
        entry["distinct_contests"].add(str(row.get("ncaa_contest_id")))
        if row.get("probability_home_win") is not None:
            entry["rows_carrying_a_probability"] += 1

    result = []
    for entry in grouped.values():
        entry["distinct_contests"] = len(entry["distinct_contests"])
        result.append(entry)
    return sorted(result, key=lambda item: (item["forecast_state"], item["abstention_reason"]))


def relabel_contests(
    snapshots: Sequence[Mapping[str, Any]],
    forecast_rows: Sequence[Mapping[str, Any]],
    labels: Mapping[str, str],
    cohort_gate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Apply the corrected taxonomy per game date and prove membership did not move."""

    window = cohort_gate.get("schedule_window", {})
    predecessor_week_zero = frozenset(window.get("week_zero_dates", []))
    predecessor_week_one = frozenset(window.get("week_one_dates", []))

    observed: dict[str, set[str]] = {}
    for row in forecast_rows:
        date = str(row.get("source_published_game_date"))
        observed.setdefault(date, set()).add(str(row.get("ncaa_contest_id")))
    for record in snapshots:
        date = str(record.get("source_published_game_date"))
        observed.setdefault(date, set()).add(str(record.get("ncaa_contest_id")))

    corrections = []
    for date in sorted(observed):
        if date in predecessor_week_zero:
            predecessor_label = "WEEK_ZERO"
        elif date in predecessor_week_one:
            predecessor_label = "WEEK_ONE"
        else:
            predecessor_label = "NOT_LABELED_BY_THE_PREDECESSOR_WINDOW"
        corrected = labels.get(date, "LABEL_NOT_PUBLISHED_BY_THE_CALENDAR_GATE")
        corrections.append(
            {
                "contest_count": len(observed[date]),
                "corrected_label": corrected,
                "game_date": date,
                "label_changed": corrected != predecessor_label,
                "membership_changed": False,
                "predecessor_label": predecessor_label,
            }
        )
    return corrections


def build_audit(
    population: Mapping[str, Any], contract: Mapping[str, Any], *, producer: str = PRODUCER
) -> dict[str, Any]:
    cohort_gate = population["cohort_gate"]
    forecast_gate = population["forecast_gate"]
    calendar_gate = population["calendar_gate"]
    snapshots = population["snapshot_records"]
    forecast_rows = population["forecast_rows"]

    labels = corrected_label_index(calendar_gate)
    by_contest = snapshot_index(snapshots)
    contest_ids = frozenset(str(record.get("ncaa_contest_id")) for record in snapshots)
    identities = forecast_gate.get("identities", {})

    audited = [
        audit_frozen_row(
            row,
            snapshot=by_contest.get(str(row.get("ncaa_contest_id"))),
            contest_ids=contest_ids,
            gate_identities=identities,
            labels=labels,
        )
        for row in forecast_rows
        if row.get("forecast_state") == FROZEN_STATE
    ]
    audited.sort(key=lambda item: (item["ncaa_contest_id"] or "", item["candidate_id"] or ""))

    verdict_counts = Counter(item["verdict"] for item in audited)
    frozen_snapshot_count = sum(
        1 for record in snapshots if record.get("forecast_state") == "SNAPSHOT_FROZEN"
    )
    unsupported_contests = sum(
        1 for record in snapshots if record.get("forecast_state") == "UNSUPPORTED_ENTITY"
    )

    reconstructed = {
        "contests_observed": len(snapshots),
        "forecast_rows_emitted": len(forecast_rows),
        "forecast_rows_frozen": len(audited),
        "snapshots_frozen": frozen_snapshot_count,
        "unsupported_contests": unsupported_contests,
    }
    expected = contract.get("expected_population", {})
    reconstruction_agreement = {
        key: reconstructed.get(key) == expected.get(key)
        for key in sorted(set(reconstructed) & set(expected))
    }

    bundle = {
        "artifact_type": "PROSPECTIVE_2026_SHADOW_FORECAST_TEMPORAL_AUDIT_GATE",
        "audited_predecessor_identities": {
            "calendar_gate_identity": calendar_gate.get("gate_identity"),
            "cohort_gate_identity": cohort_gate.get("gate_identity"),
            "forecast_gate_identity": forecast_gate.get("gate_identity"),
        },
        "authority": "THIS_AUDIT_PROVES_TIMING_ONLY_AND_CONFERS_NO_PREDICTIVE_AUTHORITY",
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "decision_unit": LOCAL_ISSUE_ID,
        "forecast_identities": identities,
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "local_issue_id": LOCAL_ISSUE_ID,
        "negative_findings": {
            "a_conservative_kickoff_bound_is_not_a_confirmed_official_kickoff_instant": True,
            "no_official_final_is_read_or_scored_by_this_audit": True,
            "the_audit_cannot_prove_a_probability_was_well_calibrated": True,
            "the_audit_reads_no_outcome_field": True,
        },
        "non_frozen_row_explanations": explain_non_frozen_rows(forecast_rows, contract),
        "outcome_exclusion": contract.get("outcome_exclusion"),
        "parent_jira_key": PARENT_JIRA_KEY,
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "reconstructed_population": reconstructed,
        "reconstruction_agrees_with_the_contract": reconstruction_agreement,
        "required_bindings": list(REQUIRED_BINDINGS),
        "result": PASS_RESULT,
        "row_verdicts": audited,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract.get("scientific_nonclaims", {}),
        "taxonomy_corrections": relabel_contests(snapshots, forecast_rows, labels, cohort_gate),
        "verdict_counts": {verdict: verdict_counts.get(verdict, 0) for verdict in VERDICTS},
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Independently re-derive the audit and compare it against the committed gate."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    if not gate_path.exists():
        raise TemporalAuditViolation("the temporal audit gate has not been materialized")
    committed = read_json(gate_path)

    if committed.get("schema_version") != SCHEMA_VERSION:
        raise TemporalAuditViolation("the committed gate schema version does not match")
    if committed.get("contract_sha256") != sha256_of(contract):
        raise TemporalAuditViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(committed) != committed.get("gate_identity"):
        raise TemporalAuditViolation("the committed gate identity does not cover its own content")

    rebuilt = build_audit(reconstruct_population(repo_root, data_root), contract)
    if rebuilt["gate_identity"] != committed.get("gate_identity"):
        raise TemporalAuditViolation(
            "the reconstructed audit does not reproduce the committed gate identity"
        )

    counts = committed.get("verdict_counts", {})
    for verdict in VERDICTS:
        if verdict not in counts:
            raise TemporalAuditViolation(f"the committed gate omits the {verdict} count")
    if sum(counts.values()) != len(committed.get("row_verdicts", [])):
        raise TemporalAuditViolation("the verdict counts do not sum to the audited row population")

    for row in committed.get("row_verdicts", []):
        if row.get("verdict") not in VERDICTS:
            raise TemporalAuditViolation("an audited row carries an undeclared verdict")
        if row.get("verdict") == PROOF_COMPLETE and row.get("missing_bindings"):
            raise TemporalAuditViolation(
                "a row was declared temporally complete while missing a required binding"
            )

    if not all(committed.get("reconstruction_agrees_with_the_contract", {}).values()):
        raise TemporalAuditViolation(
            "the reconstructed population disagrees with the contract expectation"
        )
    for correction in committed.get("taxonomy_corrections", []):
        if correction.get("membership_changed"):
            raise TemporalAuditViolation("a taxonomy correction silently changed contest membership")

    return {
        "gate_identity": committed["gate_identity"],
        "result": committed.get("result"),
        "rows_audited": len(committed.get("row_verdicts", [])),
        "verdict_counts": counts,
    }
