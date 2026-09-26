r"""Cycle #37 — Attempt #7 — append the Attempt 7 repairs to the preserved local candidate (R37A07-03-C).

    attempt07_candidate.py append --record <new file> --view-root <new owned directory>
    attempt07_candidate.py describe
    attempt07_candidate.py verify-tree <commit>
    attempt07_candidate.py rehearse --scratch <new directory> --repair <commit>

The Attempt 7 grant is exact: forward commits to the existing branch ``codex/BAT-706-cycle37-qualified-integration``
in the existing worktree ``C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review``, continuing its current
head ``bb5253b2`` (itself two Attempt 6 appends over the preserved first candidate ``daba87f0``), on main
``55e12a5a``; shared Git objects, that worktree's index and that one branch ref only. No new branch or worktree, no
deletion, reset, rewrite, push, merge, retarget or main change.

The append is the Attempt 6 procedure (``attempt06_candidate``), unchanged in method: the candidate tree is the
repair tree with main's exact entries for the six protected review controls (the paid workflow stays absent),
materialized byte for byte into an owned view, its provenance generated there by the tree's own canonical generator,
proved against its own committed blobs before any commit, then one ``[material]`` commit whose parent is the named
current head; the ref moves with an old-value check and the worktree advances by a two-way ``read-tree -m -u`` that
never writes a protected path. Only the constants (attempt, starting head, scratch root) and the commit message
differ. The private CONTROL-07 proposal is never part of the candidate: its protected controls stay main's.
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

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt06_candidate as a6c  # noqa: E402  (the Attempt 6 append: proof, materialization, generator)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 7
TOOL_VERSION = "BAS-C37A07-INTEGRATION-CANDIDATE-APPEND-v1"
MAIN_SHA = a6c.MAIN_SHA
REPAIR_BRANCH = a6c.REPAIR_BRANCH
CANDIDATE_BRANCH = a6c.CANDIDATE_BRANCH
CANDIDATE_WORKTREE = a6c.CANDIDATE_WORKTREE
PROTECTED_PATHS = a6c.PROTECTED_PATHS
PROVENANCE_FILES = a6c.PROVENANCE_FILES
#: The preserved first candidate (every append descends from it) and the head the Attempt 7 grant names.
PRESERVED_HEAD = a6c.ISSUED_CANDIDATE_HEAD
ISSUED_CANDIDATE_HEAD = "bb5253b2be7a95026fc3c9594b244d59939816c9"
SCRATCH = Path(r"C:\BatteredAggieSyndrome.packaging\c37a07\candidate")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str, **kw: Any) -> str:
    return a6c.git(*args, **kw)


def verify_tree(revision: str, *, main: str | None = None) -> dict[str, Any]:
    return a6c.verify_tree(revision, main=main)


def entry(revision: str, path: str) -> tuple[str, str] | None:
    return a6c.entry(revision, path)


def append(record_path: Path, view_root: Path, *, previous_head: str | None = None,
           rehearsal_repair: str | None = None) -> dict[str, Any]:
    """One forward append from ``previous_head`` (the granted head ``bb5253b2`` by default)."""

    expected = previous_head or ISSUED_CANDIDATE_HEAD
    head = git("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}", check=False)
    if head != expected:
        raise SystemExit(f"{CANDIDATE_BRANCH} is at {head}, not the named previous head {expected}; refusing")
    for ancestor in (PRESERVED_HEAD, ISSUED_CANDIDATE_HEAD):
        if subprocess.run(["git", "--no-optional-locks", "-C", str(a6c.REPO), "merge-base", "--is-ancestor", ancestor,
                           head], capture_output=True, check=False).returncode != 0:
            raise SystemExit(f"{head} does not descend from {ancestor}; refusing")
    if rehearsal_repair is None and git("status", "--porcelain=v1", "-uall", repo=a6c.WORKTREE):
        raise SystemExit("the repair worktree is not clean; the candidate follows only a committed subject")
    if git("status", "--porcelain=v1", "-uall", repo=a6c.CANDIDATE_WORKTREE):
        raise SystemExit("the candidate worktree is not clean")
    if git("rev-parse", "HEAD", repo=a6c.CANDIDATE_WORKTREE) != head:
        raise SystemExit("the candidate worktree is not at the candidate branch head")
    if git("rev-parse", "refs/heads/main") != MAIN_SHA:
        raise SystemExit("main is not the issued base; refusing")
    repair = rehearsal_repair or git("rev-parse", "HEAD", repo=a6c.WORKTREE)
    if git("rev-parse", REPAIR_BRANCH) != repair:
        raise SystemExit(f"the repair subject is not at the head of {REPAIR_BRANCH}")
    if view_root.exists():
        raise SystemExit(f"{view_root} exists; the validation view is written once")
    before_refs = a6c.refs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    a6c.SCRATCH.mkdir(parents=True, exist_ok=True)
    index = a6c.SCRATCH / f"append-{stamp}.index"
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    git("read-tree", f"{repair}^{{tree}}", env=env)
    records = []
    for path in PROTECTED_PATHS:
        main_entry = entry(MAIN_SHA, path)
        records.append(f"{main_entry[0]} {main_entry[1]}\t{path}" if main_entry else f"0 {'0' * 40}\t{path}")
    git("update-index", "-z", "--index-info", env=env, stdin="".join(record + "\0" for record in records))
    base_tree = git("write-tree", env=env)
    wrong = [path for path in PROTECTED_PATHS if entry(base_tree, path) != entry(MAIN_SHA, path)]
    if wrong:
        raise SystemExit(f"the candidate tree does not carry main's entries for {wrong}; no commit was made")
    view = view_root / "tree"
    materialized = a6c.materialize(base_tree, view)
    generated = a6c.generate_in_view(view)
    provenance = {}
    for path in PROVENANCE_FILES:
        blob = git("hash-object", "-w", str(view / path))
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        provenance[path] = {"blob": blob, "sha256": hashlib.sha256((view / path).read_bytes()).hexdigest(),
                            "bytes": (view / path).stat().st_size,
                            "repair_blob": (entry(repair, path) or (None, None))[1]}
    tree = git("write-tree", env=env)
    differing = sorted(line for line in git("diff-tree", "-r", "--name-only", "--no-commit-id", f"{repair}^{{tree}}",
                                            tree).splitlines() if line)
    unexpected = sorted(set(differing) - set(PROTECTED_PATHS) - set(PROVENANCE_FILES))
    if unexpected:
        raise SystemExit(f"the candidate tree differs from the repair tree outside the protected and provenance "
                         f"paths: {unexpected[:6]}")
    proof = verify_tree(tree)
    if not proof["consistent"]:
        raise SystemExit(f"the generated provenance does not agree with the committed tree: {proof['problems']}")
    count = int(git("rev-list", "--count", f"{MAIN_SHA}..{repair}"))
    message = a6c.SCRATCH / f"append-{stamp}.message.txt"
    message.write_text(
        "[material] carry the Attempt 7 lineage and storage repairs onto the candidate with provenance generated from "
        "its own tree (BAT-706, MF37A06-01, MF37A06-02)\n\n"
        f"The tree of {REPAIR_BRANCH} at {repair},\n"
        f"as one forward commit on the candidate {head[:8]}, prepared locally under the Cycle 37 Attempt 7\n"
        "append grant. Nothing is pushed or merged; the repair branch, main and every earlier candidate commit\n"
        f"(the preserved first candidate {PRESERVED_HEAD[:8]} included) keep their commits.\n\n"
        "The protected scientific-review controls keep main's exact bytes (the paid workflow stays absent); the\n"
        "private CONTROL-07 proposal is not part of this tree. The provenance files are generated by the tree's own\n"
        "canonical generator from a byte-for-byte materialization of this tree and proved against its committed\n"
        "blobs.\n\n"
        f"Repair-branch commits over main (not in the candidate's history): {count}.\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n", encoding="utf-8", newline="\n")
    commit = git("commit-tree", tree, "-p", head, "-F", str(message))
    git("update-index", "-q", "--refresh", repo=a6c.CANDIDATE_WORKTREE)
    git("read-tree", "-m", "-u", "-n", head, commit, repo=a6c.CANDIDATE_WORKTREE)
    git("update-ref", "-m", "Cycle #37 Attempt #7 append (MF37A06-01, MF37A06-02)", f"refs/heads/{CANDIDATE_BRANCH}",
        commit, head)
    git("read-tree", "-m", "-u", head, commit, repo=a6c.CANDIDATE_WORKTREE)
    skip = git("ls-files", "-v", "--", *PROTECTED_PATHS, repo=a6c.CANDIDATE_WORKTREE).splitlines()
    written = [path for path in PROTECTED_PATHS if (a6c.CANDIDATE_WORKTREE / path).exists()]
    status = git("status", "--porcelain=v1", "-uall", repo=a6c.CANDIDATE_WORKTREE)
    after_refs = a6c.refs()
    changed_refs = sorted(name for name in set(before_refs) | set(after_refs) if before_refs.get(name) != after_refs.get(name))
    record = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS_LOCAL_WORK_REMAINS (candidate append)",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "tool_version": TOOL_VERSION,
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "created_at": utc_now(),
        "repair_head": repair, "previous_candidate_head": head, "candidate_commit": commit, "candidate_tree": tree,
        "preserved_first_candidate": PRESERVED_HEAD, "attempt7_start_head": ISSUED_CANDIDATE_HEAD,
        "base_tree_before_provenance": base_tree, "private_index_file": str(index), "message_file": str(message),
        "message_sha256": hashlib.sha256(message.read_bytes()).hexdigest(),
        "validation_view": {**materialized, **generated, "state": "inert byte copies of the candidate tree; retained"},
        "provenance_files": provenance, "tree_differs_from_repair_in": differing, "committed_tree_proof": proof,
        "worktree": {"skip_worktree_entries": skip, "protected_paths_written_to_disk": written,
                     "status_after": status.splitlines(), "head_after": git("rev-parse", "HEAD", repo=a6c.CANDIDATE_WORKTREE)},
        "refs_changed": changed_refs, "only_the_candidate_ref_changed": changed_refs == [f"refs/heads/{CANDIDATE_BRANCH}"],
        "previous_head_is_parent": git("rev-list", "--parents", "-n", "1", commit).split()[1:] == [head],
        "rehearsal": rehearsal_repair is not None, "repository": str(a6c.REPO),
        "not_done": "No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation.",
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def rehearse(scratch: Path, repair: str) -> dict[str, Any]:
    """Rehearsal only: the same append in a scratch repository borrowing the shared objects read-only, holding its
    own main, repair and candidate refs (the candidate at ``bb5253b2``); the granted candidate is never touched."""

    if scratch.exists():
        raise SystemExit(f"{scratch} exists; a rehearsal is written once")
    common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir", repo=a6c.WORKTREE))
    repo = scratch / "repo.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(repo)], check=True, capture_output=True)
    (repo / "objects" / "info" / "alternates").write_text((common / "objects").as_posix() + "\n", encoding="utf-8",
                                                         newline="\n")
    for ref, sha in (("refs/heads/main", MAIN_SHA), (f"refs/heads/{REPAIR_BRANCH}", repair),
                     (f"refs/heads/{CANDIDATE_BRANCH}", ISSUED_CANDIDATE_HEAD)):
        git("update-ref", ref, sha, repo=repo)
    a6c.REPO, a6c.CANDIDATE_WORKTREE, a6c.SCRATCH = repo, scratch / "w", scratch / "index"
    git("worktree", "add", "--no-checkout", str(a6c.CANDIDATE_WORKTREE), CANDIDATE_BRANCH)
    git("read-tree", "HEAD", repo=a6c.CANDIDATE_WORKTREE)
    present = [path for path in PROTECTED_PATHS if entry(ISSUED_CANDIDATE_HEAD, path) is not None]
    git("update-index", "--skip-worktree", "--", *present, repo=a6c.CANDIDATE_WORKTREE)
    git("checkout-index", "--all", repo=a6c.CANDIDATE_WORKTREE)
    record = append(scratch / "records" / "CANDIDATE_APPEND_REHEARSAL.json", scratch / "v", rehearsal_repair=repair)
    return {"scratch_repository": str(repo), "candidate_worktree": str(a6c.CANDIDATE_WORKTREE), "append": record,
            "meaning": "A rehearsal of the append in a scratch repository; the granted append is made separately."}


def describe() -> dict[str, Any]:
    record = a6c.describe()
    head = record.get("candidate_head")
    record["attempt7_start_head"] = ISSUED_CANDIDATE_HEAD
    record["attempt7_start_is_ancestor"] = bool(head) and subprocess.run(
        ["git", "--no-optional-locks", "-C", str(a6c.REPO), "merge-base", "--is-ancestor", ISSUED_CANDIDATE_HEAD, head],
        capture_output=True, check=False).returncode == 0
    return record


def main(argv: list[str] | None = None) -> int:
    a6c.SCRATCH = SCRATCH
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    made = sub.add_parser("append")
    made.add_argument("--record", type=Path, required=True)
    made.add_argument("--view-root", type=Path, required=True)
    made.add_argument("--previous-head", default=None,
                      help="the current candidate head a later append continues (default: the granted head)")
    sub.add_parser("describe")
    rehearsed = sub.add_parser("rehearse")
    rehearsed.add_argument("--scratch", type=Path, required=True)
    rehearsed.add_argument("--repair", required=True)
    checked = sub.add_parser("verify-tree")
    checked.add_argument("revision")
    args = parser.parse_args(argv)
    if args.mode == "append":
        result = append(args.record, args.view_root, previous_head=args.previous_head)
    elif args.mode == "rehearse":
        result = rehearse(args.scratch, args.repair)
    elif args.mode == "verify-tree":
        result = verify_tree(args.revision)
    else:
        result = describe()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if args.mode != "verify-tree" or result["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
