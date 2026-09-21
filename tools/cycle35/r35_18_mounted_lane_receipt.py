"""R35-18: prove what environment a validation lane's subprocess actually used.

Cycle #35 closeout review (20260921T025300Z), section 1:

    "The affected Family B test modules require AGGIE_ANALYTICS_DATA_ROOT
    to be explicitly set, not merely that the default directory exists.
    The receipt generator hardcodes the intended data-root path and tests
    DATA_ROOT.is_dir(); it does not establish what environment the test
    subprocess actually used... Capture subprocess environment allowlisted
    to relevant non-secret path/seed settings, imported module paths, real
    required payload readiness, test discovery, skips/reasons and actual
    process exit. Do not print credentials or the full environment."

The gate those modules use is:

    LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and
                 DATA_ROOT.exists()

so a directory existing on disk proves nothing about whether the tests
ran. `python -m unittest discover` without that variable set skips all
nine of them and still exits 0.

Every lane here therefore runs a PRE-FLIGHT PROBE in the same environment
as the test command. The probe reports the environment from INSIDE the
subprocess -- the effective data root, whether the skip gate would open,
which module files actually got imported and whether the payloads those
tests need are readable. The receipt records what the process really saw,
not what the caller intended it to see.

Only non-secret path/seed variables are ever recorded; the allowlist is
explicit and the full environment is never captured.
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
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")

#: The ONLY environment variables this tool ever records. Everything else
#: is excluded by construction so a credential cannot reach a receipt.
ENV_ALLOWLIST = (
    "AGGIE_ANALYTICS_DATA_ROOT",
    "PYTHONPATH",
    "PYTHONHASHSEED",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONNOUSERSITE",
    "PYTHONUTF8",
    "TZ",
)

#: Modules whose resolved file path is worth recording: it proves whether
#: the installed wheel or the working tree's src/ was actually imported.
PROBE_MODULES = (
    "aggie_analytics",
    "aggie_analytics.data.tamu_official_1998_2009_rejection_integrity",
    "aggie_analytics.cycle35.availability",
)

PROBE_SOURCE = r'''
import importlib, json, os, sys
from pathlib import Path

allow = %(allowlist)s
env = {name: os.environ.get(name) for name in allow}
data_root_raw = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
data_root = Path(data_root_raw) if data_root_raw else None

modules = {}
for name in %(modules)s:
    try:
        mod = importlib.import_module(name)
        modules[name] = getattr(mod, "__file__", None) or str(getattr(mod, "__path__", ""))
    except Exception as exc:
        modules[name] = "IMPORT_FAILED: %%s" %% exc

payloads = {}
for label, relative in %(payloads)s:
    if data_root is None:
        payloads[label] = {"checked": None, "exists": False, "reason": "no data root in env"}
        continue
    target = data_root / relative
    payloads[label] = {
        "checked": str(target),
        "exists": target.exists(),
        "is_dir": target.is_dir() if target.exists() else None,
    }

print(json.dumps({
    "environment_allowlisted": env,
    "data_root_env_set": bool(data_root_raw),
    "data_root_exists": bool(data_root and data_root.exists()),
    # This is the EXACT gate the Family B modules evaluate.
    "family_b_skip_gate_open": bool(data_root_raw) and bool(data_root and data_root.exists()),
    "interpreter": sys.executable,
    "cwd": os.getcwd(),
    "sys_path_head": sys.path[:6],
    "imported_module_files": modules,
    "payload_readiness": payloads,
}))
'''

#: Payloads the mounted Family B lane genuinely needs, relative to the
#: data root. Readiness is checked rather than assumed.
REQUIRED_PAYLOADS: tuple[tuple[str, str], ...] = (
    (
        "union_1996_expanded_features",
        "features/tamu_official_gamebook_union_1996_expanded",
    ),
    (
        "structured_row_corpus",
        "features/tamu_official_1998_2009_structured_row_corpus",
    ),
)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def build_environment(data_root: Path | None, hash_seed: str | None) -> dict[str, str]:
    """A minimal, explicit environment for the lane subprocess."""

    env = dict(os.environ)
    env.pop("AGGIE_ANALYTICS_DATA_ROOT", None)
    if data_root is not None:
        env["AGGIE_ANALYTICS_DATA_ROOT"] = str(data_root)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if hash_seed is not None:
        env["PYTHONHASHSEED"] = hash_seed
    return env


def run_probe(env: dict[str, str]) -> dict[str, Any]:
    """Ask the subprocess itself what environment it received."""

    source = PROBE_SOURCE % {
        "allowlist": repr(list(ENV_ALLOWLIST)),
        "modules": repr(list(PROBE_MODULES)),
        "payloads": repr([list(item) for item in REQUIRED_PAYLOADS]),
    }
    completed = subprocess.run(
        [sys.executable, "-B", "-c", source],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        return {
            "probe_succeeded": False,
            "exit_code": completed.returncode,
            "stderr_tail": (completed.stderr or "").strip().splitlines()[-5:],
        }
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return {"probe_succeeded": False, "stdout_head": completed.stdout[:400]}
    payload["probe_succeeded"] = True
    return payload


_COUNT_PATTERNS = (
    re.compile(r"(?P<count>\d+) (?P<kind>passed|failed|error|errors|skipped|deselected)"),
)


def parse_pytest_summary(text: str) -> dict[str, Any]:
    """Counts and the full skip inventory from a pytest log."""

    tail = text.strip().splitlines()
    summary_line = ""
    for line in reversed(tail[-15:]):
        if re.search(r"\b(passed|failed|error|skipped|no tests ran)\b", line):
            summary_line = line.strip()
            break
    counts: dict[str, int] = {}
    for pattern in _COUNT_PATTERNS:
        for match in pattern.finditer(summary_line):
            kind = match.group("kind").rstrip("s")
            counts[kind] = counts.get(kind, 0) + int(match.group("count"))

    skips: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("SKIPPED"):
            continue
        location, _, reason = stripped.partition(": ")
        skips.append({"entry": location.strip(), "reason": reason.strip()})

    reason_counts: dict[str, int] = {}
    for item in skips:
        reason_counts[item["reason"]] = reason_counts.get(item["reason"], 0) + 1
    return {
        "summary_line": summary_line,
        "counts": counts,
        "skip_inventory": skips,
        "skip_reason_counts": reason_counts,
        "skips_listed": len(skips),
    }


def run_lane(
    lane: str,
    command: Sequence[str],
    *,
    data_root: Path | None,
    hash_seed: str | None,
    log_path: Path,
    detail: str = "",
) -> dict[str, Any]:
    """Run one lane and bind it to the environment it really used."""

    env = build_environment(data_root, hash_seed)
    probe = run_probe(env)
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        list(command),
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ended = datetime.now(timezone.utc)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        (completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8"
    )
    parsed = parse_pytest_summary(completed.stdout or "")
    return {
        "lane": lane,
        "detail": detail,
        "command": list(command),
        "interpreter": sys.executable,
        "cwd": str(REPO_ROOT),
        "requested_data_root": str(data_root) if data_root else None,
        "requested_hash_seed": hash_seed,
        "effective_environment": probe,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "exit_code": completed.returncode,
        "log_path": str(log_path),
        "log_sha256": sha256_file(log_path),
        **parsed,
        "mounted_lane_established": bool(
            probe.get("family_b_skip_gate_open")
        ),
        "environment_capture_is_allowlisted_not_full": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument(
        "--family-b-only",
        action="store_true",
        help="Run only the two Family B modules in both configurations "
        "instead of the whole suite (minutes rather than tens of minutes).",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    logs = out_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    family_b = [
        "tests/test_tamu_official_1998_2009_rejection_integrity.py",
        "tests/test_tamu_official_gamebook_union_1998_rejection_complete.py",
    ]
    pytest_base = [sys.executable, "-B", "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider"]

    lanes: list[dict[str, Any]] = []

    lanes.append(
        run_lane(
            "FAMILY_B_MOUNTED_EXPLICIT_ENV",
            [*pytest_base, *family_b],
            data_root=Path(args.data_root),
            hash_seed="0",
            log_path=logs / "FAMILY_B_MOUNTED_EXPLICIT_ENV.log",
            detail="AGGIE_ANALYTICS_DATA_ROOT explicitly set. This is the "
            "configuration in which the Family B skip gate actually opens.",
        )
    )
    lanes.append(
        run_lane(
            "FAMILY_B_ENV_UNSET_CONTROL",
            [*pytest_base, *family_b],
            data_root=None,
            hash_seed="0",
            log_path=logs / "FAMILY_B_ENV_UNSET_CONTROL.log",
            detail="Control: the same tests with the mount variable unset. "
            "They skip and the command exits 0, which is why directory "
            "presence alone cannot establish that the lane ran.",
        )
    )

    if not args.family_b_only:
        lanes.append(
            run_lane(
                "FULL_SUITE_MOUNTED_EXPLICIT_ENV",
                [*pytest_base, "tests"],
                data_root=Path(args.data_root),
                hash_seed="0",
                log_path=logs / "FULL_SUITE_MOUNTED_EXPLICIT_ENV.log",
                detail="Genuinely mounted full suite: the mount variable is "
                "explicitly set, so data-root-gated modules execute.",
            )
        )
        lanes.append(
            run_lane(
                "FULL_SUITE_GENUINELY_UNMOUNTED",
                [*pytest_base, "tests"],
                data_root=None,
                hash_seed="0",
                log_path=logs / "FULL_SUITE_GENUINELY_UNMOUNTED.log",
                detail="Genuinely unmounted full suite: the mount variable is "
                "absent, reproducing the hosted-runner shape.",
            )
        )

    mounted = [lane for lane in lanes if lane["mounted_lane_established"]]
    result = {
        "artifact_type": "CYCLE35_MOUNTED_LANE_RECEIPT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
        ).stdout.strip(),
        "lanes": lanes,
        "lane_count": len(lanes),
        "mounted_lanes_established": len(mounted),
        "mounted_lanes_passing": [
            lane["lane"] for lane in mounted if lane["exit_code"] == 0
        ],
        "mounted_lanes_failing": [
            lane["lane"] for lane in mounted if lane["exit_code"] != 0
        ],
        "canonical_mounted_acceptance": (
            "FAIL"
            if any(lane["exit_code"] != 0 for lane in mounted)
            else ("PASS" if mounted else "NOT_ESTABLISHED")
        ),
        "directory_presence_does_not_establish_execution": True,
        "inherited_failures_are_not_concealed": True,
        "environment_capture_is_allowlisted_not_full": True,
        "secrets_never_captured": True,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "CYCLE35_MOUNTED_LANE_RECEIPT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "head": result["head"],
                "canonical_mounted_acceptance": result["canonical_mounted_acceptance"],
                "lanes": [
                    {
                        "lane": lane["lane"],
                        "gate_open": lane["mounted_lane_established"],
                        "exit_code": lane["exit_code"],
                        "summary": lane["summary_line"],
                        "skips_listed": lane["skips_listed"],
                    }
                    for lane in lanes
                ],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
