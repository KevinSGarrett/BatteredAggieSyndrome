from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import ControllerState, parse_rfc3339, rfc3339


CONTROLLER_TASK = "BAS-UnifiedAssistiveController"
WATCHDOG_TASK = "BAS-UnifiedAssistiveWatchdog"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"SERVICE_EVIDENCE_NOT_OBJECT:{path}")
    return payload


def validate_release(release_root: Path) -> dict[str, Any]:
    manifest_path = release_root / "RELEASE_MANIFEST.json"
    if not manifest_path.is_file():
        raise ValueError("SERVICE_RELEASE_MANIFEST_MISSING")
    manifest = _load_json(manifest_path)
    build_commit = manifest.get("build_commit", "")
    if release_root.name != build_commit:
        raise ValueError("SERVICE_RELEASE_DIRECTORY_COMMIT_MISMATCH")
    findings: list[str] = []
    for relative, identity in manifest.get("files", {}).items():
        candidate = release_root / Path(*relative.split("/"))
        if not candidate.is_file():
            findings.append(f"SERVICE_RELEASE_FILE_MISSING:{relative}")
            continue
        if candidate.stat().st_size != identity.get("bytes"):
            findings.append(f"SERVICE_RELEASE_FILE_SIZE_MISMATCH:{relative}")
        if sha256_file(candidate) != identity.get("sha256"):
            findings.append(f"SERVICE_RELEASE_FILE_HASH_MISMATCH:{relative}")
    return {
        "path": str(release_root),
        "build_commit": build_commit,
        "manifest_sha256": sha256_file(manifest_path),
        "source_tree_sha256": manifest.get("source_tree_sha256"),
        "file_count": len(manifest.get("files", {})),
        "valid": not findings,
        "findings": findings,
    }


def evaluate_live_service(
    *,
    runtime_root: Path,
    tasks: list[dict[str, Any]],
    now: datetime | None = None,
    heartbeat_max_age_seconds: int = 90,
    watchdog_max_age_seconds: int = 600,
) -> dict[str, Any]:
    moment = now or datetime.now(timezone.utc)
    findings: list[str] = []
    by_name = {item.get("task_name"): item for item in tasks}
    if len(tasks) != 2 or set(by_name) != {CONTROLLER_TASK, WATCHDOG_TASK}:
        findings.append("SERVICE_TASK_POPULATION_MISMATCH")
    task_builds: set[str] = set()
    release_roots: set[Path] = set()
    for name in (CONTROLLER_TASK, WATCHDOG_TASK):
        task = by_name.get(name)
        if task is None:
            continue
        if task.get("state") != "Running" or not task.get("enabled"):
            findings.append(f"SERVICE_TASK_NOT_RUNNING:{name}")
        if task.get("run_level") != "Limited":
            findings.append(f"SERVICE_TASK_NOT_LIMITED:{name}")
        principal = str(task.get("principal", ""))
        if not principal or principal.upper().endswith("SYSTEM"):
            findings.append(f"SERVICE_TASK_PRINCIPAL_INVALID:{name}")
        arguments = str(task.get("arguments", ""))
        working_directory = Path(str(task.get("working_directory", "")))
        release_roots.add(working_directory)
        tokens = arguments.split()
        if "--build-commit" not in tokens:
            findings.append(f"SERVICE_TASK_BUILD_COMMIT_MISSING:{name}")
        else:
            index = tokens.index("--build-commit")
            if index + 1 >= len(tokens):
                findings.append(f"SERVICE_TASK_BUILD_COMMIT_MISSING:{name}")
            else:
                task_builds.add(tokens[index + 1].strip('"'))
    if len(release_roots) != 1:
        findings.append("SERVICE_TASK_RELEASE_ROOT_DISAGREEMENT")
        release = {"valid": False, "findings": ["SERVICE_RELEASE_ROOT_NOT_UNIQUE"], "build_commit": None}
    else:
        try:
            release = validate_release(next(iter(release_roots)))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            release = {"valid": False, "findings": [str(exc)], "build_commit": None}
        findings.extend(release["findings"])
    heartbeat_path = runtime_root / "evidence/current/controller-heartbeat.json"
    watchdog_path = runtime_root / "watchdog/current/watchdog-report.json"
    try:
        heartbeat = _load_json(heartbeat_path)
        heartbeat_age = max(0.0, (moment - parse_rfc3339(heartbeat["observed_at"])).total_seconds())
        if heartbeat_age > heartbeat_max_age_seconds:
            findings.append("SERVICE_CONTROLLER_HEARTBEAT_STALE")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        heartbeat = {}
        heartbeat_age = None
        findings.append(f"SERVICE_CONTROLLER_HEARTBEAT_INVALID:{exc}")
    try:
        watchdog = _load_json(watchdog_path)
        watchdog_age = max(0.0, (moment - parse_rfc3339(watchdog["observed_at"])).total_seconds())
        if watchdog_age > watchdog_max_age_seconds:
            findings.append("SERVICE_WATCHDOG_REPORT_STALE")
        if watchdog.get("result") != "PASS" or not watchdog.get("controller_alive"):
            findings.append("SERVICE_WATCHDOG_CONTROLLER_HEALTH_FAILED")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        watchdog = {}
        watchdog_age = None
        findings.append(f"SERVICE_WATCHDOG_REPORT_INVALID:{exc}")
    build_commit = release.get("build_commit")
    observed_builds = task_builds | {
        str(item) for item in (heartbeat.get("build_commit"), watchdog.get("controller_build_commit"), watchdog.get("watchdog_build_commit")) if item
    }
    if not build_commit or observed_builds != {build_commit}:
        findings.append("SERVICE_BUILD_IDENTITY_DISAGREEMENT")
    database = runtime_root / "state/orchestrator.sqlite3"
    try:
        state = ControllerState(database).status()
        if state["journal_mode"] != "WAL" or state["integrity_check"] != "ok":
            findings.append("SERVICE_DATABASE_HEALTH_FAILED")
    except (OSError, ValueError) as exc:
        state = {"scheduler_cycles": 0, "journal_mode": None, "integrity_check": None}
        findings.append(f"SERVICE_DATABASE_INVALID:{exc}")
    deployed_healthy = not findings
    scheduler_cycles = int(state.get("scheduler_cycles", 0))
    dispatch_state = heartbeat.get("dispatch_engine_state")
    return {
        "schema_version": 1,
        "artifact_type": "UNIFIED_ASSISTIVE_LIVE_SERVICE_CAPTURE",
        "observed_at": rfc3339(moment),
        "result": "PASS" if deployed_healthy else "FAIL",
        "service_shell_state": "DEPLOYED_HEALTHY" if deployed_healthy else "DEPLOYMENT_FAILED",
        "overall_operational_completion": "INCOMPLETE",
        "findings": findings,
        "tasks": tasks,
        "release": release,
        "controller": {
            "heartbeat_sha256": sha256_file(heartbeat_path) if heartbeat_path.is_file() else None,
            "heartbeat_age_seconds": heartbeat_age,
            "owner_id": heartbeat.get("owner_id"),
            "build_commit": heartbeat.get("build_commit"),
            "dispatch_engine_state": dispatch_state,
            "queue_evaluation_observations": heartbeat.get("queue_evaluation_observations", 0),
        },
        "watchdog": {
            "report_sha256": sha256_file(watchdog_path) if watchdog_path.is_file() else None,
            "report_age_seconds": watchdog_age,
            "build_commit": watchdog.get("watchdog_build_commit"),
            "controller_alive": watchdog.get("controller_alive", False),
        },
        "database": {
            "path": str(database),
            "journal_mode": state.get("journal_mode"),
            "integrity_check": state.get("integrity_check"),
            "schema_version": state.get("schema_version"),
        },
        "scheduler": {
            "recorded_cycles": scheduler_cycles,
            "real_cycles": 0,
            "operational": scheduler_cycles > 0 and dispatch_state not in {None, "NOT_IMPLEMENTED_IN_THIS_ATOMIC_UNIT"},
        },
        "cold_boot_without_user_logon": "NOT_PROVEN",
        "credential_values_captured": False,
    }
