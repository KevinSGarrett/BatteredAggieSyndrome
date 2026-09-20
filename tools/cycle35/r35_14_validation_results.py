"""R35-14: record exactly what ran, in which lane, and what it proved.

The rule this file exists to obey: no claim may exceed the tested scope. A
finite suite cannot establish "zero regressions across the entire dataset",
so the artifact records commands, lanes, counts, skips and reasons, and says
plainly which dimensions remain FAIL.

Lane results are parsed from real captured output rather than typed in, so a
lane that did not finish cannot silently become a pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_RAN = re.compile(r"^Ran (\d+) tests? in ([0-9.]+)s", re.M)
_RESULT = re.compile(r"^(OK|FAILED)(?:\s*\((.*)\))?\s*$", re.M)


def parse_unittest_output(text: str) -> dict[str, Any]:
    ran = _RAN.search(text or "")
    result = _RESULT.search(text or "")
    detail = (result.group(2) or "") if result else ""
    counts: dict[str, int] = {}
    for key in ("failures", "errors", "skipped", "expected failures"):
        found = re.search(key.replace(" ", r"\s") + r"=(\d+)", detail)
        if found:
            counts[key.replace(" ", "_")] = int(found.group(1))
    return {
        "tests_run": int(ran.group(1)) if ran else None,
        "runtime_seconds": float(ran.group(2)) if ran else None,
        "result": result.group(1) if result else "DID_NOT_COMPLETE",
        "detail": detail,
        "counts": counts,
        "completed": bool(result),
    }


def read_lane(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"output_path": str(path), "completed": False,
                "result": "OUTPUT_NOT_PRESENT"}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"output_path": str(path), **parse_unittest_output(text)}


def git(args: list[str]) -> str:
    out = subprocess.run(
        ["git"] + args, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )
    return out.stdout.strip()


#: Lanes executed interactively, with their observed results. Each entry
#: names the exact command so it can be re-run.
DIRECT_LANES: tuple[dict[str, Any], ...] = (
    {
        "lane": "STRICT_REPOSITORY_VALIDATION",
        "command": "python tools/validate_repository.py --repo-root . --strict",
        "result": "PASS",
        "detail": "repository structure, manifests, governance IDs, secret "
        "scan and forbidden-artifact scan",
    },
    {
        "lane": "CHANGED_FILE_LINT",
        "command": "python -m ruff check src/aggie_analytics/cycle35/ "
        "src/aggie_analytics/cycle33/ tools/cycle35/ tests/test_cycle35_*.py",
        "result": "PASS",
        "detail": "All checks passed after fixing 4 F401 unused imports.",
    },
    {
        "lane": "DIFF_CHECK",
        "command": "git diff --check 517ff324..HEAD",
        "result": "PASS",
        "detail": "no whitespace or conflict-marker errors",
    },
    {
        "lane": "WARNINGS_AS_ERRORS_HASHSEED_0",
        "command": "PYTHONHASHSEED=0 python -W error -m unittest "
        "<11 cycle33/34/35 modules>",
        "result": "OK",
        "tests_run": 259,
        "detail": "mounted data root",
    },
    {
        "lane": "WARNINGS_AS_ERRORS_HASHSEED_1",
        "command": "PYTHONHASHSEED=1 python -W error -m unittest "
        "<11 cycle33/34/35 modules>",
        "result": "OK",
        "tests_run": 259,
    },
    {
        "lane": "WARNINGS_AS_ERRORS_HASHSEED_12345",
        "command": "PYTHONHASHSEED=12345 python -W error -m unittest "
        "<11 cycle33/34/35 modules>",
        "result": "OK",
        "tests_run": 259,
    },
    {
        "lane": "PRIVATE_DATA_MOUNTED",
        "command": "python -m pytest tests/test_protected_replay_dry_run.py",
        "result": "PASS",
        "tests_run": 27,
        "detail": "rebuild mandatory and matching",
    },
    {
        "lane": "PRIVATE_DATA_EMPTY_ROOT",
        "command": "AGGIE_ANALYTICS_DATA_ROOT=<empty dir> python -m pytest "
        "tests/test_protected_replay_dry_run.py",
        "result": "PASS",
        "tests_run": 26,
        "skipped": 1,
        "detail": "reproduces the hosted-runner shape; the one skip names the "
        "observed state DATA_ROOT_PRESENT_BUT_EMPTY",
    },
    {
        "lane": "PRIVATE_DATA_PARTIAL_ROOT",
        "command": "AGGIE_ANALYTICS_DATA_ROOT=<manifest + 1 payload> python -m "
        "pytest tests/test_protected_replay_dry_run.py",
        "result": "PASS",
        "tests_run": 26,
        "skipped": 1,
        "detail": "state PAYLOADS_PARTIALLY_PRESENT",
    },
    {
        "lane": "ISOLATED_NON_EDITABLE_WHEEL",
        "command": "python -m pip wheel . --no-deps; fresh venv; pip install "
        "--no-deps <wheel>; import and build schema with no src on sys.path",
        "result": "PASS",
        "detail": "aggie_analytics_engine-0.25.0.dev25-py3-none-any.whl "
        "sha256 a26d796779494966b788a54bc6293232aa55d3ce7820f399b25c027583193ceb; "
        "all cycle35 modules import and the 15-table release schema is created "
        "from the installed wheel alone",
    },
    {
        "lane": "HOSTED_CI_PR_691",
        "command": "gh pr checks 691",
        "result": "PASS",
        "detail": "12 of 12 checks pass, including core-validation "
        "(windows-latest, 3.12) -- the exact check that failed at PR #690's "
        "head. codex-review and no-api-attestation both pass in ~8s, "
        "confirming no paid review API was invoked; no "
        "paid-scientific-review-ready label was applied.",
    },
    {
        "lane": "FULL_SUITE_MOUNTED_RED_TESTS",
        "command": "grep '^(FAIL|ERROR): ' mounted_full_run.txt",
        "result": "FAIL",
        "detail": "All 4 red tests in the mounted lane belong to the Family B "
        "family: rejection-integrity test_gate_reconstructs (ERROR) and "
        "test_reconstruction_does_not_read_the_working_checkout_commit (FAIL), "
        "gamebook_union_1998_rejection_complete setUpClass (ERROR), and "
        "gamebook_union_2000_expanded test_bat623_row_and_coverage_tampers_fail "
        "(ERROR).",
    },
    {
        "lane": "FAMILY_B_MOUNTED",
        "command": "AGGIE_ANALYTICS_DATA_ROOT=<lake> python -m pytest "
        "tests/test_tamu_official_1998_2009_rejection_integrity.py "
        "tests/test_tamu_official_gamebook_union_1998_rejection_complete.py",
        "result": "FAIL",
        "detail": "2 failed, 5 passed, 2 errors — independently reproduced, "
        "unchanged by this cycle, and blocked on "
        "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001. NOT green-by-exception.",
    },
    {
        "lane": "DETERMINISTIC_RELEASE_REPLAY",
        "command": "r35_03_build_coaching_release.py run twice into separate "
        "release paths",
        "result": "PASS",
        "detail": "12 tables, all row identities identical across independent "
        "builds; database file bytes differ (sqlite page layout), which is "
        "why row identity rather than file hash is the scientific test",
    },
)

PREEXISTING_OBSERVATIONS: tuple[dict[str, Any], ...] = (
    {
        "observation": "`python.exe -m unittest: error: the following "
        "arguments are required: --database` is printed to stderr when "
        "test_cycle33_national_staff is imported.",
        "status": "PRE_EXISTING",
        "verified_how": "Reproduced identically at the Cycle #34 predecessor "
        "head in the cycle34-repair worktree. Not introduced by this cycle.",
    },
)



_RED = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)", re.M)


def red_ids(path: Path) -> set[str]:
    """Exact identities of every failing/erroring test in a captured log."""

    if not path or not Path(path).is_file():
        return set()
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return {m.group(3) + "." + m.group(2) for m in _RED.finditer(text)}


def baseline_comparison(
    candidate: str, baseline: str, lane: str
) -> dict[str, Any]:
    """Prove inheritance by exact SET, never by matching counts.

    Equal counts with different members would be a regression plus a fix
    cancelling out, which a count comparison cannot see.
    """

    if not candidate or not baseline:
        return {"lane": lane, "state": "NOT_COMPARED"}
    mine = red_ids(Path(candidate))
    theirs = red_ids(Path(baseline))
    if not theirs:
        return {"lane": lane, "state": "BASELINE_NOT_CAPTURED"}
    new = sorted(mine - theirs)
    fixed = sorted(theirs - mine)
    return {
        "lane": lane,
        "state": "COMPARED",
        "candidate_red_count": len(mine),
        "baseline_red_count": len(theirs),
        "regressions_introduced": new,
        "regression_count": len(new),
        "red_at_baseline_green_now": fixed,
        "fixed_count": len(fixed),
        "inherited_red_count": len(mine & theirs),
        "identical_red_set": mine == theirs,
        "inheritance_proven_by_set_not_count": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--mounted-output", default="")
    ap.add_argument("--unmounted-output", default="")
    ap.add_argument("--unmounted-baseline", default="")
    ap.add_argument("--mounted-baseline", default="")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    full_lanes = {
        "FULL_SUITE_MOUNTED": read_lane(Path(args.mounted_output))
        if args.mounted_output
        else {"result": "NOT_CAPTURED"},
        "FULL_SUITE_UNMOUNTED": read_lane(Path(args.unmounted_output))
        if args.unmounted_output
        else {"result": "NOT_CAPTURED"},
    }

    result = {
        "artifact_type": "CYCLE35_VALIDATION_RESULTS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "exact_head": git(["rev-parse", "HEAD"]),
        "exact_tree": git(["rev-parse", "HEAD^{tree}"]),
        "branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "worktree_clean": not git(["status", "--porcelain"]),
        "python_version": subprocess.run(
            ["python", "--version"], capture_output=True, text=True, check=False
        ).stdout.strip(),
        "data_root": r"C:\BatteredAggieSyndrome.data",
        "direct_lanes": list(DIRECT_LANES),
        "direct_lane_count": len(DIRECT_LANES),
        "full_suite_lanes": full_lanes,
        "pre_existing_observations": list(PREEXISTING_OBSERVATIONS),
        "baseline_equivalence": [
            baseline_comparison(
                args.unmounted_output, args.unmounted_baseline, "UNMOUNTED"
            ),
            baseline_comparison(
                args.mounted_output, args.mounted_baseline, "MOUNTED"
            ),
        ],
        "failing_dimensions": [
            {
                "dimension": "FAMILY_B_CANONICAL_MOUNTED",
                "state": "FAIL",
                "reason": "The committed rejection-integrity gate's "
                "ledger_identity does not equal the independent "
                "reconstruction. A complete isolated candidate successor is "
                "prepared; activating canonical routing requires "
                "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001.",
            },
            {
                "dimension": "BAT637_CODE_SIDECAR_PIN",
                "state": "FAIL",
                "reason": "A stale hardcoded pin in one module, deliberately "
                "not patched by copying the live gate hash into it.",
            },
        ],
        "claims_not_made": [
            "No claim of zero regressions across the entire real dataset. A "
            "finite suite cannot establish that.",
            "Repeated runs of the same tests are NOT summed as unique "
            "coverage; each lane's count is reported separately with its "
            "purpose.",
            "Green results in one lane do not cancel a red result in another; "
            "the Family B mounted failure stands on its own.",
            "Hosted CI green on PR #691 covers the repository suite on the "
            "hosted runners. It does NOT cover the mounted private-data lane, "
            "which the hosted runner cannot execute, so Family B remains FAIL "
            "regardless of the green hosted result.",
        ],
        "inherited_failure_baseline": {
            "family_b": "Reproduced at the Cycle #34 predecessor head with "
            "identical failure reasons before any Cycle #35 change, so it is "
            "demonstrably inherited rather than newly introduced.",
        },
    }
    (out_dir / "CYCLE35_VALIDATION_RESULTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "direct_lanes": len(DIRECT_LANES),
            "full_suite": {k: v.get("result") for k, v in full_lanes.items()},
            "full_suite_counts": {
                k: {"tests": v.get("tests_run"), "counts": v.get("counts")}
                for k, v in full_lanes.items()
            },
            "failing_dimensions": [
                d["dimension"] for d in result["failing_dimensions"]
            ],
            "baseline_equivalence": [
                {k: v for k, v in row.items()
                 if k in ("lane","state","regression_count","fixed_count",
                          "inherited_red_count","candidate_red_count",
                          "baseline_red_count")}
                for row in result["baseline_equivalence"]
            ],
            "head": result["exact_head"][:12],
            "clean": result["worktree_clean"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
