r"""Cycle #37 — Attempt #5 — prepare the one separate local integration candidate (R37A05-07-C).

    attempt05_candidate.py create --record <new file>
    attempt05_candidate.py describe

The grant is exact: a new worktree at ``C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review`` on the new
branch ``codex/BAT-706-cycle37-qualified-integration``, from main ``55e12a5a``, using only shared Git objects, the
new ref and the worktree registration. Nothing is pushed, merged, retargeted, closed, deleted or rewritten; the
repair branch and every other ref keep their commits.

The candidate is one ``[material]`` commit on main whose tree is the repair branch's final tree, except for the
protected review controls -- the scientific-review workflows, rules, prompt, schema and validator, which the
contract denies as write paths in both worktrees. Those paths carry main's exact blobs (a path main does not have
stays absent), because changing the trusted review controls of main is an owner decision this candidate does not
make; the branch's own versions are named in the record. The tree is written through a private index file, so
no worktree index changes. The new worktree is populated without ever writing a protected path: its index is
read from the candidate, the protected entries are marked skip-worktree, and only the other entries are checked
out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
TOOL_VERSION = "BAS-C37A05-INTEGRATION-CANDIDATE-v1"
WORKTREE = Path(__file__).resolve().parents[2]
MAIN_SHA = "55e12a5aad3a7e843204fcba619c3cb3d3d6194d"
REPAIR_BRANCH = "codex/BAT-706-cycle37-rework"
CANDIDATE_BRANCH = "codex/BAT-706-cycle37-qualified-integration"
CANDIDATE_WORKTREE = Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review")
#: The protected review controls (contract denied write paths in both worktrees).
PROTECTED_PATHS = (
    ".github/workflows/codex-scientific-review.yml",
    ".github/workflows/paid-scientific-review.yml",
    ".github/CODE_REVIEW_RULES.md",
    ".github/codex/prompts/scientific-review.md",
    "schemas/scientific_review/codex_scientific_review.schema.json",
    "tools/validate_codex_scientific_review.py",
)
SCRATCH = Path(r"C:\BatteredAggieSyndrome.packaging\c37a05\candidate")
#: The repository whose objects, refs and worktree registrations the candidate is written to. For the granted
#: candidate it is the repair worktree's own repository (shared objects); a rehearsal rebinds it to a scratch
#: repository that borrows those objects read-only, so a rehearsal never writes to the shared repository.
REPO = WORKTREE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str, repo: Path | None = None, env: dict[str, str] | None = None, check: bool = True,
        stdin: str | None = None) -> str:
    completed = subprocess.run(["git", "--no-optional-locks", "-C", str(repo or REPO), *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=env, check=False, input=stdin)
    if check and completed.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}")
    return completed.stdout.strip()


def entry(revision: str, path: str) -> tuple[str, str] | None:
    """(mode, blob) of ``path`` at ``revision``, or None when the path is absent there."""

    line = git("ls-tree", revision, "--", path)
    if not line:
        return None
    meta, _name = line.split("\t", 1)
    mode, kind, blob = meta.split()
    return mode, blob


def refs() -> dict[str, str]:
    return dict(line.split(" ", 1)[::-1] for line in git("for-each-ref", "--format=%(objectname) %(refname)").splitlines())


def describe() -> dict[str, Any]:
    """What the candidate is and how it relates to main and the repair branch, from Git alone."""

    head = git("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}", check=False)
    repair = git("rev-parse", REPAIR_BRANCH)
    record: dict[str, Any] = {"candidate_branch": CANDIDATE_BRANCH, "candidate_head": head or None,
                              "candidate_worktree": str(CANDIDATE_WORKTREE), "main": MAIN_SHA,
                              "main_ref": git("rev-parse", "refs/heads/main"), "repair_branch": REPAIR_BRANCH,
                              "repair_head": repair, "repair_tree": git("rev-parse", f"{repair}^{{tree}}")}
    if not head:
        return record
    record["candidate_tree"] = git("rev-parse", f"{head}^{{tree}}")
    record["candidate_parents"] = git("rev-list", "--parents", "-n", "1", head).split()[1:]
    record["candidate_subject"] = git("log", "-1", "--format=%s", head)
    changed = [line for line in git("diff-tree", "-r", "--name-only", "--no-commit-id", record["repair_tree"],
                                    record["candidate_tree"]).splitlines() if line.strip()]
    record["paths_differing_from_the_repair_tree"] = changed
    record["protected_paths"] = [{"path": path, "main": entry(MAIN_SHA, path), "repair": entry(repair, path),
                                  "candidate": entry(head, path)} for path in PROTECTED_PATHS]
    record["protected_paths_equal_main"] = all(row["candidate"] == row["main"] for row in record["protected_paths"])
    record["only_protected_paths_differ"] = set(changed) <= set(PROTECTED_PATHS)
    record["files_changed_against_main"] = len([line for line in git("diff-tree", "-r", "--name-only",
                                                                       "--no-commit-id", MAIN_SHA,
                                                                       record["candidate_tree"]).splitlines() if line])
    record["repair_commits_consolidated"] = int(git("rev-list", "--count", f"{MAIN_SHA}..{repair}"))
    return record


def create(record_path: Path) -> dict[str, Any]:
    if git("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}", check=False):
        raise SystemExit(f"{CANDIDATE_BRANCH} already exists; the candidate is created once")
    if CANDIDATE_WORKTREE.exists():
        raise SystemExit(f"{CANDIDATE_WORKTREE} already exists; the candidate is created once")
    if git("status", "--porcelain=v1", "-uall", repo=WORKTREE):
        raise SystemExit("the repair worktree is not clean; the candidate is made only from a committed subject")
    if git("rev-parse", "refs/heads/main") != MAIN_SHA:
        raise SystemExit("main is not the issued base; refusing")
    repair = git("rev-parse", "HEAD", repo=WORKTREE)
    if git("rev-parse", REPAIR_BRANCH) != repair:
        raise SystemExit(f"the repair worktree is not at the head of {REPAIR_BRANCH}; refusing")
    before_refs = refs()
    # The candidate tree, through a private index file: the repair tree with main's protected entries.
    SCRATCH.mkdir(parents=True, exist_ok=True)
    index = SCRATCH / f"candidate-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.index"
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    git("read-tree", f"{repair}^{{tree}}", env=env)
    # Main's entry for each protected path, or mode 0 (remove) where main has none. --index-info reads only the
    # index and the object store, never a work tree; -z records end in NUL, which no newline translation touches.
    # Git ignores, with exit 0, a path it cannot verify, so the written tree is proved below before any commit.
    records = []
    for path in PROTECTED_PATHS:
        main_entry = entry(MAIN_SHA, path)
        records.append(f"{main_entry[0]} {main_entry[1]}\t{path}" if main_entry else f"0 {'0' * 40}\t{path}")
    git("update-index", "-z", "--index-info", env=env, stdin="".join(record + "\0" for record in records))
    tree = git("write-tree", env=env)
    wrong = [path for path in PROTECTED_PATHS if entry(tree, path) != entry(MAIN_SHA, path)]
    if wrong:
        raise SystemExit(f"the candidate tree {tree} does not carry main's entries for {wrong}; no commit was made")
    withheld = [path for path in PROTECTED_PATHS if entry(repair, path) != entry(MAIN_SHA, path)]
    count = int(git("rev-list", "--count", f"{MAIN_SHA}..{repair}"))
    message = SCRATCH / (index.stem + ".message.txt")
    message.write_text(
        "[material] consolidate the Cycle 37 repair branch onto main as one locally qualified candidate (BAT-706)\n\n"
        f"The tree of {REPAIR_BRANCH} at {repair} ({count} commits after main {MAIN_SHA[:8]}), as one commit on main,\n"
        "prepared locally for review under the Cycle 37 Attempt 5 grant. Nothing is pushed or merged, and the repair\n"
        "branch keeps every original commit and its review provenance.\n\n"
        "Withheld: the protected scientific-review controls keep main's exact bytes; changing them on main is an\n"
        "owner decision. Differing on the repair branch: " + (", ".join(withheld) or "none") + ".\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n", encoding="utf-8", newline="\n")
    commit = git("commit-tree", tree, "-p", MAIN_SHA, "-F", str(message))
    # The new ref and worktree registration, with no checkout yet.
    git("worktree", "add", "--no-checkout", "-b", CANDIDATE_BRANCH, str(CANDIDATE_WORKTREE), commit)
    git("read-tree", "HEAD", repo=CANDIDATE_WORKTREE)
    present = [path for path in PROTECTED_PATHS if entry(commit, path) is not None]
    if present:
        git("update-index", "--skip-worktree", "--", *present, repo=CANDIDATE_WORKTREE)
    git("checkout-index", "--all", repo=CANDIDATE_WORKTREE)
    written_protected = [path for path in PROTECTED_PATHS if (CANDIDATE_WORKTREE / path).exists()]
    status = git("status", "--porcelain=v1", "-uall", repo=CANDIDATE_WORKTREE)
    after_refs = refs()
    changed_refs = sorted(name for name in set(before_refs) | set(after_refs)
                          if before_refs.get(name) != after_refs.get(name))
    record = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS_LOCAL_WORK_REMAINS (local integration "
                 "candidate prepared)",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "tool_version": TOOL_VERSION,
        "created_at": utc_now(), "repair_head": repair, "candidate_commit": commit, "candidate_tree": tree,
        "private_index_file": str(index), "message_file": str(message),
        "message_sha256": hashlib.sha256(message.read_bytes()).hexdigest(),
        "protected_paths_marked_skip_worktree": present, "protected_paths_written_to_disk": written_protected,
        "worktree_status_after_population": status.splitlines(),
        "refs_changed": changed_refs,
        "only_the_new_branch_ref_changed": changed_refs == [f"refs/heads/{CANDIDATE_BRANCH}"],
        "withheld_protected_paths": withheld, **describe(),
        "not_done": "No push, remote PR, merge, retarget, closure, deletion, history rewrite or default activation.",
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    made = sub.add_parser("create")
    made.add_argument("--record", type=Path, required=True)
    sub.add_parser("describe")
    args = parser.parse_args(argv)
    result = create(args.record) if args.mode == "create" else describe()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
