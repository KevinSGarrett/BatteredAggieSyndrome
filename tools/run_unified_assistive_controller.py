from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.controller_state import ControllerState, LeaderLock
from aggie_analytics.assistive_plane.service_runtime import ControllerService, ControllerServiceConfig


DEFAULT_RUNTIME = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")


def commit_identity(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    release_manifest = ROOT / "RELEASE_MANIFEST.json"
    if release_manifest.is_file():
        return json.loads(release_manifest.read_text(encoding="utf-8"))["build_commit"]
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "status", "heartbeat", "cycle", "serve"])
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--owner-id", default=f"{os.environ.get('COMPUTERNAME', 'unknown')}:{os.getpid()}:{uuid.uuid4().hex}")
    parser.add_argument("--build-commit")
    parser.add_argument("--heartbeat-seconds", type=float, default=30.0)
    parser.add_argument("--queue-evaluation-seconds", type=float, default=60.0)
    parser.add_argument("--lease-ttl-seconds", type=int, default=120)
    parser.add_argument("--maximum-runtime-seconds", type=float)
    parser.add_argument("--inventory-sha256")
    parser.add_argument("--cycle-id")
    parser.add_argument("--eligible-units", type=int, default=0)
    parser.add_argument("--dispatched-units", type=int, default=0)
    parser.add_argument("--no-change", action="store_true")
    args = parser.parse_args()
    database = args.runtime_root / "state" / "orchestrator.sqlite3"
    state = ControllerState(database)
    if args.command == "serve":
        stop_event = threading.Event()

        def stop_service(_signum: int, _frame: object) -> None:
            stop_event.set()

        signal.signal(signal.SIGINT, stop_service)
        signal.signal(signal.SIGTERM, stop_service)
        service = ControllerService(
            ControllerServiceConfig(
                runtime_root=args.runtime_root,
                owner_id=args.owner_id,
                build_commit=commit_identity(args.build_commit),
                heartbeat_seconds=args.heartbeat_seconds,
                queue_evaluation_seconds=args.queue_evaluation_seconds,
                lease_ttl_seconds=args.lease_ttl_seconds,
            )
        )
        print(json.dumps(service.run(stop_event, maximum_runtime_seconds=args.maximum_runtime_seconds), sort_keys=True))
        return 0
    if args.command == "init":
        state.initialize()
        with LeaderLock(args.runtime_root / "runtime" / "controller.lock"):
            build_commit = commit_identity(args.build_commit)
            state.acquire_leader(args.owner_id, build_commit)
            state.append_event("CONTROLLER_INITIALIZED", {"owner_id": args.owner_id, "build_commit": build_commit})
            state.release_leader(args.owner_id)
        print(json.dumps({"result": "PASS", **state.status()}, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps(state.status(), sort_keys=True))
        return 0
    if args.command == "heartbeat":
        state.heartbeat(args.owner_id)
        print(json.dumps({"result": "PASS", "owner_id": args.owner_id}, sort_keys=True))
        return 0
    if not args.inventory_sha256 or not args.cycle_id:
        parser.error("cycle requires --inventory-sha256 and --cycle-id")
    state.record_cycle(
        cycle_id=args.cycle_id,
        inventory_sha256=args.inventory_sha256,
        eligible_units=args.eligible_units,
        dispatched_units=args.dispatched_units,
        no_change=args.no_change,
        result="INCOMPLETE_FOUNDATION_ONLY",
    )
    print(json.dumps({"result": "INCOMPLETE", "cycle_id": args.cycle_id}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
