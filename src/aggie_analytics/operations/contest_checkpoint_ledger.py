"""Cycle 27 contest/checkpoint ledger: join valid receipts, never backfill.

Completed timely receipts remain completed after the clock passes. An empty
contest universe without independent empty-universe authority is a failure.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

AM_CONTEST_ID = "6607349"
WEEK1_CONTEST_COUNT = 91
T24H = "T24H"
T90M = "T90M"
CAPTURE_WINDOW = timedelta(minutes=60)
WAKE_LEAD = timedelta(minutes=45)
SATURDAY_T90_START = datetime(2026, 9, 5, 14, 30, tzinfo=timezone.utc)
SATURDAY_REMAINING_T24_END = datetime(2026, 9, 5, 8, 0, tzinfo=timezone.utc)
SUNDAY_KICKOFF_DATE = "2026-09-06"
MONDAY_KICKOFF_DATE = "2026-09-07"

NOT_OPEN = "NOT_OPEN"
CAPTURE_IN_PROGRESS = "CAPTURE_IN_PROGRESS"
EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
FORECAST_FROZEN = "FORECAST_FROZEN"
ABSTAINED_AT_CHECKPOINT = "ABSTAINED_AT_CHECKPOINT"
MISSED_CUTOFF_NO_BACKFILL = "MISSED_CUTOFF_NO_BACKFILL"
CONFLICT = "CONFLICT"
POSTPONED = "POSTPONED"
CANCELED = "CANCELED"

CHECKPOINT_STATES = frozenset(
    {
        NOT_OPEN,
        CAPTURE_IN_PROGRESS,
        EVIDENCE_CAPTURED,
        FORECAST_FROZEN,
        ABSTAINED_AT_CHECKPOINT,
        MISSED_CUTOFF_NO_BACKFILL,
        CONFLICT,
        POSTPONED,
        CANCELED,
    }
)


class EmptyUniverseWithoutAuthority(ValueError):
    """Zero work is valid only with explicit independently established authority."""


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_contest_universe(
    contests: Sequence[Mapping[str, Any]] | None,
    *,
    empty_universe_authority: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Fail closed when the caller supplies an empty universe without authority."""
    rows = list(contests or [])
    if rows:
        return [dict(row) for row in rows]
    authority = empty_universe_authority or {}
    if authority.get("empty_universe_authorized") is not True:
        raise EmptyUniverseWithoutAuthority("EMPTY_UNIVERSE_WITHOUT_AUTHORITY")
    if not str(authority.get("authority_identity") or "").strip():
        raise EmptyUniverseWithoutAuthority("EMPTY_UNIVERSE_WITHOUT_AUTHORITY")
    return []


def _receipt_issued_at(receipt: Mapping[str, Any]) -> datetime:
    return parse_utc(
        str(receipt.get("issued_at_utc") or receipt.get("freeze_at_utc") or "")
    )


def _receipt_earliest_cutoff(receipt: Mapping[str, Any]) -> datetime:
    return parse_utc(
        str(
            receipt.get("earliest_cutoff_utc")
            or receipt.get("earliest_eligible_cutoff_utc")
            or ""
        )
    )


def load_valid_receipts(receipt_paths: Sequence[Path]) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for path in receipt_paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        label = str(payload.get("checkpoint_label") or "")
        kind = T90M if ("T-90" in label or "T90M" in label or "T90" in label) else T24H
        issued = _receipt_issued_at(payload)
        earliest = _receipt_earliest_cutoff(payload)
        if issued > earliest:
            continue
        name = Path(path).name.upper()
        if "SATURDAY" in name:
            coverage = "REMAINING_WINDOW"
        elif "SEP3" in name and kind == T90M:
            coverage = "SAME_UTC_DAY_REMAINING_WINDOW"
        else:
            coverage = "EXACT_EARLIEST_CLUSTER"
        loaded.append(
            {
                "path": str(path).replace("\\", "/"),
                "artifact_type": payload.get("artifact_type"),
                "kind": kind,
                "issued_at_utc": format_utc(issued),
                "earliest_cutoff_utc": format_utc(earliest),
                "coverage": coverage,
                "forecast_frozen": False,
                "label_authority": payload.get("label_authority"),
                "raw_collection_only": True,
            }
        )
    return loaded


def receipt_covers_contest(
    receipt: Mapping[str, Any],
    contest: Mapping[str, Any],
    kind: str,
) -> bool:
    if receipt.get("kind") != kind:
        return False
    cutoff_key = "t24h_cutoff_utc" if kind == T24H else "t90m_cutoff_utc"
    cutoff = parse_utc(str(contest[cutoff_key]))
    issued = parse_utc(str(receipt["issued_at_utc"]))
    earliest = parse_utc(str(receipt["earliest_cutoff_utc"]))
    if issued > cutoff:
        return False
    window_open = cutoff - CAPTURE_WINDOW
    if issued < window_open:
        return False
    contest_id = str(contest["ncaa_contest_id"])
    coverage = str(receipt.get("coverage") or "")
    if coverage == "EXACT_EARLIEST_CLUSTER":
        return cutoff == earliest
    if kind == T24H and coverage == "REMAINING_WINDOW":
        if contest_id == AM_CONTEST_ID:
            return False
        return earliest <= cutoff <= SATURDAY_REMAINING_T24_END
    if coverage == "SAME_UTC_DAY_REMAINING_WINDOW":
        return cutoff >= earliest and cutoff.date() == earliest.date()
    return False


def live_owner_for(
    contest_id: str,
    kind: str,
    live_owners: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    for owner in live_owners:
        if owner.get("kind") != kind:
            continue
        if contest_id in set(owner.get("contest_ids") or []):
            return dict(owner)
    return None


def contest_status_state(contest: Mapping[str, Any]) -> str | None:
    status = str(contest.get("official_status") or contest.get("status") or "")
    token = status.strip().upper()
    if token in {"POSTPONED", "PPD"}:
        return POSTPONED
    if token in {"CANCELED", "CANCELLED", "CANCELLED_CONTEST", "NO_CONTEST"}:
        return CANCELED
    return None


def evaluate_checkpoint_state(
    *,
    now: datetime,
    contest: Mapping[str, Any],
    kind: str,
    receipts: Sequence[Mapping[str, Any]],
    live_owners: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Clock-aware state that never recomputes a timely receipt as missed."""
    cutoff_key = "t24h_cutoff_utc" if kind == T24H else "t90m_cutoff_utc"
    cutoff = parse_utc(str(contest[cutoff_key]))
    window_open = cutoff - CAPTURE_WINDOW
    covering = [
        receipt
        for receipt in receipts
        if receipt_covers_contest(receipt, contest, kind)
    ]
    owner = live_owner_for(str(contest["ncaa_contest_id"]), kind, live_owners)
    postponed = contest_status_state(contest)
    if postponed:
        state = postponed
    elif covering and any(item.get("forecast_frozen") for item in covering):
        state = FORECAST_FROZEN
    elif covering:
        state = EVIDENCE_CAPTURED
    elif owner is not None and now < cutoff:
        state = CAPTURE_IN_PROGRESS
    elif now >= cutoff:
        if contest.get("abstention_reasons"):
            state = ABSTAINED_AT_CHECKPOINT
        else:
            state = MISSED_CUTOFF_NO_BACKFILL
    elif now < window_open:
        state = NOT_OPEN
    else:
        state = NOT_OPEN
    if covering and owner is not None and kind == T90M:
        # Dedicated live owner plus a prior different-window receipt is not
        # a conflict when the covering receipt is for this same kind/window.
        pass
    return {
        "state": state,
        "cutoff_utc": format_utc(cutoff),
        "capture_window_open_utc": format_utc(window_open),
        "joined_receipts": [item["artifact_type"] for item in covering],
        "live_owner": owner.get("name") if owner else None,
        "forecast_frozen": False,
        "completed_valid_receipt_retained_after_cutoff": bool(covering)
        and now >= cutoff,
    }


def build_cutoff_clusters(
    contests: Sequence[Mapping[str, Any]], kind: str
) -> list[dict[str, Any]]:
    cutoff_key = "t24h_cutoff_utc" if kind == T24H else "t90m_cutoff_utc"
    grouped: dict[str, list[str]] = defaultdict(list)
    for contest in contests:
        grouped[str(contest[cutoff_key])].append(str(contest["ncaa_contest_id"]))
    clusters = []
    for cutoff, ids in sorted(grouped.items()):
        kickoffs = sorted(
            {
                str(row["kickoff_bound_utc"])
                for row in contests
                if str(row[cutoff_key]) == cutoff
            }
        )
        clusters.append(
            {
                "cutoff_utc": cutoff,
                "kind": kind,
                "contest_count": len(ids),
                "contest_ids": sorted(ids),
                "kickoff_bound_utc": kickoffs,
            }
        )
    return clusters


def sunday_monday_ownership_plan(
    contests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    sunday = []
    monday = []
    for contest in contests:
        kickoff = str(contest["kickoff_bound_utc"])
        day = kickoff[:10]
        row = {
            "ncaa_contest_id": contest["ncaa_contest_id"],
            "kickoff_bound_utc": contest["kickoff_bound_utc"],
            "t24h_cutoff_utc": contest["t24h_cutoff_utc"],
            "t90m_cutoff_utc": contest["t90m_cutoff_utc"],
            "t24h_wake_utc": format_utc(
                parse_utc(str(contest["t24h_cutoff_utc"])) - WAKE_LEAD
            ),
            "t90m_wake_utc": format_utc(
                parse_utc(str(contest["t90m_cutoff_utc"])) - WAKE_LEAD
            ),
            "do_not_use_am_sleeper_pids": True,
            "planned_owner": "CYCLE27_CURSOR_AGENT",
        }
        if day == SUNDAY_KICKOFF_DATE and kickoff >= "2026-09-06T12:00:00Z":
            sunday.append(row)
        elif day == MONDAY_KICKOFF_DATE:
            monday.append(row)
    return {
        "git_publication_coordinator": "CYCLE27_CURSOR_AGENT",
        "note": (
            "Sunday 23:30Z and Monday 23:30Z contests remain NOT_OPEN at Friday "
            "T90. Arm dedicated owners before those windows. Do not reuse A&M "
            "PIDs 28372/24528/27724/32428."
        ),
        "sunday": sunday,
        "monday": monday,
    }


def cycle27_live_owners() -> list[dict[str, Any]]:
    return [
        {
            "name": "FRIDAY_T90M",
            "kind": T90M,
            "contest_ids": ["6594366"],
            "primary_pid": 40708,
            "failover_pid": 41416,
            "wake_utc": "2026-09-04T20:15:00Z",
            "cutoff_utc": "2026-09-04T21:00:00Z",
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
        },
        {
            "name": "FRIDAY_T90M_2130Z",
            "kind": T90M,
            "contest_ids": ["6598559", "6619544"],
            "primary_pid": 42852,
            "wake_utc": "2026-09-04T20:45:00Z",
            "cutoff_utc": "2026-09-04T21:30:00Z",
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
        },
        {
            "name": "FRIDAY_T90M_2230Z",
            "kind": T90M,
            "contest_ids": ["6592887", "6601163", "6611346"],
            "primary_pid": 10732,
            "wake_utc": "2026-09-04T21:45:00Z",
            "cutoff_utc": "2026-09-04T22:30:00Z",
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
        },
        {
            "name": "FRIDAY_T90M_2330Z",
            "kind": T90M,
            "contest_ids": ["6602792", "6620138"],
            "primary_pid": 42444,
            "wake_utc": "2026-09-04T22:45:00Z",
            "cutoff_utc": "2026-09-04T23:30:00Z",
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
        },
        {
            "name": "SATURDAY_T90M_1430Z",
            "kind": T90M,
            "contest_ids": [
                "6590890",
                "6593811",
                "6594325",
                "6601384",
                "6611692",
                "6611873",
                "6613128",
                "6617023",
                "6620636",
                "6620944",
            ],
            "primary_pid": 14180,
            "wake_utc": "2026-09-05T13:45:00Z",
            "cutoff_utc": "2026-09-05T14:30:00Z",
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
        },
        {
            "name": "AM_T24H",
            "kind": T24H,
            "contest_ids": [AM_CONTEST_ID],
            "primary_pid": 28372,
            "failover_pid": 27724,
            "wake_utc": "2026-09-04T22:15:00Z",
            "cutoff_utc": "2026-09-04T23:00:00Z",
            "do_not_kill": True,
        },
        {
            "name": "AM_T90M",
            "kind": T90M,
            "contest_ids": [AM_CONTEST_ID],
            "primary_pid": 24528,
            "failover_pid": 32428,
            "wake_utc": "2026-09-05T20:45:00Z",
            "cutoff_utc": "2026-09-05T21:30:00Z",
            "do_not_kill": True,
        },
    ]


def saturday_t90_clusters_without_am(
    contests: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    clusters = []
    for cluster in build_cutoff_clusters(contests, T90M):
        cutoff = parse_utc(cluster["cutoff_utc"])
        if cutoff < SATURDAY_T90_START:
            continue
        ids = list(cluster["contest_ids"])
        am_owned = AM_CONTEST_ID in ids
        national_ids = [item for item in ids if item != AM_CONTEST_ID]
        planned = {
            **cluster,
            "wake_utc": format_utc(cutoff - WAKE_LEAD),
            "am_contest_excluded_from_national_owner": am_owned,
            "national_contest_ids": national_ids,
            "national_contest_count": len(national_ids),
            "planned_national_owner": "CYCLE27_SATURDAY_T90M_NATIONAL",
            "am_owner_if_present": "AM_T90M" if am_owned else None,
            "do_not_duplicate_am_pids": True,
        }
        clusters.append(planned)
    return clusters


def build_cycle27_ledger(
    *,
    c26_ledger: Mapping[str, Any],
    receipts: Sequence[Mapping[str, Any]],
    now: datetime,
    live_owners: Sequence[Mapping[str, Any]] | None = None,
    empty_universe_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contests = require_contest_universe(
        c26_ledger.get("contests"),
        empty_universe_authority=empty_universe_authority,
    )
    if len(contests) != WEEK1_CONTEST_COUNT and empty_universe_authority is None:
        raise ValueError(
            f"expected {WEEK1_CONTEST_COUNT} contests, got {len(contests)}"
        )
    owners = list(live_owners if live_owners is not None else cycle27_live_owners())
    rows = []
    for contest in contests:
        t24 = evaluate_checkpoint_state(
            now=now,
            contest=contest,
            kind=T24H,
            receipts=receipts,
            live_owners=owners,
        )
        t90 = evaluate_checkpoint_state(
            now=now,
            contest=contest,
            kind=T90M,
            receipts=receipts,
            live_owners=owners,
        )
        rows.append(
            {
                "ncaa_contest_id": contest["ncaa_contest_id"],
                "kickoff_bound_utc": contest["kickoff_bound_utc"],
                "t24h_cutoff_utc": contest["t24h_cutoff_utc"],
                "t90m_cutoff_utc": contest["t90m_cutoff_utc"],
                "t24h_state": t24["state"],
                "t90m_state": t90["state"],
                "t24h": t24,
                "t90m": t90,
                "abstention_reasons": list(contest.get("abstention_reasons") or []),
                "predecessor_c26_t24h_state": contest.get("t24h_state"),
                "predecessor_c26_t90m_state": contest.get("t90m_state"),
            }
        )
    saturday_ids = [
        row["ncaa_contest_id"]
        for row in rows
        if "CYCLE26_SEP5_SATURDAY_T24H_FREEZE_RECEIPT" in row["t24h"]["joined_receipts"]
    ]
    return {
        "artifact_type": "CYCLE27_CONTEST_CHECKPOINT_LEDGER",
        "issued_at_utc": format_utc(now),
        "as_of_utc": format_utc(now),
        "predecessor_c26_ledger_issued_at_utc": c26_ledger.get("issued_at_utc"),
        "dataset_identity": c26_ledger.get("dataset_identity"),
        "contest_count": len(rows),
        "clock_uncertainty": "Host OS clock; local receipt is not cryptographic proof",
        "completed_valid_receipts_retained_after_cutoff": True,
        "do_not_recompute_saturday_as_missed": True,
        "raw_collection_is_not_forecast_frozen": True,
        "joined_receipts": [item["artifact_type"] for item in receipts],
        "saturday_t24h_completed_contest_ids": saturday_ids,
        "saturday_t24h_completed_count": len(saturday_ids),
        "t24h_state_counts": _count_states(rows, "t24h_state"),
        "t90m_state_counts": _count_states(rows, "t90m_state"),
        "cutoff_clusters": {
            "t24h": build_cutoff_clusters(contests, T24H),
            "t90m": build_cutoff_clusters(contests, T90M),
        },
        "sunday_monday_ownership_plan": sunday_monday_ownership_plan(contests),
        "live_owners": owners,
        "heartbeat_pid": 22176,
        "git_publication_coordinator": "CYCLE27_CURSOR_AGENT",
        "do_not_kill_pids": [
            28372,
            24528,
            27724,
            32428,
            22176,
            40708,
            41416,
            42852,
            10732,
            42444,
            14180,
        ],
        "contests": rows,
        "note": (
            "Ledger joins Sep3 T90, Sep4 window T24, and Saturday T24 receipts. "
            "EVIDENCE_CAPTURED is not FORECAST_FROZEN. Late operations cannot "
            "backfill a missed checkpoint."
        ),
    }


def _count_states(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row[key])] += 1
    return dict(sorted(counts.items()))


def default_receipt_paths(ops26: Path, artifacts26: Path) -> list[Path]:
    names = (
        "CYCLE26_SEP3_T90M_FREEZE_RECEIPT.json",
        "CYCLE26_SEP4_WINDOW_T24H_FREEZE_RECEIPT.json",
        "CYCLE26_SEP5_SATURDAY_T24H_FREEZE_RECEIPT.json",
    )
    paths = []
    for name in names:
        ops_path = ops26 / name
        art_path = artifacts26 / name
        if ops_path.is_file():
            paths.append(ops_path)
        elif art_path.is_file():
            paths.append(art_path)
        else:
            raise FileNotFoundError(name)
    return paths


def load_c26_ledger(ops26: Path, artifacts26: Path) -> dict[str, Any]:
    for path in (
        ops26 / "CYCLE26_CHECKPOINT_ELIGIBILITY_LEDGER.json",
        artifacts26 / "CYCLE26_CHECKPOINT_ELIGIBILITY_LEDGER.json",
    ):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("CYCLE26_CHECKPOINT_ELIGIBILITY_LEDGER.json")


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_lease_and_restart_plan(
    *,
    ledger: Mapping[str, Any],
    now: datetime,
) -> dict[str, Any]:
    contests = ledger["contests"]
    return {
        "artifact_type": "CYCLE27_LEASE_AND_RESTART_PLAN",
        "issued_at_utc": format_utc(now),
        "as_of_utc": format_utc(now),
        "this_plan_does_not_kill_live_owners": True,
        "do_not_kill_pids": [
            28372,
            24528,
            27724,
            32428,
            22176,
            40708,
            41416,
            42852,
            10732,
            42444,
            14180,
        ],
        "atomic_lease_module": {
            "ops_runtime": "C:/BatteredAggieSyndrome.data/ops/cycle27/checkpoint_lease.py",
            "versioned_source": "src/aggie_analytics/operations/checkpoint_lease.py",
            "injectable_lease_root": True,
            "stale_owner_requires_verified_recovery": True,
            "age_delete_forbidden": True,
            "start_is_not_completion": True,
        },
        "failover_policy": (
            "src/aggie_analytics/operations/checkpoint_failover_policy.py"
        ),
        "current_owners": {
            "friday_t90m": {
                "checkpoint": "FRI_T90M_20260904T2100Z",
                "contest_id": "6594366",
                "primary_pid": 40708,
                "failover_pid": 41416,
                "wake_utc": "2026-09-04T20:15:00Z",
                "cutoff_utc": "2026-09-04T21:00:00Z",
                "no_git_commit_from_sleeper": True,
            },
            "am_t24h": {
                "checkpoint": "AM_T24H",
                "contest_id": AM_CONTEST_ID,
                "primary_pid": 28372,
                "failover_pid": 27724,
                "wake_utc": "2026-09-04T22:15:00Z",
                "cutoff_utc": "2026-09-04T23:00:00Z",
            },
            "am_t90m": {
                "checkpoint": "AM_T90M",
                "contest_id": AM_CONTEST_ID,
                "primary_pid": 24528,
                "failover_pid": 32428,
                "wake_utc": "2026-09-05T20:45:00Z",
                "cutoff_utc": "2026-09-05T21:30:00Z",
            },
            "overnight_heartbeat_pid": 22176,
            "git_publication_coordinator": "CYCLE27_CURSOR_AGENT",
            "friday_t90m_2130z": {
                "checkpoint": "FRI_T90M_20260904T2130Z",
                "contest_ids": ["6598559", "6619544"],
                "primary_pid": 42852,
                "wake_utc": "2026-09-04T20:45:00Z",
                "cutoff_utc": "2026-09-04T21:30:00Z",
                "no_git_commit_from_sleeper": True,
            },
            "friday_t90m_2230z": {
                "checkpoint": "FRI_T90M_20260904T2230Z",
                "contest_ids": ["6592887", "6601163", "6611346"],
                "primary_pid": 10732,
                "wake_utc": "2026-09-04T21:45:00Z",
                "cutoff_utc": "2026-09-04T22:30:00Z",
                "no_git_commit_from_sleeper": True,
            },
            "friday_t90m_2330z": {
                "checkpoint": "FRI_T90M_20260904T2330Z",
                "contest_ids": ["6602792", "6620138"],
                "primary_pid": 42444,
                "wake_utc": "2026-09-04T22:45:00Z",
                "cutoff_utc": "2026-09-04T23:30:00Z",
                "no_git_commit_from_sleeper": True,
            },
            "saturday_t90m_1430z": {
                "checkpoint": "SAT_T90M_20260905T1430Z",
                "contest_ids": [
                    "6590890",
                    "6593811",
                    "6594325",
                    "6601384",
                    "6611692",
                    "6611873",
                    "6613128",
                    "6617023",
                    "6620636",
                    "6620944",
                ],
                "primary_pid": 14180,
                "wake_utc": "2026-09-05T13:45:00Z",
                "cutoff_utc": "2026-09-05T14:30:00Z",
                "no_git_commit_from_sleeper": True,
            },
        },
        "restart_policy": {
            "stale_pid_not_deleted_unconditionally": True,
            "collision_holds_live_owner": True,
            "expiry_without_verified_recovery_is_not_acquire": True,
            "reused_pid_different_run_id_is_not_renew": True,
            "start_log_or_lease_acquire_is_not_completion": True,
            "git_publication_is_separate_from_capture": True,
            "verified_recovery_operator": "CYCLE27_CURSOR_AGENT",
        },
        "saturday_t90_clusters_starting_2026_09_05T14_30Z": (
            saturday_t90_clusters_without_am(contests)
        ),
        "sunday_monday_ownership_plan": ledger["sunday_monday_ownership_plan"],
        "note": (
            "Remaining Saturday T90 national clusters start 2026-09-05T14:30Z. "
            "A&M contest 6607349 stays on PIDs 24528/32428; do not duplicate."
        ),
    }
