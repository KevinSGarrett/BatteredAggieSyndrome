"""Inventory live Cycle 27 checkpoint owners from process command lines.

A saved PID or START line is not liveness. Stale PIDs are not owners.
Command lines are reduced to script basename plus Checkpoint/TargetUtc/
CutoffUtc/CohortContest; secret-bearing arguments are not recorded.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.operations.contest_checkpoint_ledger import (
    AM_CONTEST_ID,
    T24H,
    T90M,
    WAKE_LEAD,
    build_cutoff_clusters,
    format_utc,
    parse_utc,
)

AM_T90_NATIONAL_DUPLICATE = "SAT_T90M_20260905T2130Z"
CHECKPOINT_RE = re.compile(r"-Checkpoint\s+([A-Z0-9_]+)", re.IGNORECASE)
TARGET_RE = re.compile(r"-TargetUtc\s+(\S+)", re.IGNORECASE)
CUTOFF_RE = re.compile(r"-CutoffUtc\s+(\S+)", re.IGNORECASE)
COHORT_RE = re.compile(r"-CohortContest\s+(\S+)", re.IGNORECASE)
SCRIPT_RE = re.compile(r"([A-Za-z0-9_\-]+\.ps1)", re.IGNORECASE)
CHECKPOINT_STAMP_RE = re.compile(r"(20\d{6}T\d{4}Z)$")

SCRIPT_KIND = {
    "run_t24h_cluster_capture.ps1": "t24h_cluster",
    "run_t90m_cluster_capture.ps1": "t90m_cluster",
    "run_scheduled_am_t90m_capture.ps1": "am_t90m_primary",
    "run_am_t90m_failover.ps1": "am_t90m_failover",
    "run_scheduled_am_t24h_capture.ps1": "am_t24h_primary",
    "run_cycle26_overnight_heartbeat.ps1": "overnight_heartbeat",
    "run_cluster_watchdog.ps1": "cluster_watchdog",
    "run_overnight_ledger_refresh.ps1": "ledger_refresh",
}

PROCESS_FILTER = (
    "run_t24h_cluster_capture|run_t90m_cluster_capture|"
    "run_scheduled_am_t90m|run_am_t90m_failover|"
    "run_scheduled_am_t24h|run_cycle26_overnight_heartbeat|"
    "run_cluster_watchdog|run_overnight_ledger_refresh"
)


def cutoff_from_checkpoint(checkpoint: str) -> str | None:
    match = CHECKPOINT_STAMP_RE.search(str(checkpoint or ""))
    if not match:
        return None
    stamp = datetime.strptime(match.group(1), "%Y%m%dT%H%MZ").replace(
        tzinfo=timezone.utc
    )
    return format_utc(stamp)


def sanitize_command_line(command_line: str) -> dict[str, str]:
    """Keep only non-secret scheduler identity tokens."""
    command = str(command_line or "")
    match = SCRIPT_RE.search(command)
    script = match.group(1).lower() if match else ""
    checkpoint = CHECKPOINT_RE.search(command)
    target = TARGET_RE.search(command)
    cutoff = CUTOFF_RE.search(command)
    cohort = COHORT_RE.search(command)
    sanitized = {"script": script}
    if checkpoint:
        sanitized["checkpoint"] = checkpoint.group(1).upper()
    if target:
        sanitized["target_utc"] = target.group(1)
    if cutoff:
        sanitized["cutoff_utc"] = cutoff.group(1)
    if cohort:
        sanitized["cohort_contest"] = cohort.group(1)
    return sanitized


def parse_live_process_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    pid = int(row.get("pid") or 0)
    if pid <= 0:
        return None
    sanitized = sanitize_command_line(str(row.get("command_line") or ""))
    script = sanitized.get("script") or ""
    kind = SCRIPT_KIND.get(script)
    if kind is None:
        return None
    checkpoint = sanitized.get("checkpoint")
    if checkpoint == AM_T90_NATIONAL_DUPLICATE:
        return {
            "pid": pid,
            "role": "skipped_am_t90_national_duplicate",
            "checkpoint": checkpoint,
            "live": True,
            "do_not_launch_duplicate": True,
        }
    parsed = {
        "pid": pid,
        "role": kind,
        "checkpoint": checkpoint,
        "target_utc": sanitized.get("target_utc"),
        "cutoff_utc": sanitized.get("cutoff_utc"),
        "cohort_contest": sanitized.get("cohort_contest"),
        "live": True,
        "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
        "saved_pid_alone_is_not_liveness": True,
    }
    return parsed


def load_arm_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not Path(path).is_file():
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    launched = payload.get("launched") or []
    return [dict(row) for row in launched if isinstance(row, Mapping)]


def contest_ids_for_cutoff(
    contests: Sequence[Mapping[str, Any]],
    kind: str,
    cutoff_utc: str | None,
) -> list[str]:
    if not cutoff_utc:
        return []
    for cluster in build_cutoff_clusters(contests, kind):
        if cluster["cutoff_utc"] == cutoff_utc:
            return list(cluster["contest_ids"])
    return []


def collect_windows_process_rows() -> list[dict[str, Any]]:
    """Confirm liveness via Win32 command lines. No secret arguments stored."""
    script = (
        "$procs = Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -match '{PROCESS_FILTER}' }}; "
        "$rows = @(); "
        "foreach ($p in @($procs)) { "
        "$rows += [pscustomobject]@{ pid = $p.ProcessId; "
        "command_line = [string]$p.CommandLine } }; "
        "$rows | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0 or not str(completed.stdout or "").strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    rows = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "pid": int(item.get("pid") or 0),
                "command_line": str(item.get("command_line") or ""),
            }
        )
    return rows


def build_live_owner_inventory(
    *,
    processes: Sequence[Mapping[str, Any]],
    contests: Sequence[Mapping[str, Any]] | None = None,
    t24_arm: Path | None = None,
    t90_arm: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Bind one live owner per remaining checkpoint. Stale PIDs are not owners."""
    issued = now or datetime.now(timezone.utc)
    parsed = [
        item for item in (parse_live_process_row(row) for row in processes) if item
    ]
    t24_arm_rows = {str(row.get("checkpoint")): row for row in load_arm_rows(t24_arm)}
    t90_arm_rows = {str(row.get("checkpoint")): row for row in load_arm_rows(t90_arm)}
    contest_rows = list(contests or [])
    live_owners: list[dict[str, Any]] = []
    current_owners: dict[str, Any] = {}
    do_not_kill: list[int] = []
    skipped_duplicates: list[dict[str, Any]] = []

    def remember_pid(pid: int | None) -> None:
        if pid and int(pid) not in do_not_kill:
            do_not_kill.append(int(pid))

    for item in parsed:
        remember_pid(int(item["pid"]))
        role = str(item.get("role") or "")
        if role == "skipped_am_t90_national_duplicate":
            skipped_duplicates.append(item)
            continue
        if role in {"overnight_heartbeat", "cluster_watchdog", "ledger_refresh"}:
            live_owners.append(
                {
                    "name": role,
                    "pid": item["pid"],
                    "primary_pid": item["pid"],
                    "do_not_kill": True,
                    "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
                }
            )
            current_owners[role] = {
                "pid": item["pid"],
                "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
            }
            continue
        if role == "am_t90m_primary":
            existing = current_owners.get("am_t90m") or {}
            owner = {
                "name": "AM_T90M",
                "kind": T90M,
                "contest_ids": [AM_CONTEST_ID],
                "primary_pid": item["pid"],
                "wake_utc": item.get("target_utc") or "2026-09-05T20:45:00Z",
                "cutoff_utc": "2026-09-05T21:30:00Z",
                "do_not_kill": True,
                "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
            }
            if existing.get("failover_pid"):
                owner["failover_pid"] = existing["failover_pid"]
            live_owners = [row for row in live_owners if row.get("name") != "AM_T90M"]
            live_owners.append(owner)
            current_owners["am_t90m"] = {
                "checkpoint": "AM_T90M",
                "contest_id": AM_CONTEST_ID,
                "primary_pid": item["pid"],
                "failover_pid": existing.get("failover_pid"),
                "wake_utc": owner["wake_utc"],
                "cutoff_utc": owner["cutoff_utc"],
                "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
            }
            continue
        if role == "am_t90m_failover":
            am = current_owners.setdefault(
                "am_t90m",
                {
                    "checkpoint": "AM_T90M",
                    "contest_id": AM_CONTEST_ID,
                    "cutoff_utc": "2026-09-05T21:30:00Z",
                },
            )
            am["failover_pid"] = item["pid"]
            for owner in live_owners:
                if owner.get("name") == "AM_T90M":
                    owner["failover_pid"] = item["pid"]
            continue
        checkpoint = str(item.get("checkpoint") or "")
        if not checkpoint:
            continue
        kind = T24H if "T24H" in checkpoint else T90M
        arm = t24_arm_rows.get(checkpoint) or t90_arm_rows.get(checkpoint) or {}
        cutoff = item.get("cutoff_utc") or arm.get("cutoff_utc")
        if not cutoff:
            cutoff = cutoff_from_checkpoint(checkpoint)
        wake = item.get("target_utc") or arm.get("wake_utc")
        if not wake and cutoff:
            wake = format_utc(parse_utc(str(cutoff)) - WAKE_LEAD)
        contest_ids = contest_ids_for_cutoff(contest_rows, kind, cutoff)
        cohort = item.get("cohort_contest") or arm.get("cohort")
        if not contest_ids and cohort:
            contest_ids = [str(cohort)]
        owner = {
            "name": checkpoint,
            "kind": kind,
            "contest_ids": contest_ids,
            "primary_pid": item["pid"],
            "wake_utc": wake,
            "cutoff_utc": cutoff,
            "do_not_kill": True,
            "no_git_commit_from_sleeper": True,
            "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
        }
        live_owners.append(owner)
        current_owners[checkpoint.lower()] = {
            "checkpoint": checkpoint,
            "contest_ids": contest_ids,
            "primary_pid": item["pid"],
            "wake_utc": wake,
            "cutoff_utc": cutoff,
            "no_git_commit_from_sleeper": True,
            "liveness": "CONFIRMED_PROCESS_COMMAND_LINE",
        }

    am = current_owners.get("am_t90m")
    if (
        isinstance(am, Mapping)
        and not am.get("primary_pid")
        and not am.get("failover_pid")
    ):
        current_owners["am_t90m"] = {
            **dict(am),
            "liveness": "DEAD_NEEDS_WATCHDOG_RECOVERY",
        }

    return {
        "artifact_type": "CYCLE27_LIVE_OWNER_INVENTORY",
        "issued_at_utc": format_utc(issued),
        "inventory_source": "CONFIRMED_PROCESS_COMMAND_LINE",
        "saved_pid_alone_is_not_liveness": True,
        "stale_hardcoded_pids_are_not_owners": True,
        "live_process_count": len(parsed),
        "live_owners": live_owners,
        "current_owners": current_owners,
        "do_not_kill_pids": sorted(do_not_kill),
        "skipped_am_t90_national_duplicates": skipped_duplicates,
        "git_publication_coordinator": "CYCLE27_CURSOR_AGENT",
    }
