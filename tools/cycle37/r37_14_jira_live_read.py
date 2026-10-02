r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14-AC06: a fresh, complete-field, READ-ONLY read of the live Jira sets
this cycle owns, written to the private evidence root and never to Git.

It reads, and only reads:

* every issue in project BAT, all navigable fields, paged;
* the four existing CFIP owner issues the recovery plan names
  (CFIP-19, CFIP-22, CFIP-24, CFIP-27), with their comments, so that any
  later proposal comment can check for an existing effect before it is
  written;
* the comments on the six BAT owner issues (BAT-706/708/701/696/417/324),
  for the same reason.

The client this tool builds has a ``get`` and nothing else. It cannot post,
put or delete, so a mistake here cannot change Jira. Every HTTP attempt --
including a retry -- is counted against the attempt's metadata ceiling, and
an equivalent failing route stops after two tries, as the assignment
requires.

The credential is read the way the established importer reads it: from
``JIRA_API_KEY`` in the authoritative project ``.env``, resolved through the
git common directory. It is held in memory for the Authorization header and
is never printed, logged or written.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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

BASE_URL = "https://kevinsgarrett.atlassian.net"
EMAIL = "kevinsgarrett@gmail.com"
PROJECT = "BAT"
CFIP_OWNERS = ("CFIP-19", "CFIP-22", "CFIP-24", "CFIP-27")
BAT_OWNERS = ("BAT-706", "BAT-708", "BAT-701", "BAT-696", "BAT-417", "BAT-324")
MAX_TRIES_PER_ROUTE = 2


class ReadOnlyJira:
    """A Jira client that can only GET, and counts every attempt."""

    def __init__(self, token: str, ceiling_remaining: int) -> None:
        auth = base64.b64encode(f"{EMAIL}:{token}".encode("utf-8")).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "User-Agent": "BAS-Cycle37-ReadOnly/1.0",
        }
        self.attempts: list[dict[str, Any]] = []
        self.ceiling_remaining = ceiling_remaining

    def get(self, path: str) -> Any:
        last_error = ""
        for attempt in range(1, MAX_TRIES_PER_ROUTE + 1):
            if len(self.attempts) >= self.ceiling_remaining:
                raise RuntimeError(
                    "the metadata request ceiling would be exceeded; stopping rather "
                    "than overspending"
                )
            started = datetime.now(timezone.utc).isoformat()
            request = urllib.request.Request(
                BASE_URL + path, method="GET", headers=self._headers
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    raw = response.read()
                    self.attempts.append(
                        {"path": path.split("?")[0], "attempt": attempt,
                         "status": response.status, "at": started, "bytes": len(raw)}
                    )
                    return json.loads(raw.decode("utf-8")) if raw else None
            except urllib.error.HTTPError as error:
                last_error = f"HTTP {error.code}"
                self.attempts.append(
                    {"path": path.split("?")[0], "attempt": attempt,
                     "status": error.code, "at": started, "bytes": 0}
                )
                if error.code not in (429, 500, 502, 503, 504):
                    break
                time.sleep(3.0 * attempt)
            except (urllib.error.URLError, TimeoutError) as error:
                last_error = type(error).__name__
                self.attempts.append(
                    {"path": path.split("?")[0], "attempt": attempt,
                     "status": None, "at": started, "bytes": 0}
                )
                time.sleep(3.0 * attempt)
        raise RuntimeError(f"GET {path.split('?')[0]} failed after its tries: {last_error}")


def authoritative_env(repo: Path) -> Path:
    run = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=str(repo), capture_output=True, text=True, check=False,
    )
    if run.returncode != 0:
        raise SystemExit("cannot resolve the authoritative git common directory")
    path = Path(run.stdout.strip()).resolve().parent / ".env"
    if not path.is_file():
        raise SystemExit("the authoritative project .env is not present")
    return path


def read_token(path: Path) -> str:
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.startswith("JIRA_API_KEY="):
            value = raw.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise SystemExit("JIRA_API_KEY is missing or blank in the authoritative .env")


def search_all(client: ReadOnlyJira, jql: str, fields: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    token = None
    while True:
        query = {"jql": jql, "fields": fields, "maxResults": 100}
        if token:
            query["nextPageToken"] = token
        page = client.get("/rest/api/3/search/jql?" + urllib.parse.urlencode(query))
        issues.extend(page.get("issues") or [])
        token = page.get("nextPageToken")
        if not token or page.get("isLast"):
            return issues


def text_of(node: Any) -> str:
    """Flatten Atlassian document format to plain text for a comparison."""

    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        return "".join(text_of(child) for child in node.get("content") or [])
    if isinstance(node, list):
        return "".join(text_of(child) for child in node)
    return ""


def supplement(client: ReadOnlyJira, out: Path, first_read: Path) -> int:
    """Complete what the first read could not, without repeating it.

    Two gaps, both found by reading the first read's output rather than its
    summary: the manager's 742-issue live set is BAT and CFIP together, and
    the first read took only the four CFIP owner issues; and Jira's search
    returns at most 20 comments per issue, so three BAT owner issues came
    back truncated (20 of 22, 20 of 27, 20 of 33). A proposal comment must
    check the WHOLE comment history for an existing effect, so a truncated
    history is not good enough to post against.
    """

    first = json.loads(first_read.read_text(encoding="utf-8"))
    cfip = search_all(client, "project = CFIP ORDER BY key ASC",
                      "summary,status,issuetype,parent,labels,updated,resolution")
    full_comments: dict[str, list[dict[str, Any]]] = {}
    for issue in first["cfip_owner_issues"] + first["bat_owner_issues_with_comments"]:
        block = (issue.get("fields") or {}).get("comment") or {}
        if len(block.get("comments") or []) >= int(block.get("total") or 0):
            continue
        page = client.get(
            f"/rest/api/3/issue/{issue['key']}/comment?maxResults=1000&orderBy=created"
        )
        full_comments[issue["key"]] = [
            {"id": c.get("id"), "created": c.get("created"),
             "author": (c.get("author") or {}).get("displayName"),
             "text": text_of(c.get("body"))[:4000]}
            for c in (page or {}).get("comments") or []
        ]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"JIRA_LIVE_SUPPLEMENT_{stamp}.json"
    _bas_atomic.write_text(path, json.dumps({
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37, "attempt_number": 2, "read_at_utc": stamp,
        "supplements": str(first_read),
        "cfip_issues": cfip,
        "untruncated_comments": full_comments,
    }, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37, "attempt_number": 2, "state": "ACTUAL_STATE",
        "read_only": True, "client_capabilities": ["GET"],
        "requests": client.attempts, "request_count": len(client.attempts),
        "cfip_issue_count": len(cfip),
        "untruncated_comment_counts": {k: len(v) for k, v in full_comments.items()},
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    receipt_text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    _bas_atomic.write_text(out / f"JIRA_LIVE_SUPPLEMENT_RECEIPT_{stamp}.json", receipt_text, encoding="utf-8")
    _bas_atomic.write_text(out / "JIRA_LIVE_SUPPLEMENT_RECEIPT.json", receipt_text, encoding="utf-8")
    print("requests      :", len(client.attempts))
    print("CFIP issues   :", len(cfip))
    print("untruncated   :", receipt["untruncated_comment_counts"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="Private evidence directory. Never a path inside Git.")
    parser.add_argument("--ceiling-remaining", type=int, required=True)
    parser.add_argument("--supplement", type=Path, default=None,
                        help="Complete an earlier read instead of repeating it.")
    args = parser.parse_args()

    out = args.out_dir.resolve()
    repo = args.repo_root.resolve()
    if repo in out.parents or out == repo:
        raise SystemExit("refusing to write Jira evidence inside the Git worktree")
    out.mkdir(parents=True, exist_ok=True)

    client = ReadOnlyJira(read_token(authoritative_env(repo)), args.ceiling_remaining)
    if args.supplement:
        return supplement(client, out, args.supplement)

    fields_meta = client.get("/rest/api/3/field")
    by_name = {str(f.get("name")): str(f.get("id")) for f in fields_meta or []}
    local_field = by_name.get("Local Issue ID")
    sprint_field = by_name.get("Sprint")

    bat = search_all(client, f"project = {PROJECT} ORDER BY key ASC", "*navigable")
    cfip = search_all(
        client, "key in (" + ",".join(CFIP_OWNERS) + ") ORDER BY key ASC", "*navigable,comment"
    )
    owners = search_all(
        client, "key in (" + ",".join(BAT_OWNERS) + ") ORDER BY key ASC", "*navigable,comment"
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = out / f"JIRA_LIVE_READ_{stamp}.json"
    raw_doc = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "read_at_utc": stamp,
        "base_url": BASE_URL,
        "local_issue_id_field": local_field,
        "sprint_field": sprint_field,
        "bat_issues": bat,
        "cfip_owner_issues": cfip,
        "bat_owner_issues_with_comments": owners,
    }
    _bas_atomic.write_text(raw_path, json.dumps(raw_doc, ensure_ascii=False), encoding="utf-8")

    # A complete-field export in the column vocabulary the established
    # reconciler reads (reconcile_jira_export.py).
    export_path = out / f"BAT_JIRA_EXPORT_{stamp}.csv"
    columns = ["Issue key", "Issue id", "Local Issue ID", "Summary", "Issue Type", "Status",
               "Resolution", "Assignee", "Sprint", "Updated", "Created", "Parent", "Labels"]
    with _bas_atomic.open_write(export_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\r\n")
        writer.writeheader()
        for issue in bat:
            f = issue.get("fields") or {}
            sprint = f.get(sprint_field) if sprint_field else None
            if isinstance(sprint, list):
                sprint = ";".join(str((s or {}).get("name") or "") for s in sprint)
            writer.writerow({
                "Issue key": issue.get("key"),
                "Issue id": issue.get("id"),
                "Local Issue ID": (f.get(local_field) or "") if local_field else "",
                "Summary": f.get("summary") or "",
                "Issue Type": (f.get("issuetype") or {}).get("name") or "",
                "Status": (f.get("status") or {}).get("name") or "",
                "Resolution": (f.get("resolution") or {}).get("name") or "",
                "Assignee": (f.get("assignee") or {}).get("emailAddress")
                            or (f.get("assignee") or {}).get("displayName") or "",
                "Sprint": sprint or "",
                "Updated": f.get("updated") or "",
                "Created": f.get("created") or "",
                "Parent": (f.get("parent") or {}).get("key") or "",
                "Labels": ";".join(f.get("labels") or []),
            })

    comments = {}
    for issue in cfip + owners:
        entries = ((issue.get("fields") or {}).get("comment") or {}).get("comments") or []
        comments[issue["key"]] = [
            {"id": c.get("id"), "created": c.get("created"),
             "author": (c.get("author") or {}).get("displayName"),
             "text": text_of(c.get("body"))[:4000]}
            for c in entries
        ]
    comments_path = out / f"JIRA_OWNER_COMMENTS_{stamp}.json"
    _bas_atomic.write_text(comments_path, json.dumps(comments, indent=1, ensure_ascii=False), encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-14",
        "acceptance": ["R37-14-AC06", "R37-01-CF-OBL-JIRA-READBACK"],
        "read_only": True,
        "client_capabilities": ["GET"],
        "requests": client.attempts,
        "request_count": len(client.attempts),
        "bat_issue_count": len(bat),
        "bat_with_local_issue_id": sum(
            1 for i in bat if local_field and ((i.get("fields") or {}).get(local_field))
        ),
        "cfip_owner_issues": [i["key"] for i in cfip],
        "bat_owner_issues": [i["key"] for i in owners],
        "owner_comment_counts": {k: len(v) for k, v in comments.items()},
        "local_issue_id_field": local_field,
        "raw": {"path": str(raw_path), "sha256": digest(raw_path)},
        "export": {"path": str(export_path), "sha256": digest(export_path), "rows": len(bat)},
        "comments": {"path": str(comments_path), "sha256": digest(comments_path)},
        "private": "Written under the attempt's private evidence root; nothing here is in Git.",
        "credential": "Read from the authoritative .env into memory only; not printed, logged or written.",
    }
    # A stamped receipt per read keeps every earlier read's receipt; the
    # fixed name is only the latest pointer (a second read once replaced the
    # first read's only receipt).
    receipt_text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    _bas_atomic.write_text(out / f"JIRA_LIVE_READ_RECEIPT_{stamp}.json", receipt_text, encoding="utf-8")
    receipt_path = out / "JIRA_LIVE_READ_RECEIPT.json"
    _bas_atomic.write_text(receipt_path, receipt_text, encoding="utf-8")
    print("requests      :", len(client.attempts))
    print("BAT issues    :", len(bat), "| with Local Issue ID:", receipt["bat_with_local_issue_id"])
    print("CFIP owners   :", receipt["cfip_owner_issues"])
    print("BAT owners    :", receipt["bat_owner_issues"])
    print("comments      :", receipt["owner_comment_counts"])
    print("receipt       :", receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
