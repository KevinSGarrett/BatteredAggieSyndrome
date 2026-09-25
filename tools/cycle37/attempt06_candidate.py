r"""Cycle #37 — Attempt #6 — append the repair and correct provenance to the preserved local candidate (MF37A05-02).

    attempt06_candidate.py append --record <new file> --view-root <new owned directory>
    attempt06_candidate.py describe
    attempt06_candidate.py verify-tree <commit>

The grant is exact: forward commits to the existing branch ``codex/BAT-706-cycle37-qualified-integration`` in the
existing worktree ``C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review``, starting at ``daba87f0`` on main
``55e12a5a``; shared Git objects, that worktree's index and that one branch ref only. No new branch or worktree, no
deletion, reset, rewrite, push, merge or main change.

``daba87f0`` kept main's bytes for the six protected review controls but committed the repair branch's provenance,
which lists the repair branch's blobs for three of them and a paid workflow absent from the tree. The appended
commit carries the final repair tree with the same protected entries (main's exact blobs, the absent workflow
still absent) and provenance generated *for its own committed tree*:

1. the candidate tree is written through a private index (the repair tree, then main's protected entries);
2. that tree is materialized, byte for byte, into a bounded owned view under the validation root -- the protected
   files there are inert copies of main's blobs, read by the generator and never executed;
3. the canonical generator (``tools/repo_integrity.write_manifest`` from that same tree) writes
   ``provenance/CURRENT_TREE.txt``, ``PROJECT_FILE_MANIFEST.csv`` and ``PROJECT_FILE_HASHES.sha256`` in the view;
4. those three files replace the repair branch's in the private index, and the resulting tree is proved against
   its own Git blobs by an independent computation (every path, byte count and SHA-256 from ``git cat-file``, not
   from any file on disk) before any commit is made;
5. one ``[material]`` commit with parent ``daba87f0`` is written, the branch ref moves forward with an old-value
   check, and the existing worktree is advanced by a two-way ``read-tree -m -u`` that never writes a protected path
   (they are identical in both trees and stay skip-worktree).

``verify-tree`` repeats step 4 for any commit: a changed or absent committed path, a stale generated view or a
path hidden by skip-worktree cannot pass it, because it reads only committed blobs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt05_candidate as a5c  # noqa: E402  (the Attempt 5 candidate tool: constants and Git helpers)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 6
TOOL_VERSION = "BAS-C37A06-INTEGRATION-CANDIDATE-APPEND-v1"
WORKTREE = Path(__file__).resolve().parents[2]
REPO = WORKTREE
MAIN_SHA = a5c.MAIN_SHA
REPAIR_BRANCH = a5c.REPAIR_BRANCH
CANDIDATE_BRANCH = a5c.CANDIDATE_BRANCH
CANDIDATE_WORKTREE = a5c.CANDIDATE_WORKTREE
PROTECTED_PATHS = a5c.PROTECTED_PATHS
#: The candidate head the grant names; the append is made exactly once, from it.
ISSUED_CANDIDATE_HEAD = "daba87f012291f5f8d8def001d89b9e47c506a43"
PROVENANCE_FILES = ("provenance/CURRENT_TREE.txt", "provenance/PROJECT_FILE_MANIFEST.csv",
                    "provenance/PROJECT_FILE_HASHES.sha256")
MANIFEST_EXCLUDE = ("provenance/PROJECT_FILE_MANIFEST.csv", "provenance/PROJECT_FILE_HASHES.sha256")
SCRATCH = Path(r"C:\BatteredAggieSyndrome.packaging\c37a06\candidate")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str, repo: Path | None = None, env: dict[str, str] | None = None, check: bool = True,
        stdin: str | None = None) -> str:
    return a5c.git(*args, repo=repo or REPO, env=env, check=check, stdin=stdin)


def git_bytes(*args: str, repo: Path | None = None) -> bytes:
    completed = subprocess.run(["git", "--no-optional-locks", "-C", str(repo or REPO), *args], capture_output=True,
                               check=False)
    if completed.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr[-400:]!r}")
    return completed.stdout


def entry(revision: str, path: str) -> tuple[str, str] | None:
    # No "--": the lanes' write guard admits ls-tree positionals but not a pathspec separator.
    line = git("ls-tree", revision, path)
    if not line:
        return None
    meta, _name = line.split("\t", 1)
    mode, _kind, blob = meta.split()
    return mode, blob


def refs() -> dict[str, str]:
    return dict(line.split(" ", 1)[::-1] for line in git("for-each-ref", "--format=%(objectname) %(refname)").splitlines())


# ------------------------------------------------------------------------------ committed-tree proof


def tree_blobs(revision: str) -> dict[str, dict[str, Any]]:
    """Every path of ``revision`` with its mode, byte count and SHA-256, read from Git blobs alone."""

    listing = git_bytes("ls-tree", "-r", "-z", "--full-tree", revision).split(b"\0")
    entries = {}
    for item in listing:
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        if kind != "blob":
            continue
        entries[path.decode("utf-8", "surrogateescape")] = {"mode": mode, "blob": blob}
    # One batch process for every blob: sizes and SHA-256 of the committed bytes.
    order = sorted(entries)
    request = "".join(entries[path]["blob"] + "\n" for path in order).encode()
    process = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "cat-file", "--batch"], input=request,
                             capture_output=True, check=True)
    data = process.stdout
    offset = 0
    for path in order:
        header_end = data.index(b"\n", offset)
        blob, kind, size = data[offset:header_end].decode().split()
        start = header_end + 1
        content = data[start:start + int(size)]
        offset = start + int(size) + 1
        entries[path].update(bytes=int(size), sha256=hashlib.sha256(content).hexdigest())
    return entries


def verify_tree(revision: str, *, main: str | None = None) -> dict[str, Any]:
    """The committed provenance of ``revision`` against the blobs ``revision`` actually carries, and its protected
    entries against ``main`` (the issued main by default)."""

    main = main or MAIN_SHA
    blobs = tree_blobs(revision)
    problems: list[str] = []
    manifest_text = git_bytes("show", f"{revision}:provenance/PROJECT_FILE_MANIFEST.csv").decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(manifest_text)))
    manifest = {row["path"]: row for row in rows}
    expected_paths = sorted(set(blobs) - set(MANIFEST_EXCLUDE))
    missing = sorted(set(expected_paths) - set(manifest))
    extra = sorted(set(manifest) - set(expected_paths))
    changed = sorted(path for path in set(manifest) & set(expected_paths)
                     if manifest[path]["sha256"] != blobs[path]["sha256"]
                     or int(manifest[path]["bytes"]) != blobs[path]["bytes"])
    for label, items in (("committed paths absent from the manifest", missing),
                         ("manifest paths absent from the committed tree", extra),
                         ("manifest rows whose bytes or SHA-256 differ from the committed blob", changed)):
        if items:
            problems.append(f"{len(items)} {label}: {items[:6]}")
    hashes_text = git_bytes("show", f"{revision}:provenance/PROJECT_FILE_HASHES.sha256").decode("utf-8")
    hash_rows = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in hashes_text.splitlines() if line.strip()}
    if hash_rows != {path: row["sha256"] for path, row in manifest.items()}:
        problems.append("PROJECT_FILE_HASHES.sha256 does not repeat the manifest's rows")
    tree_text = git_bytes("show", f"{revision}:provenance/CURRENT_TREE.txt").decode("utf-8")
    listed = [line for line in tree_text.splitlines() if line]
    wanted = sorted(set(blobs) - {"provenance/CURRENT_TREE.txt"})
    if listed != wanted:
        problems.append(f"CURRENT_TREE.txt lists {len(listed)} paths; the committed tree has {len(wanted)} "
                        f"(missing {sorted(set(wanted) - set(listed))[:4]}, extra {sorted(set(listed) - set(wanted))[:4]})")
    protected = [{"path": path, "entry": entry(revision, path), "main": entry(main, path)} for path in PROTECTED_PATHS]
    if any(row["entry"] != row["main"] for row in protected):
        problems.append(f"protected entries differ from main: {[r['path'] for r in protected if r['entry'] != r['main']]}")
    return {"revision": revision, "main": main, "tree": git("rev-parse", f"{revision}^{{tree}}"),
            "committed_paths": len(blobs),
            "manifest_rows": len(rows), "hash_rows": len(hash_rows), "current_tree_rows": len(listed),
            "committed_absent_from_manifest": missing, "manifest_absent_from_tree": extra,
            "manifest_rows_differing_from_blobs": changed, "protected_entries": protected,
            "protected_entries_equal_main": all(row["entry"] == row["main"] for row in protected),
            "method": ("every path, byte count and SHA-256 read from the committed Git blobs with git cat-file; no file "
                       "on disk is read, so skip-worktree or absent working files cannot mask a mismatch"),
            "problems": problems, "consistent": not problems}


# ------------------------------------------------------------------------------ append


def materialize(tree: str, view: Path) -> dict[str, Any]:
    """Extract ``tree`` byte for byte into ``view`` (streamed; no archive file is kept)."""

    view.mkdir(parents=True)
    process = subprocess.Popen(["git", "--no-optional-locks", "-C", str(REPO), "archive", "--format=tar", tree],
                               stdout=subprocess.PIPE)
    count = 0
    with tarfile.open(fileobj=process.stdout, mode="r|") as bundle:
        for member in bundle:
            bundle.extract(member, view, filter="data")
            count += member.isfile()
    if process.wait() != 0:
        raise SystemExit("git archive of the candidate tree failed")
    return {"view": str(view), "files": count}


def generate_in_view(view: Path) -> dict[str, Any]:
    """The canonical generator of the materialized tree itself, run in the view with no source outside it."""

    code = ("import sys; from pathlib import Path; root = Path(sys.argv[1]); "
            "sys.path[:0] = [str(root), str(root / 'src')]; "
            "from tools.repo_integrity import write_manifest; rows, fingerprint = write_manifest(root); "
            "print(len(rows), fingerprint)")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", GIT_CEILING_DIRECTORIES=str(view.parent))
    env.pop("PYTHONPATH", None)
    completed = subprocess.run([sys.executable, "-B", "-c", code, str(view)], cwd=str(view), env=env,
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"the canonical generator failed in the view: {completed.stderr[-800:]}")
    rows, fingerprint = completed.stdout.split()
    return {"generator": str(view / "tools" / "repo_integrity.py"), "generator_sha256": hashlib.sha256(
        (view / "tools" / "repo_integrity.py").read_bytes()).hexdigest(), "manifest_rows": int(rows),
            "tree_fingerprint": fingerprint, "git_enumeration": "none (the view is not a repository; files enumerated)"}


def append(record_path: Path, view_root: Path, *, rehearsal_repair: str | None = None,
           previous_head: str | None = None) -> dict[str, Any]:
    """One forward append. ``previous_head`` names the head the caller appends to (the issued head by default); a
    later append must name the current head exactly and descend from the issued head, so no append is repeated or
    skipped. ``rehearsal_repair`` is set only by :func:`rehearse`, whose scratch repository holds the repair ref
    itself; the granted append takes the repair worktree's clean committed head."""

    expected = previous_head or ISSUED_CANDIDATE_HEAD
    head = git("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}", check=False)
    if head != expected:
        raise SystemExit(f"{CANDIDATE_BRANCH} is at {head}, not the named previous head {expected}; refusing")
    if subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "merge-base", "--is-ancestor",
                       ISSUED_CANDIDATE_HEAD, head], capture_output=True, check=False).returncode != 0:
        raise SystemExit(f"{head} does not descend from the preserved candidate {ISSUED_CANDIDATE_HEAD}; refusing")
    if rehearsal_repair is None and git("status", "--porcelain=v1", "-uall", repo=WORKTREE):
        raise SystemExit("the repair worktree is not clean; the candidate follows only a committed subject")
    if git("status", "--porcelain=v1", "-uall", repo=CANDIDATE_WORKTREE):
        raise SystemExit("the candidate worktree is not clean")
    if git("rev-parse", "HEAD", repo=CANDIDATE_WORKTREE) != head:
        raise SystemExit("the candidate worktree is not at the candidate branch head")
    if git("rev-parse", "refs/heads/main") != MAIN_SHA:
        raise SystemExit("main is not the issued base; refusing")
    repair = rehearsal_repair or git("rev-parse", "HEAD", repo=WORKTREE)
    if git("rev-parse", REPAIR_BRANCH) != repair:
        raise SystemExit(f"the repair subject is not at the head of {REPAIR_BRANCH}")
    if view_root.exists():
        raise SystemExit(f"{view_root} exists; the validation view is written once")
    before_refs = refs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    index = SCRATCH / f"append-{stamp}.index"
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
    materialized = materialize(base_tree, view)
    generated = generate_in_view(view)
    provenance = {}
    for path in PROVENANCE_FILES:
        blob = git("hash-object", "-w", str(view / path))
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        provenance[path] = {"blob": blob, "sha256": hashlib.sha256((view / path).read_bytes()).hexdigest(),
                            "bytes": (view / path).stat().st_size,
                            "repair_blob": (entry(repair, path) or (None, None))[1]}
    tree = git("write-tree", env=env)
    # The tree differs from the repair tree only in the protected entries and the three provenance files.
    differing = sorted(line for line in git("diff-tree", "-r", "--name-only", "--no-commit-id", f"{repair}^{{tree}}",
                                            tree).splitlines() if line)
    unexpected = sorted(set(differing) - set(PROTECTED_PATHS) - set(PROVENANCE_FILES))
    if unexpected:
        raise SystemExit(f"the candidate tree differs from the repair tree outside the protected and provenance "
                         f"paths: {unexpected[:6]}")
    proof = verify_tree(tree)
    if not proof["consistent"]:
        raise SystemExit(f"the generated provenance does not agree with the committed tree: {proof['problems']}")
    count = int(git("rev-list", "--count", f"{head}..{repair}"))
    message = SCRATCH / f"append-{stamp}.message.txt"
    message.write_text(
        "[material] carry the Attempt 6 repairs onto the candidate with provenance generated from its own tree "
        "(BAT-706, MF37A05-02)\n\n"
        f"The tree of {REPAIR_BRANCH} at {repair},\n"
        f"as one forward commit on the preserved candidate {head[:8]}, prepared locally under the Cycle 37\n"
        "Attempt 6 append grant. Nothing is pushed or merged; the repair branch, main and the candidate's\n"
        "first commit keep their commits.\n\n"
        "The protected scientific-review controls keep main's exact bytes (the paid workflow stays absent).\n"
        "The provenance files are generated by the tree's own canonical generator from a byte-for-byte\n"
        "materialization of this tree and proved against its committed blobs; the repair branch's provenance,\n"
        "which names its own control blobs, is not carried.\n\n"
        f"Repair-branch commits consolidated (not in the candidate's history): {count}.\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n", encoding="utf-8", newline="\n")
    commit = git("commit-tree", tree, "-p", head, "-F", str(message))
    # The worktree's index may carry stale stat data from its first population (checkout-index does not record
    # it), which a two-way merge reads as "not uptodate". Refresh only that stat data, then prove the merge in a
    # dry run before the ref moves, so a refused merge can never leave the ref ahead of the worktree.
    git("update-index", "-q", "--refresh", repo=CANDIDATE_WORKTREE)
    git("read-tree", "-m", "-u", "-n", head, commit, repo=CANDIDATE_WORKTREE)
    git("update-ref", "-m", "Cycle #37 Attempt #6 append (MF37A05-02)", f"refs/heads/{CANDIDATE_BRANCH}", commit, head)
    # Advance the existing worktree's index and files; protected entries are identical in both trees and stay
    # skip-worktree, so none of them is written.
    git("read-tree", "-m", "-u", head, commit, repo=CANDIDATE_WORKTREE)
    skip = git("ls-files", "-v", "--", *PROTECTED_PATHS, repo=CANDIDATE_WORKTREE).splitlines()
    written = [path for path in PROTECTED_PATHS if (CANDIDATE_WORKTREE / path).exists()]
    status = git("status", "--porcelain=v1", "-uall", repo=CANDIDATE_WORKTREE)
    after_refs = refs()
    changed_refs = sorted(name for name in set(before_refs) | set(after_refs)
                          if before_refs.get(name) != after_refs.get(name))
    record = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS_LOCAL_WORK_REMAINS (candidate "
                 "append)",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "tool_version": TOOL_VERSION,
        "created_at": utc_now(), "repair_head": repair, "previous_candidate_head": head, "candidate_commit": commit,
        "candidate_tree": tree, "base_tree_before_provenance": base_tree, "private_index_file": str(index),
        "message_file": str(message), "message_sha256": hashlib.sha256(message.read_bytes()).hexdigest(),
        "validation_view": {**materialized, **generated, "state": "inert byte copies of the candidate tree; retained"},
        "provenance_files": provenance, "tree_differs_from_repair_in": differing,
        "committed_tree_proof": proof,
        "worktree": {"skip_worktree_entries": skip, "protected_paths_written_to_disk": written,
                     "status_after": status.splitlines(),
                     "head_after": git("rev-parse", "HEAD", repo=CANDIDATE_WORKTREE)},
        "refs_changed": changed_refs,
        "only_the_candidate_ref_changed": changed_refs == [f"refs/heads/{CANDIDATE_BRANCH}"],
        "previous_head_is_parent": git("rev-list", "--parents", "-n", "1", commit).split()[1:] == [head],
        "rehearsal": rehearsal_repair is not None, "repository": str(REPO),
        "not_done": "No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation.",
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return record


def rehearse(scratch: Path, repair: str) -> dict[str, Any]:
    """Rehearsal only: the same append in a scratch repository that borrows the shared objects read-only
    (objects/info/alternates) and holds its own main, repair and candidate refs, with a scratch checkout of the issued
    candidate prepared exactly as the preserved one was (protected entries skip-worktree, never on disk). Nothing is
    written to the shared repository, its refs or the preserved candidate worktree."""

    global REPO, CANDIDATE_WORKTREE, SCRATCH
    if scratch.exists():
        raise SystemExit(f"{scratch} exists; a rehearsal is written once")
    common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir", repo=WORKTREE))
    repo = scratch / "repo.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(repo)], check=True, capture_output=True)
    # LF only: git reads a CRLF line as an object directory whose name ends in a carriage return.
    (repo / "objects" / "info" / "alternates").write_text((common / "objects").as_posix() + "\n", encoding="utf-8",
                                                         newline="\n")
    for ref, sha in (("refs/heads/main", MAIN_SHA), (f"refs/heads/{REPAIR_BRANCH}", repair),
                     (f"refs/heads/{CANDIDATE_BRANCH}", ISSUED_CANDIDATE_HEAD)):
        git("update-ref", ref, sha, repo=repo)
    REPO, CANDIDATE_WORKTREE, SCRATCH = repo, scratch / "w", scratch / "index"
    git("worktree", "add", "--no-checkout", str(CANDIDATE_WORKTREE), CANDIDATE_BRANCH)
    git("read-tree", "HEAD", repo=CANDIDATE_WORKTREE)
    present = [path for path in PROTECTED_PATHS if entry(ISSUED_CANDIDATE_HEAD, path) is not None]
    git("update-index", "--skip-worktree", "--", *present, repo=CANDIDATE_WORKTREE)
    git("checkout-index", "--all", repo=CANDIDATE_WORKTREE)
    prepared = {"skip_worktree": git("ls-files", "-v", "--", *present, repo=CANDIDATE_WORKTREE).splitlines(),
                "status": git("status", "--porcelain=v1", "-uall", repo=CANDIDATE_WORKTREE).splitlines()}
    record = append(scratch / "records" / "CANDIDATE_APPEND_REHEARSAL.json", scratch / "v", rehearsal_repair=repair)
    return {"scratch_repository": str(repo), "borrowed_objects": str(common / "objects"),
            "candidate_worktree": str(CANDIDATE_WORKTREE), "prepared_checkout": prepared, "append": record,
            "meaning": "A rehearsal of the append in a scratch repository; the granted append is made separately."}


def describe() -> dict[str, Any]:
    head = git("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}", check=False)
    repair = git("rev-parse", REPAIR_BRANCH)
    record: dict[str, Any] = {"candidate_branch": CANDIDATE_BRANCH, "candidate_head": head or None,
                              "candidate_worktree": str(CANDIDATE_WORKTREE), "main": MAIN_SHA,
                              "main_ref": git("rev-parse", "refs/heads/main"), "repair_branch": REPAIR_BRANCH,
                              "repair_head": repair, "repair_tree": git("rev-parse", f"{repair}^{{tree}}"),
                              "issued_candidate_head": ISSUED_CANDIDATE_HEAD}
    if not head:
        return record
    record["candidate_tree"] = git("rev-parse", f"{head}^{{tree}}")
    record["candidate_parents"] = git("rev-list", "--parents", "-n", "1", head).split()[1:]
    record["candidate_first_parent_chain"] = git("rev-list", "--first-parent", f"{MAIN_SHA}..{head}").splitlines()
    record["issued_head_is_ancestor"] = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(REPO), "merge-base", "--is-ancestor", ISSUED_CANDIDATE_HEAD, head],
        capture_output=True, check=False).returncode == 0
    record["candidate_subject"] = git("log", "-1", "--format=%s", head)
    changed = [line for line in git("diff-tree", "-r", "--name-only", "--no-commit-id", record["repair_tree"],
                                    record["candidate_tree"]).splitlines() if line.strip()]
    record["paths_differing_from_the_repair_tree"] = changed
    record["protected_paths"] = [{"path": path, "main": entry(MAIN_SHA, path), "repair": entry(repair, path),
                                  "candidate": entry(head, path)} for path in PROTECTED_PATHS]
    record["protected_paths_equal_main"] = all(row["candidate"] == row["main"] for row in record["protected_paths"])
    record["only_protected_and_provenance_paths_differ"] = set(changed) <= set(PROTECTED_PATHS) | set(PROVENANCE_FILES)
    record["files_changed_against_main"] = len([line for line in git("diff-tree", "-r", "--name-only",
                                                                       "--no-commit-id", MAIN_SHA,
                                                                       record["candidate_tree"]).splitlines() if line])
    record["repair_commits_consolidated"] = int(git("rev-list", "--count", f"{MAIN_SHA}..{repair}"))
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    made = sub.add_parser("append")
    made.add_argument("--record", type=Path, required=True)
    made.add_argument("--view-root", type=Path, required=True)
    made.add_argument("--previous-head", default=None,
                      help="the current candidate head a later append continues (default: the issued head)")
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
