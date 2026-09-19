"""Mounted full unittest with verified runtime source/data binding.

Does not hardcode a predecessor SHA. Does not rematerialize lake gates.
A restored tracked file is recorded as mutation, not purity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\VALIDATION_RUNTIME"
)
GATE = REPO / "artifacts" / "validation" / "mounted_acceptance_gate.json"
DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def source_digest(repo: Path) -> str:
    listing = git("ls-files", "-z")
    hasher = hashlib.sha256()
    for rel in listing.split("\0"):
        if not rel:
            continue
        path = repo / rel
        if path.is_file():
            hasher.update(rel.encode("utf-8"))
            hasher.update(b"\0")
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def import_locations() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    code = (
        "import aggie_analytics, aggie_analytics.cycle33.query, "
        "aggie_analytics.data.tamu_official_1998_2009_rejection_integrity as m; "
        "print(aggie_analytics.__file__); "
        "print(aggie_analytics.cycle33.query.__file__); "
        "print(m.__file__)"
    )
    text = subprocess.check_output(
        [sys.executable, "-c", code],
        cwd=REPO,
        env=env,
        text=True,
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "aggie_analytics": lines[0] if lines else "",
        "cycle33.query": lines[1] if len(lines) > 1 else "",
        "rejection_integrity": lines[2] if len(lines) > 2 else "",
    }


def main() -> int:
    pass_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    out = Path(os.environ.get("CYCLE33_MOUNTED_OUT", str(DEFAULT_OUT)))
    out.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = git("status", "--porcelain")
    detached = branch == "HEAD"
    isolated_detached_used = detached and not bool(dirty)
    digest = source_digest(REPO)
    imports = import_locations()
    gate_before = sha256_file(GATE)
    gate_bytes = GATE.read_bytes() if GATE.is_file() else None
    lake_gate = (
        REPO / "artifacts" / "data_lake" / "tamu_official_1998_2009_rejection_integrity_gate.json"
    )
    lake_before = sha256_file(lake_gate)
    env = os.environ.copy()
    env["AGGIE_ANALYTICS_DATA_ROOT"] = str(DATA_ROOT)
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONHASHSEED"] = env.get("PYTHONHASHSEED") or "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    log = out / f"mounted_full_{head[:8]}_pass{pass_id}.txt"
    started = utc_now()
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=REPO,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    ended = utc_now()
    gate_after = sha256_file(GATE)
    lake_after = sha256_file(lake_gate)
    restored = False
    if gate_bytes is not None and GATE.is_file() and GATE.read_bytes() != gate_bytes:
        GATE.write_bytes(gate_bytes)
        restored = True
    text = log.read_text(encoding="utf-8", errors="replace")
    receipt = {
        "artifact_type": "CYCLE33_MOUNTED_FULL_UNITTEST",
        "binding": {
            "git_head": head,
            "abbrev_ref": branch,
            "detached_head": detached,
            "dirty": bool(dirty),
            "dirty_paths": [line for line in dirty.splitlines() if line][:40],
            "source_tree_digest_sha256": digest,
            "interpreter": sys.executable,
            "python_version": sys.version,
            "pythonpath": env["PYTHONPATH"],
            "hashseed": env["PYTHONHASHSEED"],
            "data_root": str(DATA_ROOT),
            "imported_modules": imports,
            "checkout_src_on_pythonpath": True,
            "hardcoded_predecessor_head_forbidden": True,
        },
        "pass": pass_id,
        "started_utc": started,
        "ended_utc": ended,
        "exit_code": proc.returncode,
        "log": str(log),
        "log_sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
        "gate_sha256_before": gate_before,
        "gate_sha256_after_run": gate_after,
        "lake_rejection_gate_sha256_before": lake_before,
        "lake_rejection_gate_sha256_after_run": lake_after,
        "tracked_gate_restored": restored,
        "restored_file_is_not_purity": restored,
        "distinct_from_mounted_acceptance_replay": True,
        "historical_receipts_not_relabeled": [
            "VALIDATION_FB365260/mounted_full_287e8cc7_pass1.json",
            "VALIDATION_FB365260/mounted_full_287e8cc7_pass2.json",
        ],
        "da8a2e86_is_historical_only": True,
        "suite": "mounted_full_unittest",
        "isolated_detached_preferred": True,
        "isolated_detached_used": isolated_detached_used,
        "isolated_reason": (
            "isolated_detached_used is true only for a clean detached HEAD checkout. "
            "A dirty branch worktree is not an isolated submitted-head suite. "
            "A restored tracked file is mutation, not purity."
            if isolated_detached_used
            else (
                "This run is not a clean detached submitted-head checkout "
                f"(abbrev_ref={branch!r}, dirty={bool(dirty)})."
            )
        ),
        "unmounted_package_and_reference_are_distinct_suites": True,
    }
    (out / f"mounted_full_{head[:8]}_pass{pass_id}.json").write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
