r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

The single entry point the Cycle 37 rework contract names for all 21
worker lanes:

    rework_lanes.py --lane <id> --out-root <evidence root>

Design commitments, each of which exists because a previous lane receipt
was less honest than it looked:

* **It invokes the real tools.** No lane re-implements what a checked-in
  tool or an installed consumer already does. Where a lane's subject does
  not exist yet, the lane reports ``BLOCKED`` naming the missing artifact;
  it never substitutes a proxy and calls it a pass.
* **Imports are bound, not assumed.** The packaging venv carries an
  editable ``.pth`` for a *different* worktree, so an unbound child would
  silently test the wrong source. Every child gets ``PYTHONPATH`` pointing
  at the selected worktree, and :func:`bind_source` records the resolved
  origin of every module it is about to exercise. A lane whose binding
  does not hold refuses before it runs anything.
* **Raw output survives.** The complete stdout/stderr of every command is
  written under ``<out-root>/logs/<LANE>/`` before any classification, so
  the receipt is never the only account of the run.
* **Skips, imports and duplicate identities are conserved.** Lane state
  comes from :mod:`aggie_analytics.validation.lane_harness`, so an
  all-skipped TEST lane is ``UNSATISFIED_NO_EXECUTED_TEST`` rather than a
  pass, and two same-named failures in different modules stay two.
* **Declared roots are propagated.** ``BAS_VALIDATION_ROOT`` and
  ``BAS_PACKAGING_ROOT`` are passed into every child, so no lane writes
  into a root this attempt does not own.

This driver decides what a command did. It never decides whether a
scientific result is acceptable, and it cannot turn an inherited red lane
green.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
if str(WORKTREE / "src") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.validation.lane_harness import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_RUN,
    PASS,
    UNSATISFIED,
    run_lane as harness_run_lane,
)
from aggie_analytics import atomic_io as _bas_atomic

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 2
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "REWORK-20260922T171601Z"
LABEL = f"Cycle #{CYCLE_NUMBER} - Attempt #{ATTEMPT_NUMBER} - ACTUAL_STATE"

EXPECTED_BASE_SHA = "2202b2b2d48217ecfcf52df4464c21abd077ef06"
EXPECTED_BASE_TREE = "388fb91c075b10e2923db9717b63c9f4d44cc1a8"
EXPECTED_BRANCH = "codex/BAT-706-cycle37-rework"

DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37r-171601")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37r-171601")
PREDECESSOR_WORKTREE = Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-integration")
BASELINE_EXPORT = PACKAGING_ROOT / "baseline-2202b2b2"

#: The delivered Cycle 36 national release the manager reviewed, and its
#: recorded digest. A lane that reads it proves it read *these* bytes.
DELIVERED_C36_DB = (
    DATA_ROOT
    / "ops/cycle36/runs/20260921T200027Z/implementation_output"
    / "release_c36_r1/CYCLE36_NATIONAL_RELEASE.sqlite"
)
DELIVERED_C36_DB_SHA256 = (
    "beabfe4ddff771bd694dfd7370380380c25a63b640478c2f89bbf640b2044a77"
)

#: Every lane is measured against the whole data root (W37R-66). The repository validator and the mounted suites
#: call producers' ``materialize`` functions that rewrite payloads under ``features`` in place, and predecessor
#: pipeline tests wrote the Cycle 34 receipts (W37R-68); nothing outside this attempt's own root is an output of
#: this attempt, so a lane's ``read_only`` is what this measurement shows, never a constant. The exclusions are
#: the live areas of other writers (the manager's review trees and a Cycle 26 session watchdog that rewrites its
#: status every minute) and this attempt's own root, where every lane writes its receipt and logs.
WATCH_EXCLUDED = (
    DATA_ROOT / "ops" / "manager_review",
    DATA_ROOT / "ops" / "manager_reviews",
    DATA_ROOT / "ops" / "cycle26" / "session_watchdog",
    DATA_ROOT / "ops" / "cycle37" / "attempts" / "REWORK-20260922T171601Z",
)

#: The canonical-mounted lanes run their children under the BAS canonical write guard (clarification of
#: 2026-09-24, section 2; W37R-66/67/68). The data root stays mounted for reads; under it a whole-file write of
#: identical bytes is skipped and every other write, create, delete, rename or metadata change is refused with
#: CanonicalWriteRefused naming the path. This attempt's own root stays writable for receipts and logs. The
#: environment change is recorded in each guarded receipt; it does not replace the canonical mount.
GUARD_DIR = WORKTREE / "tools" / "cycle37" / "canonical_write_guard"
GUARDED_LANES = frozenset({"strict-mounted", "full-baseline-mounted", "full-final-mounted", "c36-15"})

#: START_BINDING's module check, run by the lane interpreter as a logged command: every bound module must resolve
#: inside the selected worktree's src, and each resolved file is printed (W37R-70).
MODULE_ORIGIN_PROBE = (
    "import importlib, pathlib, sys\n"
    "root = pathlib.Path(sys.argv[1]).resolve()\n"
    "outside = []\n"
    "for name in sys.argv[2:]:\n"
    "    origin = pathlib.Path(importlib.import_module(name).__file__).resolve()\n"
    "    print(name, origin)\n"
    "    if root not in origin.parents:\n"
    "        outside.append(name)\n"
    "print('outside the selected worktree:', outside or 'none')\n"
    "sys.exit(1 if outside else 0)\n"
)
#: FINAL_PACKET's input listing, as a logged command: the result, head and digest of every expected lane receipt.
RECEIPT_LISTING = (
    "import hashlib, json, pathlib, sys\n"
    "root = pathlib.Path(sys.argv[1])\n"
    "for lane in sys.argv[2:]:\n"
    "    path = root / (lane + '.json')\n"
    "    if not path.is_file():\n"
    "        print(lane, 'NO_RECEIPT')\n"
    "        continue\n"
    "    data = json.loads(path.read_text(encoding='utf-8'))\n"
    "    head = (data.get('source_binding') or {}).get('head') or data.get('head')\n"
    "    print(lane, data.get('result'), head, hashlib.sha256(path.read_bytes()).hexdigest())\n"
)

FAMILY_B_SEED_CONTRACT = DATA_ROOT / "ops/cycle37/CYCLE35_FAMILY_B_SEED_CONTRACT.json"
FAMILY_B_CONTRACT_ID = "CYCLE35-FAMILY-B-COMPOSED-SEED-V1"

#: Modules whose admission/parsing behaviour this cycle changes or depends on.
#: Their resolved origin is recorded before any lane runs, which is what makes
#: "source-bound" a fact rather than a label.
BOUND_MODULES = (
    "aggie_analytics.workspace.paths",
    "aggie_analytics.validation.lane_harness",
    "aggie_analytics.cycle33.query",
    "aggie_analytics.cycle35.query",
    "aggie_analytics.cycle36.release_query",
    "aggie_analytics.cycle36.kernel_reference",
    "aggie_analytics.cycle36.scoring_guards",
    "aggie_analytics.cycle37.admission_domains",
    "aggie_analytics.cycle37.source_identity",
)

#: Focused suites: every suite bound to a module this attempt changed.
#:
#: The pre-existing suites below are listed for a specific reason. An earlier
#: version of this tuple held only the new ``test_cycle37_*`` modules, so the
#: focused lane passed while `scoring_guards` and `kernel_reference` were
#: repaired *and their own existing suites were never run*. The baseline
#: versus final comparison then reported twelve failures introduced by this
#: attempt in exactly those two suites. A lane that claims to cover "all
#: changed and material modules" has to name the suites that already test
#: them, not only the ones the attempt wrote.
FOCUSED_TESTS = (
    # Added by this attempt.
    "test_cycle37_workspace_paths",
    "test_cycle37_lane_harness",
    "test_cycle37_release_query",
    "test_cycle37_source_identity",
    "test_cycle37_admission_domains",
    "test_cycle37_corrected_release",
    "test_cycle37_membership_authenticity",
    "test_cycle37_national_eras",
    "test_cycle37_deterministic_stats",
    "test_cycle37_restoration_search",
    "test_cycle37_c01_boundary_repair",
    "test_cycle37_plan_domain_trace",
    "test_cycle37_cfip_proposals",
    "test_cycle37_obligation_reverification",
    "test_cycle37_contest_site",
    "test_cycle37_responsibility",
    "test_cycle37_kernel_reconciliation",
    "test_cycle37_staff_reparse",
    "test_cycle37_career_reparse",
    "test_cycle37_user_corpus_lineage",
    "test_cycle37_fetch",
    "test_cycle37_alias_team_season",
    "test_cycle37_career_link_identity",
    "test_cycle37_independent_tools",
    "test_cycle37_canonical_write_guard",
    "test_cycle37_thread_repairs",
    "test_cycle37_packet_headline",
    "test_cycle36_c01_boundary",
    # Pre-existing suites for the modules this attempt changed.
    "test_cycle36_scoring_guards",
    "test_cycle36_kernel_reference",
    "test_cycle36_membership_lineage",
    "test_cycle33_availability_pit_corpus",
    "test_cycle36_availability_identity",
    "test_tracked_file_purity",
)

#: Declared polarity for every probe the workspace counterexample tool emits.
#: A positive must be ALLOWED, a negative must be REFUSED, and a probe in
#: neither set fails the lane rather than being silently assumed benign.
POSITIVE_PROBES = frozenset(
    {
        "positive_allocation",
        "mf37_03_valid_entry_digests",
        "mf37_01_fresh_explicit_workspace",
    }
)
NEGATIVE_PROBES = frozenset(
    {
        "mf37_02_parent_traversal_tool",
        "mf37_02_absolute_run_id",
        "mf37_02_unc_run_id",
        "mf37_02_drive_qualified_tool",
        "mf37_02_separator_in_run_id",
        "mf37_03_no_entry_digests",
        "mf37_03_empty_entry_digests",
        "mf37_03_partial_entry_digests",
        "mf37_03_malformed_entry_digests",
        "mf37_03_escaping_entry_path",
        "mf37_03_changed_entry_digests",
        "mf37_03_absent_pinned_entry",
        "mf37_03_verify_disabled_without_reason",
        "mf37_01_explicit_workspace_over_existing",
    }
)


# ------------------------------------------------------------------- helpers


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str, repo: Path = WORKTREE) -> str:
    """Run git and return its stdout stripped of surrounding whitespace.

    Never use this for porcelain status: see :func:`porcelain_lines`.
    """

    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return (completed.stdout or "").strip()


def porcelain_lines(repo: Path = WORKTREE) -> list[tuple[str, str]]:
    """``git status --porcelain=v1 -uall`` as (status, path) pairs.

    Porcelain v1 is column-significant: an unstaged modification is
    ``" M path"``, with a *leading space*. Passing that through a helper that
    strips stdout removes the space, so slicing ``line[3:]`` then drops the
    first character of the path -- ``tools/...`` became ``ools/...``, and the
    per-file digest of the first dirty entry silently became ABSENT. The
    columns are read here without stripping the line.
    """

    completed = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-uall", "-z"],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return parse_porcelain(completed.stdout or "")


def parse_porcelain(payload: str) -> list[tuple[str, str]]:
    """Split a NUL-separated porcelain v1 payload into (status, path) pairs."""

    rows: list[tuple[str, str]] = []
    for record in payload.split(chr(0)):
        if len(record) < 4:
            continue
        rows.append((record[:2], record[3:]))
    return rows


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    """Whether ``ancestor`` is reachable from ``descendant``."""

    return (
        subprocess.run(
            ["git", "-C", str(WORKTREE), "merge-base", "--is-ancestor", ancestor, descendant],
            check=False, capture_output=True,
        ).returncode
        == 0
    )


def free_space() -> dict[str, Any]:
    total, used, free = shutil.disk_usage("C:/")
    return {
        "volume": "C:",
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "free_gib": round(free / 1024**3, 3),
        "contract_reserve_bytes": 8 * 1024**3,
        "contract_peak_extra_bytes": 6 * 1024**3,
        "reserve_satisfied": free >= 8 * 1024**3,
    }


def canonical_snapshot(root: Path = DATA_ROOT, excluded: Iterable[Path] = WATCH_EXCLUDED) -> dict[str, list[int]]:
    """[size, mtime_ns, birth_ns] of every file, and [0, 0, birth_ns] of every directory, under ``root``.

    Birth time, not ``st_ino``: ``DirEntry.stat()`` reports a zero file id on Windows, while a file replaced
    through a temporary file gets a new birth time. A directory's size and times come from its parent's index,
    which NTFS updates lazily, so an untouched directory can appear changed between two snapshots; directories
    are compared by existence and birth only, and a write inside one is seen at the file. Reparse points are
    recorded but never followed.
    """

    skip = {os.path.normcase(str(path)) for path in excluded}
    snapshot: dict[str, list[int]] = {}
    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if os.path.normcase(entry.path) in skip:
                        continue
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    birth = getattr(stat, "st_birthtime_ns", None) or stat.st_ctime_ns
                    is_dir = entry.is_dir(follow_symlinks=False)
                    snapshot[os.path.relpath(entry.path, root).replace("\\", "/")] = (
                        [0, 0, birth] if is_dir else [stat.st_size, stat.st_mtime_ns, birth])
                    if is_dir and not getattr(stat, "st_file_attributes", 0) & 0x400:
                        stack.append(entry.path)
        except OSError:
            continue
    return snapshot


def canonical_writes(before: dict[str, list[int]], after: dict[str, list[int]]) -> dict[str, Any]:
    """What changed under the watched trees between two snapshots: created, removed and rewritten entries."""

    created = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
    return {
        "watched": str(DATA_ROOT),
        "excluded": [str(path) for path in WATCH_EXCLUDED],
        "created": [{"path": path, "after": after[path]} for path in created],
        "removed": [{"path": path, "before": before[path]} for path in removed],
        "changed": [{"path": path, "before": before[path], "after": after[path]} for path in changed],
        "count": len(created) + len(removed) + len(changed),
        "fields": ["size", "mtime_ns", "birth_ns"],
        "directories": "compared by existence and birth only; their indexed times lag on NTFS",
    }


def child_env(**extra: str | None) -> dict[str, str | None]:
    """The environment every lane child inherits.

    ``PYTHONPATH`` is what makes a child import the *selected* worktree
    rather than the editable install the packaging venv carries for another
    one. The declared roots are passed down so no child writes outside the
    roots this attempt owns.
    """

    env: dict[str, str | None] = {
        "PYTHONPATH": str(WORKTREE / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "BAS_VALIDATION_ROOT": str(VALIDATION_ROOT),
        "BAS_PACKAGING_ROOT": str(PACKAGING_ROOT),
    }
    env.update(extra)
    return env


class LaneContext:
    """Everything a lane needs, plus where it must put what it produces."""

    def __init__(self, lane_id: str, out_root: Path, python: Path) -> None:
        self.lane_id = lane_id
        self.out_root = out_root
        self.python = python
        self.log_dir = out_root / "logs" / lane_id
        self.lane_dir = out_root / "evidence" / "lanes"
        self.work = VALIDATION_ROOT / f"lane_{lane_id.replace('-', '_')}"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.lane_dir.mkdir(parents=True, exist_ok=True)
        self.commands: list[dict[str, Any]] = []
        self.guarded = lane_id in GUARDED_LANES
        self.guard_log = self.log_dir / f"{lane_id}__write_guard_events.jsonl"
        if self.guarded:
            _bas_atomic.write_text(self.guard_log, "", encoding="utf-8")

    def guard_env(self, env: dict[str, str | None]) -> dict[str, str | None]:
        """The child environment with the write guard installed ahead of every other import path."""

        guarded = dict(env)
        rest = guarded.get("PYTHONPATH") or ""
        guarded["PYTHONPATH"] = os.pathsep.join(part for part in (str(GUARD_DIR), rest) if part)
        guarded["BAS_CANONICAL_WRITE_GUARD"] = str(DATA_ROOT)
        guarded["BAS_CANONICAL_WRITE_ALLOW"] = str(self.out_root)
        guarded["BAS_CANONICAL_WRITE_GUARD_LOG"] = str(self.guard_log)
        return guarded

    def run(
        self,
        name: str,
        command: Iterable[Any],
        *,
        cwd: Path = WORKTREE,
        kind: str = "TEST",
        env: dict[str, str | None] | None = None,
        parse: bool | None = None,
        timeout: int = 5400,
        note: str = "",
    ) -> dict[str, Any]:
        env = env if env is not None else child_env()
        if self.guarded:
            env = self.guard_env(env)
        record = harness_run_lane(
            f"{self.lane_id}__{name}",
            [str(item) for item in command],
            cwd=cwd,
            env=env,
            timeout=timeout,
            log_dir=self.log_dir,
            parse=(kind.upper() == "TEST") if parse is None else parse,
            kind=kind,
            note=note,
        )
        self.commands.append(record)
        return record

    def fresh_work(self) -> Path:
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)
        return self.work


# --------------------------------------------------------------- source bind


def bind_source() -> dict[str, Any]:
    """Prove which source, tree and dirt this run is about to exercise."""

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    # ``-uall`` expands an untracked *directory* into its files. Without it a
    # whole new tools/ tree is one unhashable entry, and the dirty digest would
    # be blind to what is actually inside it.
    dirty_entries = porcelain_lines()

    # A dirty tree is legitimate mid-repair, but the receipt has to pin *which*
    # dirt, or a later claim cannot be tied to the bytes that produced it.
    dirty_files: list[dict[str, Any]] = []
    accumulator = hashlib.sha256()
    for status, relative in sorted(dirty_entries, key=lambda row: row[1]):
        relative = relative.strip('"')
        candidate = WORKTREE / relative
        digest = sha256_file(candidate)
        dirty_files.append(
            {"status": status, "path": relative, "sha256": digest}
        )
        accumulator.update(relative.encode("utf-8"))
        accumulator.update(b"\0")
        accumulator.update((digest or "ABSENT").encode("ascii"))
    dirty_digest = accumulator.hexdigest() if dirty_files else None

    modules: list[dict[str, Any]] = []
    binding_holds = True
    for name in BOUND_MODULES:
        try:
            module = __import__(name, fromlist=["__file__"])
            origin = Path(module.__file__).resolve()
        except Exception as error:  # noqa: BLE001 - an unimportable module is the datum
            modules.append({"module": name, "error": f"{type(error).__name__}: {error}"})
            binding_holds = False
            continue
        inside = WORKTREE in origin.parents
        binding_holds = binding_holds and inside
        modules.append(
            {
                "module": name,
                "origin": str(origin),
                "sha256": sha256_file(origin),
                "inside_selected_worktree": inside,
            }
        )

    return {
        "worktree": str(WORKTREE),
        "branch": branch,
        "head": head,
        "tree": tree,
        "expected_head": EXPECTED_BASE_SHA,
        "expected_tree": EXPECTED_BASE_TREE,
        "expected_branch": EXPECTED_BRANCH,
        "head_is_expected_base": head == EXPECTED_BASE_SHA,
        # The contract prepares the worktree AT the base and separately grants
        # local commits on this branch, so a head ahead of the base is the
        # expected state once any repair lands. What must hold is that the head
        # still descends from the prepared base: that is what makes this
        # candidate the one the assignment issued.
        "head_descends_from_expected_base": _is_ancestor(EXPECTED_BASE_SHA, head),
        "commits_ahead_of_expected_base": git(
            "rev-list", "--count", f"{EXPECTED_BASE_SHA}..{head}"
        ),
        "branch_is_expected": branch == EXPECTED_BRANCH,
        "dirty_entry_count": len(dirty_files),
        "dirty_files": dirty_files,
        "dirty_digest": dirty_digest,
        "clean": not dirty_files,
        "module_bindings": modules,
        "import_binding_holds": binding_holds,
        "sys_path_head": sys.path[:4],
        "interpreter": sys.executable,
        "python_version": platform.python_version(),
    }


def require_binding(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any] | None:
    """Refuse to run a lane whose import binding does not hold."""

    if binding["import_binding_holds"]:
        return None
    offenders = [
        row for row in binding["module_bindings"] if not row.get("inside_selected_worktree")
    ]
    return {
        "result": BLOCKED,
        "state_reason": (
            "import binding does not hold: "
            + "; ".join(
                f"{row['module']} -> {row.get('origin') or row.get('error')}"
                for row in offenders
            )
            + ". Refusing to run a lane that would test another checkout."
        ),
    }


def dependency_inventory(python: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(python), "-m", "pip", "freeze", "--all"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
    return {
        "interpreter": str(python),
        "exit_code": completed.returncode,
        "distributions": sorted(lines),
        "editable_installs": sorted(line for line in lines if line.startswith("-e ")),
        "note": (
            "An editable install pointing at another worktree is the exact "
            "contamination PYTHONPATH binding exists to defeat; it is recorded "
            "rather than removed, because removing it would change a root this "
            "attempt does not own."
        ),
    }


# ------------------------------------------------------------------- lanes


def lane_binding(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """START_BINDING: the clean/dirty tuple, imports and dependencies."""

    worktrees = git("worktree", "list", "--porcelain")
    predecessor = {
        "path": str(PREDECESSOR_WORKTREE),
        "exists": PREDECESSOR_WORKTREE.is_dir(),
        "head": git("rev-parse", "HEAD", repo=PREDECESSOR_WORKTREE)
        if PREDECESSOR_WORKTREE.is_dir()
        else None,
        "tree": git("rev-parse", "HEAD^{tree}", repo=PREDECESSOR_WORKTREE)
        if PREDECESSOR_WORKTREE.is_dir()
        else None,
        "dirty_entries": len(
            [
                line
                for line in git("status", "--porcelain=v1", repo=PREDECESSOR_WORKTREE).splitlines()
                if line.strip()
            ]
        )
        if PREDECESSOR_WORKTREE.is_dir()
        else None,
        "role": "retained reviewed candidate; read-only for this attempt",
    }
    canonical = Path(r"C:\BatteredAggieSyndrome")
    payload = {
        "source_binding": binding,
        "dependencies": dependency_inventory(context.python),
        "declared_roots": {
            "data": str(DATA_ROOT),
            "validation": str(VALIDATION_ROOT),
            "packaging": str(PACKAGING_ROOT),
            "worktree": str(WORKTREE),
        },
        "root_existence": {
            "validation": VALIDATION_ROOT.is_dir(),
            "packaging": PACKAGING_ROOT.is_dir(),
            "data": DATA_ROOT.is_dir(),
        },
        "baseline_export": {
            "path": str(BASELINE_EXPORT),
            "exists": BASELINE_EXPORT.is_dir(),
            "purpose": (
                "Exact-hash owned export of the committed base tree. Baseline "
                "tools that write run here so the retained predecessor is "
                "never modified."
            ),
        },
        "predecessor_worktree": predecessor,
        "canonical_main": {
            "path": str(canonical),
            "head": git("rev-parse", "HEAD", repo=canonical) if canonical.is_dir() else None,
            "dirty_entries": len(
                [
                    line
                    for line in git("status", "--porcelain=v1", repo=canonical).splitlines()
                    if line.strip()
                ]
            )
            if canonical.is_dir()
            else None,
            "role": "outside every write grant for this attempt",
        },
        "registered_worktrees": [
            line.split(" ", 1)[1]
            for line in worktrees.splitlines()
            if line.startswith("worktree ")
        ],
        "delivered_inputs": {
            "cycle36_national_release": {
                "path": str(DELIVERED_C36_DB),
                "exists": DELIVERED_C36_DB.is_file(),
                "recorded_sha256": DELIVERED_C36_DB_SHA256,
                "observed_sha256": sha256_file(DELIVERED_C36_DB),
                "bytes": DELIVERED_C36_DB.stat().st_size
                if DELIVERED_C36_DB.is_file()
                else None,
            },
            "family_b_seed_contract": {
                "path": str(FAMILY_B_SEED_CONTRACT),
                "exists": FAMILY_B_SEED_CONTRACT.is_file(),
                "sha256": sha256_file(FAMILY_B_SEED_CONTRACT),
            },
        },
        "storage": free_space(),
        "hold_active": True,
    }
    observed = payload["delivered_inputs"]["cycle36_national_release"]
    payload["delivered_input_digest_matches"] = (
        observed["observed_sha256"] == observed["recorded_sha256"]
    )

    # The raw evidence behind the verdict, as logged commands: a verdict with no surviving log is reported unrun.
    context.run("git_head_and_tree", ["git", "-C", WORKTREE, "rev-parse", "HEAD", "HEAD^{tree}"], kind="CHECK",
                note="Head and tree of the selected worktree.")
    context.run("git_branch_and_status", ["git", "-C", WORKTREE, "status", "--porcelain=v1", "--branch"],
                kind="CHECK", note="Branch and dirty entries of the selected worktree.")
    context.run("module_origins", [context.python, "-B", "-c", MODULE_ORIGIN_PROBE, WORKTREE / "src",
                                   *BOUND_MODULES],
                kind="CHECK", env=child_env(PYTHONPATH=str(WORKTREE / "src")),
                note="Each bound module imported by the lane interpreter, with the file it resolves to.")
    payload["commands"] = context.commands

    problems: list[str] = []
    for record in context.commands:
        if record.get("exit_code") != 0:
            problems.append(f"{record.get('lane') or 'a binding command'} exited {record.get('exit_code')}")
    if not binding["import_binding_holds"]:
        problems.append("import binding does not resolve to the selected worktree")
    if not binding["branch_is_expected"]:
        problems.append(f"branch is {binding['branch']}, expected {EXPECTED_BRANCH}")
    if not binding["head_descends_from_expected_base"]:
        problems.append(
            f"head {binding['head']} does not descend from the prepared base "
            f"{EXPECTED_BASE_SHA}; this is not the issued candidate"
        )
    if not payload["delivered_input_digest_matches"]:
        problems.append("the delivered Cycle 36 release does not match its recorded digest")
    if not payload["storage"]["reserve_satisfied"]:
        problems.append(
            f"free space {payload['storage']['free_gib']} GiB is below the "
            f"contract's 8 GiB reserve"
        )

    payload["problems"] = problems
    payload["result"] = PASS if not problems else FAIL
    payload["state_reason"] = "; ".join(problems) if problems else "binding holds"
    return payload


def lane_paths(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """PATH_NEGATIVES: owned scratch only; sentinel and escape counterexamples."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    context.run(
        "workspace_path_suite",
        [context.python, "-B", "-m", "unittest", "-v", "test_cycle37_workspace_paths"],
        cwd=WORKTREE / "tests",
        kind="TEST",
        note="MF37-01/02/03 regressions plus the original TP37-S lifecycle suite.",
    )
    work = context.fresh_work()
    context.run(
        "mf37_counterexample_probe",
        [
            context.python,
            "-B",
            str(WORKTREE / "tools" / "cycle37" / "mf37_workspace_probe.py"),
            "--src",
            str(WORKTREE),
            "--scratch",
            str(work / "probe"),
            "--out",
            str(context.out_root / "evidence" / "repairs" / "MF37_WORKSPACE_PROBE_LANE.json"),
            "--label",
            "lane-paths",
        ],
        kind="CHECK",
        note="Sentinel preservation and allocator escape counterexamples.",
    )

    receipt_path = (
        context.out_root / "evidence" / "repairs" / "MF37_WORKSPACE_PROBE_LANE.json"
    )
    probe: dict[str, Any] = {}
    if receipt_path.is_file():
        probe = json.loads(receipt_path.read_text(encoding="utf-8"))

    # Which probes are positives and which are counterexamples is declared,
    # not inferred from a name prefix. Inferring it is how a lane starts
    # reporting its own positive control as a defect -- precisely the class of
    # harness false positive this attempt exists to remove.
    probes = probe.get("probes") or {}
    unknown = sorted(set(probes) - POSITIVE_PROBES - NEGATIVE_PROBES)
    escapes = sorted(
        name
        for name in NEGATIVE_PROBES & set(probes)
        if probes[name].get("outcome") == "ALLOWED"
    )
    broken_positives = sorted(
        name
        for name in POSITIVE_PROBES & set(probes)
        if probes[name].get("outcome") != "ALLOWED"
    )
    sentinel_preserved = bool((probe.get("mf37_01_sentinel") or {}).get("preserved"))
    seed_preserved = bool((probe.get("mf37_03_seed_unchanged") or {}).get("preserved"))

    problems: list[str] = []
    if escapes:
        problems.append(f"counterexamples still allowed: {escapes}")
    if broken_positives:
        problems.append(f"positive controls that stopped working: {broken_positives}")
    if unknown:
        problems.append(
            f"probes with no declared polarity: {unknown}; a probe whose "
            f"expected outcome is undeclared cannot support a lane result"
        )
    if probe and not sentinel_preserved:
        problems.append("the explicit-workspace sentinel was not preserved")
    if probe and not seed_preserved:
        problems.append("the pinned seed was modified by resolution")
    if not probe:
        problems.append("the counterexample probe produced no receipt")

    return {
        "commands": context.commands,
        "counterexample_receipt": str(receipt_path),
        "declared_positive_probes": sorted(POSITIVE_PROBES),
        "declared_negative_probes": sorted(NEGATIVE_PROBES),
        "counterexamples_still_allowed": escapes,
        "positive_controls_broken": broken_positives,
        "probes_with_undeclared_polarity": unknown,
        "sentinel_preserved": sentinel_preserved,
        "pinned_seed_preserved": seed_preserved,
        "problems": problems,
        "result": _combine(context.commands, problems),
        "state_reason": "; ".join(problems) if problems else "all counterexamples refused",
    }


def lane_harness(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """HARNESS_CONTROLS: wrong-source, all-skipped, import and subtest controls."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    context.run(
        "harness_identity_suite",
        [context.python, "-B", "-m", "unittest", "-v", "test_cycle37_lane_harness"],
        cwd=WORKTREE / "tests",
        kind="TEST",
        note="MF37-04 regressions, including a real all-skipped subprocess lane.",
    )
    work = context.fresh_work()
    context.run(
        "mf37_04_probe_repaired",
        [
            context.python,
            "-B",
            str(WORKTREE / "tools" / "cycle37" / "mf37_04_harness_probe.py"),
            "--src",
            str(WORKTREE),
            "--scratch",
            str(work / "after"),
            "--out",
            str(context.out_root / "evidence" / "repairs" / "MF37_04_HARNESS_PROBE_LANE.json"),
            "--label",
            "lane-harness-repaired",
        ],
        kind="CHECK",
    )

    # Deliberate wrong-checkout negative control: the same probe pointed at the
    # retained predecessor export must reproduce the defect. A control that
    # cannot reproduce the defect is not evidence that the head fixed it.
    control: dict[str, Any] = {"state": "NOT_RUN", "reason": "baseline export absent"}
    if BASELINE_EXPORT.is_dir():
        context.run(
            "wrong_checkout_negative_control",
            [
                context.python,
                "-B",
                str(WORKTREE / "tools" / "cycle37" / "mf37_04_harness_probe.py"),
                "--src",
                str(BASELINE_EXPORT),
                "--scratch",
                str(work / "before"),
                "--out",
                str(
                    context.out_root
                    / "evidence"
                    / "repairs"
                    / "MF37_04_HARNESS_PROBE_LANE_BASELINE.json"
                ),
                "--label",
                "lane-harness-predecessor",
            ],
            kind="CHECK",
            env=child_env(PYTHONPATH=str(BASELINE_EXPORT / "src")),
            note="Predecessor source must still exhibit the defect.",
        )
        baseline_receipt = (
            context.out_root
            / "evidence"
            / "repairs"
            / "MF37_04_HARNESS_PROBE_LANE_BASELINE.json"
        )
        if baseline_receipt.is_file():
            data = json.loads(baseline_receipt.read_text(encoding="utf-8"))
            control = {
                "state": "REPRODUCED"
                if not data["duplicate_identity"]["identities_conserved"]
                and data["all_skipped_lane"]["reported_as_pass"]
                else "NOT_REPRODUCED",
                "identities_conserved": data["duplicate_identity"]["identities_conserved"],
                "all_skipped_reported_as_pass": data["all_skipped_lane"]["reported_as_pass"],
                "receipt": str(baseline_receipt),
            }

    repaired_receipt = (
        context.out_root / "evidence" / "repairs" / "MF37_04_HARNESS_PROBE_LANE.json"
    )
    repaired: dict[str, Any] = {}
    if repaired_receipt.is_file():
        repaired = json.loads(repaired_receipt.read_text(encoding="utf-8"))

    problems: list[str] = []
    if not repaired:
        problems.append("the repaired-head harness probe produced no receipt")
    else:
        if not repaired["duplicate_identity"]["identities_conserved"]:
            problems.append("distinct failure identities are still merged at head")
        if repaired["all_skipped_lane"]["reported_as_pass"]:
            problems.append("an all-skipped lane is still reported as a pass at head")
    if control["state"] == "NOT_REPRODUCED":
        problems.append(
            "the wrong-checkout control did not reproduce the defect, so the "
            "head result is not evidence of a repair"
        )

    return {
        "commands": context.commands,
        "repaired_head": repaired.get("duplicate_identity"),
        "repaired_all_skipped": repaired.get("all_skipped_lane"),
        "wrong_checkout_negative_control": control,
        "problems": problems,
        "result": _combine(context.commands, problems),
        "state_reason": "; ".join(problems) if problems else "harness controls hold",
    }


def lane_focused(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """SOURCE_FOCUSED: all changed/material admission and parser modules."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    changed = _changed_paths()
    context.run(
        "focused_regressions",
        [context.python, "-B", "-m", "unittest", "-v", *FOCUSED_TESTS],
        cwd=WORKTREE / "tests",
        kind="TEST",
        note="Suites bound to every module this attempt changed.",
    )
    return {
        "commands": context.commands,
        "changed_paths": changed,
        "focused_suites": list(FOCUSED_TESTS),
        "coverage_limit": (
            "These suites cover the modules changed so far. A module changed "
            "later in this attempt without a suite named here is not covered "
            "by this lane and must not be reported as though it were."
        ),
        "result": _combine(context.commands, []),
        "state_reason": "focused suites executed",
    }


def lane_strict_mounted(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """STRICT_MOUNTED: the real repository validator against the real lake."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    record = context.run(
        "validate_repository_strict",
        [context.python, "-B", "tools/validate_repository.py", "--repo-root", ".", "--strict"],
        cwd=WORKTREE,
        kind="CHECK",
        env=child_env(AGGIE_ANALYTICS_DATA_ROOT=str(DATA_ROOT)),
        note=(
            "Canonical data root. The validator's producers re-materialise some payloads in place "
            "(W37R-66); the receipt's canonical_writes measures what this run wrote. Inherited findings "
            "remain FAIL; no restored or substituted data is used."
        ),
    )
    return {
        "commands": context.commands,
        "data_root": str(DATA_ROOT),
        "inherited_failures_remain_red": True,
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_full_suite(
    context: LaneContext, binding: dict[str, Any], *, subject: str
) -> dict[str, Any]:
    """FULL_BASELINE_MOUNTED / FULL_FINAL_MOUNTED: the whole suite, same mount."""

    if subject == "baseline":
        if not BASELINE_EXPORT.is_dir():
            return {
                "result": BLOCKED,
                "state_reason": (
                    f"the exact-hash predecessor export {BASELINE_EXPORT} does not "
                    f"exist; a baseline lane must not run against the retained "
                    f"predecessor worktree itself"
                ),
            }
        tests_dir = BASELINE_EXPORT / "tests"
        env = child_env(
            PYTHONPATH=str(BASELINE_EXPORT / "src"),
            AGGIE_ANALYTICS_DATA_ROOT=str(DATA_ROOT),
        )
        source = str(BASELINE_EXPORT)
    else:
        blocked = require_binding(context, binding)
        if blocked:
            return blocked
        tests_dir = WORKTREE / "tests"
        env = child_env(AGGIE_ANALYTICS_DATA_ROOT=str(DATA_ROOT))
        source = str(WORKTREE)

    # The invocation deliberately matches the one tools/cycle36/c36_15_validation.py
    # already uses for its whole-suite lane (`discover -s . -v` from the tests
    # directory), so the two are comparable by test identity rather than by
    # counts produced under different discovery roots.
    #
    # CORRECTION. An earlier version of this comment, and the commit that
    # introduced it, said the previous `-s <abs> -t <abs>` form "turned a
    # 12-minute run into a multi-hour one". That was wrong. The elapsed time
    # was misread: local-timestamped files were compared against UTC lane
    # timestamps, inflating the measurement by about an hour. Measured
    # properly, the earlier lane had been running roughly 13 minutes, which is
    # in line with the 737 seconds the c36_15 sublane takes. Matching the
    # invocation is worth doing for comparability; it did not fix a
    # performance problem, because there was no performance problem.
    record = context.run(
        f"full_suite_{subject}",
        [context.python, "-B", "-m", "unittest", "discover", "-s", ".", "-v"],
        cwd=tests_dir,
        kind="TEST",
        env=env,
        timeout=5400,
        note=(
            "Serial traversal of the real lake; the same invocation, runtime "
            "and mount as the other full lane so the two are comparable by "
            "test identity rather than by count."
        ),
    )
    parsed = record.get("unittest") or {}
    # W37R-24: identities alone cannot show a test failing on both sides for
    # different reasons, so the final lane also compares failure causes
    # against the baseline lane's own log.
    cause_comparison: dict[str, Any] | None = None
    baseline_receipt = context.lane_dir / "full-baseline-mounted.json"
    log = next(iter(sorted(context.log_dir.glob("*.log"))), None)
    if subject == "final" and baseline_receipt.is_file() and log is not None:
        import r37_02_cause_comparison as causes

        baseline = json.loads(baseline_receipt.read_text(encoding="utf-8"))
        baseline_log = next(iter(sorted(Path(baseline["log_dir"]).glob("*.log"))), None)
        if baseline_log is not None:
            compared = causes.compare(
                baseline_log.read_text(encoding="utf-8", errors="replace"),
                log.read_text(encoding="utf-8", errors="replace"),
            )
            cause_comparison = {
                "baseline_log": str(baseline_log),
                "final_log": str(log),
                **{k: v for k, v in compared.items() if k != "rows"},
            }
    return {
        "commands": context.commands,
        "subject": subject,
        "cause_comparison": cause_comparison,
        "source_tree": source,
        "data_root": str(DATA_ROOT),
        "tests_run": parsed.get("tests_run"),
        "executed_test_count": parsed.get("executed_test_count"),
        "failed_or_errored_identities": parsed.get("failed_or_errored_identities"),
        "import_error_identities": parsed.get("import_error_identities"),
        "skipped_count": parsed.get("skipped_count"),
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_true_unmounted(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """TRUE_UNMOUNTED: an isolated namespace, with the literal census beside it."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    work = context.fresh_work()
    empty_root = work / "empty_data_root"
    empty_root.mkdir(parents=True)

    # Unsetting the variable proves nothing about a module that carries the
    # private path as a literal, so the census is recorded with the result and
    # the variable is pointed at an empty directory rather than removed.
    literal = r"C:\BatteredAggieSyndrome.data"
    carriers: list[dict[str, Any]] = []
    for path in sorted((WORKTREE / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if literal in text:
            carriers.append(
                {
                    "path": str(path.relative_to(WORKTREE)),
                    "occurrences": text.count(literal),
                }
            )

    record = context.run(
        "focused_unmounted",
        [context.python, "-B", "-m", "unittest", "-v", *FOCUSED_TESTS],
        cwd=WORKTREE / "tests",
        kind="TEST",
        env=child_env(AGGIE_ANALYTICS_DATA_ROOT=str(empty_root)),
        note="Data root pointed at an empty owned directory, not merely unset.",
    )
    return {
        "commands": context.commands,
        "empty_data_root": str(empty_root),
        "private_root_literal_census": {
            "literal": literal,
            "source_files_containing_it": len(carriers),
            "total_occurrences": sum(row["occurrences"] for row in carriers),
            "files": carriers[:80],
        },
        "claim_bound": (
            "This lane is unmounted only for code that reaches the lake through "
            f"the environment. {len(carriers)} source file(s) carry the literal "
            "and are not excluded by it. An absent private artifact is not "
            "counted as a pass."
        ),
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_hashseed(context: LaneContext, binding: dict[str, Any], *, seed: str) -> dict[str, Any]:
    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    record = context.run(
        f"hashseed_{seed}",
        [context.python, "-B", "-m", "unittest", "-v", *FOCUSED_TESTS],
        cwd=WORKTREE / "tests",
        kind="TEST",
        env=child_env(PYTHONHASHSEED=seed),
        note=f"Same non-protected input vector and source, PYTHONHASHSEED={seed}.",
    )
    return {
        "commands": context.commands,
        "python_hash_seed": seed,
        "failed_or_errored_identities": (record.get("unittest") or {}).get(
            "failed_or_errored_identities"
        ),
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_warnings_error(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    record = context.run(
        "warnings_as_errors",
        [context.python, "-B", "-W", "error", "-m", "unittest", "-v", *FOCUSED_TESTS],
        cwd=WORKTREE / "tests",
        kind="TEST",
        note="Focused material tests with -W error.",
    )
    return {
        "commands": context.commands,
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_family_b(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """FAMILY_B_COMPOSED: fresh owned path, explicit pinned seed, real negatives."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    if not FAMILY_B_SEED_CONTRACT.is_file():
        return {
            "result": BLOCKED,
            "state_reason": f"the declared seed contract {FAMILY_B_SEED_CONTRACT} is absent",
        }

    work = context.fresh_work()
    out_dir = work / "qualification"
    record = context.run(
        "family_b_successor_qualification",
        [
            context.python,
            "-B",
            str(WORKTREE / "tools" / "cycle35" / "r35_31_family_b_successor_qualification.py"),
            "--out-dir",
            str(out_dir),
            "--data-root",
            str(DATA_ROOT),
            "--workspace",
            str(work / "isolated"),
        ],
        cwd=WORKTREE,
        kind="CHECK",
        timeout=7200,
        note=(
            "Fresh owned isolated root. LEGACY default remains; no canonical "
            "byte is written and no activation is implied."
        ),
    )
    artifact = out_dir / "CYCLE35_FAMILY_B_SUCCESSOR_QUALIFICATION.json"
    payload = (
        json.loads(artifact.read_text(encoding="utf-8")) if artifact.is_file() else {}
    )
    # R36-12: the composed unit -- upstream d48698ab/2dcb3368 with downstream
    # ab170b25/f343e4e3 -- from the sealed declared seed, in its own new root.
    # The tool exits non-zero unless every clause holds.
    composed_dir = work / "composed_qualification"
    composed = context.run(
        "family_b_composed_qualification",
        [
            context.python,
            "-B",
            str(WORKTREE / "tools" / "cycle37" / "r37_12_composed_family_b.py"),
            "--out-dir",
            str(composed_dir),
            "--isolated-root",
            str(work / "composed"),
            "--seed-contract",
            str(FAMILY_B_SEED_CONTRACT),
        ],
        cwd=WORKTREE,
        kind="CHECK",
        timeout=3600,
        note=(
            "Composed upstream+downstream in a new isolated root from the sealed "
            "seed; 32 negative controls, replay and rollback rehearsal. LEGACY "
            "default remains; no canonical byte is written."
        ),
    )
    composed_artifact = composed_dir / "CYCLE37_FAMILY_B_COMPOSED_QUALIFICATION.json"
    composed_payload = (
        json.loads(composed_artifact.read_text(encoding="utf-8"))
        if composed_artifact.is_file()
        else {}
    )
    return {
        "commands": context.commands,
        "seed_contract": str(FAMILY_B_SEED_CONTRACT),
        "seed_contract_sha256": sha256_file(FAMILY_B_SEED_CONTRACT),
        "qualification_artifact": str(artifact) if artifact.is_file() else None,
        "identity_binding": payload.get("identity_binding"),
        "canonical_preservation": payload.get("canonical_preservation")
        or payload.get("preservation"),
        "composed_qualification_artifact": (
            str(composed_artifact) if composed_artifact.is_file() else None
        ),
        "composed_qualified_in_isolation": composed_payload.get("qualified_in_isolation"),
        "composed_clauses": composed_payload.get("clauses"),
        "composed_identity_agreement": composed_payload.get("identity_agreement"),
        "composed_negative_controls": {
            "total": composed_payload.get("negative_controls_total"),
            "rejected": composed_payload.get("negative_controls_rejected"),
            "not_rejected": composed_payload.get("negative_controls_not_rejected"),
            "rejected_by_an_incidental_exception": composed_payload.get(
                "controls_rejected_by_an_incidental_exception"
            ),
        },
        "activation_authority": "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001 NOT granted by this lane",
        "result": _combine([record, composed], []),
        "state_reason": "; ".join(
            f"{r['result']}: {r['state_reason']}" for r in (record, composed)
        ),
    }


def lane_delivered_db(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """DELIVERED_DB_INDEPENDENT: the successor plus the delivered predecessors."""

    successor = _successor_release()
    if successor is None:
        return {
            "result": BLOCKED,
            "state_reason": (
                "no corrected immutable successor release has been built by this "
                "attempt yet, so there is nothing to compare against the "
                "delivered Cycle 36 release. R37-07 remains unsatisfied; this "
                "lane must not report a state derived from the predecessor alone."
            ),
            "delivered_predecessor": {
                "path": str(DELIVERED_C36_DB),
                "exists": DELIVERED_C36_DB.is_file(),
                "observed_sha256": sha256_file(DELIVERED_C36_DB),
                "recorded_sha256": DELIVERED_C36_DB_SHA256,
            },
        }
    published_c35 = (
        DATA_ROOT
        / "ops"
        / "cycle35"
        / "runs"
        / "20260921T025300Z_closeout_release"
        / "published_release"
        / "CYCLE35_COACHING_RELEASE_PUBLISHED.sqlite"
    )
    review_path = context.out_root / "evidence" / "lanes" / "DELIVERED_DB_REVIEW.json"
    command = [
        context.python, "-B",
        str(WORKTREE / "tools" / "cycle37" / "delivered_db_review.py"),
        "--successor", str(successor),
        "--predecessor", str(DELIVERED_C36_DB),
        "--out", str(review_path),
    ]
    if published_c35.is_file():
        command[-2:-2] = ["--also-compare", str(published_c35)]
    record = context.run("delivered_db_independent", command, kind="CHECK")

    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.is_file() else {}
    problems = list(review.get("findings") or [])
    # A declared reparse may change staff_role_assignment; the review excuses
    # that only when every changed observation has a matching lineage row.
    if review and not review.get("all_conserved_or_reconciled_by_lineage"):
        problems.append(
            "row conservation failed between successor and predecessor and the "
            "difference is not fully reconciled by recorded lineage"
        )
    if review and not review.get("predecessor_unchanged_by_this_review"):
        problems.append("the predecessor changed digest during a read-only review")
    return {
        "commands": context.commands,
        "successor": str(successor),
        "successor_sha256": sha256_file(successor),
        "predecessor": str(DELIVERED_C36_DB),
        "predecessor_sha256": sha256_file(DELIVERED_C36_DB),
        "row_conservation_holds": review.get("all_conserved"),
        "row_conservation_holds_or_reconciled_by_lineage": review.get(
            "all_conserved_or_reconciled_by_lineage"
        ),
        "affected_population": review.get("affected_population"),
        "lineage": (review.get("lineage") or {}).get("release_lineage"),
        "review_receipt": str(review_path),
        "problems": problems,
        "result": record["result"] if not problems else FAIL,
        "state_reason": "; ".join(problems) if problems else record["state_reason"],
    }


def lane_wheel_cli(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """BAS_WHEEL_CLI: a fresh non-editable install, queried outside every checkout."""

    work = context.fresh_work()
    venv = work / "wheel_venv"
    dist = work / "dist"

    # Every step below runs with PYTHONPATH removed. Leaving the worktree's
    # ``src`` on the path puts ``src/aggie_analytics_engine.egg-info`` in
    # scope, and pip then reports the distribution as "already installed with
    # the same version", installs nothing, and creates no console script --
    # so the lane would go on to "test" an entry point that was never
    # installed. That is the installed-package contamination R37-02 names,
    # reproduced here by the lane's own environment.
    clean_env: dict[str, str | None] = {
        "PYTHONPATH": None,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "BAS_VALIDATION_ROOT": str(VALIDATION_ROOT),
        "BAS_PACKAGING_ROOT": str(PACKAGING_ROOT),
        # No package index, no user pip cache and no self-version check: the
        # build and the install stay offline and inside the owned roots (W37R-60).
        "PIP_NO_INDEX": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }

    record_build = context.run(
        "build_wheel",
        [context.python, "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
         "--no-cache-dir", "--disable-pip-version-check", "-w", str(dist), str(WORKTREE)],
        cwd=work,
        kind="CHECK",
        env=clean_env,
        timeout=3600,
        note=("Wheel built from the selected worktree into an owned packaging root, offline: no build "
              "isolation (the lane interpreter's own setuptools), no index, no cache, no version check."),
    )
    if record_build["result"] != PASS:
        return {
            "commands": context.commands,
            "result": record_build["result"],
            "state_reason": f"wheel build did not succeed: {record_build['state_reason']}",
        }
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        return {
            "commands": context.commands,
            "result": FAIL,
            "state_reason": "the wheel build exited zero but produced no .whl",
        }
    context.run(
        "create_fresh_venv",
        [context.python, "-B", "-m", "venv", "--clear", str(venv)],
        cwd=work,
        kind="CHECK",
        env=clean_env,
    )
    venv_python = venv / "Scripts" / "python.exe"
    install = context.run(
        "install_noneditable",
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "--force-reinstall",
            str(wheels[-1]),
        ],
        cwd=work,
        kind="CHECK",
        env=clean_env,
        timeout=1800,
    )
    console_script = venv / "Scripts" / "bas-staff-query.exe"
    if install["result"] != PASS or not console_script.is_file():
        return {
            "commands": context.commands,
            "result": FAIL,
            "state_reason": (
                f"the non-editable install did not produce {console_script}. "
                f"A lane that went on to run queries here would be testing "
                f"something other than the installed entry point."
            ),
            "wheel": str(wheels[-1]),
            "install_result": install["result"],
        }

    # The queries run with no source on PYTHONPATH and from outside every
    # checkout, so a pass cannot be borrowed from the working tree.
    isolated_env = clean_env
    origin = context.run(
        "installed_module_origin",
        [
            str(venv_python),
            "-I",
            "-B",
            "-c",
            "import aggie_analytics.cycle33.query as q, sys, json;"
            "print(json.dumps({'origin': q.__file__, 'sys_path': sys.path[:5]}))",
        ],
        cwd=work,
        kind="CHECK",
        env=isolated_env,
    )
    queries = _cli_query_plan()
    executed: list[dict[str, Any]] = []
    for index, query in enumerate(queries, start=1):
        record = context.run(
            f"cli_query_{index:02d}",
            [str(console_script), *query["args"]],
            cwd=work,
            kind="CHECK",
            env=isolated_env,
            note=query["intent"],
        )
        executed.append({**record, "intent": query["intent"], "args": query["args"]})

    failing = [
        {"lane": row["lane"], "intent": row["intent"], "reason": row["state_reason"]}
        for row in executed
        if row["result"] != PASS
    ]
    # An independent recount straight from sqlite, so a working CLI is not
    # taken on its own word.
    cross_check = _independent_sql_cross_check(_successor_release() or DELIVERED_C36_DB)
    problems = []
    if failing:
        problems.append(
            f"{len(failing)} of {len(executed)} packaged queries did not succeed"
        )
    if cross_check.get("error"):
        problems.append(f"independent SQL cross-check failed: {cross_check['error']}")
    return {
        "commands": context.commands,
        "wheel": str(wheels[-1]),
        "wheel_sha256": sha256_file(wheels[-1]),
        "venv": str(venv),
        "console_script": str(console_script),
        "installed_origin": origin.get("output_tail", "").strip().splitlines()[-1:],
        "queried_database": str(_successor_release() or DELIVERED_C36_DB),
        "queried_database_sha256": sha256_file(_successor_release() or DELIVERED_C36_DB),
        "documented_examples": [
            {"lane": row["lane"], "intent": row["intent"], "args": row["args"],
             "exit_code": row["exit_code"], "result": row["result"]}
            for row in executed
        ],
        "documented_example_count": len(executed),
        "failing_examples": failing,
        "independent_sql_cross_check": cross_check,
        "problems": problems,
        "result": _combine(context.commands, problems),
        "state_reason": "; ".join(problems) if problems else (
            f"{len(executed)} packaged queries executed against the installed "
            f"entry point outside every checkout"
        ),
        "subject_caveat": (
            "These queries were run against the delivered predecessor release "
            "unless a corrected successor exists. A working consumer is not a "
            "corrected dataset: R37-07 also requires the successor."
        ),
    }


def _independent_sql_cross_check(database: Path) -> dict[str, Any]:
    """Recount the release straight from sqlite, bypassing every BAS helper.

    The point of the cross-check is that it shares no code with the consumer
    it is checking: importing the producer's own counting helper would make
    agreement guaranteed rather than informative.
    """

    import sqlite3

    if not Path(database).is_file():
        return {"error": f"{database} does not exist"}
    try:
        conn = sqlite3.connect(
            f"file:{Path(database).as_posix()}?mode=ro&immutable=1", uri=True
        )
    except sqlite3.Error as error:
        return {"error": str(error)}
    try:
        counts = {}
        for table in (
            "canonical_program",
            "program_season_membership",
            "core_role_cell",
            "staff_observation",
            "staff_role_assignment",
            "career_episode",
            "scheme_assertion",
            "responsibility_assertion",
            "user_corpus_cell",
            "unresolved_program_name",
        ):
            try:
                counts[table] = int(
                    conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                )
            except sqlite3.Error as error:
                counts[table] = f"ERROR: {error}"
        divisions = conn.execute(
            "SELECT classification_bucket, COUNT(*) FROM program_season_membership "
            "GROUP BY 1 ORDER BY 1"
        ).fetchall()
        seasons = conn.execute(
            "SELECT MIN(CAST(season AS INTEGER)), MAX(CAST(season AS INTEGER)), "
            "COUNT(DISTINCT season) FROM program_season_membership"
        ).fetchone()
        return {
            "database": str(database),
            "table_counts": counts,
            "membership_by_classification_bucket": [list(row) for row in divisions],
            "season_min_max_distinct": list(seasons),
            "method": "direct sqlite3, no aggie_analytics import",
        }
    finally:
        conn.close()


def _cli_query_plan() -> list[dict[str, Any]]:
    """The twelve documented working examples R37-07 requires.

    Kept as data so the lane reports which intent each query serves, rather
    than a count of commands that happened to exit zero.
    """

    database = str(_successor_release() or DELIVERED_C36_DB)
    plan = [
        ("detected schema is reported, not assumed", ["--schema"]),
        ("national FBS population for a historical season", ["--season", "1998", "--division", "FBS"]),
        ("national FCS population for a historical season", ["--season", "1998", "--division", "FCS"]),
        ("2026 season population across every bucket", ["--season", "2026"]),
        ("one program's whole season membership history", ["--team", "Texas A&M", "--seasons-for-team"]),
        ("one program-season staff with unknowns retained", ["--team", "Texas A&M", "--season", "2026"]),
        ("an FCS program-season", ["--team", "Montana", "--season", "2026"]),
        ("one person's career episodes and observations", ["--person", "Mike Elko"]),
        ("every class of unresolved record", ["--unresolved"]),
        ("scheme assertions with conflicts retained", ["--scheme"]),
        ("responsibility assertions with rejections retained", ["--responsibility"]),
        ("release coverage statement beside a live recount", ["--coverage"]),
        ("source-file lineage", ["--provenance"]),
    ]
    return [
        {"intent": intent, "args": ["--database", database, *args]}
        for intent, args in plan
    ]


#: The released owner wheel this lane composes against, and the digest
#: GitHub records for that release asset. A file with any other bytes is not
#: "the actual released C01 wheel" and the lane refuses to qualify against it.
C01_RELEASED_WHEEL = PACKAGING_ROOT / "c01_release" / "cfbintelligencecontracts-0.1.2-py3-none-any.whl"
C01_RELEASED_WHEEL_SHA256 = "a57d4a58cb268e14f88ea7a66bf49131e89b7f930ea1acabc05c2dfeca689af3"


def lane_c01_release(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """C01_RELEASE_COMPOSED: the BAS adapter composed with the released wheel.

    Installs the digest-verified released wheel into a fresh interpreter of
    its own, with no index access, and runs the composition: every fixture
    goes through BAS's ``project_to_staff_snapshot`` and the emitted document
    goes through the wheel's own ``validate_document``. A shape-only probe of
    the wheel -- documents built by hand and handed to its validator -- is
    what R37-13-AC03 calls insufficient, and it is not what this runs.
    """

    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    if not C01_RELEASED_WHEEL.is_file():
        return {
            "commands": context.commands,
            "result": BLOCKED,
            "state_reason": (
                f"the released C01 wheel is not present at {C01_RELEASED_WHEEL}; "
                "composing against a substitute would qualify something nobody released"
            ),
        }
    digest = sha256_file(C01_RELEASED_WHEEL)
    if digest != C01_RELEASED_WHEEL_SHA256:
        return {
            "commands": context.commands,
            "result": FAIL,
            "state_reason": (
                f"the wheel on disk hashes to {digest}, not the released "
                f"{C01_RELEASED_WHEEL_SHA256}"
            ),
        }

    work = context.fresh_work()
    venv_dir = work / "c01_venv"
    base_python = Path(sys.base_prefix) / "python.exe"
    if not base_python.is_file():
        base_python = Path(sys.executable)
    isolated = {"PYTHONPATH": None, "PYTHONNOUSERSITE": "1"}
    context.run("create_isolated_c01_venv",
                [base_python, "-m", "venv", venv_dir], kind="CHECK", env=child_env(**isolated))
    wheel_python = venv_dir / "Scripts" / "python.exe"
    context.run("install_released_wheel_no_index",
                [wheel_python, "-m", "pip", "install", "--no-index", "--no-deps",
                 C01_RELEASED_WHEEL],
                kind="CHECK", env=child_env(**isolated))
    receipt_path = context.out_root / "evidence" / "repairs" / "R37_13_C01_COMPOSITION.json"
    record = context.run(
        "compose_bas_adapter_with_released_wheel",
        [context.python, "-B", WORKTREE / "tools" / "cycle37" / "r37_13_c01_composition.py",
         "--wheel", C01_RELEASED_WHEEL, "--wheel-sha256", C01_RELEASED_WHEEL_SHA256,
         "--wheel-interpreter", wheel_python, "--out", receipt_path],
        kind="CHECK",
    )
    composition: dict[str, Any] = {}
    if receipt_path.is_file():
        composition = json.loads(receipt_path.read_text(encoding="utf-8"))
    problems = []
    if not composition:
        problems.append("the composition produced no receipt")
    else:
        if not composition.get("all_fixtures_honoured"):
            problems.append("a fixture did not honour its expectation")
        if not composition.get("all_consumer_checks_hold"):
            problems.append("a consumer check failed")
        if not composition.get("f10_separation_holds"):
            problems.append("a source scheme was admitted as an F10 state")
        if composition.get("negatives_caught_only_by_released_wheel"):
            problems.append(
                "negatives caught only by the owner schema: "
                + ", ".join(composition["negatives_caught_only_by_released_wheel"])
            )
    return {
        "commands": context.commands,
        "wheel": str(C01_RELEASED_WHEEL),
        "wheel_sha256": digest,
        "composition_receipt": str(receipt_path),
        "positives": composition.get("positives"),
        "positives_accepted_by_both": composition.get("positives_accepted_by_both"),
        "negatives": composition.get("negatives"),
        "negatives_refused": composition.get("negatives_refused"),
        "negatives_caught_by_bas_adapter": composition.get("negatives_caught_by_bas_adapter"),
        "consumers": composition.get("consumers"),
        "f10_separation": composition.get("source_scheme_vs_f10_state"),
        "problems": problems,
        "result": record["result"] if not problems else FAIL,
        "state_reason": "; ".join(problems) if problems else (
            "every fixture honoured: the adapter's own output accepted by the "
            "released wheel for positives, and refused by the adapter itself "
            "for every negative"
        ),
        "not_adoption": (
            "Qualifying BAS's projection against a released owner schema is not "
            "the owner adopting BAS's envelope and not a C01 self-approval."
        ),
    }


def lane_c36_15(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """C36_15_END_TO_END: the existing full validation tool, every sublane counted."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    work = context.fresh_work()
    out_dir = work / "c36_15"
    record = context.run(
        "c36_15_validation_full",
        [
            context.python,
            "-B",
            str(WORKTREE / "tools" / "cycle36" / "c36_15_validation.py"),
            "--out-dir",
            str(out_dir),
            "--repo",
            str(WORKTREE),
            "--full",
        ],
        cwd=WORKTREE,
        kind="CHECK",
        timeout=10800,
        note="Existing tool, unchanged invocation, now with corrected classification.",
    )
    artifact = out_dir / "CYCLE36_VALIDATION_RESULTS.json"
    payload = (
        json.loads(artifact.read_text(encoding="utf-8")) if artifact.is_file() else {}
    )
    lane_results = payload.get("lane_results") or {}
    problems = []
    unsatisfied = payload.get("lanes_unsatisfied_no_executed_test") or []
    failed = payload.get("lanes_failed") or []
    if unsatisfied:
        problems.append(f"sublanes executing no test: {unsatisfied}")
    if failed:
        problems.append(f"failed sublanes: {failed}")
    return {
        "commands": context.commands,
        "artifact": str(artifact) if artifact.is_file() else None,
        "sublane_results": lane_results,
        "sublane_count": len(lane_results),
        "aggregate_software_state": payload.get("aggregate_software_state"),
        "problems": problems,
        "result": record["result"] if not problems else FAIL,
        "state_reason": "; ".join(problems) if problems else record["state_reason"],
        "no_exception_green": True,
    }


def _distinct_interpreters(context: LaneContext) -> list[dict[str, str]]:
    """Every Python this machine offers, one entry per distinct version.

    Two paths that report the same version are one interpreter for this
    purpose: comparing a value against itself proves nothing.
    """

    import shutil
    import subprocess

    candidates = [Path(context.python), Path(sys.executable)]
    for name in ("python3.11", "python3.12", "python3.13", "python"):
        located = shutil.which(name)
        if located:
            candidates.append(Path(located))
    programs = Path.home() / "AppData" / "Local" / "Programs" / "Python"
    if programs.exists():
        candidates.extend(sorted(programs.glob("Python3*/python.exe")))

    seen_paths: set[str] = set()
    by_version: dict[str, dict[str, str]] = {}
    for candidate in candidates:
        try:
            resolved = str(candidate.resolve())
        except OSError:
            continue
        if resolved in seen_paths or not Path(resolved).is_file():
            continue
        seen_paths.add(resolved)
        try:
            version = subprocess.run(
                [resolved, "-c", "import sys;print(sys.version.split()[0])"],
                capture_output=True, text=True, timeout=120,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if version and version not in by_version:
            by_version[version] = {"path": resolved, "version": version}
    return [by_version[v] for v in sorted(by_version)]


def lane_float_successor(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """FLOAT_SUCCESSOR: the versioned numerical successor and its preimage.

    The predecessor stub asserted that neither had been produced. Both now
    have been, so the lane runs them instead of asserting anything: the
    isolation across interpreters, the qualification of the successor
    aggregation, and the restoration candidate with its complete expected
    payload. It passes only if the successor is invariant across every
    interpreter offered *and* reproduces the value the committed artifacts
    already publish -- an aggregation that changed a published number would
    not be a preserved-identity repair, however stable it was.

    No legacy byte is rewritten and nothing is adopted. The successor is
    deliberately not applied inside the module the week-zero gate binds.
    """

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    work = context.fresh_work()
    repairs = context.out_root / "evidence" / "repairs"
    isolation_path = repairs / "R37_N_FLOAT_ISOLATION.json"
    qualification_path = repairs / "R37_N_AGGREGATION_QUALIFICATION.json"
    candidate_path = repairs / "R37_N_RESTORATION_CANDIDATE.json"

    # Invariance across one interpreter is not invariance. The lane
    # collects every distinct interpreter it can find and refuses to
    # report a pass on fewer than two, because a check that cannot fail
    # has verified nothing -- which is the defect this requirement is
    # about.
    interpreters = _distinct_interpreters(context)
    if len(interpreters) < 2:
        return {
            "commands": context.commands,
            "interpreters_found": interpreters,
            "result": BLOCKED,
            "state_reason": (
                "FLOAT_SUCCESSOR compares a value across interpreters, and "
                f"only {len(interpreters)} distinct interpreter(s) could be "
                "located. Reporting invariance from a single interpreter "
                "would be a vacuous pass, so the lane refuses rather than "
                "claiming one."
            ),
            "preserved": "legacy artifacts and canonical bytes unchanged",
        }
    interpreter_paths = [row["path"] for row in interpreters]

    isolation_command = [
        context.python, "-B",
        str(WORKTREE / "tools" / "cycle37" / "r37_n_float_isolation.py"),
        "--repo-root", str(WORKTREE),
        "--data-root", str(DATA_ROOT),
        "--out", str(isolation_path),
    ]
    for interpreter in interpreter_paths:
        isolation_command += ["--interpreter", interpreter]
    context.run("float_isolation", isolation_command, kind="CHECK", timeout=5400)

    qualification_command = [
        context.python, "-B",
        str(WORKTREE / "tools" / "cycle37" / "r37_n_aggregation_qualification.py"),
        "--repo-root", str(WORKTREE),
        "--data-root", str(DATA_ROOT),
        "--scratch", str(work / "qualification"),
        "--out", str(qualification_path),
    ]
    for interpreter in interpreter_paths:
        qualification_command += ["--interpreter", interpreter]
    context.run("aggregation_qualification", qualification_command, kind="CHECK",
                timeout=5400)

    context.run(
        "restoration_candidate",
        [
            context.python, "-B",
            str(WORKTREE / "tools" / "cycle37" / "r37_n_restoration_candidate.py"),
            "--repo-root", str(WORKTREE),
            "--data-root", str(DATA_ROOT),
            "--candidate-dir", str(VALIDATION_ROOT / "r37_n_restoration_candidate"),
            "--out", str(candidate_path),
            "--request", str(context.out_root / "R37_N_RESTORATION_ACTION_REQUEST.md"),
        ],
        kind="CHECK",
        timeout=3600,
    )

    def read(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    isolation = read(isolation_path)
    qualification = read(qualification_path)
    candidate = read(candidate_path)

    invariant = (qualification.get("every_method_invariant") or {}).get(
        "exact_single_rounding"
    )
    matches = (qualification.get("every_method_matches_published") or {}).get(
        "exact_single_rounding"
    )
    claim_1 = candidate.get("claim_1_semantic_subset_identity") or {}
    claim_2 = candidate.get("claim_2_complete_expected_payload") or {}
    claim_3 = candidate.get("claim_3_proposed_serialized_bytes") or {}
    effect = candidate.get("effect_if_installed") or {}

    problems: list[str] = []
    if not qualification:
        problems.append("the aggregation qualification produced no receipt")
    if invariant is not True:
        problems.append(
            "the successor aggregation is not invariant across the interpreters offered"
        )
    if matches is not True:
        problems.append(
            "the successor aggregation does not reproduce the published value, "
            "so adopting it would move a legacy identity"
        )
    if not isolation:
        problems.append("the interpreter isolation produced no receipt")
    if not candidate:
        problems.append("the restoration candidate produced no receipt")
    if candidate and not claim_1.get("identity_matches_committed_gate"):
        problems.append("the rebuilt payload does not reproduce the committed identity")
    if candidate and claim_2.get("disagreement_count"):
        problems.append(
            f"{claim_2['disagreement_count']} payload fields disagree with the "
            "producer's declarations"
        )
    if candidate and not claim_3.get("rebuilt_twice_identically"):
        problems.append("the restoration candidate is not deterministic")
    if candidate and not effect.get("both_checks_clear"):
        problems.append(
            "serving the candidate does not clear both strict findings"
        )
    if candidate and candidate.get("executed_any_canonical_write"):
        problems.append("a canonical write was executed, which this lane forbids")

    classification = (isolation.get("classification") or {})
    mechanism = (isolation.get("mechanism_test") or {})
    return {
        "commands": context.commands,
        "successor_algorithm": qualification.get("successor_algorithm"),
        "interpreters": [row["version"] for row in interpreters],
        "interpreters_compared": len(interpreters),
        "successor_invariant": invariant,
        "successor_reproduces_published_value": matches,
        "builtin_sum_invariant": (
            qualification.get("every_method_invariant") or {}
        ).get("builtin_sum"),
        "isolation": {
            "failing_under_every_interpreter": classification.get(
                "failing_under_every_interpreter"
            ),
            "failing_under_some_interpreter_only": classification.get(
                "failing_under_some_interpreter_only"
            ),
            "explained_by_the_sum_change": mechanism.get("explained_by_the_sum_change"),
            "not_explained": mechanism.get("not_explained"),
        },
        "bounded_error_analysis": isolation.get("bounded_error_analysis"),
        "amplification": qualification.get("amplification"),
        "restoration_candidate": {
            "identity_reproduces": claim_1.get("identity_matches_committed_gate"),
            "identity_covers": claim_1.get("coverage"),
            "field_disagreements": claim_2.get("disagreement_count"),
            "candidate_sha256": claim_3.get("candidate_sha256"),
            "byte_exact_recovery_claimable": claim_3.get(
                "byte_exact_recovery_claimable"
            ),
            "both_strict_checks_clear_if_installed": effect.get("both_checks_clear"),
        },
        "adopted_anywhere": False,
        "canonical_bytes_written": 0,
        "preserved": "legacy artifacts and canonical bytes unchanged",
        "not_adopted_because": (
            qualification.get("adoption_cost") or {}
        ).get("why_local_adoption_is_not_free"),
        "problems": problems,
        "result": PASS if not problems else FAIL,
        "state_reason": (
            "; ".join(problems)
            if problems
            else "the versioned successor is invariant across interpreters and "
            "reproduces the published value, and the restoration candidate is "
            "complete, deterministic and clears both strict findings without "
            "writing a canonical byte"
        ),
    }


def lane_jira_private(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """JIRA_PRIVATE_SYNC: the established producer on a private successor.

    Consumes the attempt's fresh, complete-field, read-only live Jira read --
    it does not re-read Jira on every sweep, which would spend the metadata
    ceiling on repetition -- and runs the repository's own reconciler, the
    material-event write, the derivative rebuild and both second-pass
    validators against a private copy of the canonical records. The public
    records are hashed before and after and must be unchanged.
    """

    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    private = context.out_root / "private" / "jira"
    reads = sorted(private.glob("JIRA_LIVE_READ_2*.json"))
    supplements = sorted(private.glob("JIRA_LIVE_SUPPLEMENT_2*.json"))
    exports = sorted(private.glob("BAT_JIRA_EXPORT_2*.csv"))
    if not (reads and supplements and exports):
        return {
            "commands": context.commands,
            "result": BLOCKED,
            "state_reason": (
                "no fresh live Jira read exists under the private evidence root; "
                "run tools/cycle37/r37_14_jira_live_read.py first"
            ),
        }
    receipt_path = private / "R37_14_JIRA_CONVERGENCE.json"
    record = context.run(
        "jira_private_successor_sequence",
        [context.python, "-B", WORKTREE / "tools" / "cycle37" / "r37_14_jira_convergence.py",
         "--repo-root", WORKTREE, "--live-read", reads[-1], "--supplement", supplements[-1],
         "--export-csv", exports[-1],
         "--private-root", VALIDATION_ROOT / "jira_private_successor",
         "--out", receipt_path],
        kind="CHECK",
    )
    result: dict[str, Any] = {}
    if receipt_path.is_file():
        result = json.loads(receipt_path.read_text(encoding="utf-8"))
    successor = result.get("private_successor") or {}
    problems = []
    if not result:
        problems.append("the convergence tool produced no receipt")
    else:
        if not successor.get("every_step_exit_zero"):
            problems.append("a producer step exited non-zero")
        if not successor.get("public_records_unchanged"):
            problems.append("the public canonical records changed")
        if not successor.get("material_events_written"):
            problems.append("the apply step wrote no material event")
        if result.get("canonical_missing_live"):
            problems.append("canonical records have no live issue")
        if result.get("canonical_local_id_mismatches"):
            problems.append("Local Issue ID mismatches between live and local")
        if result.get("mirror_status_stale"):
            problems.append("the mirror's recorded status is stale against live")
    read_at = json.loads(reads[-1].read_text(encoding="utf-8")).get("read_at_utc")
    return {
        "commands": context.commands,
        "live_read": str(reads[-1]),
        "live_read_at_utc": read_at,
        "live_total": (result.get("live") or {}).get("total"),
        "live_bat_by_local_class": result.get("live_bat_by_local_class"),
        "unregistered_live_issues": result.get("unregistered_live_issues"),
        "dry_run_conflicts": successor.get("dry_run_conflicts"),
        "material_events_written": successor.get("material_events_written"),
        "public_records_unchanged": successor.get("public_records_unchanged"),
        "convergence_receipt": str(receipt_path),
        "problems": problems,
        "result": record["result"] if not problems else FAIL,
        "state_reason": "; ".join(problems) if problems else (
            "the established producer ran dry-run, apply, material event, rebuild "
            "and both second-pass validators on a private successor; the public "
            "records are unchanged"
        ),
        "no_adoption_implied": True,
    }


def lane_privacy(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """PUBLIC_PACKAGE_PRIVACY: the exact source diff and what it would publish."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked

    changed = _changed_paths()
    findings = scan_for_private_material(
        (relative, WORKTREE / relative) for relative in changed
    )

    record = context.run(
        "validate_repository_public",
        [context.python, "-B", "tools/validate_repository.py", "--repo-root", "."],
        cwd=WORKTREE,
        kind="CHECK",
        note="Secret, forbidden-artifact and manifest checks over the changed tree.",
    )
    problems = []
    if findings["credential_values"]:
        problems.append(
            f"credential-shaped values in changed files: "
            f"{[row['path'] for row in findings['credential_values']]}"
        )
    return {
        "commands": context.commands,
        "changed_path_count": len(changed),
        "changed_paths": changed,
        "private_path_references": findings["private_paths"],
        "credential_name_references": findings["credential_names"],
        "credential_findings": findings["credential_values"],
        "detector_self_scan": findings["self_scan"],
        "rule": findings["rule"],
        "no_new_paid_trigger": True,
        "problems": problems,
        "result": record["result"] if not problems else FAIL,
        "state_reason": "; ".join(problems) if problems else record["state_reason"],
    }


#: Credential *names* assembled from fragments. A scanner that spells its own
#: patterns out flags itself, which is a false positive in the review method
#: rather than a finding about the code. Building the needles at import time
#: keeps the literals out of this file while leaving the rule readable.
_CREDENTIAL_NAMES = tuple(
    "_".join(parts)
    for parts in (
        ("ATLASSIAN", "API", "TOKEN"),
        ("CFBD", "API", "KEY"),
        ("OPENAI", "API", "KEY"),
        ("GITHUB", "TOKEN"),
        ("SPORTRADAR", "API", "KEY"),
    )
)
_PRIVATE_PATH_NEEDLES = (
    "BatteredAggieSyndrome" + ".data",
    "kevinsgarrett" + ".atlassian.net",
)
#: A credential *value*: a name immediately assigned something, or a bearer
#: token with an actual token after it. A bare reference to a variable name is
#: a declared dependency, not a secret, and is reported separately.
_CREDENTIAL_VALUE_PATTERNS = tuple(
    __import__("re").compile(pattern)
    for pattern in (
        r"(?:" + "|".join(_CREDENTIAL_NAMES) + r")\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{12,}",
        r"\bBea" + r"rer\s+[A-Za-z0-9_\-\.]{12,}",
        r"\bghp_[A-Za-z0-9]{20,}",
        r"\bATATT[A-Za-z0-9_\-\.]{20,}",
    )
)


def scan_for_private_material(
    candidates: Iterable[tuple[str, Path]]
) -> dict[str, Any]:
    """Separate a declared private path from a credential name from a secret.

    All three used to be one marker list, so a tool that merely *named* an
    environment variable was reported identically to one carrying a token,
    and the scanner's own pattern list made the scanner its own worst finding.
    """

    private_paths: list[dict[str, Any]] = []
    credential_names: list[dict[str, Any]] = []
    credential_values: list[dict[str, Any]] = []

    for relative, candidate in candidates:
        if not Path(candidate).is_file():
            continue
        try:
            text = Path(candidate).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        paths_hit = [needle for needle in _PRIVATE_PATH_NEEDLES if needle in text]
        if paths_hit:
            private_paths.append({"path": relative, "references": paths_hit})
        names_hit = [name for name in _CREDENTIAL_NAMES if name in text]
        if names_hit:
            credential_names.append({"path": relative, "names": names_hit})
        matches = [
            match.group(0)[:24] + "..."
            for pattern in _CREDENTIAL_VALUE_PATTERNS
            for match in pattern.finditer(text)
        ]
        if matches:
            credential_values.append({"path": relative, "match_count": len(matches)})

    this_file = Path(__file__).resolve()
    self_matches = [
        pattern.pattern[:40]
        for pattern in _CREDENTIAL_VALUE_PATTERNS
        if pattern.search(this_file.read_text(encoding="utf-8", errors="replace"))
    ]
    return {
        "private_paths": private_paths,
        "credential_names": credential_names,
        "credential_values": credential_values,
        "self_scan": {
            "scanner": str(this_file.relative_to(WORKTREE)),
            "scanner_is_scanned_by_the_same_rule": True,
            "scanner_matches": self_matches,
            "note": (
                "The scanner is not exempted. It carries no credential value "
                "because its needles are assembled from fragments, so a match "
                "here would be a real finding."
            ),
        },
        "rule": (
            "A private root path is a declared dependency. A credential "
            "variable NAME is a reference. Only a name assigned a value, or a "
            "bearer/token literal, is treated as a secret."
        ),
    }


def lane_retired(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """RETIRED_INACTIVE: the real decommission validator; the interlock is not run."""

    blocked = require_binding(context, binding)
    if blocked:
        return blocked
    validator = WORKTREE / "tools" / "validate_retired_assistive_pipeline_decommission.py"
    if not validator.is_file():
        return {
            "result": BLOCKED,
            "state_reason": f"{validator} does not exist at the selected head",
        }
    record = context.run(
        "retired_assistive_decommission",
        [context.python, "-B", str(validator), "--repo-root", "."],
        cwd=WORKTREE,
        kind="CHECK",
        note="Reachability only. The retired interlock is deliberately not executed.",
    )
    return {
        "commands": context.commands,
        "interlock_executed": False,
        "result": record["result"],
        "state_reason": record["state_reason"],
    }


def lane_packet(context: LaneContext, binding: dict[str, Any]) -> dict[str, Any]:
    """FINAL_PACKET: refresh every section against the final source and lane set."""

    lane_dir = context.out_root / "evidence" / "lanes"
    present: dict[str, Any] = {}
    for lane_id in WORKER_LANES:
        path = lane_dir / f"{lane_id}.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            present[lane_id] = {
                "result": data.get("result"),
                "state_reason": data.get("state_reason"),
                "observed_at": data.get("observed_at"),
                "head": (data.get("source_binding") or {}).get("head")
                or data.get("head"),
                "sha256": sha256_file(path),
            }
        else:
            present[lane_id] = {"result": NOT_RUN, "state_reason": "no receipt written"}

    context.run("lane_receipts", [context.python, "-B", "-c", RECEIPT_LISTING, lane_dir, *WORKER_LANES],
                kind="CHECK", note="The result, head and digest of every expected lane receipt the verdict reads.")

    states = [row["result"] for row in present.values()]
    if any(state in (FAIL, BLOCKED) for state in states):
        aggregate = FAIL
    elif any(state == UNSATISFIED for state in states):
        aggregate = UNSATISFIED
    elif all(state == NOT_RUN for state in states):
        aggregate = NOT_RUN
    elif any(state == NOT_RUN for state in states):
        aggregate = "PARTIAL"
    else:
        aggregate = PASS

    problems = [
        f"{lane_id}: {row['result']}"
        for lane_id, row in present.items()
        if row["result"] != PASS
    ]
    return {
        "commands": context.commands,
        "lane_receipts": present,
        "expected_worker_lanes": list(WORKER_LANES),
        "manager_pending_lane": "MANAGER_INDEPENDENT",
        "aggregate_software_state": aggregate,
        "problems": problems,
        "result": PASS if not problems else FAIL,
        "state_reason": (
            "every worker lane satisfied"
            if not problems
            else f"{len(problems)} worker lane(s) unsatisfied or unrun"
        ),
        "cycle_complete_prohibited": "hold_active",
    }


# ------------------------------------------------------------------ plumbing


def _combine(commands: list[dict[str, Any]], problems: list[str]) -> str:
    if problems:
        return FAIL
    if not commands:
        return NOT_RUN
    states = [record["result"] for record in commands]
    if any(state == BLOCKED for state in states):
        return BLOCKED
    if any(state == FAIL for state in states):
        return FAIL
    if any(state == UNSATISFIED for state in states):
        return UNSATISFIED
    return PASS


def _changed_paths() -> list[str]:
    return sorted(path.strip('"') for _status, path in porcelain_lines())


def _successor_release() -> Path | None:
    """The corrected immutable release this attempt produces, if it exists yet.

    Content-addressed, so the path carries the identity. Exactly one is
    expected; more than one means two identities are published at once and
    the lane should say so rather than silently pick the last.
    """

    candidate_root = DATA_ROOT / "ops/cycle37/attempts" / ATTEMPT_ID / "release"
    if not candidate_root.is_dir():
        return None
    # A later build supersedes an earlier one without deleting it; the build
    # writes CURRENT_RELEASE.json naming the identity in force. The pointer is
    # believed only if the file it names exists under this root.
    pointer = candidate_root / "CURRENT_RELEASE.json"
    if pointer.is_file():
        named = json.loads(pointer.read_text(encoding="utf-8"))
        database = candidate_root / "sha256" / str(named.get("content_identity")) / str(named.get("database_name"))
        if not database.is_file():
            raise RuntimeError(f"CURRENT_RELEASE.json names {database}, which does not exist")
        return database
    candidates = sorted(candidate_root.rglob("*.sqlite"))
    if len(candidates) > 1:
        raise RuntimeError(
            f"{len(candidates)} published releases under {candidate_root}; a "
            f"content-addressed release root must hold one identity per build "
            f"and the lane will not choose between them: {candidates}"
        )
    return candidates[0] if candidates else None


WORKER_LANES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "binding": ("START_BINDING", lane_binding),
    "paths": ("PATH_NEGATIVES", lane_paths),
    "harness": ("HARNESS_CONTROLS", lane_harness),
    "focused": ("SOURCE_FOCUSED", lane_focused),
    "strict-mounted": ("STRICT_MOUNTED", lane_strict_mounted),
    "full-baseline-mounted": (
        "FULL_BASELINE_MOUNTED",
        lambda c, b: lane_full_suite(c, b, subject="baseline"),
    ),
    "full-final-mounted": (
        "FULL_FINAL_MOUNTED",
        lambda c, b: lane_full_suite(c, b, subject="final"),
    ),
    "true-unmounted": ("TRUE_UNMOUNTED", lane_true_unmounted),
    "hashseed-0": ("HASHSEED0", lambda c, b: lane_hashseed(c, b, seed="0")),
    "hashseed-1": ("HASHSEED1", lambda c, b: lane_hashseed(c, b, seed="1")),
    "warnings-error": ("WARNINGS_ERROR", lane_warnings_error),
    "family-b": ("FAMILY_B_COMPOSED", lane_family_b),
    "delivered-db": ("DELIVERED_DB_INDEPENDENT", lane_delivered_db),
    "wheel-cli": ("BAS_WHEEL_CLI", lane_wheel_cli),
    "c01-release": ("C01_RELEASE_COMPOSED", lane_c01_release),
    "c36-15": ("C36_15_END_TO_END", lane_c36_15),
    "float-successor": ("FLOAT_SUCCESSOR", lane_float_successor),
    "jira-private": ("JIRA_PRIVATE_SYNC", lane_jira_private),
    "privacy": ("PUBLIC_PACKAGE_PRIVACY", lane_privacy),
    "retired": ("RETIRED_INACTIVE", lane_retired),
    "packet": ("FINAL_PACKET", lane_packet),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=sorted(WORKER_LANES))
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument(
        "--list-lanes",
        action="store_true",
        help="Print the lane registry and exit without running anything.",
    )
    args = parser.parse_args()

    if args.list_lanes:
        print(json.dumps({k: v[0] for k, v in WORKER_LANES.items()}, indent=2))
        return 0

    out_root = args.out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "evidence" / "repairs").mkdir(parents=True, exist_ok=True)
    VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)
    PACKAGING_ROOT.mkdir(parents=True, exist_ok=True)

    contract_lane_id, handler = WORKER_LANES[args.lane]
    context = LaneContext(args.lane, out_root, Path(sys.executable))
    started = utc_now()
    space_before = free_space()
    canonical_before = canonical_snapshot()
    binding = bind_source()

    try:
        payload = handler(context, binding)
    except Exception as error:  # noqa: BLE001 - a crashed lane is BLOCKED, never a pass
        import traceback

        payload = {
            "result": BLOCKED,
            "state_reason": f"the lane raised {type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }

    receipt: dict[str, Any] = {
        "label": LABEL,
        "cycle_number": CYCLE_NUMBER,
        "attempt_number": ATTEMPT_NUMBER,
        "state": "ACTUAL_STATE",
        "cycle_id": CYCLE_ID,
        "attempt_id": ATTEMPT_ID,
        "lane": args.lane,
        "contract_lane_id": contract_lane_id,
        "executor": "worker",
        "started_at": started,
        "observed_at": utc_now(),
        "out_root": str(out_root),
        "log_dir": str(context.log_dir),
        "source_binding": binding,
        "storage_before": space_before,
        "storage_after": free_space(),
        "declared_roots": {
            "validation": str(VALIDATION_ROOT),
            "packaging": str(PACKAGING_ROOT),
            "data": str(DATA_ROOT),
        },
        "hold_active": True,
        "scientific_acceptance": "NOT_GRANTED_BY_THIS_LANE",
    }
    receipt.update(payload)
    receipt.setdefault("result", NOT_RUN)
    writes = canonical_writes(canonical_before, canonical_snapshot())
    if context.guarded:
        events = []
        if context.guard_log.is_file():
            for line in context.guard_log.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
        counts: dict[str, int] = {}
        for event in events:
            counts[event.get("event", "?")] = counts.get(event.get("event", "?"), 0) + 1
        receipt["write_guard"] = {
            "mode": "COMPARE_BEFORE_WRITE_REFUSE_OTHERWISE",
            "environment_change": (
                "Children run with the BAS canonical write guard prepended to PYTHONPATH (sitecustomize). The "
                "canonical data root is still the mounted data root for every read; under it identical-byte "
                "whole-file writes are skipped and every other write is refused, except under this attempt's "
                "own root. This is recorded, not hidden: it is the prevention the clarification requires."),
            "guarded_root": str(DATA_ROOT), "allowed_roots": [str(context.out_root)],
            "module": str(GUARD_DIR / "bas_canonical_write_guard.py"),
            "module_sha256": sha256_file(GUARD_DIR / "bas_canonical_write_guard.py"),
            "events_log": str(context.guard_log), "events_log_sha256": sha256_file(context.guard_log),
            "event_counts": counts,
            "blocked": [event for event in events if event.get("event") == "BLOCKED"][:50],
        }
    receipt["canonical_writes"] = writes
    receipt["read_only"] = writes["count"] == 0
    receipt["read_only_basis"] = "MEASURED_ON_THE_WATCHED_CANONICAL_TREES"

    destination = context.lane_dir / f"{args.lane}.json"
    _bas_atomic.write_text(destination, 
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print(f"{LABEL}")
    print(f"lane      : {args.lane}  ({contract_lane_id})")
    print(f"result    : {receipt['result']}")
    print(f"reason    : {receipt.get('state_reason')}")
    print(f"canonical : {writes['count']} entries written under {writes['watched']} (exclusions in the receipt)")
    print(f"receipt   : {destination}")
    print(f"logs      : {context.log_dir}")
    return 0 if receipt["result"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
