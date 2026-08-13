from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.live_service import evaluate_live_service
from aggie_analytics.assistive_plane.service_runtime import ContentAddressedReportStore


DEFAULT_RUNTIME = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")
TASKS = ("BAS-UnifiedAssistiveController", "BAS-UnifiedAssistiveWatchdog")


def collect_windows_tasks() -> list[dict[str, object]]:
    names = ",".join(f"'{name}'" for name in TASKS)
    command = (
        f"$items=@({names});$rows=foreach($name in $items){{"
        "$task=Get-ScheduledTask -TaskName $name -ErrorAction Stop;"
        "$info=Get-ScheduledTaskInfo -TaskName $name;"
        "[pscustomobject]@{task_name=$name;state=[string]$task.State;enabled=[bool]$task.Settings.Enabled;"
        "principal=[string]$task.Principal.UserId;run_level=[string]$task.Principal.RunLevel;"
        "logon_type=[string]$task.Principal.LogonType;execute=[string]$task.Actions.Execute;"
        "arguments=[string]$task.Actions.Arguments;working_directory=[string]$task.Actions.WorkingDirectory;"
        "last_task_result=[int64]$info.LastTaskResult}};$rows|ConvertTo-Json -Depth 4 -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    return payload if isinstance(payload, list) else [payload]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--tasks-json", type=Path)
    args = parser.parse_args()
    if args.tasks_json:
        tasks = json.loads(args.tasks_json.read_text(encoding="utf-8"))
    elif sys.platform == "win32":
        tasks = collect_windows_tasks()
    else:
        raise RuntimeError("WINDOWS_SERVICE_CAPTURE_REQUIRES_TASK_FIXTURE_OFF_WINDOWS")
    capture = evaluate_live_service(runtime_root=args.runtime_root, tasks=tasks)
    store = ContentAddressedReportStore(args.runtime_root / "service-state")
    path, digest = store.write("captures", capture, current_name="service-state.json")
    print(json.dumps({"status": capture["result"], "path": str(path), "sha256": digest, **capture}, sort_keys=True))
    return 0 if capture["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
