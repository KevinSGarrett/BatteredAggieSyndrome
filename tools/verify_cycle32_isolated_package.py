"""Install the committed package into an isolated venv and import from it.

Tests run from the worktree tests/ path, but aggie_analytics must resolve to
site-packages, not checkout/src. PYTHONPATH is cleared.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> dict:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout_tail": (completed.stdout or "")[-4000:],
        "stderr_tail": (completed.stderr or "")[-4000:],
    }


def main() -> int:
    venv = Path(tempfile.mkdtemp(prefix="bas-c32-pkg-"))
    py = venv / "Scripts" / "python.exe"
    pip = venv / "Scripts" / "pip.exe"
    steps: list[dict] = []
    steps.append(run([sys.executable, "-m", "venv", str(venv)]))
    if not py.is_file():
        payload = {
            "artifact_type": "CYCLE32_ISOLATED_PACKAGE_LANE",
            "as_of_utc": utc_now(),
            "status": "VENV_CREATE_FAILED",
            "venv": str(venv),
            "steps": steps,
        }
        out = OUT / "science" / "CYCLE32_ISOLATED_PACKAGE_LANE.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "VENV_CREATE_FAILED"}))
        return 1
    steps.append(run([str(py), "-m", "pip", "install", "-U", "pip"]))
    steps.append(run([str(pip), "install", f"{ROOT}[kernel]"]))
    env = {key: value for key, value in os.environ.items() if key.upper() != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    locate = run(
        [
            str(py),
            "-c",
            (
                "import aggie_analytics, pathlib, sys; "
                "p=pathlib.Path(aggie_analytics.__file__).resolve(); "
                "print(p); "
                "print('CHECKOUT_SRC' if 'worktrees' in str(p) and 'src' in str(p) else 'SITE'); "
                "import aggie_analytics.cycle30.kernel_model as km; "
                "print(km.__file__)"
            ),
        ],
        env=env,
        cwd=Path(r"C:\Windows\System32"),
    )
    steps.append(locate)
    tests = run(
        [str(py), "-B", "-m", "unittest", "tests.test_cycle32_manager_counterexamples"],
        env=env,
        cwd=ROOT,
    )
    steps.append(tests)
    installed_from_site = "SITE" in (locate.get("stdout_tail") or "")
    payload = {
        "artifact_type": "CYCLE32_ISOLATED_PACKAGE_LANE",
        "as_of_utc": utc_now(),
        "venv": str(venv),
        "pythonpath_cleared": True,
        "installed_from_site_packages": installed_from_site,
        "import_returncode": locate["returncode"],
        "unittest_returncode": tests["returncode"],
        "status": (
            "PASS_LOCAL"
            if locate["returncode"] == 0 and tests["returncode"] == 0 and installed_from_site
            else "FAIL"
        ),
        "import_stdout_tail": locate.get("stdout_tail"),
        "unittest_stderr_tail": tests.get("stderr_tail"),
        "checkout_not_on_pythonpath": True,
    }
    out = OUT / "science" / "CYCLE32_ISOLATED_PACKAGE_LANE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "import_rc": locate["returncode"],
                "tests_rc": tests["returncode"],
                "site": installed_from_site,
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS_LOCAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
