"""Atomic checkpoint lease with primary/failover CAS takeover.

A live owner cannot be displaced by PID ordering or a second launch. Takeover
requires verified expiry, verified dead owner PID, and compare-and-swap of the
expected cas_token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import ctypes
except ImportError:
    ctypes = None  # type: ignore[assignment]

DEFAULT_LEASE_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\leases")
SCHEDULER_ACTIVE_OR_BOUND = "SCHEDULER_ACTIVE_OR_BOUND"
PRIMARY = "PRIMARY"
FAILOVER = "FAILOVER"


class LeaseError(ValueError):
    """Raised when a lease contract is violated."""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt" and ctypes is not None:
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, int(pid)
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


def _root(lease_root: Path | None) -> Path:
    if lease_root is not None:
        return Path(lease_root)
    env = os.environ.get("CYCLE29_LEASE_ROOT")
    return Path(env) if env else DEFAULT_LEASE_ROOT


def _slot(contest_id: str, checkpoint: str, lease_root: Path | None = None) -> Path:
    safe_contest = "".join(ch if ch.isalnum() else "_" for ch in contest_id)
    safe_checkpoint = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in checkpoint
    )
    return _root(lease_root) / f"{safe_contest}__{safe_checkpoint}"


def _lock_dir(contest_id: str, checkpoint: str, lease_root: Path | None = None) -> Path:
    return _slot(contest_id, checkpoint, lease_root) / "LOCK"


def _lease_path(
    contest_id: str, checkpoint: str, lease_root: Path | None = None
) -> Path:
    return _lock_dir(contest_id, checkpoint, lease_root) / "lease.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def acquire(
    *,
    contest_id: str,
    checkpoint: str,
    cutoff_utc: str,
    owner_id: str,
    role: str,
    pid: int,
    ttl_seconds: int,
    heartbeat_seconds: int,
    expected_cas_token: str | None = None,
    lease_root: Path | None = None,
    write_paths: list[str] | None = None,
) -> dict[str, Any]:
    if role not in {PRIMARY, FAILOVER}:
        return {"ok": False, "action": "INVALID_ROLE", "exit_code": 2}
    if ttl_seconds < 1 or heartbeat_seconds < 1:
        return {"ok": False, "action": "INVALID_TTL", "exit_code": 2}
    slot = _slot(contest_id, checkpoint, lease_root)
    slot.mkdir(parents=True, exist_ok=True)
    lock_dir = _lock_dir(contest_id, checkpoint, lease_root)
    lease_path = _lease_path(contest_id, checkpoint, lease_root)
    cas_token = uuid.uuid4().hex
    payload = {
        "artifact_type": "CYCLE29_CHECKPOINT_LEASE",
        "owner_id": owner_id,
        "role": role,
        "pid": int(pid),
        "contest_id": contest_id,
        "checkpoint": checkpoint,
        "cutoff_utc": cutoff_utc,
        "acquired_at_utc": utc_stamp(),
        "heartbeat_at_utc": utc_stamp(),
        "expiry_unix": time.time() + ttl_seconds,
        "expiry_utc": datetime.fromtimestamp(
            time.time() + ttl_seconds, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "heartbeat_seconds": heartbeat_seconds,
        "ttl_seconds": ttl_seconds,
        "cas_token": cas_token,
        "write_paths": list(
            write_paths or [str(slot / "owner_outputs" / "receipt.json")]
        ),
        "lease_identity": str(slot),
    }
    tmp_dir = slot / f".lock_tmp_{uuid.uuid4().hex}"
    try:
        tmp_dir.mkdir()
        _atomic_write(tmp_dir / "lease.json", payload)
        os.rename(tmp_dir, lock_dir)
        return {"ok": True, "action": "ACQUIRED", "lease": payload, "exit_code": 0}
    except OSError:
        if tmp_dir.exists():
            try:
                for child in tmp_dir.iterdir():
                    child.unlink()
                tmp_dir.rmdir()
            except OSError:
                pass
        deadline = time.time() + 2.0
        while time.time() < deadline and not lease_path.exists():
            time.sleep(0.02)
        if not lease_path.exists():
            return {
                "ok": False,
                "action": "LOCK_DIR_WITHOUT_PAYLOAD",
                "exit_code": 3,
            }
        existing = json.loads(lease_path.read_text(encoding="utf-8"))
        owner_pid = int(existing.get("pid") or 0)
        expired = float(existing.get("expiry_unix") or 0) < time.time()
        alive = _pid_alive(owner_pid)
        if existing.get("owner_id") == owner_id and owner_pid == int(pid):
            existing["heartbeat_at_utc"] = utc_stamp()
            existing["expiry_unix"] = time.time() + ttl_seconds
            existing["expiry_utc"] = datetime.fromtimestamp(
                time.time() + ttl_seconds, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            _atomic_write(lease_path, existing)
            return {"ok": True, "action": "RENEWED", "lease": existing, "exit_code": 0}
        if alive and not expired:
            return {
                "ok": False,
                "action": SCHEDULER_ACTIVE_OR_BOUND,
                "lease": existing,
                "exit_code": 4,
            }
        if expected_cas_token is None:
            return {
                "ok": False,
                "action": "STALE_OWNER_REQUIRES_VERIFIED_CAS",
                "lease": existing,
                "pid_alive": alive,
                "expired": expired,
                "exit_code": 5,
            }
        if expected_cas_token != existing.get("cas_token"):
            return {
                "ok": False,
                "action": "CAS_TOKEN_MISMATCH",
                "lease": existing,
                "exit_code": 6,
            }
        if alive or not expired:
            return {
                "ok": False,
                "action": "CAS_TAKEOVER_DENIED_NOT_EXPIRED_OR_ALIVE",
                "lease": existing,
                "exit_code": 7,
            }
        _atomic_write(lease_path, payload)
        return {
            "ok": True,
            "action": "CAS_TAKEOVER",
            "lease": payload,
            "predecessor": existing,
            "exit_code": 0,
        }


def reject_stale_takeover_without_expiry(
    *, expired: bool, pid_alive: bool, cas_ok: bool
) -> None:
    if (pid_alive or not expired) or not cas_ok:
        raise LeaseError("stale/failover lease takeover without expiry authority")


def release(
    *,
    contest_id: str,
    checkpoint: str,
    owner_id: str,
    pid: int,
    lease_root: Path | None = None,
) -> dict[str, Any]:
    lease_path = _lease_path(contest_id, checkpoint, lease_root)
    lock_dir = _lock_dir(contest_id, checkpoint, lease_root)
    if not lease_path.exists():
        return {"ok": True, "action": "ALREADY_ABSENT", "exit_code": 0}
    existing = json.loads(lease_path.read_text(encoding="utf-8"))
    if existing.get("owner_id") != owner_id or int(existing.get("pid") or 0) != int(
        pid
    ):
        return {
            "ok": False,
            "action": "REFUSED_RELEASE_OWNER_MISMATCH",
            "lease": existing,
            "exit_code": 8,
        }
    lease_path.unlink()
    try:
        lock_dir.rmdir()
    except OSError:
        return {
            "ok": False,
            "action": "RELEASED_PAYLOAD_LOCKDIR_REMAINS",
            "exit_code": 9,
        }
    return {"ok": True, "action": "RELEASED", "exit_code": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["acquire", "release", "inspect"])
    parser.add_argument("--contest-id", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--cutoff-utc", default="")
    parser.add_argument("--owner-id", default="")
    parser.add_argument("--role", default=PRIMARY)
    parser.add_argument("--pid", type=int, default=os.getpid())
    parser.add_argument("--ttl-seconds", type=int, default=8 * 3600)
    parser.add_argument("--heartbeat-seconds", type=int, default=60)
    parser.add_argument("--expected-cas-token", default=None)
    parser.add_argument("--lease-root", default=None)
    args = parser.parse_args(argv)
    root = Path(args.lease_root) if args.lease_root else None
    if args.command == "inspect":
        path = _lease_path(args.contest_id, args.checkpoint, root)
        if not path.exists():
            result: dict[str, Any] = {"ok": True, "action": "ABSENT", "exit_code": 0}
        else:
            existing = json.loads(path.read_text(encoding="utf-8"))
            result = {
                "ok": True,
                "action": "PRESENT",
                "lease": existing,
                "pid_alive": _pid_alive(int(existing.get("pid") or 0)),
                "expired": float(existing.get("expiry_unix") or 0) < time.time(),
                "exit_code": 0,
            }
    elif args.command == "release":
        result = release(
            contest_id=args.contest_id,
            checkpoint=args.checkpoint,
            owner_id=args.owner_id,
            pid=args.pid,
            lease_root=root,
        )
    else:
        result = acquire(
            contest_id=args.contest_id,
            checkpoint=args.checkpoint,
            cutoff_utc=args.cutoff_utc,
            owner_id=args.owner_id,
            role=args.role,
            pid=args.pid,
            ttl_seconds=args.ttl_seconds,
            heartbeat_seconds=args.heartbeat_seconds,
            expected_cas_token=args.expected_cas_token,
            lease_root=root,
        )
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return int(result.get("exit_code") or (0 if result.get("ok") else 1))


if __name__ == "__main__":
    raise SystemExit(main())
