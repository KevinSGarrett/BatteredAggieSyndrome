from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog  # noqa: E402
from aggie_analytics.assistive_plane.service_runtime import (  # noqa: E402
    WatchdogService,
    WatchdogServiceConfig,
)


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
    parser.add_argument("command", choices=["inspect", "serve"], nargs="?", default="inspect")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument(
        "--database",
        type=Path,
    )
    parser.add_argument("--heartbeat-max-age-seconds", type=int, default=90)
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--maximum-runtime-seconds", type=float)
    parser.add_argument("--build-commit")
    args = parser.parse_args()
    database = args.database or args.runtime_root / "state" / "orchestrator.sqlite3"
    if args.command == "serve":
        stop_event = threading.Event()

        def stop_service(_signum: int, _frame: object) -> None:
            stop_event.set()

        signal.signal(signal.SIGINT, stop_service)
        signal.signal(signal.SIGTERM, stop_service)
        service = WatchdogService(
            WatchdogServiceConfig(
                runtime_root=args.runtime_root,
                build_commit=commit_identity(args.build_commit),
                interval_seconds=args.interval_seconds,
                heartbeat_max_age_seconds=args.heartbeat_max_age_seconds,
            )
        )
        print(json.dumps(service.run(stop_event, maximum_runtime_seconds=args.maximum_runtime_seconds), sort_keys=True))
        return 0
    # An interactive inspection is an operational audit, not merely a process
    # health probe. Pass explicit evidence paths so ReadOnlyWatchdog enables
    # its fail-closed inventory/scheduler checks, and bind the result to the
    # release identity represented by the calling source tree.
    report = ReadOnlyWatchdog(
        database,
        args.heartbeat_max_age_seconds,
        inventory_path=args.runtime_root.parent / "inventory" / "current" / "inventory.json",
        scheduler_report_path=args.runtime_root / "evidence" / "current" / "scheduler-evaluation.json",
        expected_build_commit=commit_identity(args.build_commit),
    ).inspect()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
