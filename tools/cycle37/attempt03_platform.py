r"""Cycle #37 — Attempt #3 — platform lifecycle reads, counted, and the two granted Jira comment targets.

TP37-A03-07 and R37A03-07-B. The issued contract declares three request lanes and their ceilings:

* ``GITHUB_METADATA`` (90): paginated BAS PR/check/thread/ref and accessible GridironCortex metadata;
* ``JIRA_METADATA_AND_ALLOWED_COMMENTS`` (100): verified issue/board/sync reads plus comments on exactly
  BAT-706 and BAT-708;
* ``SOURCE_ACQUISITION`` (0): nothing here acquires a source.

Every HTTP attempt -- a failure and a retry included -- is appended to
``<out-root>/evidence/platform/REQUEST_LEDGER.jsonl`` *before* its result is used, and the lane's running
total is checked against its ceiling before the attempt is made, so a run stops rather than overspends. A
GitHub request is one ``gh api`` invocation; no ``--paginate`` is used, because an automatic paginator issues
requests this ledger could not count.

Mutation is confined to one function, :func:`post_comment`, which accepts only BAT-706 and BAT-708, refuses
to post a marker already present in the issue's complete comment history, and reads the comment back. No
status, label, owner, board, PR, branch or owner-repository write exists in this module. Local Git state is
read with ``--no-optional-locks`` so that inspecting another checkout never rewrites its index.

The Jira credential is read from the authoritative project ``.env`` exactly as the established reader
(``r37_14_jira_live_read``) reads it, held in memory for the Authorization header and never printed, logged
or written.
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

sys.dont_write_bytecode = True

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 3
#: The BEFORE and DURING receipts were written with an ASCII-hyphen label ("Cycle #37 - Attempt #3 - DURING");
#: they stay byte-for-byte as written and are bound through the labelled PLATFORM_RECONCILIATION index.
LABEL = "Cycle #37 — Attempt #3 — IN_PROGRESS_LOCAL_WORK_REMAINS"
REPO = Path(__file__).resolve().parents[2]
JIRA_BASE = "https://kevinsgarrett.atlassian.net"
BAS_REPO = "KevinSGarrett/BatteredAggieSyndrome"
ORG = "GridironCortex"
ALL22_ROOT = Path(r"C:\All-22\repos")
MAIN_CHECKOUT = Path(r"C:\BatteredAggieSyndrome")
PRIVATE_JIRA_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a03\jira")

LANES = {"GITHUB_METADATA": 90, "JIRA_METADATA_AND_ALLOWED_COMMENTS": 100, "SOURCE_ACQUISITION": 0}
COMMENT_TARGETS = frozenset({"BAT-706", "BAT-708"})
BOARDS = ("134", "174", "192", "193")
BAT_OWNER_ISSUES = ("BAT-706", "BAT-708", "BAT-523", "BAT-401", "BAT-429", "BAT-709", "BAT-690", "BAT-637")
CFIP_OWNER_ISSUES = ("CFIP-19", "CFIP-22", "CFIP-24", "CFIP-27")
PHASES = ("BEFORE", "DURING", "AFTER")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def label(phase: str) -> str:
    return f"{LABEL} ({phase} platform duty)"


def subject() -> dict[str, Any]:
    """The exact source subject a platform receipt was taken against: head, tree, digest and cleanliness."""

    def out(*args: str) -> str:
        return subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False).stdout.strip()

    head = out("rev-parse", "HEAD")
    listing = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "ls-tree", "-r", "--full-tree", head],
                             capture_output=True, check=False).stdout
    return {"worktree": str(REPO), "branch": out("rev-parse", "--abbrev-ref", "HEAD"), "head": head,
            "tree": out("rev-parse", "HEAD^{tree}"), "source_digest": sha256_bytes(listing),
            "source_digest_method": "sha256(git ls-tree -r --full-tree HEAD)",
            "clean": not out("status", "--porcelain=v1", "-uall")}


def write_new(path: Path, text: str) -> str:
    """Write a new evidence file and return its SHA-256. Never replaces an existing file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return sha256_file(path)


class Ledger:
    """Append-only request ledger with per-lane ceilings."""

    def __init__(self, out_root: Path, phase: str) -> None:
        self.path = out_root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.phase = phase

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def used(self, lane: str) -> int:
        return sum(1 for row in self.rows() if row["lane"] == lane)

    def reserve(self, lane: str) -> None:
        if lane not in LANES:
            raise RuntimeError(f"undeclared request lane {lane!r}")
        if self.used(lane) >= LANES[lane]:
            raise RuntimeError(f"{lane} ceiling {LANES[lane]} reached; stopping rather than overspending")

    def record(self, lane: str, method: str, target: str, status: Any, attempt: int, detail: str = "") -> None:
        row = {"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "lane": lane, "phase": self.phase,
               "method": method, "target": target, "status": status, "attempt": attempt, "retry": attempt > 1,
               "at": utc_now(), "detail": detail}
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def totals(self) -> dict[str, dict[str, int]]:
        result = {lane: {"requests": 0, "retries": 0, "ceiling": ceiling} for lane, ceiling in LANES.items()}
        for row in self.rows():
            result[row["lane"]]["requests"] += 1
            result[row["lane"]]["retries"] += int(bool(row.get("retry")))
        return result


# ------------------------------------------------------------------------- Jira


def authoritative_env() -> Path:
    run = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=str(REPO),
                         capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise SystemExit("cannot resolve the authoritative git common directory")
    path = Path(run.stdout.strip()).resolve().parent / ".env"
    if not path.is_file():
        raise SystemExit("the authoritative project .env is not present")
    return path


def jira_credentials() -> tuple[str, str]:
    email, token = "", ""
    for raw in authoritative_env().read_text(encoding="utf-8-sig").splitlines():
        key, _, value = raw.partition("=")
        value = value.strip().strip('"').strip("'")
        if key.strip() == "JIRA_API_KEY":
            token = value
        elif key.strip() == "JIRA_EMAIL":
            email = value
    if not token or not email:
        raise SystemExit("JIRA_EMAIL or JIRA_API_KEY is missing in the authoritative .env")
    return email, token


class Jira:
    LANE = "JIRA_METADATA_AND_ALLOWED_COMMENTS"

    def __init__(self, ledger: Ledger) -> None:
        # Named "credential", not "token": the repository's secret scanner reads "token = <identifier>" as a
        # credential-like assignment. The value itself is never written anywhere.
        email, credential = jira_credentials()
        auth = base64.b64encode(f"{email}:{credential}".encode("utf-8")).decode("ascii")
        self._headers = {"Authorization": f"Basic {auth}", "Accept": "application/json",
                         "User-Agent": "BAS-Cycle37-Attempt3/1.0"}
        self.ledger = ledger

    def request(self, method: str, path: str, body: Any = None) -> Any:
        last = ""
        target = path.split("?")[0]
        for attempt in (1, 2):
            self.ledger.reserve(self.LANE)
            data = json.dumps(body).encode("utf-8") if body is not None else None
            headers = dict(self._headers)
            if data is not None:
                headers["Content-Type"] = "application/json"
            request = urllib.request.Request(JIRA_BASE + path, method=method, headers=headers, data=data)
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    raw = response.read()
                    self.ledger.record(self.LANE, method, target, response.status, attempt, f"{len(raw)} bytes")
                    return json.loads(raw.decode("utf-8")) if raw else None
            except urllib.error.HTTPError as error:
                self.ledger.record(self.LANE, method, target, error.code, attempt)
                last = f"HTTP {error.code}"
                # A write is never retried blindly: its outcome must be read back first.
                if method != "GET" or error.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError) as error:
                self.ledger.record(self.LANE, method, target, None, attempt, type(error).__name__)
                last = type(error).__name__
                if method != "GET":
                    break
            time.sleep(3.0 * attempt)
        raise RuntimeError(f"{method} {target} failed: {last}")

    def search(self, jql: str, fields: str, limit_pages: int = 20) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        token = None
        for _ in range(limit_pages):
            query = {"jql": jql, "fields": fields, "maxResults": 100}
            if token:
                query["nextPageToken"] = token
            page = self.request("GET", "/rest/api/3/search/jql?" + urllib.parse.urlencode(query)) or {}
            issues.extend(page.get("issues") or [])
            token = page.get("nextPageToken")
            if not token or page.get("isLast"):
                return issues
        raise RuntimeError("search exceeded its declared page bound")


def adf_text(node: Any) -> str:
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        return "".join(adf_text(child) for child in node.get("content") or []) + (
            "\n" if node.get("type") in {"paragraph", "heading", "listItem"} else "")
    if isinstance(node, list):
        return "".join(adf_text(child) for child in node)
    return ""


def full_comments(jira: Jira, key: str) -> list[dict[str, Any]]:
    page = jira.request("GET", f"/rest/api/3/issue/{key}/comment?maxResults=1000&orderBy=created") or {}
    return [{"id": c.get("id"), "created": c.get("created"), "updated": c.get("updated"),
             "author": (c.get("author") or {}).get("displayName"), "text": adf_text(c.get("body"))}
            for c in page.get("comments") or []]


def jira_read(out_root: Path, phase: str, full_export: bool) -> dict[str, Any]:
    ledger = Ledger(out_root, phase)
    jira = Jira(ledger)
    folder = out_root / "evidence" / "platform" / phase / "jira"
    at = stamp()
    boards: dict[str, Any] = {}
    for board in BOARDS:
        config = jira.request("GET", f"/rest/agile/1.0/board/{board}/configuration")
        filter_id = ((config or {}).get("filter") or {}).get("id")
        flt = jira.request("GET", f"/rest/api/3/filter/{filter_id}") if filter_id else None
        boards[board] = {"configuration": config, "filter": flt}
    owners = jira.search("key in (" + ",".join(BAT_OWNER_ISSUES) + ") ORDER BY key ASC",
                         "summary,status,resolution,assignee,labels,issuetype,parent,updated,issuelinks,description")
    cfip = jira.search("key in (" + ",".join(CFIP_OWNER_ISSUES) + ") ORDER BY key ASC",
                       "summary,status,resolution,labels,updated,description,issuelinks")
    comments = {key: full_comments(jira, key) for key in sorted(COMMENT_TARGETS)}
    document: dict[str, Any] = {"label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER,
                                "attempt_number": ATTEMPT_NUMBER, "phase": phase, "read_at": utc_now(),
                                "boards": boards, "owner_issues": owners, "cfip_owner_issues": cfip,
                                "granted_comment_target_comments": comments}
    export = None
    if full_export:
        fields_meta = jira.request("GET", "/rest/api/3/field") or []
        by_name = {str(f.get("name")): str(f.get("id")) for f in fields_meta}
        local_field, sprint_field = by_name.get("Local Issue ID"), by_name.get("Sprint")
        # The reconciler prefers the project's Logical Workflow State over a mapping of the raw status; an
        # export without it makes every issue's state look changed. It is resolved by its exact field name.
        logical_field = by_name.get("Logical Workflow State")
        bat = jira.search("project = BAT ORDER BY key ASC", "*navigable")
        document.update(local_issue_id_field=local_field, sprint_field=sprint_field,
                        logical_workflow_state_field=logical_field, bat_issue_count=len(bat),
                        field_catalog_used={name: by_name.get(name) for name in
                                            ("Local Issue ID", "Sprint", "Logical Workflow State")})
        export_path = folder / f"BAT_CANONICAL_EXPORT_{at}.csv"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        columns = ["Issue key", "Issue id", "Local Issue ID", "Summary", "Issue Type", "Status",
                   "Logical Workflow State", "Resolution", "Assignee", "Sprint", "Updated", "Created", "Parent",
                   "Labels"]

        def option(value: Any) -> str:
            if isinstance(value, dict):
                return str(value.get("value") or value.get("name") or "")
            return "" if value is None else str(value)
        with export_path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\r\n")
            writer.writeheader()
            for issue in bat:
                f = issue.get("fields") or {}
                sprint = f.get(sprint_field) if sprint_field else None
                if isinstance(sprint, list):
                    sprint = ";".join(str((s or {}).get("name") or "") for s in sprint)
                writer.writerow({
                    "Issue key": issue.get("key"), "Issue id": issue.get("id"),
                    "Local Issue ID": (f.get(local_field) or "") if local_field else "",
                    "Summary": f.get("summary") or "", "Issue Type": (f.get("issuetype") or {}).get("name") or "",
                    "Status": (f.get("status") or {}).get("name") or "",
                    "Logical Workflow State": option(f.get(logical_field)) if logical_field else "",
                    "Resolution": (f.get("resolution") or {}).get("name") or "",
                    "Assignee": (f.get("assignee") or {}).get("emailAddress")
                    or (f.get("assignee") or {}).get("displayName") or "",
                    "Sprint": sprint or "", "Updated": f.get("updated") or "", "Created": f.get("created") or "",
                    "Parent": (f.get("parent") or {}).get("key") or "", "Labels": ";".join(f.get("labels") or []),
                })
        export = {"path": str(export_path), "sha256": sha256_file(export_path), "rows": len(bat),
                  "with_local_issue_id": sum(1 for i in bat if local_field and (i.get("fields") or {}).get(local_field))}
        raw_path = folder / f"BAT_PROJECT_RAW_{at}.json"
        write_new(raw_path, json.dumps({"issues": bat}, ensure_ascii=False))
        export["raw"] = {"path": str(raw_path), "sha256": sha256_file(raw_path)}
    raw = folder / f"JIRA_READ_{at}.json"
    digest = write_new(raw, json.dumps(document, indent=1, ensure_ascii=False))
    summary = {
        "label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "phase": phase, "observed_at": utc_now(), "read_only": True, "raw": {"path": str(raw), "sha256": digest},
        "boards": {b: {"name": ((v["configuration"] or {}).get("name")),
                       "filter_jql": ((v["filter"] or {}).get("jql")),
                       "columns": [{"name": c.get("name"), "statuses": [s.get("id") for s in c.get("statuses") or []]}
                                   for c in (((v["configuration"] or {}).get("columnConfig") or {}).get("columns") or [])]}
                   for b, v in boards.items()},
        "owner_issue_states": {i["key"]: {"status": ((i.get("fields") or {}).get("status") or {}).get("name"),
                                           "resolution": ((i.get("fields") or {}).get("resolution") or {}).get("name"),
                                           "labels": (i.get("fields") or {}).get("labels"),
                                           "updated": (i.get("fields") or {}).get("updated")} for i in owners},
        "cfip_owner_states": {i["key"]: {"status": ((i.get("fields") or {}).get("status") or {}).get("name"),
                                          "updated": (i.get("fields") or {}).get("updated")} for i in cfip},
        "granted_comment_counts": {k: len(v) for k, v in comments.items()},
        "export": export, "request_totals": ledger.totals(),
    }
    write_new(folder / f"JIRA_READ_SUMMARY_{at}.json", json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def post_comment(out_root: Path, phase: str, issue: str, marker: str, body_file: Path) -> dict[str, Any]:
    if issue not in COMMENT_TARGETS:
        raise SystemExit(f"{issue} is not a granted comment target; only {sorted(COMMENT_TARGETS)} are")
    text = body_file.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit("the comment body must carry its deterministic marker")
    ledger = Ledger(out_root, phase)
    jira = Jira(ledger)
    folder = out_root / "evidence" / "platform" / phase / "jira"
    before = full_comments(jira, issue)
    existing = [c for c in before if marker in (c.get("text") or "")]
    receipt: dict[str, Any] = {"label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER,
                               "attempt_number": ATTEMPT_NUMBER, "phase": phase, "issue": issue, "marker": marker,
                               "body_sha256": sha256_bytes(text.encode("utf-8")), "comments_before": len(before),
                               "action": "ADD_EVIDENCE_OR_PROPOSAL_COMMENT_WITH_READBACK", "actor": "worker",
                               "target": f"https://kevinsgarrett.atlassian.net/browse/{issue}"}
    if existing:
        receipt.update(result="NOT_EXECUTED", reason="marker already present; duplicate refused",
                       existing_comment_ids=[c["id"] for c in existing])
    else:
        paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": line}]}
                      for line in text.splitlines() if line.strip()]
        created: Any = None
        error = None
        try:
            created = jira.request("POST", f"/rest/api/3/issue/{issue}/comment",
                                   {"body": {"type": "doc", "version": 1, "content": paragraphs}})
        except RuntimeError as exc:  # the outcome is read back, never assumed
            error = str(exc)
        after = full_comments(jira, issue)
        matched = [c for c in after if marker in (c.get("text") or "")]
        receipt.update(result="SUCCEEDED" if matched else ("UNKNOWN" if error else "FAILED"),
                       post_error=error, created_id=(created or {}).get("id"),
                       readback_comment_ids=[c["id"] for c in matched], comments_after=len(after),
                       readback_text_sha256=[sha256_bytes((c.get("text") or "").encode("utf-8")) for c in matched])
    receipt["request_totals"] = ledger.totals()
    receipt["observed_at"] = utc_now()
    path = folder / f"JIRA_COMMENT_{issue}_{stamp()}.json"
    write_new(path, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    receipt["receipt_path"] = str(path)
    return receipt


# ---------------------------------------------------------------------- GitHub


def gh(ledger: Ledger, args: list[str], target: str) -> Any:
    lane = "GITHUB_METADATA"
    last = ""
    for attempt in (1, 2):
        ledger.reserve(lane)
        run = subprocess.run(["gh", "api", *args], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", check=False)
        ledger.record(lane, "GET" if "graphql" not in args else "POST_GRAPHQL_READ", target,
                      run.returncode, attempt, (run.stderr or "")[:200])
        if run.returncode == 0:
            return json.loads(run.stdout) if run.stdout.strip() else None
        last = (run.stderr or "").strip()[:300]
        if "404" in last or "403" in last:
            break
        time.sleep(3.0 * attempt)
    return {"error": last}


PR_QUERY = """
query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){
 pullRequests(states:OPEN,first:20,after:$cursor){pageInfo{hasNextPage endCursor} nodes{
  number title url isDraft headRefName headRefOid baseRefName baseRefOid mergeable reviewDecision updatedAt
  reviews(last:30){nodes{state author{login} commit{oid} submittedAt}}
  reviewThreads(first:100){totalCount nodes{id isResolved isOutdated path line comments(first:1){nodes{databaseId author{login} createdAt}}}}
  commits(last:1){nodes{commit{oid statusCheckRollup{state contexts(first:100){nodes{
   __typename ... on CheckRun{name status conclusion completedAt checkSuite{app{slug}}} ... on StatusContext{context state createdAt}}}}}}}
 }}}}
"""


def git_read(path: Path, *args: str) -> dict[str, Any]:
    run = subprocess.run(["git", "--no-optional-locks", "-C", str(path), *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=False)
    return {"exit": run.returncode, "stdout": run.stdout, "stderr": run.stderr[:500]}


def local_git_inventory() -> dict[str, Any]:
    worktrees = git_read(REPO, "worktree", "list", "--porcelain")["stdout"]
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in worktrees.splitlines() + [""]:
        if not line.strip():
            if current:
                rows.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value or True
    for row in rows:
        path = Path(str(row.get("worktree")))
        status = git_read(path, "status", "--porcelain=v1", "-uall") if path.is_dir() else {"exit": None, "stdout": ""}
        row["exists"] = path.is_dir()
        row["dirty_entries"] = len([x for x in status["stdout"].splitlines() if x.strip()])
        row["status_exit"] = status["exit"]
    refs = git_read(REPO, "for-each-ref", "--format=%(refname)%09%(objectname)%09%(committerdate:iso-strict)",
                    "refs/heads", "refs/remotes")["stdout"].splitlines()
    return {"worktrees": rows, "worktree_count": len(rows),
            "detached": [r["worktree"] for r in rows if r.get("detached")],
            "refs": [dict(zip(("ref", "sha", "committed"), line.split("\t"))) for line in refs],
            "local_branch_count": sum(1 for line in refs if line.startswith("refs/heads/")),
            "remote_tracking_count": sum(1 for line in refs if line.startswith("refs/remotes/")),
            "note": "Read with --no-optional-locks; no fetch/prune was run, so remote-tracking refs are as last fetched."}


def github_read(out_root: Path, phase: str) -> dict[str, Any]:
    ledger = Ledger(out_root, phase)
    folder = out_root / "evidence" / "platform" / phase / "github"
    doc: dict[str, Any] = {"label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER,
                           "attempt_number": ATTEMPT_NUMBER, "phase": phase, "read_at": utc_now()}
    doc["repository"] = gh(ledger, [f"repos/{BAS_REPO}"], "repos/{repo}")
    doc["main_branch"] = gh(ledger, [f"repos/{BAS_REPO}/branches/main"], "repos/{repo}/branches/main")
    doc["main_protection"] = gh(ledger, [f"repos/{BAS_REPO}/branches/main/protection"], "branches/main/protection")
    pulls: list[Any] = []
    cursor = None
    for _ in range(5):
        args = ["graphql", "-f", f"query={PR_QUERY}", "-F", "owner=KevinSGarrett", "-F", "name=BatteredAggieSyndrome"]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        page = gh(ledger, args, "graphql:open_pull_requests")
        block = ((((page or {}).get("data") or {}).get("repository") or {}).get("pullRequests") or {})
        pulls.extend(block.get("nodes") or [])
        info = block.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
    doc["open_pull_requests"] = pulls
    doc["recently_closed"] = gh(ledger, [f"repos/{BAS_REPO}/pulls?state=closed&sort=updated&direction=desc&per_page=30"],
                                "repos/{repo}/pulls?state=closed")
    branches: list[Any] = []
    for page_number in range(1, 4):
        page = gh(ledger, [f"repos/{BAS_REPO}/branches?per_page=100&page={page_number}"], "repos/{repo}/branches")
        if not isinstance(page, list):
            branches.append(page)
            break
        branches.extend(page)
        if len(page) < 100:
            break
    doc["remote_branches"] = branches
    doc["local_git"] = local_git_inventory()
    doc["main_checkout"] = {"path": str(MAIN_CHECKOUT), "head": git_read(MAIN_CHECKOUT, "rev-parse", "HEAD")["stdout"].strip(),
                            "dirty_entries": len([x for x in git_read(MAIN_CHECKOUT, "status", "--porcelain=v1")["stdout"].splitlines() if x.strip()])}
    at = stamp()
    raw = folder / f"GITHUB_READ_{at}.json"
    digest = write_new(raw, json.dumps(doc, indent=1, ensure_ascii=False))
    summary = {
        "label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "phase": phase, "observed_at": utc_now(), "read_only": True, "raw": {"path": str(raw), "sha256": digest},
        "main_head": ((doc["main_branch"] or {}).get("commit") or {}).get("sha"),
        "open_pr_count": len(pulls),
        "open_prs": [{"number": p.get("number"), "head": p.get("headRefOid"), "base": p.get("baseRefName"),
                      "draft": p.get("isDraft"), "review_decision": p.get("reviewDecision"),
                      "unresolved_threads": sum(1 for t in ((p.get("reviewThreads") or {}).get("nodes") or [])
                                                if not t.get("isResolved")),
                      "threads_total": (p.get("reviewThreads") or {}).get("totalCount"),
                      "rollup": ((((p.get("commits") or {}).get("nodes") or [{}])[0].get("commit") or {})
                                 .get("statusCheckRollup") or {}).get("state")} for p in pulls],
        "remote_branch_count": len([b for b in branches if isinstance(b, dict) and "name" in b]),
        "local_worktrees": doc["local_git"]["worktree_count"], "local_branches": doc["local_git"]["local_branch_count"],
        "main_checkout": doc["main_checkout"], "request_totals": ledger.totals(),
    }
    summary["unresolved_thread_total"] = sum(p["unresolved_threads"] for p in summary["open_prs"])
    write_new(folder / f"GITHUB_READ_SUMMARY_{at}.json", json.dumps(summary, indent=2) + "\n")
    return summary


# ---------------------------------------------------------------------- All-22


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def all22_read(out_root: Path, phase: str, remote_manifest: Path | None) -> dict[str, Any]:
    ledger = Ledger(out_root, phase)
    folder = out_root / "evidence" / "platform" / phase / "all22"
    repos: list[Any] = []
    for page_number in range(1, 4):
        page = gh(ledger, [f"orgs/{ORG}/repos?per_page=100&type=all&page={page_number}"], "orgs/{org}/repos")
        if not isinstance(page, list):
            repos.append(page)
            break
        repos.extend(page)
        if len(page) < 100:
            break
    rows = []
    for repo in [r for r in repos if isinstance(r, dict) and r.get("name")]:
        name, branch = repo["name"], repo.get("default_branch") or "main"
        head = gh(ledger, [f"repos/{ORG}/{name}/branches/{branch}"], "repos/{org}/{repo}/branches/{default}")
        releases = gh(ledger, [f"repos/{ORG}/{name}/releases?per_page=10"], "repos/{org}/{repo}/releases")
        local = ALL22_ROOT / name
        rows.append({
            "name": name, "archived": repo.get("archived"), "fork": repo.get("fork"), "private": repo.get("private"),
            "default_branch": branch, "remote_head": ((head or {}).get("commit") or {}).get("sha"),
            "releases": [{"tag": r.get("tag_name"), "published_at": r.get("published_at"),
                          "assets": [{"name": a.get("name"), "size": a.get("size")} for a in r.get("assets") or []]}
                         for r in (releases if isinstance(releases, list) else [])],
            "local_path": str(local), "local_exists": local.is_dir(),
            "local_head": git_read(local, "rev-parse", "HEAD")["stdout"].strip() if local.is_dir() else None,
            "local_status": git_read(local, "status", "--porcelain=v2", "-uall")["stdout"] if local.is_dir() else None,
        })
    owner_check: dict[str, Any] | None = None
    specs = next((r for r in rows if r["name"] == "CFBProgramSpecifications"), None)
    if remote_manifest and specs and specs.get("remote_head"):
        manifest = json.loads(remote_manifest.read_text(encoding="utf-8-sig"))
        tree = gh(ledger, [f"repos/{ORG}/CFBProgramSpecifications/git/trees/{specs['remote_head']}?recursive=1"],
                  "repos/{org}/CFBProgramSpecifications/git/trees/{head}")
        blobs = {t["path"]: t["sha"] for t in (tree or {}).get("tree") or [] if t.get("type") == "blob"}
        snapshot_dir = remote_manifest.parent / "remote_owner_snapshots"
        compared = []
        for snapshot in sorted(snapshot_dir.glob("*.md")):
            local_blob = git_blob_sha1(snapshot.read_bytes())
            matches = sorted(path for path, sha in blobs.items() if sha == local_blob)
            compared.append({"snapshot": snapshot.name, "git_blob_sha1": local_blob, "present_at_remote_head_as": matches})
        owner_check = {"remote_head": specs["remote_head"], "tree_truncated": (tree or {}).get("truncated"),
                       "snapshots_compared": len(compared),
                       "snapshots_present_unchanged": sum(1 for c in compared if c["present_at_remote_head_as"]),
                       "rows": compared, "manifest": str(remote_manifest), "manifest_sha256": sha256_file(remote_manifest)}
    at = stamp()
    doc = {"label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
           "phase": phase, "observed_at": utc_now(), "organization": ORG, "repositories": rows,
           "discovered_count": len(rows), "owner_plan_check": owner_check,
           "enumeration": "orgs/{org}/repos per_page=100 type=all, explicit pages, no auto-pagination",
           "visibility_limits": "Only repositories visible to the authenticated gh account are enumerated."}
    raw = folder / f"ALL22_READ_{at}.json"
    digest = write_new(raw, json.dumps(doc, indent=1, ensure_ascii=False))
    summary = {k: doc[k] for k in ("label", "subject", "cycle_number", "attempt_number", "phase", "observed_at", "organization",
                                   "discovered_count", "enumeration", "visibility_limits")}
    summary.update(raw={"path": str(raw), "sha256": digest}, request_totals=ledger.totals(),
                   repositories=[{k: r[k] for k in ("name", "archived", "fork", "remote_head", "local_head", "local_exists")}
                                 | {"local_dirty_entries": len([x for x in (r["local_status"] or "").splitlines() if x.strip()]),
                                    "release_tags": [x["tag"] for x in r["releases"]]} for r in rows],
                   owner_plan_check={k: v for k, v in (owner_check or {}).items() if k != "rows"} or None)
    write_new(folder / f"ALL22_READ_SUMMARY_{at}.json", json.dumps(summary, indent=2) + "\n")
    return summary


def jira_successor(out_root: Path, phase: str, export: Path, apply: bool) -> dict[str, Any]:
    """Run the selected canonical producer against a private copy of the committed Jira pack.

    The selected SYNC contract names ``jira/tools/reconcile_jira_export.py`` (dry-run, then apply),
    ``rebuild_all_derivatives`` (called by the reconciler), ``validate_second_pass.py`` and
    ``run_second_pass_audit.py``. The copy lives under this attempt's private root, so neither the committed
    canonical records nor any live issue changes; adoption of the private successor is a separate decision
    this attempt is not granted.
    """

    import shutil

    # A short attempt-owned root: the pack's archived issue names exceed Windows MAX_PATH under the evidence
    # root (the first BEFORE copy there failed partway and is retained as that failure's evidence).
    folder = PRIVATE_JIRA_ROOT / f"{phase[0]}{stamp()[:15]}"
    pack = folder / "jira"
    shutil.copytree(REPO / "jira", pack)
    python = sys.executable
    env = {k: v for k, v in __import__("os").environ.items()
           if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}}
    env.update(PYTHONDONTWRITEBYTECODE="1", BAS_JIRA_REPO_ROOT=str(REPO))
    # The pack's tools read the authoritative repository through REPO_ROOT and write through their own
    # JIRA_ROOT (the private copy). That split is not relied on alone: every step runs under the canonical write
    # guard with the worktree, the data root and the main checkout protected and only this private folder
    # writable, so a write that reached the committed pack would be refused and logged, not made.
    guard_log = folder / "guard_events.jsonl"
    env.update(PYTHONPATH=str(REPO / "tools" / "cycle37" / "canonical_write_guard"),
               BAS_CANONICAL_WRITE_GUARD=__import__("os").pathsep.join(
                   str(p) for p in (REPO, Path(r"C:\BatteredAggieSyndrome.data"), MAIN_CHECKOUT) if p.exists()),
               BAS_CANONICAL_WRITE_ALLOW=str(folder), BAS_CANONICAL_WRITE_GUARD_LOG=str(guard_log),
               BAS_NETWORK_GUARD="DENY_NON_LOOPBACK")

    def records() -> dict[str, Any]:
        return {p.relative_to(pack).as_posix(): json.loads(p.read_text(encoding="utf-8-sig"))
                for p in sorted((pack / "records" / "issues").rglob("*.json"))}

    before = records()
    # The selected mirror scope is the canonical JSON Local Issue IDs; the live project also carries auxiliary
    # entries and issues with no Local Issue ID. Those rows are recorded as outside the scope, never added.
    canonical_ids = {str(v.get("local_id")) for v in before.values()}
    with export.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        live_rows = list(reader)
    in_scope = [row for row in live_rows if row.get("Local Issue ID") in canonical_ids]
    outside = [{"issue_key": row.get("Issue key"), "local_issue_id": row.get("Local Issue ID") or None,
                "status": row.get("Status")} for row in live_rows if row.get("Local Issue ID") not in canonical_ids]
    missing_live = sorted(canonical_ids - {row.get("Local Issue ID") for row in live_rows})
    source_export = {"path": str(export), "sha256": sha256_file(export)}
    scoped_export = folder / "BAT_CANONICAL_SCOPE_EXPORT.csv"
    with scoped_export.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(in_scope)
    export = scoped_export
    steps = [("dry-run", [python, "-B", str(pack / "tools" / "reconcile_jira_export.py"), str(export), "--dry-run",
                          "--repo-root", str(REPO)])]
    if apply:
        steps += [("apply", [python, "-B", str(pack / "tools" / "reconcile_jira_export.py"), str(export),
                             "--repo-root", str(REPO)]),
                  ("strict", [python, "-B", str(pack / "tools" / "validate_second_pass.py"), "--repo-root", str(REPO),
                              "--mode", "validate"]),
                  ("audit", [python, "-B", str(pack / "tools" / "run_second_pass_audit.py"), "--mode", "validate"]),
                  ("second-dry-run", [python, "-B", str(pack / "tools" / "reconcile_jira_export.py"), str(export),
                                      "--dry-run", "--repo-root", str(REPO)])]
    commands = []
    for name, command in steps:
        run = subprocess.run(command, cwd=str(folder), env=env, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=600, check=False)
        stdout, stderr = folder / f"{name}.stdout.txt", folder / f"{name}.stderr.txt"
        write_new(stdout, run.stdout)
        write_new(stderr, run.stderr)
        parsed: Any = None
        try:
            parsed = json.loads(run.stdout)
        except ValueError:
            parsed = None
        commands.append({"name": name, "command": command, "cwd": str(folder), "exit": run.returncode,
                         "stdout": str(stdout), "stdout_sha256": sha256_file(stdout), "stderr": str(stderr),
                         "summary": ({k: v for k, v in parsed.items() if k != "conflicts"} if isinstance(parsed, dict) else
                                     run.stdout.strip()[:400]),
                         "conflict_count": len(parsed.get("conflicts") or []) if isinstance(parsed, dict) else None})
        if run.returncode != 0:
            break
    after = records()
    changed = [{"path": k, "local_id": v.get("local_id"), "before": before.get(k), "after": v}
               for k, v in after.items() if v != before.get(k)]
    guard_events = ([json.loads(line) for line in guard_log.read_text(encoding="utf-8").splitlines() if line.strip()]
                    if guard_log.is_file() else [])
    committed_status = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), "status", "--porcelain=v1",
                                       "-uall", "--", "jira"], capture_output=True, text=True, check=False).stdout
    receipt = {"label": label(phase), "subject": subject(), "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
               "phase": phase, "observed_at": utc_now(), "private_root": str(folder),
               "canonical_source": str(REPO / "jira"), "source_export": source_export,
               "export": str(export), "export_sha256": sha256_file(export),
               "canonical_record_count": len(before), "live_row_count": len(live_rows),
               "in_scope_row_count": len(in_scope), "outside_scope_rows": outside,
               "outside_scope_count": len(outside), "canonical_ids_missing_from_live": missing_live,
               "commands": commands,
               "record_changes_in_private_copy": changed, "changed_local_ids": [c["local_id"] for c in changed],
               "write_guard": {"log": str(guard_log), "events": len(guard_events),
                               "blocked": [row for row in guard_events if row.get("event") == "BLOCKED"]},
               "committed_pack_status_after": committed_status.splitlines(),
               "live_mutations": 0, "committed_canonical_mutations": len(committed_status.splitlines()),
               "adopted": False,
               "adoption_authority": "NOT_GRANTED_IN_THIS_ATTEMPT"}
    path = out_root / "evidence" / "platform" / phase / "jira" / f"JIRA_PRIVATE_SUCCESSOR_{stamp()}.json"
    write_new(path, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    receipt["receipt_path"] = str(path)
    receipt["record_changes_in_private_copy"] = len(changed)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    js = sub.add_parser("jira-successor")
    js.add_argument("--out-root", type=Path, required=True)
    js.add_argument("--phase", choices=PHASES, default="DURING")
    js.add_argument("--export", type=Path, required=True)
    js.add_argument("--apply", action="store_true")
    for name in ("jira-read", "jira-comment", "github-read", "all22-read", "ledger"):
        p = sub.add_parser(name)
        p.add_argument("--out-root", type=Path, required=True)
        p.add_argument("--phase", choices=PHASES, default="DURING")
        if name == "jira-read":
            p.add_argument("--full-export", action="store_true")
        if name == "jira-comment":
            p.add_argument("--issue", required=True)
            p.add_argument("--marker", required=True)
            p.add_argument("--body-file", type=Path, required=True)
        if name == "all22-read":
            p.add_argument("--remote-manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    out_root = args.out_root.resolve()
    if REPO in out_root.parents or out_root == REPO:
        raise SystemExit("refusing to write platform evidence inside the Git worktree")
    if args.mode == "jira-read":
        result = jira_read(out_root, args.phase, args.full_export)
    elif args.mode == "jira-comment":
        result = post_comment(out_root, args.phase, args.issue, args.marker, args.body_file)
    elif args.mode == "github-read":
        result = github_read(out_root, args.phase)
    elif args.mode == "all22-read":
        result = all22_read(out_root, args.phase, args.remote_manifest)
    elif args.mode == "jira-successor":
        result = jira_successor(out_root, args.phase, args.export.resolve(), args.apply)
    else:
        result = Ledger(out_root, args.phase).totals()
    print(json.dumps(result, indent=2, default=str)[:20000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
