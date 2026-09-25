r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-13-AC01 / AC02: refresh the five organization heads and the AREA24
owner documents, read-only, and say exactly what changed.

AC01 asks for the five GridironCortex heads and the relevant local clone
states, and for the CURRENT AREA24 owners 00-21 with their capability
suffixes 0574-0595 -- not the twelve historical recovery aliases treated as
the whole program. AC02 asks for the manager's 34-file hashes to be compared,
changed sections reread, and dirty trees preserved.

What this does, and the one network read it relies on:

* **Remote heads** come from one GraphQL read that returns all five
  repositories' default-branch heads and releases in a single request. The
  response is passed in with ``--remote`` so the request is counted once in
  the attempt ledger and not repeated here.
* **Local clone state** is read with ``git rev-parse``, ``git status`` and
  ``git cat-file``. Nothing is fetched, checked out or written; a dirty clone
  stays dirty and its working tree is never read for content.
* **The 34 files** are compared three ways: the manager's recorded sha256,
  the sha256 of the manager's snapshot bytes on disk, and the sha256 of the
  blob at the manager's revision taken from the local clone's object store
  with ``git show <rev>:<path>``. Because the remote head is re-verified in
  the same run, "the blob at that revision" is also "what the remote serves
  now" whenever the head has not moved.
* **Current versus alias** is read from the owner table in
  ``00_BAS_FILM_INTEGRATION_MASTER.md`` at that revision and from
  ``generated/CAPABILITY_TO_EPIC.yaml``, not asserted from filenames.

Nothing outside ``--out`` is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True

REPOSITORIES = (
    "CFBProgramSpecifications",
    "CFBIntelligenceContracts",
    "CFBFilmAssemblyLine",
    "CFBFilmIntelligence",
    "CFBProgramOps",
)

#: The manager's observed heads, as ALL22_ALIGNMENT.md records them.
MANAGER_OBSERVED = {
    "CFBProgramSpecifications": "886e277dd9f34eb0ea1de78f98ee516bcc0c33cb",
    "CFBIntelligenceContracts": "a14acac36545b56cc5808614d1c8f4608b10ce4e",
    "CFBFilmAssemblyLine": "5ad91f8029286617937ab366682360443175dc6c",
    "CFBFilmIntelligence": "44a59b64a7950e30c0cca6249cdf75fd046a6ce2",
    "CFBProgramOps": "8cd836da83a76b3db756cd35f685d2107f94e219",
}

AREA_PREFIX = "50_BAS_INTEGRATION/"


def git(repo: Path, *args: str) -> tuple[int, bytes]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, timeout=300
    )
    return completed.returncode, completed.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clone_state(repo: Path) -> dict[str, Any]:
    if not repo.exists():
        return {"path": str(repo), "exists": False}
    code, head = git(repo, "rev-parse", "HEAD")
    _, status = git(repo, "status", "--porcelain=v1", "-z")
    entries = [e for e in status.decode("utf-8", "replace").split("\0") if e.strip()]
    _, url = git(repo, "remote", "get-url", "origin")
    return {
        "path": str(repo),
        "exists": True,
        "head": head.decode().strip() if code == 0 else None,
        "origin": url.decode().strip(),
        "dirty_entries": len(entries),
        "working_tree_read": False,
    }


def has_object(repo: Path, oid: str) -> bool:
    code, _ = git(repo, "cat-file", "-e", f"{oid}^{{commit}}")
    return code == 0


def owner_table(master: str) -> dict[str, str]:
    """Current owner number -> filename, from the master's own table."""

    owners = {}
    for match in re.finditer(r"^\|\s*(\d{2})\s*\|\s*`([^`]+\.md)`", master, re.M):
        owners[match.group(1)] = match.group(2)
    return owners


def capability_map(yaml_text: str) -> dict[str, str]:
    """Owner number -> capability id, for the AREA24 integration block."""

    found = {}
    for match in re.finditer(r"capability_id:\s*(CAP-BAS-INTEGRAT-(\d{2})-[A-Z0-9-]+-(\d{4}))", yaml_text):
        found[match.group(2)] = match.group(1)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--remote", type=Path, required=True,
                        help="The single GraphQL response for the five repositories.")
    parser.add_argument("--clone-root", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    remote_doc = json.loads(args.remote.read_text(encoding="utf-8"))
    remote: dict[str, dict[str, Any]] = {}
    for node in (remote_doc.get("data") or {}).values():
        if not node:
            continue
        name = node["nameWithOwner"].split("/", 1)[1]
        target = (node.get("defaultBranchRef") or {}).get("target") or {}
        remote[name] = {
            "name_with_owner": node["nameWithOwner"],
            "private": node.get("isPrivate"),
            "default_branch": (node.get("defaultBranchRef") or {}).get("name"),
            "head": target.get("oid"),
            "head_committed": target.get("committedDate"),
            "releases": [
                {
                    "tag": rel["tagName"],
                    "created": rel["createdAt"],
                    "tag_commit": (rel.get("tagCommit") or {}).get("oid"),
                    "assets": [
                        {"name": a["name"], "size": a["size"], "digest": a.get("digest")}
                        for a in rel["releaseAssets"]["nodes"]
                    ],
                }
                for rel in node["releases"]["nodes"]
            ],
        }

    repositories = []
    for name in REPOSITORIES:
        clones = [clone_state(root / name) for root in args.clone_root]
        head = (remote.get(name) or {}).get("head")
        for clone in clones:
            if clone.get("exists") and head:
                clone["contains_remote_head_object"] = has_object(Path(clone["path"]), head)
                clone["at_remote_head"] = clone.get("head") == head
        observed = MANAGER_OBSERVED[name]
        repositories.append(
            {
                "repository": name,
                "remote": remote.get(name),
                "remote_visible": name in remote,
                "manager_observed_head": observed,
                "remote_head_equals_manager_observed": head == observed,
                "state": (
                    "UNCHANGED_SINCE_MANAGER_SNAPSHOT"
                    if head == observed
                    else "MOVED_SINCE_MANAGER_SNAPSHOT"
                    if head
                    else "NOT_VISIBLE"
                ),
                "local_clones": clones,
            }
        )

    # ------------------------------------------------ the 34 AREA24 files
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    refs = [r for r in contract.get("source_refs") or [] if str(r.get("id", "")).startswith("AREA24-")]
    spec_head = MANAGER_OBSERVED["CFBProgramSpecifications"]
    spec_clone = next(
        (Path(c["path"]) for r in repositories if r["repository"] == "CFBProgramSpecifications"
         for c in r["local_clones"] if c.get("exists") and c.get("contains_remote_head_object")),
        None,
    )
    master_text = yaml_text = ""
    if spec_clone is not None:
        _, master = git(spec_clone, "show", f"{spec_head}:{AREA_PREFIX}00_BAS_FILM_INTEGRATION_MASTER.md")
        _, yaml_bytes = git(spec_clone, "show", f"{spec_head}:generated/CAPABILITY_TO_EPIC.yaml")
        master_text = master.decode("utf-8", "replace")
        yaml_text = yaml_bytes.decode("utf-8", "replace")
    owners = owner_table(master_text)
    capabilities = capability_map(yaml_text)
    owner_by_file = {filename: number for number, filename in owners.items()}

    files = []
    for ref in refs:
        snapshot = Path(ref["path"])
        filename = snapshot.name
        snapshot_bytes = snapshot.read_bytes() if snapshot.is_file() else None
        blob_digest = None
        if spec_clone is not None:
            code, blob = git(spec_clone, "show", f"{spec_head}:{AREA_PREFIX}{filename}")
            blob_digest = sha256(blob) if code == 0 else None
        number = owner_by_file.get(filename)
        role = "CURRENT_OWNER" if number is not None else "HISTORICAL_RECOVERY_ALIAS"
        recorded = ref.get("sha256")
        files.append(
            {
                "source_ref": ref["id"],
                "file": AREA_PREFIX + filename,
                "role": role,
                "owner_number": number,
                "capability_id": capabilities.get(number) if number else None,
                "manager_recorded_sha256": recorded,
                "snapshot_sha256": sha256(snapshot_bytes) if snapshot_bytes is not None else None,
                "blob_at_manager_revision_sha256": blob_digest,
                "snapshot_matches_record": snapshot_bytes is not None and sha256(snapshot_bytes) == recorded,
                "revision_blob_matches_record": blob_digest == recorded,
                "changed": not (blob_digest == recorded and snapshot_bytes is not None
                                and sha256(snapshot_bytes) == recorded),
            }
        )

    spec_remote = next(r for r in repositories if r["repository"] == "CFBProgramSpecifications")
    current = [f for f in files if f["role"] == "CURRENT_OWNER"]
    aliases = [f for f in files if f["role"] == "HISTORICAL_RECOVERY_ALIAS"]
    suffixes = sorted(int(f["capability_id"][-4:]) for f in current if f["capability_id"])
    changed = [f for f in files if f["changed"]]

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-13",
        "acceptance": ["R37-13-AC01", "R37-13-AC02", "R37-01-AC03"],
        "remote_read": {
            "path": str(args.remote),
            "sha256": sha256(args.remote.read_bytes()),
            "requests": 1,
            "note": "One GraphQL read for all five repositories, counted once in the attempt ledger.",
        },
        "repositories": repositories,
        "moved_since_manager_snapshot": [
            r["repository"] for r in repositories if r["state"] == "MOVED_SINCE_MANAGER_SNAPSHOT"
        ],
        "area24": {
            "manager_revision": spec_head,
            "remote_head_still_at_manager_revision": spec_remote["remote_head_equals_manager_observed"],
            "read_from_clone": str(spec_clone) if spec_clone else None,
            "files_compared": len(files),
            "current_owners": len(current),
            "historical_recovery_aliases": len(aliases),
            "current_owner_capability_suffixes": [suffixes[0], suffixes[-1]] if suffixes else None,
            "capability_suffixes_contiguous": suffixes == list(range(suffixes[0], suffixes[-1] + 1)) if suffixes else False,
            "files_changed": len(changed),
            "changed": changed,
            "files": files,
        },
        "preserved": (
            "No clone was fetched, checked out or written. Working trees were "
            "never read for content; file bytes come from git's object store "
            "at the named revision, so a dirty clone's uncommitted edits cannot "
            "leak into the comparison and are left exactly as found."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for r in repositories:
        print(f"{r['repository']:<26} {r['state']:<34} remote={((r['remote'] or {}).get('head') or '')[:10]}")
    print("AREA24 files compared     :", len(files), f"({len(current)} current, {len(aliases)} aliases)")
    print("capability suffixes       :", receipt["area24"]["current_owner_capability_suffixes"],
          "contiguous:", receipt["area24"]["capability_suffixes_contiguous"])
    print("files changed             :", len(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
