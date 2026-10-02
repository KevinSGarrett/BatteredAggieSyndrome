r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Build the corrected release from a clean, isolated, installed BAS wheel (R35-03:
"clean isolated wheel builds this release from receipts; repeated replay
produces the same scientific row identities").

1. Build the wheel from the selected worktree, offline: no build isolation (the
   running interpreter's own setuptools), no index, no cache, no version check.
2. Create a fresh virtual environment and install only that wheel, the same way.
3. Run ``python -I -B -m aggie_analytics.cycle37.release_cli`` with the given
   build arguments from a working directory outside every checkout, with
   PYTHONPATH removed; isolated mode ignores it and the user site anyway.
4. Refuse the result unless the release receipt's builder block shows the CLI
   and the corrected-release module were loaded from that environment's
   site-packages, in isolated mode, from the installed distribution.

The builder itself builds the release twice in separate roots and compares
them at scientific-row grain, so the replay requirement is the builder's own
determinism block.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

WORKTREE = Path(__file__).resolve().parents[2]
OFFLINE = {"PIP_NO_INDEX": "1", "PIP_NO_CACHE_DIR": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
PIP_OFFLINE = ["--no-index", "--no-cache-dir", "--disable-pip-version-check"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}}
    env.update(OFFLINE)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
    return env


def run(label: str, command: list[str], cwd: Path, log_dir: Path, steps: list[dict[str, Any]]) -> int:
    log = log_dir / f"{label}.log"
    started = datetime.now(timezone.utc).isoformat()
    with _bas_atomic.open_write(log, "w", encoding="utf-8") as handle:
        proc = subprocess.run([str(c) for c in command], cwd=str(cwd), env=clean_env(), stdout=handle,
                              stderr=subprocess.STDOUT, timeout=7200)
    steps.append({"step": label, "command": [str(c) for c in command], "cwd": str(cwd), "exit_code": proc.returncode,
                  "log": str(log), "log_sha256": sha256_file(log), "started_at": started,
                  "finished_at": datetime.now(timezone.utc).isoformat()})
    return proc.returncode


def installed_names(freeze_log: Path) -> list[str]:
    """Distribution names from ``pip freeze`` lines: ``name==version`` or a direct reference ``name @ url``."""

    lines = [line.strip() for line in freeze_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(re.split(r"==| @ ", line, maxsplit=1)[0].strip().lower() for line in lines)


def evaluate(built: dict[str, Any], python: Path, venv: Path, freeze_log: Path) -> dict[str, bool]:
    builder = built.get("builder") or {}
    site = (venv / "Lib" / "site-packages").resolve() if os.name == "nt" else None
    cli_file = Path(builder.get("cli_module_file") or "")
    module_file = Path(builder.get("corrected_release_module_file") or "")
    return {
        "cli_loaded_from_the_fresh_environment": bool(site) and site in cli_file.parents,
        "corrected_release_loaded_from_the_fresh_environment": bool(site) and site in module_file.parents,
        "nothing_loaded_from_the_worktree": WORKTREE not in cli_file.parents and WORKTREE not in module_file.parents,
        "isolated_mode": builder.get("isolated_mode") is True,
        "interpreter_is_the_fresh_environment": Path(builder.get("executable") or "").resolve() == python.resolve(),
        "installed_distribution_present": bool(builder.get("installed_distribution")),
        "cwd_outside_the_worktree": WORKTREE not in Path(builder.get("cwd") or "/").resolve().parents
                                     and Path(builder.get("cwd") or "/").resolve() != WORKTREE,
        "installed_set_is_pip_and_the_wheel_only": installed_names(freeze_log) == ["aggie-analytics-engine", "pip"],
        "built_twice_with_matching_identity": (built.get("determinism") or {}).get("content_identity_matches") is True,
        "identical_at_scientific_grain": (built.get("determinism") or {}).get("all_identical_at_scientific_grain")
                                         is True,
    }


def recheck(path: Path) -> int:
    """Re-derive the checks from a finished run's own recorded logs and receipt, keeping the first evaluation."""

    receipt = json.loads(path.read_text(encoding="utf-8"))
    work = Path(receipt["work_dir"])
    venv = work / "venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    step = next(s for s in receipt["steps"] if s["step"] == "installed_set")
    freeze_log = Path(step["log"])
    if sha256_file(freeze_log) != step["log_sha256"]:
        raise SystemExit("the recorded pip freeze log changed since the run; not rechecked")
    built = json.loads(Path(receipt["release_receipt"]).read_text(encoding="utf-8"))
    checks = evaluate(built, python, venv, freeze_log)
    result = "BUILT_FROM_ISOLATED_WHEEL" if all(checks.values()) else "REFUSED"
    evaluations = receipt.setdefault("evaluations", [])
    if not evaluations:
        evaluations.append({"result": receipt.get("result"), "reason": receipt.get("reason"),
                            "checks": receipt.get("checks"), "installed_set_as_first_parsed": receipt.get("installed_set"),
                            "evaluated_at": receipt.get("finished_at")})
    evaluations.append({
        "result": result, "checks": checks, "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "why_rechecked": ("The first evaluation split `pip freeze` output on whitespace, so the direct-reference line "
                          "'aggie-analytics-engine @ file:///...' read as three names. The checker is fixed; this "
                          "evaluation reads the same recorded log (its SHA-256 re-verified) and the same release "
                          "receipt. Nothing was rebuilt.")})
    receipt["installed_set"] = installed_names(freeze_log)
    receipt.update(result=result, checks=checks,
                   reason=(f"release {receipt.get('content_identity')} built by the installed wheel"
                           if result == "BUILT_FROM_ISOLATED_WHEEL" else
                           "failed: " + ", ".join(k for k, v in checks.items() if not v)))
    _bas_atomic.write_text(path, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result, "-", receipt["reason"])
    return 0 if result == "BUILT_FROM_ISOLATED_WHEEL" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    parser.add_argument("--work-dir", type=Path,
                        help="owned directory for the wheel, the fresh environment and the logs")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--recheck", action="store_true",
                        help="re-derive the checks of the finished run named by --receipt from its recorded logs")
    parser.add_argument("build_args", nargs=argparse.REMAINDER,
                        help="arguments for aggie_analytics.cycle37.release_cli, after --")
    args = parser.parse_args(argv)
    if args.recheck:
        return recheck(args.receipt)
    if args.work_dir is None:
        parser.error("--work-dir is required for a build")
    build_args = [a for a in args.build_args if a != "--"]
    if "--out" not in build_args:
        parser.error("the release_cli arguments must include --out")
    release_receipt = Path(build_args[build_args.index("--out") + 1])

    work = args.work_dir.resolve()
    if work.exists() and any(work.iterdir()):
        parser.error(f"{work} is not empty; a clean build needs a fresh directory")
    dist, venv, logs, cwd = work / "dist", work / "venv", work / "logs", work / "run"
    for d in (dist, logs, cwd):
        d.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    receipt: dict[str, Any] = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE", "cycle_number": 37, "attempt_number": 2,
        "artifact_type": "R37_07_WHEEL_BUILT_RELEASE", "requirement": "R37-07-CF-R35-03",
        "worktree": str(WORKTREE), "work_dir": str(work), "steps": steps,
        "offline_environment": OFFLINE, "started_at": datetime.now(timezone.utc).isoformat(),
    }

    def finish(result: str, reason: str) -> int:
        receipt.update(result=result, reason=reason, finished_at=datetime.now(timezone.utc).isoformat())
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        _bas_atomic.write_text(args.receipt, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(result, "-", reason)
        return 0 if result == "BUILT_FROM_ISOLATED_WHEEL" else 1

    head = subprocess.run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(WORKTREE), "status", "--porcelain=v1"], capture_output=True,
                           text=True).stdout.strip()
    receipt.update(source_head=head, source_dirty_entries=len(dirty.splitlines()) if dirty else 0)
    if dirty:
        return finish("REFUSED", "the worktree has uncommitted changes; the wheel would not match any commit")

    if run("build_wheel", [sys.executable, "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                           *PIP_OFFLINE, "-w", dist, WORKTREE], work, logs, steps):
        return finish("FAILED", "wheel build failed")
    wheels = sorted(dist.glob("aggie_analytics_engine-*.whl"))
    if len(wheels) != 1:
        return finish("FAILED", f"expected one wheel, found {len(wheels)}")
    receipt["wheel"] = {"path": str(wheels[0]), "sha256": sha256_file(wheels[0]), "bytes": wheels[0].stat().st_size}

    if run("create_fresh_venv", [sys.executable, "-B", "-m", "venv", venv], work, logs, steps):
        return finish("FAILED", "venv creation failed")
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if run("install_wheel_only", [python, "-m", "pip", "install", "--no-deps", *PIP_OFFLINE, wheels[0]],
           work, logs, steps):
        return finish("FAILED", "wheel install failed")
    run("installed_set", [python, "-m", "pip", "freeze", "--all", "--disable-pip-version-check"], work, logs, steps)
    receipt["installed_set"] = installed_names(logs / "installed_set.log")

    code = run("build_release_from_wheel",
               [python, "-I", "-B", "-m", "aggie_analytics.cycle37.release_cli", *build_args], cwd, logs, steps)
    if code or not release_receipt.is_file():
        return finish("FAILED", f"the installed CLI exited {code}")
    built = json.loads(release_receipt.read_text(encoding="utf-8"))
    builder = built.get("builder") or {}
    checks = evaluate(built, python, venv, logs / "installed_set.log")
    receipt.update(release_receipt=str(release_receipt), content_identity=built.get("content_identity"),
                   release_version=built.get("release_version"), published_release=built.get("published_release"),
                   published_sha256=built.get("published_sha256"), builder=builder, checks=checks)
    if not all(checks.values()):
        return finish("REFUSED", "failed: " + ", ".join(k for k, v in checks.items() if not v))
    return finish("BUILT_FROM_ISOLATED_WHEEL", f"release {built.get('content_identity')} built by the installed wheel")


if __name__ == "__main__":
    raise SystemExit(main())
