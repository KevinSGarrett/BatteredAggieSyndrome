"""Week Zero 2026 live shadow execution and temporally eligible scoring.

The lane is observation only. It refreshes the official Week Zero surface at execution
time, reconciles it against the already frozen snapshots and forecasts, records the
official final status when one exists, and scores only rows whose Phase 4 temporal audit
reached a complete proof. It never creates, revises or backfills a forecast.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.shadow.week_zero_2026_live_execution.v1"
CONTRACT_ID = "BAT-665-WEEK-ZERO-2026-LIVE-SHADOW-EXECUTION-V1"
CLASSIFICATION = "WEEK_ZERO_2026_LIVE_SHADOW_EXECUTION_AND_TEMPORALLY_ELIGIBLE_SCORING"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-665"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK-ZERO-LIVE-SHADOW-EXECUTION-001"
PRODUCER = "tools/build_week_zero_2026_live_shadow_execution.py"

CONTRACT_RELATIVE = "configs/week_zero_2026_live_execution_contract.json"
GATE_RELATIVE = "artifacts/shadow/week_zero_2026_live_execution_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/week_zero_2026_live_execution_replay.json"
AUDIT_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_temporal_audit_gate.json"
FORECAST_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_forecast_gate.json"

PASS_RESULT = "PASS_WEEK_ZERO_2026_LIVE_SHADOW_EXECUTION"
AWAITING = "AWAITING_OFFICIAL_FINAL"
SCORED = "SCORED"
CANCELED = "CANCELED_OR_SUSPENDED"
MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
PROOF_COMPLETE = "TEMPORAL_PROOF_COMPLETE"

FINAL_OBSERVED = "OFFICIAL_FINAL_OBSERVED"
FINAL_ABSENT = "NO_OFFICIAL_FINAL_PUBLISHED_YET"
BEFORE_KICKOFF = "CONTEST_HAS_NOT_REACHED_ITS_KICKOFF_BOUND"

NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


class LiveExecutionViolation(RuntimeError):
    """Raised when the live execution input or artifact is not admissible."""


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
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(
        timezone.utc
    )


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise LiveExecutionViolation(f"the live execution contract is not present at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise LiveExecutionViolation("the live execution contract identifier does not match")
    return contract


def classify_official_status(text: str, contract: Mapping[str, Any]) -> str:
    """Map a refreshed official status string onto a contract-declared state."""

    lowered = (text or "").casefold()
    tokens = contract.get("final_status_tokens", {})
    for token in tokens.get("CANCELED_OR_SUSPENDED", []):
        if token in lowered:
            return CANCELED
    for token in tokens.get("FINAL", []):
        if token in lowered:
            return FINAL_OBSERVED
    return FINAL_ABSENT


def parse_official_finals(
    document: str, contract: Mapping[str, Any], *, game_date: str
) -> list[dict[str, Any]]:
    """Extract per-contest official status and score from a refreshed scoreboard page."""

    finals: list[dict[str, Any]] = []
    for block in re.split(r'(?=href="/contests/\d+/)', document):
        identifier = re.search(r'href="/contests/(\d+)/', block)
        if identifier is None:
            continue
        status_text = ""
        status_match = re.search(
            r">\s*(FINAL[^<]*|Final[^<]*|Canceled|Cancelled|Postponed|Suspended|No Contest)\s*<",
            block,
        )
        if status_match:
            status_text = status_match.group(1).strip()
        scores = [int(value) for value in re.findall(r'class="[^"]*score[^"]*"[^>]*>\s*(\d+)\s*<', block)]
        finals.append(
            {
                "away_points": scores[0] if len(scores) >= 2 else None,
                "game_date": game_date,
                "home_points": scores[1] if len(scores) >= 2 else None,
                "ncaa_contest_id": identifier.group(1),
                "official_status_state": classify_official_status(status_text, contract),
                "official_status_text": status_text,
            }
        )
    return finals


def load_capture_manifest(data_root: Path, capture_identity: str) -> dict[str, Any]:
    path = (
        Path(data_root)
        / "manifests"
        / "shadow"
        / "week_zero_2026_live_execution"
        / "sha256"
        / capture_identity
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    if not path.exists():
        raise LiveExecutionViolation(f"the live execution capture manifest is missing: {path}")
    return read_json(path)


def latest_capture_manifest(data_root: Path) -> dict[str, Any]:
    root = Path(data_root) / "manifests" / "shadow" / "week_zero_2026_live_execution" / "sha256"
    candidates = sorted(root.glob("*/week_zero_2026_live_execution_capture_manifest.json"))
    if not candidates:
        raise LiveExecutionViolation("no live execution capture manifest has been produced")
    manifests = [read_json(path) for path in candidates]
    manifests.sort(key=lambda item: str(item.get("issued_at_utc")))
    return manifests[-1]


def reconstruct_frozen_population(repo_root: Path, data_root: Path) -> dict[str, Any]:
    repo_root, data_root = Path(repo_root), Path(data_root)
    forecast_gate = read_json(repo_root / FORECAST_GATE_RELATIVE)
    audit_gate = read_json(repo_root / AUDIT_GATE_RELATIVE)
    manifest = read_json(data_root / forecast_gate["manifest"]["relative_path"])
    payloads = {
        payload["name"]: read_jsonl(data_root / payload["relative_path"])
        for payload in manifest.get("payloads", [])
    }
    return {
        "audit_gate": audit_gate,
        "forecast_gate": forecast_gate,
        "forecast_rows": payloads.get("prospective_2026_shadow_forecasts.jsonl", []),
        "snapshot_records": payloads.get("prospective_2026_shadow_snapshots.jsonl", []),
    }


def brier_score(probability: float, outcome: int) -> float:
    return (probability - outcome) ** 2


def log_loss(probability: float, outcome: int, clip: Sequence[float]) -> float:
    bounded = min(max(probability, float(clip[0])), float(clip[1]))
    return -(outcome * math.log(bounded) + (1 - outcome) * math.log(1 - bounded))


def calibration_bins(
    scored: Sequence[Mapping[str, Any]], edges: Sequence[float]
) -> list[dict[str, Any]]:
    bins = []
    for index in range(len(edges) - 1):
        low, high = float(edges[index]), float(edges[index + 1])
        last = index == len(edges) - 2
        members = [
            row
            for row in scored
            if low <= float(row["probability_home_win"]) < high
            or (last and float(row["probability_home_win"]) == high)
        ]
        bins.append(
            {
                "bin_lower": low,
                "bin_upper": high,
                "mean_observed_outcome": (
                    None
                    if not members
                    else sum(int(row["home_win"]) for row in members) / len(members)
                ),
                "mean_predicted_probability": (
                    None
                    if not members
                    else sum(float(row["probability_home_win"]) for row in members) / len(members)
                ),
                "row_count": len(members),
            }
        )
    return bins


def score_eligible_rows(
    rows: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Compute Brier, log loss, accuracy and calibration over eligible scored rows only."""

    clip = contract.get("log_loss_clip", [1e-15, 1 - 1e-15])
    if not rows:
        return {
            "accuracy": None,
            "brier_score": None,
            "calibration_bins": calibration_bins([], contract["calibration_bin_edges"]),
            "log_loss": None,
            "scored_row_count": 0,
        }
    briers = [brier_score(float(r["probability_home_win"]), int(r["home_win"])) for r in rows]
    losses = [log_loss(float(r["probability_home_win"]), int(r["home_win"]), clip) for r in rows]
    hits = [
        1 if (float(r["probability_home_win"]) >= 0.5) == bool(int(r["home_win"])) else 0
        for r in rows
    ]
    return {
        "accuracy": sum(hits) / len(rows),
        "brier_score": sum(briers) / len(briers),
        "calibration_bins": calibration_bins(rows, contract["calibration_bin_edges"]),
        "log_loss": sum(losses) / len(losses),
        "scored_row_count": len(rows),
    }


def execute_week_zero(
    population: Mapping[str, Any],
    capture_manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    execution_time: datetime,
    producer: str = PRODUCER,
) -> dict[str, Any]:
    week_zero_dates = frozenset(contract["week_zero_game_dates"])
    audit_gate = population["audit_gate"]
    forecast_gate = population["forecast_gate"]

    verdicts = {
        (row["ncaa_contest_id"], row["candidate_id"]): row
        for row in audit_gate.get("row_verdicts", [])
    }
    snapshots = {
        str(record["ncaa_contest_id"]): record for record in population["snapshot_records"]
    }
    refresh_rows = [
        row
        for row in capture_manifest.get("refreshed_contests", [])
        if str(row.get("game_date")) in week_zero_dates
    ]
    refreshed = {str(row["ncaa_contest_id"]): row for row in refresh_rows}
    substituted_dates = sorted(
        {
            str(row["game_date"])
            for row in refresh_rows
            if str(row.get("source_published_game_date")) != str(row.get("game_date"))
        }
    )
    finals = {
        str(row["ncaa_contest_id"]): row for row in capture_manifest.get("official_finals", [])
    }

    week_zero_contests = sorted(
        contest_id
        for contest_id, record in snapshots.items()
        if str(record.get("source_published_game_date")) in week_zero_dates
    ) or sorted(refreshed)

    contest_rows: list[dict[str, Any]] = []
    for contest_id in week_zero_contests:
        snapshot = snapshots.get(contest_id, {})
        detail = snapshot.get("snapshot") or {}
        kickoff = parse_utc(snapshot.get("kickoff_utc_conservative_lower_bound"))
        refresh = refreshed.get(contest_id, {})
        final = finals.get(contest_id, {})
        frozen_here = [
            row
            for row in population["forecast_rows"]
            if str(row.get("ncaa_contest_id")) == contest_id
            and row.get("forecast_state") == "FORECAST_FROZEN"
        ]

        kickoff_elapsed = kickoff is not None and execution_time >= kickoff
        if kickoff is None:
            timing_state = "KICKOFF_BOUND_UNKNOWN"
        elif kickoff_elapsed:
            timing_state = "KICKOFF_BOUND_HAS_ELAPSED"
        else:
            timing_state = BEFORE_KICKOFF

        status_state = final.get("official_status_state", FINAL_ABSENT)
        if kickoff_elapsed and not frozen_here:
            contest_state = MISSED_CUTOFF
        elif status_state == CANCELED:
            contest_state = CANCELED
        elif status_state == FINAL_OBSERVED:
            contest_state = FINAL_OBSERVED
        else:
            contest_state = AWAITING

        contest_rows.append(
            {
                "contest_state": contest_state,
                "frozen_forecast_row_count": len(frozen_here),
                "kickoff_bound_utc": snapshot.get("kickoff_utc_conservative_lower_bound"),
                "ncaa_contest_id": contest_id,
                "official_final_status_state": status_state,
                "official_final_status_text": final.get("official_status_text"),
                "official_status_capture_sha256": final.get("capture_sha256"),
                "official_status_retrieved_at_utc": final.get("retrieved_at_utc"),
                "refreshed_broadcast_text": refresh.get("source_published_broadcast_text"),
                "refreshed_clock_text": refresh.get("source_published_clock_text"),
                "refreshed_clock_matches_frozen_snapshot": (
                    None
                    if not refresh
                    else refresh.get("source_published_clock_text")
                    == snapshot.get("source_published_clock_text")
                ),
                "snapshot_frozen_at_utc": detail.get("snapshot_frozen_at_utc"),
                "timing_state": timing_state,
            }
        )

    eligible_rows: list[dict[str, Any]] = []
    forecast_rows: list[dict[str, Any]] = []
    for row in population["forecast_rows"]:
        contest_id = str(row.get("ncaa_contest_id"))
        if contest_id not in set(week_zero_contests):
            continue
        if row.get("forecast_state") != "FORECAST_FROZEN":
            continue
        verdict = verdicts.get((contest_id, row.get("candidate_id")), {})
        final = finals.get(contest_id, {})
        temporally_eligible = verdict.get("verdict") == PROOF_COMPLETE
        has_final = final.get("official_status_state") == FINAL_OBSERVED
        home_points, away_points = final.get("home_points"), final.get("away_points")
        resolvable = (
            has_final
            and isinstance(home_points, int)
            and isinstance(away_points, int)
            and home_points != away_points
        )
        if temporally_eligible and resolvable:
            state, reason = SCORED, "SCORED_AGAINST_AN_OFFICIAL_FINAL_WITH_A_COMPLETE_PROOF"
            eligible_rows.append(
                {
                    "candidate_id": row.get("candidate_id"),
                    "home_win": 1 if home_points > away_points else 0,
                    "ncaa_contest_id": contest_id,
                    "probability_home_win": row.get("probability_home_win"),
                }
            )
        elif not temporally_eligible:
            state = AWAITING
            reason = "THE_PHASE_FOUR_TEMPORAL_AUDIT_DID_NOT_REACH_A_COMPLETE_PROOF"
        elif final.get("official_status_state") == CANCELED:
            state, reason = CANCELED, "THE_OFFICIAL_SURFACE_REPORTS_A_CANCELED_OR_SUSPENDED_CONTEST"
        else:
            state, reason = AWAITING, "NO_ELIGIBLE_OFFICIAL_FINAL_EXISTS_AT_EXECUTION_TIME"
        forecast_rows.append(
            {
                "candidate_id": row.get("candidate_id"),
                "forecast_state": state,
                "ncaa_contest_id": contest_id,
                "probability_home_win": row.get("probability_home_win"),
                "state_reason": reason,
                "temporal_audit_verdict": verdict.get("verdict", "NO_PHASE_FOUR_VERDICT_EXISTS"),
            }
        )
    forecast_rows.sort(key=lambda item: (item["ncaa_contest_id"], item["candidate_id"] or ""))

    metrics = score_eligible_rows(eligible_rows, contract)
    contest_state_counts = Counter(row["contest_state"] for row in contest_rows)
    forecast_state_counts = Counter(row["forecast_state"] for row in forecast_rows)

    transitions = [
        {
            "entity_id": row["ncaa_contest_id"],
            "entity_kind": "CONTEST",
            "observed_at_utc": iso_utc(execution_time),
            "to_state": row["contest_state"],
        }
        for row in contest_rows
    ] + [
        {
            "entity_id": f"{row['ncaa_contest_id']}::{row['candidate_id']}",
            "entity_kind": "FORECAST",
            "observed_at_utc": iso_utc(execution_time),
            "to_state": row["forecast_state"],
        }
        for row in forecast_rows
    ]

    bundle = {
        "append_only_transitions": sorted(
            transitions, key=lambda item: (item["entity_kind"], item["entity_id"])
        ),
        "artifact_type": "WEEK_ZERO_2026_LIVE_SHADOW_EXECUTION_GATE",
        "authority": "OBSERVATION_ONLY_NO_FORECAST_IS_CREATED_REVISED_OR_BACKFILLED_HERE",
        "backfill_performed": False,
        "bound_predecessor_identities": {
            "forecast_gate_identity": forecast_gate.get("gate_identity"),
            "temporal_audit_gate_identity": audit_gate.get("gate_identity"),
        },
        "capture_identity": capture_manifest.get("capture_identity"),
        "classification": CLASSIFICATION,
        "contest_rows": contest_rows,
        "contest_state_counts": dict(sorted(contest_state_counts.items())),
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "decision_unit": LOCAL_ISSUE_ID,
        "execution_time_utc": iso_utc(execution_time),
        "forecast_rows": forecast_rows,
        "forecast_state_counts": dict(sorted(forecast_state_counts.items())),
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "local_issue_id": LOCAL_ISSUE_ID,
        "metrics": metrics,
        "negative_findings": {
            "no_candidate_was_tuned_selected_promoted_or_altered_from_week_zero": True,
            "no_forecast_was_emitted_for_a_contest_whose_kickoff_bound_had_elapsed": True,
            "the_refreshed_kickoff_clock_remains_a_published_local_clock_not_a_confirmed_instant": True,
        },
        "outcome_exclusion": contract.get("outcome_exclusion"),
        "parent_jira_key": PARENT_JIRA_KEY,
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "refreshed_capture_summary": {
            "captured_before_any_week_zero_kickoff": all(
                row["timing_state"] == BEFORE_KICKOFF for row in contest_rows
            ),
            "dates_the_source_substituted": substituted_dates,
            "distinct_refreshed_contests": len(refreshed),
            "official_final_count": sum(
                1 for row in contest_rows if row["official_final_status_state"] == FINAL_OBSERVED
            ),
            "refreshed_capture_rows": len(refresh_rows),
            "week_zero_contest_count": len(contest_rows),
        },
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract.get("scientific_nonclaims", {}),
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, data_root: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    if not gate_path.exists():
        raise LiveExecutionViolation("the live execution gate has not been materialized")
    committed = read_json(gate_path)

    if committed.get("schema_version") != SCHEMA_VERSION:
        raise LiveExecutionViolation("the committed gate schema version does not match")
    if committed.get("contract_sha256") != sha256_of(contract):
        raise LiveExecutionViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(committed) != committed.get("gate_identity"):
        raise LiveExecutionViolation("the committed gate identity does not cover its own content")
    if committed.get("backfill_performed"):
        raise LiveExecutionViolation("the committed gate admits a backfill")

    population = reconstruct_frozen_population(repo_root, data_root)
    capture_manifest = load_capture_manifest(data_root, committed["capture_identity"])
    rebuilt = execute_week_zero(
        population,
        capture_manifest,
        contract,
        execution_time=parse_utc(committed["execution_time_utc"]),
    )
    if rebuilt["gate_identity"] != committed.get("gate_identity"):
        raise LiveExecutionViolation(
            "the reconstructed live execution does not reproduce the committed gate identity"
        )

    assert_no_scored_row_without_a_complete_proof(committed)
    assert_no_forecast_issued_after_kickoff(committed, population)

    return {
        "contest_state_counts": committed.get("contest_state_counts"),
        "forecast_state_counts": committed.get("forecast_state_counts"),
        "gate_identity": committed["gate_identity"],
        "metrics": committed.get("metrics"),
        "result": committed.get("result"),
    }


def assert_no_scored_row_without_a_complete_proof(gate: Mapping[str, Any]) -> None:
    for row in gate.get("forecast_rows", []):
        if row.get("forecast_state") == SCORED and row.get("temporal_audit_verdict") != PROOF_COMPLETE:
            raise LiveExecutionViolation(
                "a row was scored without a complete Phase 4 temporal proof"
            )


def assert_no_forecast_issued_after_kickoff(
    gate: Mapping[str, Any], population: Mapping[str, Any]
) -> None:
    kickoffs = {
        str(record["ncaa_contest_id"]): parse_utc(
            record.get("kickoff_utc_conservative_lower_bound")
        )
        for record in population["snapshot_records"]
    }
    scored_contests = {
        row["ncaa_contest_id"] for row in gate.get("forecast_rows", []) if row.get("forecast_state") == SCORED
    }
    for row in population["forecast_rows"]:
        contest_id = str(row.get("ncaa_contest_id"))
        if contest_id not in scored_contests or row.get("forecast_state") != "FORECAST_FROZEN":
            continue
        issued, kickoff = parse_utc(row.get("created_at_utc")), kickoffs.get(contest_id)
        if issued is None or kickoff is None or issued >= kickoff:
            raise LiveExecutionViolation(
                "a scored contest carries a forecast that was not provably issued before kickoff"
            )
