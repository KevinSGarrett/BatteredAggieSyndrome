from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller_state import ControllerState, parse_rfc3339, rfc3339


CONTROLLER_TASK = "BAS-UnifiedAssistiveController"
WATCHDOG_TASK = "BAS-UnifiedAssistiveWatchdog"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


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


def validate_release_pointer(runtime_root: Path) -> dict[str, Any]:
    pointer_path = runtime_root / "deployment/current-release.json"
    pointer = _load_json(pointer_path)
    if (
        pointer.get("schema_version") != 1
        or pointer.get("artifact_type") != "UNIFIED_ASSISTIVE_RELEASE_POINTER"
    ):
        raise ValueError("SERVICE_RELEASE_POINTER_SCHEMA_INVALID")
    build_commit = pointer.get("build_commit")
    if not isinstance(build_commit, str) or not COMMIT_RE.fullmatch(build_commit):
        raise ValueError("SERVICE_RELEASE_POINTER_BUILD_INVALID")
    expected_release = (runtime_root / "releases" / build_commit).resolve(strict=True)
    configured_release = pointer.get("release_root")
    if (
        not isinstance(configured_release, str)
        or Path(configured_release).resolve(strict=True) != expected_release
    ):
        raise ValueError("SERVICE_RELEASE_POINTER_PATH_INVALID")
    release = validate_release(expected_release)
    if sha256_file(expected_release / "RELEASE_MANIFEST.json") != pointer.get(
        "release_manifest_sha256"
    ):
        raise ValueError("SERVICE_RELEASE_POINTER_MANIFEST_HASH_MISMATCH")
    if release.get("source_tree_sha256") != pointer.get("source_tree_sha256"):
        raise ValueError("SERVICE_RELEASE_POINTER_SOURCE_TREE_MISMATCH")
    return {
        **release,
        "deployment_mode": "STABLE_LAUNCHER_RELEASE_POINTER",
        "pointer_path": str(pointer_path),
        "pointer_sha256": sha256_file(pointer_path),
    }


def _same_path(left: Path, right: Path) -> bool:
    return str(left.resolve()).casefold() == str(right.resolve()).casefold()


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
    launcher_root = runtime_root / "launcher"
    launcher_path = launcher_root / "launch_unified_assistive_service.py"
    stable_mode_flags = [
        _same_path(Path(str(task.get("working_directory", ""))), launcher_root)
        or str(launcher_path) in str(task.get("arguments", ""))
        for task in tasks
    ]
    stable_launcher_mode = bool(stable_mode_flags) and any(stable_mode_flags)
    if stable_launcher_mode and not all(stable_mode_flags):
        findings.append("SERVICE_TASK_DEPLOYMENT_MODE_DISAGREEMENT")
    for name in (CONTROLLER_TASK, WATCHDOG_TASK):
        task = by_name.get(name)
        if task is None:
            continue
        if task.get("state") != "Running" or not task.get("enabled"):
            findings.append(f"SERVICE_TASK_NOT_RUNNING:{name}")
        if task.get("run_level") != "Limited":
            findings.append(f"SERVICE_TASK_NOT_LIMITED:{name}")
        principal = str(task.get("principal", ""))
        if principal.upper() not in {"LOCAL SERVICE", r"NT AUTHORITY\LOCAL SERVICE"}:
            findings.append(f"SERVICE_TASK_PRINCIPAL_INVALID:{name}")
        if str(task.get("logon_type", "")) != "ServiceAccount":
            findings.append(f"SERVICE_TASK_NOT_NONINTERACTIVE:{name}")
        trigger_types = task.get("trigger_types", [])
        if not isinstance(trigger_types, list) or "MSFT_TaskBootTrigger" not in trigger_types:
            findings.append(f"SERVICE_TASK_STARTUP_TRIGGER_MISSING:{name}")
        arguments = str(task.get("arguments", ""))
        working_directory = Path(str(task.get("working_directory", "")))
        if stable_launcher_mode:
            role = "controller" if name == CONTROLLER_TASK else "watchdog"
            expected_arguments = (
                f'-B "{launcher_path}" --role {role} '
                f'--runtime-root "{runtime_root}"'
            )
            if not _same_path(working_directory, launcher_root):
                findings.append(f"SERVICE_TASK_STABLE_WORKING_DIRECTORY_INVALID:{name}")
            if arguments.strip() != expected_arguments:
                findings.append(f"SERVICE_TASK_STABLE_LAUNCHER_ARGUMENTS_INVALID:{name}")
        else:
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
    if stable_launcher_mode:
        try:
            release = validate_release_pointer(runtime_root)
            if not launcher_path.is_file():
                findings.append("SERVICE_STABLE_LAUNCHER_MISSING")
            task_builds.add(str(release["build_commit"]))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            release = {"valid": False, "findings": [str(exc)], "build_commit": None}
        findings.extend(release["findings"])
    elif len(release_roots) != 1:
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
        structural_result = watchdog.get("structural_result", watchdog.get("result"))
        if structural_result != "PASS" or not watchdog.get("controller_alive"):
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
        state = {
            "scheduler_cycles": 0,
            "scheduler_dispatched_units": 0,
            "scheduler_no_change_cycles": 0,
            "active_idle_intervals": 0,
            "journal_mode": None,
            "integrity_check": None,
        }
        findings.append(f"SERVICE_DATABASE_INVALID:{exc}")
    deployed_healthy = not findings
    scheduler_cycles = int(state.get("scheduler_cycles", 0))
    scheduler_dispatched = int(state.get("scheduler_dispatched_units", 0))
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
            "scheduler_last_result": heartbeat.get("scheduler_last_result"),
            "scheduler_inventory_sha256": heartbeat.get("scheduler_inventory_sha256"),
            "scheduler_eligible_units": heartbeat.get("scheduler_eligible_units", 0),
            "scheduler_provider_calls": heartbeat.get("scheduler_provider_calls", 0),
        },
        "watchdog": {
            "report_sha256": sha256_file(watchdog_path) if watchdog_path.is_file() else None,
            "report_age_seconds": watchdog_age,
            "build_commit": watchdog.get("watchdog_build_commit"),
            "controller_alive": watchdog.get("controller_alive", False),
            "structural_result": watchdog.get("structural_result", watchdog.get("result")),
            "operational_result": watchdog.get("operational_result", watchdog.get("result")),
            "operational_findings": watchdog.get("operational_findings", []),
        },
        "database": {
            "path": str(database),
            "journal_mode": state.get("journal_mode"),
            "integrity_check": state.get("integrity_check"),
            "schema_version": state.get("schema_version"),
        },
        "scheduler": {
            "recorded_cycles": scheduler_cycles,
            "real_cycles": scheduler_cycles,
            "dispatched_units": scheduler_dispatched,
            "no_change_cycles": int(state.get("scheduler_no_change_cycles", 0)),
            "active_idle_intervals": int(state.get("active_idle_intervals", 0)),
            "operational": scheduler_cycles > 0 and scheduler_dispatched > 0,
        },
        "cold_boot_without_user_logon": (
            "STARTUP_CAPABLE_NONINTERACTIVE_RUNTIME_VERIFIED_BOOT_OBSERVATION_PENDING"
            if deployed_healthy else "NOT_PROVEN"
        ),
        "credential_values_captured": False,
    }
