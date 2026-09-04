"""Atomic checkpoint lease. Stale owner requires verified recovery, not age-delete.

A successful acquire is START/progress only. It is not capture completion,
FORECAST_FROZEN, or Git publication success.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import ctypes
except ImportError:
    ctypes = None  # type: ignore[assignment]

LEASE_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27\leases")
START_ACTIONS = frozenset({"ACQUIRED", "RENEWED"})
COMPLETION_ACTIONS = frozenset({"COMPLETE", "FORECAST_FROZEN", "EVIDENCE_CAPTURED"})


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_lease_root(lease_root: Path | None = None) -> Path:
    return Path(lease_root) if lease_root is not None else LEASE_ROOT


def lease_action_is_completion(action: str) -> bool:
    """Acquire/renew START a run; they never complete a checkpoint."""
    return action in COMPLETION_ACTIONS


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt" and ctypes is not None:
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire(
    *,
    checkpoint: str,
    owner: str,
    run_id: str,
    ttl_seconds: int,
    heartbeat_seconds: int,
    pid: int,
    lease_root: Path | None = None,
    pid_alive: Any | None = None,
    now_unix: float | None = None,
) -> dict[str, Any]:
    if ttl_seconds < 1 or heartbeat_seconds < 1:
        raise ValueError("ttl and heartbeat must be positive")
    root = resolve_lease_root(lease_root)
    slot = root / checkpoint
    slot.mkdir(parents=True, exist_ok=True)
    lock_dir = slot / "LOCK"
    clock = utc_now()
    unix = time.time() if now_unix is None else now_unix
    alive_fn = _pid_alive if pid_alive is None else pid_alive
    payload = {
        "checkpoint": checkpoint,
        "owner": owner,
        "run_id": run_id,
        "pid": pid,
        "acquired_at_utc": clock.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "heartbeat_at_utc": clock.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at_unix": unix + ttl_seconds,
        "heartbeat_seconds": heartbeat_seconds,
        "start_identity": f"pid:{pid}:run:{run_id}",
        "completion": False,
    }
    try:
        os.mkdir(lock_dir)
        (lock_dir / "lease.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        return {"ok": True, "action": "ACQUIRED", "lease": payload}
    except FileExistsError:
        existing_path = lock_dir / "lease.json"
        if not existing_path.exists():
            return {
                "ok": False,
                "action": "LOCK_DIR_WITHOUT_PAYLOAD",
                "reason": "investigate hung acquire; do not delete blindly",
            }
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        owner_pid = int(existing.get("pid") or 0)
        expired = float(existing.get("expires_at_unix") or 0) < unix
        alive = bool(alive_fn(owner_pid))
        if existing.get("run_id") == run_id and owner_pid == pid:
            existing["heartbeat_at_utc"] = clock.strftime("%Y-%m-%dT%H:%M:%SZ")
            existing["expires_at_unix"] = unix + ttl_seconds
            existing_path.write_text(
                json.dumps(existing, indent=2) + "\n", encoding="utf-8"
            )
            return {"ok": True, "action": "RENEWED", "lease": existing}
        if alive and not expired:
            return {
                "ok": False,
                "action": "HELD_BY_LIVE_OWNER",
                "lease": existing,
            }
        return {
            "ok": False,
            "action": "STALE_OWNER_REQUIRES_VERIFIED_RECOVERY",
            "lease": existing,
            "pid_alive": alive,
            "expired": expired,
        }


def release(
    *,
    checkpoint: str,
    run_id: str,
    pid: int,
    lease_root: Path | None = None,
) -> dict[str, Any]:
    lock_dir = resolve_lease_root(lease_root) / checkpoint / "LOCK"
    payload_path = lock_dir / "lease.json"
    if not payload_path.exists():
        return {"ok": True, "action": "ALREADY_ABSENT"}
    existing = json.loads(payload_path.read_text(encoding="utf-8"))
    if existing.get("run_id") != run_id or int(existing.get("pid") or 0) != pid:
        return {
            "ok": False,
            "action": "REFUSED_RELEASE_OWNER_MISMATCH",
            "lease": existing,
        }
    payload_path.unlink()
    try:
        lock_dir.rmdir()
    except OSError:
        return {"ok": False, "action": "RELEASED_PAYLOAD_LOCKDIR_REMAINS"}
    return {"ok": True, "action": "RELEASED"}


def recover_stale(
    *,
    checkpoint: str,
    evidence: dict[str, Any],
    lease_root: Path | None = None,
) -> dict[str, Any]:
    """Recover only with verified dead pid + expiry + explicit evidence."""
    if evidence.get("verified_pid_dead") is not True:
        return {"ok": False, "action": "RECOVERY_DENIED_PID_NOT_VERIFIED_DEAD"}
    if evidence.get("verified_expired") is not True:
        return {"ok": False, "action": "RECOVERY_DENIED_NOT_EXPIRED"}
    if evidence.get("operator") != "CYCLE27_CURSOR_AGENT":
        return {"ok": False, "action": "RECOVERY_DENIED_OPERATOR"}
    root = resolve_lease_root(lease_root)
    lock_dir = root / checkpoint / "LOCK"
    payload_path = lock_dir / "lease.json"
    if payload_path.exists():
        archived = (
            root
            / checkpoint
            / (f"recovered_{utc_now().strftime('%Y%m%dT%H%M%SZ')}.json")
        )
        archived.write_text(payload_path.read_text(encoding="utf-8"), encoding="utf-8")
        payload_path.unlink()
    try:
        lock_dir.rmdir()
    except OSError:
        return {"ok": False, "action": "RECOVERY_LOCKDIR_REMAINS"}
    return {"ok": True, "action": "RECOVERED_STALE"}
