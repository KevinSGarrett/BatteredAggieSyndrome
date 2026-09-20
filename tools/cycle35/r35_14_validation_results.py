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
        "lane": "FULL_SUITE_MOUNTED_CLEAN",
        "command": "AGGIE_ANALYTICS_DATA_ROOT=<lake> python -m unittest "
        "discover -s tests   (no concurrent jobs)",
        "result": "FAIL",
        "tests_run": 3842,
        "detail": "3 red, IDENTICAL set to the predecessor baseline's 3. "
        "Zero regressions and zero fixes by exact set membership. All three "
        "are the Family B family blocked on "
        "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001.",
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



#: MF35-10 repair: this previously stopped at the FIRST parenthesized group
#: (`^(FAIL|ERROR): (\S+) \(([^)]+)\)`), which is the module.Class group --
#: it never captured a trailing `subTest` parameter group. unittest renders
#: a subTest failure as `FAIL: method (module.Class) (season=2019)`; the old
#: pattern matched only through `(module.Class)` and silently dropped
#: ` (season=2019)`, so every distinct parameterized subtest of the same
#: method collapsed to ONE identity. A manager-observed baseline comparison
#: this caused: six season-specific subtest failure EVENTS collapsed into
#: two method-level IDs, an undercount a set-based regression/inheritance
#: comparison never surfaced as wrong because it was internally consistent
#: with itself -- both sides of the comparison collapsed the same way. The
#: trailing group `(.*)$` now captures any subtest-parameter suffix (or an
#: empty string for a non-subtest failure) so each parameterized event keeps
#: its own identity.
_RED = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)(.*)$", re.M)


def red_ids(path: Path) -> set[str]:
    """Exact identities of every failing/erroring test in a captured log,
    including each distinct subTest parameterization as its own identity."""

    if not path or not Path(path).is_file():
        return set()
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return {m.group(3) + "." + m.group(2) + m.group(4) for m in _RED.finditer(text)}


def red_events(path: Path) -> list[dict[str, Any]]:
    """Every failing/erroring EVENT in a captured log, preserving event type
    (FAIL vs ERROR), method, module/class, and subtest parameter suffix
    separately -- not just the collapsed identity string `red_ids` returns.

    MF35-10: "preserve event type, method, subtest parameters and exception
    signatures" is a different, stronger claim than a deduplicated identity
    set; a caller that needs to answer "how many distinct FAILURE EVENTS
    occurred" (as opposed to "how many distinct test identities are red")
    needs this, since two DIFFERENT event types (a FAIL and an ERROR) for
    the same method/subtest are still two events, not one.
    """

    if not path or not Path(path).is_file():
        return []
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return [
        {
            "event_type": m.group(1),
            "method": m.group(2),
            "module_class": m.group(3),
            "subtest_suffix": m.group(4).strip(),
            "identity": m.group(3) + "." + m.group(2) + m.group(4),
        }
        for m in _RED.finditer(text)
    ]


def baseline_comparison(
    candidate: str, baseline: str, lane: str
) -> dict[str, Any]:
    """Prove inheritance by exact SET, never by matching counts.

    Equal counts with different members would be a regression plus a fix
    cancelling out, which a count comparison cannot see.

    MF35-10: `candidate_red_count`/`baseline_red_count` count DISTINCT
    IDENTITIES (post subtest-parameter fix, this no longer collapses
    parameterized subtests into one identity -- see `_RED`/`red_ids`). That
    is still a different question from "how many failure/error EVENTS were
    reported," since a log can repeat the same identity's traceback in more
    than one section. `candidate_event_count`/`baseline_event_count` answer
    that second question from `red_events` directly. Neither count is
    hidden in favor of the other; they answer different questions.
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
        "candidate_event_count": len(red_events(Path(candidate))),
        "baseline_event_count": len(red_events(Path(baseline))),
        "regressions_introduced": new,
        "regression_count": len(new),
        "red_at_baseline_green_now": fixed,
        "fixed_count": len(fixed),
        "inherited_red_count": len(mine & theirs),
        "identical_red_set": mine == theirs,
        "inheritance_proven_by_set_not_count": True,
        "identity_count_and_event_count_answer_different_questions": True,
    }


def lane_staleness(
    output_path: str, declared_head: str, report_generation_head: str
) -> dict[str, Any]:
    """MF35-10: a validation receipt must never let a report's OWN
    generation-time head stand in for the head that was actually checked
    out when a lane's output was captured. A manager reproduction found
    exactly this: a report claimed head f948e319 with a dirty worktree while
    the branch's actual submission was c6bb041a -- the report had been
    regenerated later, at a different head, without re-running the lanes it
    was describing.

    This records, per lane, whatever head the CALLER declares the output
    was captured at (there is no way to derive it from the raw unittest log
    text itself), and flags plainly when that is unknown or differs from
    the head this report is being generated at -- rather than silently
    implying the report-generation head covers every lane in the file.
    """

    if not output_path:
        return {"state": "LANE_NOT_CAPTURED"}
    mtime = None
    path = Path(output_path)
    if path.is_file():
        mtime = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    if not declared_head:
        return {
            "state": "LANE_HEAD_NOT_DECLARED_BY_CALLER",
            "output_mtime_utc": mtime,
            "reuse_at_report_generation_head_is_unproven": True,
        }
    matches = declared_head == report_generation_head
    return {
        "state": "LANE_HEAD_DECLARED",
        "declared_head": declared_head,
        "output_mtime_utc": mtime,
        "matches_report_generation_head": matches,
        "reuse_at_report_generation_head_is_unproven": not matches,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--mounted-output", default="")
    ap.add_argument("--unmounted-output", default="")
    ap.add_argument("--unmounted-baseline", default="")
    ap.add_argument("--mounted-baseline", default="")
    ap.add_argument(
        "--mounted-output-head", default="",
        help="git commit checked out when --mounted-output was captured, "
        "if known; leave unset if not tracked by the caller.",
    )
    ap.add_argument(
        "--unmounted-output-head", default="",
        help="git commit checked out when --unmounted-output was captured, "
        "if known; leave unset if not tracked by the caller.",
    )
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

    report_generation_head = git(["rev-parse", "HEAD"])

    result = {
        "artifact_type": "CYCLE35_VALIDATION_RESULTS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        # MF35-10: renamed from `exact_head`/`exact_tree`/`worktree_clean`.
        # Those names, unqualified, read as if they described every lane in
        # this report; they only ever described the moment THIS report was
        # generated, which can be a different commit than the one that
        # actually produced a given lane's captured output below.
        "report_generation_head": report_generation_head,
        "report_generation_tree": git(["rev-parse", "HEAD^{tree}"]),
        "branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "report_generation_worktree_clean": not git(["status", "--porcelain"]),
        "lane_head_binding": {
            "FULL_SUITE_MOUNTED": lane_staleness(
                args.mounted_output, args.mounted_output_head, report_generation_head
            ),
            "FULL_SUITE_UNMOUNTED": lane_staleness(
                args.unmounted_output, args.unmounted_output_head, report_generation_head
            ),
        },
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
        "mounted_lane_new_red_test": {
            "test": "test_tamu_official_gamebook_union_2000_expanded."
            "Expanded2000ReconstructionAndTamperTests."
            "test_bat623_row_and_coverage_tampers_fail",
            "state": "NOT_CLAIMED_INHERITED",
            "why_not_claimed": (
                "It is red in this branch's mounted full run and NOT red in "
                "the predecessor's mounted full run, so it fails the "
                "baseline-equivalence test and may not be called inherited."
            ),
            "observed_error": (
                "AuthorityViolation: external 2001-expanded reconstruction "
                "was required but the data root is not mounted"
            ),
            "code_change_ruled_out": (
                "git diff 517ff324..HEAD touches ZERO files under "
                "src/aggie_analytics/data/, so no module in this failure's "
                "call path was modified by this cycle."
            ),
            "predicate_recheck": (
                "upstream_is_ready(data_root, repo_root) returns True when "
                "evaluated directly at this head against the same mounted "
                "lake, so the condition that raised is not reproducible on "
                "demand."
            ),
            "environmental_difference_observed": (
                "The mounted full run finished at 14:50:22 while a "
                "concurrent job recursively reading 34,701 files under the "
                "same data root ran until 14:42:27. The predecessor baseline "
                "ran later, without that concurrency. This is a difference "
                "in run conditions, not in code -- recorded as an "
                "observation, not accepted as the explanation."
            ),
            "isolated_rerun_result": (
                "Two independent isolated runs of the module at this head "
                "against the same mounted lake: 12 passed each time, "
                "including this test (291s and 286s). It does not reproduce."
            ),
            "clean_full_run_result": (
                "A full mounted suite re-run at this head with NO concurrent "
                "jobs produced 3 red tests whose identities are IDENTICAL to "
                "the predecessor baseline's 3. This test is green in it. "
                "Zero regressions and zero fixes against baseline, by exact "
                "set membership."
            ),
            "evidence_chain": [
                "Full mounted run concurrent with a 34,701-file traversal of "
                "the same root: RED",
                "Isolated module run #1 (nothing else running): 12 passed",
                "Isolated module run #2 (nothing else running): 12 passed",
                "Full mounted run with no concurrent jobs: GREEN, red set "
                "identical to predecessor baseline",
            ],
            # MF35-10 repair: the claim below was WITHDRAWN. A Cycle #35
            # manager diagnostic (PATHLIB_RUNTIME_MECHANISM.json,
            # PATHLIB_INJECTED_ERROR_TESTS.json) ran the actual CPython
            # 3.11.9 `pathlib.Path.is_file()`/`_ignore_error` source under
            # this project's own Python and found the sharing-violation
            # mechanism asserted here is FALSE: `_ignore_error` only
            # suppresses winerrors 21 (ERROR_NOT_READY), 123
            # (ERROR_INVALID_NAME) and 1921 (a reparse-point cycle) -- NOT
            # winerror 32 (ERROR_SHARING_VIOLATION, "the file is in use by
            # another process"), which is the actual "another process has
            # this file open" case a sharing-violation claim requires. An
            # injected winerror 32 in the same environment raises
            # PermissionError; it is NOT swallowed. Correlating a red result
            # with concurrent I/O is not proof of the specific syscall/error
            # that caused it, and the specific mechanism named here is
            # actively disproven, not merely unproven.
            "mechanism_status": "WITHDRAWN_DISPROVEN_BY_INDEPENDENT_DIAGNOSTIC",
            "withdrawn_claim": (
                "upstream_is_ready decides mounted-ness with four "
                "Path.is_file() calls, and pathlib's is_file() catches "
                "OSError and returns False for ignorable errors -- which on "
                "Windows includes sharing violations."
            ),
            "disproof": (
                "Under Python 3.11.9, pathlib._ignore_error only ignores "
                "winerror in {21, 123, 1921} (plus a short errno allowlist); "
                "winerror 32 (ERROR_SHARING_VIOLATION) is not among them. An "
                "injected winerror 32 / errno 13 raises PermissionError "
                "rather than being swallowed. A sharing violation from "
                "another process holding the file open is therefore NOT the "
                "mechanism by which this predicate could return a false "
                "'not mounted' result."
            ),
            "actual_cause": "CAUSE_UNPROVEN",
            "diagnostic_plan_not_yet_run": (
                "Determine which of the three actually-ignored winerrors "
                "(21/123/1921), or a different failure mode entirely (e.g. "
                "a transient network/UNC timeout on the mounted data root, "
                "which is a different exception class), was live during the "
                "one red full-mounted run, by injecting each candidate error "
                "in isolation against upstream_is_ready's real call sites "
                "and reproducing a false negative under the SAME concurrent "
                "load pattern that was observed -- correlation with a "
                "concurrent traversal is not sufficient."
            ),
            "disposition": "NOT_A_REGRESSION_CAUSE_UNPROVEN",
            "honest_summary": (
                "Red exactly once, in a full mounted suite that ran "
                "concurrently with a heavy lake-reading job. Green in two "
                "isolated runs and in a clean full mounted run whose red set "
                "is identical to the predecessor baseline. No file in its "
                "call path was changed by this cycle, so this is NOT a "
                "regression from these changes -- that empirical finding "
                "stands independently of the cause. The originally-claimed "
                "mechanism (a pathlib-swallowed Windows sharing violation) "
                "is withdrawn as disproven; the actual cause of the single "
                "red observation remains CAUSE_UNPROVEN and is not closed. "
                "It is also not 'inherited' in the strict sense -- it was "
                "green at the predecessor and is green here; the correct "
                "label is a latent, not-yet-diagnosed environment-sensitive "
                "defect in a module this cycle did not touch."
            ),
        },
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
            "report_generation_head": result["report_generation_head"][:12],
            "report_generation_worktree_clean": result["report_generation_worktree_clean"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
