"""R36-15: run every validation lane and propagate its result honestly.

Each lane records the exact command, the exit code, the timing and the
parsed test identities. A lane that did not run is ``NOT_RUN``; a lane that
cannot run is ``BLOCKED`` with a reason. Neither is ever reported as a pass,
and no lane's result is inferred from another's.

Two honesty problems the Cycle #35 review raised are addressed directly:

* **"Unmounted" was not proved.** Unsetting the data-root environment
  variable does not exclude a module that hardcodes the private path. This
  runner points the variable at an empty directory AND censuses every source
  file that contains the private root literal, so the lane's actual reach is
  measured rather than asserted.
* **An unchanged failure set is not a pass.** Failed, errored and skipped
  test identities are captured per lane so a baseline comparison is about
  identities, not counts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

sys.dont_write_bytecode = True
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from aggie_analytics.workspace.paths import (  # noqa: E402
    WorkspaceError,
    allocate_run_workspace,
)
from aggie_analytics import atomic_io as _bas_atomic

# MF37-04 repair. The parser and the lane classifier used to live here as two
# regexes and an `exit_code == 0` test. They now come from the shared harness,
# which keeps the full dotted identity of every failure (so two same-named
# methods in different modules stay two failures) and refuses to call a lane
# that executed no unskipped test a pass.
from aggie_analytics.validation.lane_harness import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_RUN,
    PASS,
    UNSATISFIED,
    parse_unittest as _parse_unittest,
    run_lane as _run_lane,
)

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

PRIVATE_ROOT_LITERAL = r"C:\BatteredAggieSyndrome.data"
DATA_ROOT_ENV = "AGGIE_ANALYTICS_DATA_ROOT"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def parse_unittest(output: str) -> dict[str, Any]:
    """Preserved name, corrected behaviour (MF37-04).

    Callers and prior receipts refer to ``parse_unittest``; the identity
    keys it returns are now full dotted paths that no longer collapse two
    same-named methods, and the skip/import/subtest sets are kept whole.
    """

    return _parse_unittest(output)


def run_lane(
    lane: str,
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 5400,
    log_dir: Path,
    parse: bool = True,
    kind: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Preserved signature, corrected classification (MF37-04).

    A lane whose output is parsed as unittest is a ``TEST`` lane; one that
    runs a validator and is not parsed is a ``CHECK`` lane. The distinction
    matters because only a ``TEST`` lane can be unsatisfied by executing no
    assertion: a ``TEST`` lane that exits 0 without executing an unskipped
    case is now ``UNSATISFIED_NO_EXECUTED_TEST`` rather than ``PASS``. The
    command, its exit code and its raw log are recorded exactly as before.
    """

    return _run_lane(
        lane,
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        log_dir=log_dir,
        parse=parse,
        kind=kind or ("TEST" if parse else "CHECK"),
        note=note,
    )


def private_root_census(repo: Path) -> dict[str, Any]:
    """Which source files reach the private root regardless of the environment.

    This is the honest limit of any "unmounted" claim: a module carrying the
    literal path does not care what the environment variable says.
    """

    hits: list[dict[str, Any]] = []
    for path in sorted((repo / "src").rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if PRIVATE_ROOT_LITERAL in text:
            hits.append(
                {
                    "path": str(path.relative_to(repo)),
                    "occurrences": text.count(PRIVATE_ROOT_LITERAL),
                }
            )
    return {
        "literal": PRIVATE_ROOT_LITERAL,
        "source_files_containing_it": len(hits),
        "total_occurrences": sum(row["occurrences"] for row in hits),
        "files": hits[:60],
        "what_this_means": (
            "An unmounted lane that only unsets "
            f"{DATA_ROOT_ENV} does not exclude these modules. The lane below "
            "points the variable at an empty directory and reports this census "
            "beside its result, so the claim is bounded by what was measured."
        ),
    }


def build(out_dir: Path, repo: Path, full: bool) -> dict[str, Any]:
    log_dir = out_dir / "validation_logs"
    lanes: list[dict[str, Any]] = []
    python = sys.executable
    tests_dir = repo / "tests"

    lanes.append(
        run_lane(
            "local_strict_repository",
            [python, "tools/validate_repository.py", "--repo-root", ".", "--strict"],
            cwd=repo,
            log_dir=log_dir,
            parse=False,
            note="Manifest, secrets, forbidden artifacts, governance ids, holds.",
        )
    )
    lanes.append(
        run_lane(
            "execution_focus_path_classification",
            [python, "tools/validate_execution_focus.py", "--repo-root", "."],
            cwd=repo,
            env={"AGGIE_ANALYTICS_ENFORCE_PATH_CLASSIFICATION": "1"},
            log_dir=log_dir,
            parse=False,
            note=(
                "Full-history local run. Hosted pull-request checks enforce "
                "changed-path classification only for commits unique to the "
                "branch, so the local finding set is a superset."
            ),
        )
    )
    lanes.append(
        run_lane(
            "cycle36_focused_regressions",
            [
                python,
                "-m",
                "unittest",
                "-v",
                "test_cycle36_source_scoped_season",
                "test_cycle36_membership_lineage",
                "test_cycle36_venue_vintage",
                "test_cycle36_kernel_reference",
                "test_cycle36_c01_boundary",
                "test_cycle36_scoring_guards",
                "test_cycle36_packet_guards",
                "test_cycle36_availability_identity",
                "test_cycle36_release_builder",
                "test_cycle36_jsonl_io",
                "test_cycle36_independent_season_reader",
                "test_cycle36_all22_section_trace",
                "test_cycle36_mirror_discrepancy",
                "test_cycle36_career_corpus",
            ],
            cwd=tests_dir,
            log_dir=log_dir,
            note="Every regression this cycle added, run together.",
        )
    )
    lanes.append(
        run_lane(
            "deterministic_hash_seed_0",
            [
                python,
                "-m",
                "unittest",
                "test_cycle36_source_scoped_season",
                "test_cycle36_membership_lineage",
                "test_cycle36_kernel_reference",
            ],
            cwd=tests_dir,
            env={"PYTHONHASHSEED": "0"},
            log_dir=log_dir,
            note="Serial; shares no external file with another lane.",
        )
    )
    lanes.append(
        run_lane(
            "deterministic_hash_seed_12345",
            [
                python,
                "-m",
                "unittest",
                "test_cycle36_source_scoped_season",
                "test_cycle36_membership_lineage",
                "test_cycle36_kernel_reference",
            ],
            cwd=tests_dir,
            env={"PYTHONHASHSEED": "12345"},
            log_dir=log_dir,
            note="Serial; compared against seed 0 for identical identities.",
        )
    )
    lanes.append(
        run_lane(
            "warnings_as_errors",
            [
                python,
                "-W",
                "error",
                "-m",
                "unittest",
                "test_cycle36_source_scoped_season",
                "test_cycle36_membership_lineage",
                "test_cycle36_venue_vintage",
                "test_cycle36_kernel_reference",
                "test_cycle36_c01_boundary",
                "test_cycle36_scoring_guards",
                "test_cycle36_packet_guards",
                "test_cycle36_availability_identity",
                "test_cycle36_release_builder",
                "test_cycle36_jsonl_io",
                "test_cycle36_independent_season_reader",
                "test_cycle36_all22_section_trace",
                "test_cycle36_mirror_discrepancy",
                "test_cycle36_career_corpus",
            ],
            cwd=tests_dir,
            log_dir=log_dir,
            note="Serial.",
        )
    )

    # The isolated-successor lane and the installed-wheel lane are separate
    # from the repository suite: one builds a Family B successor in a root
    # that must not already exist, the other installs a released wheel in a
    # throwaway virtualenv and runs ITS validators. Both are re-executed here
    # so the lane table carries their receipts rather than pointing at an
    # earlier run.
    # The successor's lake paths are content-addressed --
    # features/<name>/sha256/<64 hex>/<file> -- so the destination has to stay
    # inside the Windows 260-character limit or the copy fails and the lane
    # reports a qualification failure that belongs to the path, not to the
    # successor. That constraint used to be met by hardcoding the drive-root
    # directory "C:\basc36lane" and calling
    # ``shutil.rmtree(..., ignore_errors=True)`` on it before every run: two
    # concurrent runs deleted each other's workspace, an unrelated directory
    # occupying that name would have been destroyed silently, and a failed
    # cleanup was discarded.
    #
    # The path budget is now measured and enforced (a run namespace under the
    # declared .validation root fits with room to spare), the workspace is
    # unique per run, and cleanup refuses anything this run does not own.
    workspace = allocate_run_workspace("c36_15", category="validation")
    isolated_root = workspace.root / "iso"
    seed_contract_path = (
        workspace.layout.root("data")
        / "ops"
        / "cycle37"
        / "CYCLE35_FAMILY_B_SEED_CONTRACT.json"
    )
    lanes.append(
        run_lane(
            "isolated_successor_mounted",
            [
                python,
                "tools/cycle36/c36_12_family_b_composed.py",
                "--out-dir",
                str(out_dir / "lane_family_b"),
                "--isolated-root",
                str(isolated_root),
                "--seed-contract",
                str(seed_contract_path),
            ],
            cwd=repo,
            log_dir=log_dir,
            parse=False,
            timeout=1800,
            note=(
                "Composed Family B successor in a fresh isolated root. "
                "Canonical files are not touched and the default stays LEGACY."
            ),
        )
    )
    # Cleanup is a recorded outcome, not a silent side effect. A lane that
    # failed keeps its workspace so the failure can be inspected; a lane that
    # passed releases it, and the receipt says which happened either way.
    family_b_passed = lanes[-1].get("exit_code") == 0
    if family_b_passed:
        try:
            workspace_receipt = workspace.release()
        except WorkspaceError as error:
            workspace_receipt = {
                "state": "RELEASE_REFUSED",
                "root": str(workspace.root),
                "error": str(error),
            }
    else:
        workspace_receipt = {
            "state": "RETAINED_FOR_INVESTIGATION",
            "root": str(workspace.root),
            "reason": "the composed Family B lane did not exit cleanly",
        }
    workspace_receipt["workspace"] = workspace.describe()
    workspace_receipt["seed_contract"] = str(seed_contract_path)
    lanes.append(
        run_lane(
            "installed_wheel_cli_schema_smoke",
            [
                python,
                "tools/cycle36/c36_13_c01_qualification.py",
                "--out-dir",
                str(out_dir / "lane_c01"),
            ],
            cwd=repo,
            log_dir=log_dir,
            parse=False,
            timeout=1800,
            note=(
                "Released C01 wheel installed in a throwaway virtualenv with "
                "no index access; its own validators executed on synthetic "
                "payloads."
            ),
        )
    )

    with tempfile.TemporaryDirectory(prefix="c36_unmounted_") as empty_root:
        lanes.append(
            run_lane(
                "true_unmounted_cycle36_regressions",
                [
                    python,
                    "-m",
                    "unittest",
                    "test_cycle36_source_scoped_season",
                    "test_cycle36_membership_lineage",
                    "test_cycle36_venue_vintage",
                    "test_cycle36_kernel_reference",
                    "test_cycle36_c01_boundary",
                    "test_cycle36_scoring_guards",
                    "test_cycle36_packet_guards",
                    "test_cycle36_availability_identity",
                    "test_cycle36_release_builder",
                    "test_cycle36_jsonl_io",
                    "test_cycle36_independent_season_reader",
                    "test_cycle36_all22_section_trace",
                    "test_cycle36_mirror_discrepancy",
                    "test_cycle36_career_corpus",
                ],
                cwd=tests_dir,
                env={DATA_ROOT_ENV: empty_root},
                log_dir=log_dir,
                note=(
                    f"{DATA_ROOT_ENV} points at an empty directory. See the "
                    "private-root census for what this does and does not prove."
                ),
            )
        )

    if full:
        lanes.append(
            run_lane(
                "canonical_mounted_full_suite",
                [python, "-m", "unittest", "discover", "-s", ".", "-v"],
                cwd=tests_dir,
                log_dir=log_dir,
                timeout=5400,
                note="Whole suite with the canonical private data root mounted.",
            )
        )
        with tempfile.TemporaryDirectory(prefix="c36_unmounted_full_") as empty_root:
            lanes.append(
                run_lane(
                    "true_unmounted_full_suite",
                    [python, "-m", "unittest", "discover", "-s", ".", "-v"],
                    cwd=tests_dir,
                    env={DATA_ROOT_ENV: empty_root},
                    log_dir=log_dir,
                    timeout=5400,
                    note=(
                        "Whole suite with the data-root variable pointed at an "
                        "empty directory."
                    ),
                )
            )
    else:
        for lane in ("canonical_mounted_full_suite", "true_unmounted_full_suite"):
            lanes.append(
                {
                    "lane": lane,
                    "result": NOT_RUN,
                    "reason": "--full was not requested for this invocation",
                    "command": None,
                    "exit_code": None,
                }
            )

    seed_lanes = {
        lane["lane"]: lane.get("unittest", {}).get("failed_or_errored_identities")
        for lane in lanes
        if lane["lane"].startswith("deterministic_hash_seed")
    }
    seeds = list(seed_lanes.values())
    artifact = {
        "artifact_type": "CYCLE36_VALIDATION_RESULTS",
        "generated_at_utc": utc_now(),
        "source": {
            "repo": str(repo),
            "head": git(repo, "rev-parse", "HEAD"),
            "tree": git(repo, "rev-parse", "HEAD^{tree}"),
            "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_entries": len(
                [
                    line
                    for line in git(repo, "status", "--porcelain=v1").splitlines()
                    if line.strip()
                ]
            ),
        },
        "interpreter": sys.version,
        "lanes": lanes,
        "workspace_lifecycle": workspace_receipt,
        "lane_results": {lane["lane"]: lane["result"] for lane in lanes},
        "private_root_census": private_root_census(repo),
        "hash_seed_identities_agree": (
            len(seeds) == 2 and seeds[0] == seeds[1]
        ),
        "lanes_not_run": [lane["lane"] for lane in lanes if lane["result"] == NOT_RUN],
        "lanes_blocked": [lane["lane"] for lane in lanes if lane["result"] == BLOCKED],
        "lanes_failed": [lane["lane"] for lane in lanes if lane["result"] == FAIL],
        # MF37-04: a lane that exited zero without executing an unskipped test
        # is neither a pass nor an inherited failure. It gets its own set so it
        # cannot disappear into "not failed".
        "lanes_unsatisfied_no_executed_test": [
            lane["lane"] for lane in lanes if lane["result"] == UNSATISFIED
        ],
        "lanes_satisfying_acceptance": [
            lane["lane"] for lane in lanes if lane.get("satisfies_acceptance")
        ],
        "lane_unittest_reconciliation_problems": {
            lane["lane"]: lane["unittest_reconciliation"]["problems"]
            for lane in lanes
            if lane.get("unittest_reconciliation")
            and not lane["unittest_reconciliation"]["consistent"]
        },
        "aggregate_software_state": (
            FAIL
            if any(lane["result"] in (FAIL, BLOCKED) for lane in lanes)
            else UNSATISFIED
            if any(lane["result"] == UNSATISFIED for lane in lanes)
            else NOT_RUN
            if not lanes or all(lane["result"] == NOT_RUN for lane in lanes)
            else "PARTIAL"
            if any(lane["result"] == NOT_RUN for lane in lanes)
            else PASS
        ),
        "no_lane_result_inferred_from_another": True,
        "unchanged_failures_are_not_a_pass": (
            "Failed, errored and skipped identities are recorded per lane so a "
            "baseline comparison is about which tests, not how many."
        ),
        "scientific_validity_not_implied": (
            "A green lane means the commands exited zero. It is not a claim "
            "that the data are scientifically correct or independently "
            "accepted."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_VALIDATION_RESULTS.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run the whole test suite mounted and unmounted (slow).",
    )
    args = parser.parse_args()
    artifact = build(args.out_dir, args.repo.resolve(), args.full)
    print(
        json.dumps(
            {
                "head": artifact["source"]["head"],
                "lane_results": artifact["lane_results"],
                "lanes_failed": artifact["lanes_failed"],
                "lanes_not_run": artifact["lanes_not_run"],
                "hash_seed_identities_agree": artifact["hash_seed_identities_agree"],
                "private_root_literal_files": artifact["private_root_census"][
                    "source_files_containing_it"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
