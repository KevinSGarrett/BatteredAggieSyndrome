"""R35-16: assemble the Cycle #35 follow-up's evidence-bound validation
packet successor.

Cycle #35 manager follow-up (20260920T224700Z), Section 7: "The existing
authoritative CYCLE35_VALIDATION_RESULTS.json ... still binds f948e319 ...
Preserve it as historical evidence, but publish a clearly linked successor
packet." and "Bind the reported 3,670-pass / 269-skip / 498-subtest run to
its exact command, runner, interpreter, cwd, source imports, effective
data-root variables, resolved mount, dirty-state digest, source/data
identities, raw log, times and exit."

This reads the raw logs this cycle actually produced (never re-derives a
result from memory) and binds each lane to its real command, exit code and
log path. The old 3,670/269/498 full-suite claim from before this cycle's
fixes could not be located at the paths this session checked either (the
manager's own review reported the same); it is recorded here as
UNLOCATED_NOT_BOUND rather than silently treated as equivalent to, or
overwritten by, the fresh receipts below -- a fresh run at a different
head is not evidence for or against an unlocated older one.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T224700Z_r35_validation_packet"
)
LOG_DIR = RUN_DIR / "logs"
OLD_VALIDATION_RESULTS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output\CYCLE35_VALIDATION_RESULTS.json"
)
DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")


def git(args: list[str]) -> str:
    out = subprocess.run(
        ["git"] + args, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def log_tail(path: Path, lines: int = 12) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]


def exit_code_of(path: Path) -> int | None:
    for line in reversed(log_tail(path, 5)):
        m = re.match(r"^EXIT:(-?\d+)$", line.strip())
        if m:
            return int(m.group(1))
    return None


def summarize_pytest_tail(path: Path) -> str:
    for line in reversed(log_tail(path, 8)):
        line = line.strip()
        if re.search(r"passed|failed|error", line) and "%" not in line:
            return line
    return ""


def lane(
    lane_id: str,
    *,
    command: str,
    log_name: str,
    detail: str = "",
    result_override: str | None = None,
) -> dict[str, Any]:
    log_path = LOG_DIR / log_name
    exit_code = exit_code_of(log_path)
    result = result_override
    if result is None:
        result = "PASS" if exit_code == 0 else ("NOT_RUN" if exit_code is None else "FAIL")
    return {
        "lane": lane_id,
        "command": command,
        "log_path": str(log_path),
        "log_sha256": sha256_file(log_path),
        "log_present": log_path.is_file(),
        "exit_code": exit_code,
        "result": result,
        "detail": detail or summarize_pytest_tail(log_path),
    }


def build() -> dict[str, Any]:
    head = git(["rev-parse", "HEAD"])
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    dirty = git(["status", "--porcelain"])
    reviewed_head = "49fb52a837cbf213ce3f47002c2e181f854cdd02"

    lanes = [
        lane(
            "STRICT_REPOSITORY_VALIDATION",
            command="python tools/validate_repository.py --repo-root . --strict",
            log_name="STRICT_REPOSITORY_VALIDATION.log",
        ),
        lane(
            "CHANGED_FILE_LINT",
            command="python -m ruff check src/aggie_analytics/cycle35/ "
            "src/aggie_analytics/cycle33/ tools/cycle35/ tests/test_cycle35_*.py",
            log_name="CHANGED_FILE_LINT.log",
        ),
        lane(
            "DIFF_CHECK",
            command=f"git diff --check {reviewed_head}..HEAD",
            log_name="DIFF_CHECK.log",
        ),
        lane(
            "WARNINGS_AS_ERRORS_HASHSEED_0",
            command="PYTHONHASHSEED=0 python -B -W error -m pytest -q -p no:asyncio "
            "tests/test_cycle33_*.py tests/test_cycle34_*.py tests/test_cycle35_*.py",
            log_name="WARNINGS_AS_ERRORS_HASHSEED_0.log",
            detail="-p no:asyncio added: an unrelated pytest-asyncio plugin "
            "PytestDeprecationWarning aborted the run under -W error before any "
            "test executed; none of these tests are async. Scope is broader than "
            "the original lane's unnamed 11-module subset (every cycle33/34/35 "
            "test file, not a curated list the original run's own raw log was "
            "not locatable to reconstruct exactly).",
        ),
        lane(
            "WARNINGS_AS_ERRORS_HASHSEED_1",
            command="PYTHONHASHSEED=1 python -B -W error -m pytest -q -p no:asyncio "
            "tests/test_cycle33_*.py tests/test_cycle34_*.py tests/test_cycle35_*.py",
            log_name="WARNINGS_AS_ERRORS_HASHSEED_1.log",
        ),
        lane(
            "WARNINGS_AS_ERRORS_HASHSEED_12345",
            command="PYTHONHASHSEED=12345 python -B -W error -m pytest -q -p no:asyncio "
            "tests/test_cycle33_*.py tests/test_cycle34_*.py tests/test_cycle35_*.py",
            log_name="WARNINGS_AS_ERRORS_HASHSEED_12345.log",
        ),
        lane(
            "PRIVATE_DATA_MOUNTED",
            command="python -m pytest -q tests/test_protected_replay_dry_run.py",
            log_name="PRIVATE_DATA_MOUNTED.log",
            detail="Real mounted data root, no override.",
        ),
        lane(
            "PRIVATE_DATA_EMPTY_ROOT",
            command="AGGIE_ANALYTICS_DATA_ROOT=<empty dir> "
            "python -m pytest -q tests/test_protected_replay_dry_run.py",
            log_name="PRIVATE_DATA_EMPTY_ROOT.log",
            detail="Reproduces the hosted-runner shape.",
        ),
        lane(
            "PRIVATE_DATA_PARTIAL_ROOT",
            command="",
            log_name="PRIVATE_DATA_PARTIAL_ROOT.log",
            detail="Not reproduced this cycle: the original lane's exact "
            "manifest-plus-one-payload fixture state was not reconstructed. "
            "Genuine gap, not a claimed pass.",
            result_override="NOT_RUN",
        ),
        lane(
            "ISOLATED_NON_EDITABLE_WHEEL",
            command="python -m pip wheel . --no-deps; fresh venv; "
            "pip install --no-deps <wheel>; import with no src on sys.path; "
            "apply_migrations builds the release schema",
            log_name="WHEEL_IMPORT_SCHEMA.log",
            detail="aggie_analytics_engine-0.25.0.dev25-py3-none-any.whl sha256 "
            "26c4451136996f7610d8e9bcf43e0047720ba18fd4831e652cb6ad970bc8db7a "
            "(rebuilt at this head; differs from the prior evidence's wheel "
            "digest because the source content differs). 16 tables created "
            "(15 release tables + schema_migration), all cycle35 modules "
            "import from site-packages only.",
        ),
        lane(
            "FULL_SUITE_MOUNTED",
            command="python -m unittest discover -s tests -q",
            log_name="FULL_SUITE_MOUNTED.log",
            detail="Real mounted data root, no override.",
        ),
        lane(
            "DETERMINISTIC_RELEASE_REPLAY",
            command="",
            log_name="DETERMINISTIC_RELEASE_REPLAY.log",
            detail="Not independently re-executed at this exact lane's "
            "invocation this cycle. coaching_release's builder was exercised "
            "extensively via real-data runs and its own test suite "
            "(test_cycle35_r35_03_coaching_release.py and others) this "
            "session, but not via this specific twice-run identity-comparison "
            "lane. Genuine gap, not a claimed pass.",
            result_override="NOT_RUN",
        ),
    ]

    old_receipt_present = OLD_VALIDATION_RESULTS.is_file()

    return {
        "artifact_type": "CYCLE35_VALIDATION_RESULTS_SUCCESSOR",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "supersedes_note": (
            "Preserves ops/cycle35/runs/20260920T172801Z/implementation_output/"
            "CYCLE35_VALIDATION_RESULTS.json as historical evidence (it still "
            "binds an earlier head, f948e319, and records mounted/unmounted "
            "failures from that point). This artifact is the current, "
            "evidence-derived successor at the final candidate head below. A "
            "code flag saying notes are stale is not this successor; this is."
        ),
        "old_validation_results_path": str(OLD_VALIDATION_RESULTS),
        "old_validation_results_present": old_receipt_present,
        "old_validation_results_sha256": sha256_file(OLD_VALIDATION_RESULTS),
        "reported_3670_pass_269_skip_498_subtest_run": {
            "state": "UNLOCATED_NOT_BOUND",
            "reason": (
                "This cycle's manager review reported the same: 'The author's "
                "new 1,398-row database and 3,670-pass full-run log were not "
                "located in the inspected authoritative output paths and were "
                "not independently rerun.' A repeated search this session "
                "(ops/**/3670*, raw-log greps) did not locate the original raw "
                "log either. Its reported totals are not declared false; they "
                "remain unbound to a command/cwd/exit/log and are not treated "
                "as equivalent to, superseded by, or contradicted by the fresh "
                "FULL_SUITE_MOUNTED receipt below, which was run at a "
                "different head with different code."
            ),
        },
        "final_candidate_head": {
            "commit": head,
            "branch": branch,
            "reviewed_head": reviewed_head,
            "commits_since_reviewed_head": len(
                git(["log", "--format=%H", f"{reviewed_head}..{head}"]).splitlines()
            ),
        },
        "runner": {
            "interpreter": sys.executable,
            "python_version": sys.version,
            "cwd": str(REPO_ROOT),
            "pythonpath_src": str(REPO_ROOT / "src"),
            "data_root": str(DATA_ROOT),
            "data_root_resolved_mount": DATA_ROOT.is_dir(),
        },
        "dirty_state_digest": {
            "porcelain_entries": dirty.splitlines() if dirty else [],
            "entry_count": len(dirty.splitlines()) if dirty else 0,
            "note": "configs/omitted_protected_tune_contract.json, if present, "
            "is a fixture test_protected_split_exposure.py writes during a "
            "full-suite run and is not part of this cycle's own changes.",
        },
        "lanes": lanes,
        "lane_count": len(lanes),
        "lanes_not_run": [l["lane"] for l in lanes if l["result"] == "NOT_RUN"],
        "lanes_failed": [l["lane"] for l in lanes if l["result"] == "FAIL"],
        "canonical_vs_isolated_successor": (
            "FULL_SUITE_MOUNTED reports the canonical mounted lane's real "
            "current red set, if any, separately from any isolated-successor "
            "artifact (e.g. R35-10's Family B candidate, built under an "
            "isolated data root and never substituted for canonical mounted "
            "acceptance)."
        ),
        "green_tests_establish": (
            "No failures observed in the tests actually run, not the absence "
            "of every regression or scientific defect."
        ),
        "pit_admitted": False,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = build()
    (out_dir / "CYCLE35_VALIDATION_RESULTS_SUCCESSOR.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "head": result["final_candidate_head"]["commit"],
            "lane_count": result["lane_count"],
            "lanes_not_run": result["lanes_not_run"],
            "lanes_failed": result["lanes_failed"],
            "lane_results": {l["lane"]: l["result"] for l in result["lanes"]},
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
