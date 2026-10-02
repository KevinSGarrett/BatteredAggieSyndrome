"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-01 AC03: a read-only refresh of the start-state record -- base, head,
tree, dirt, worktrees, module paths, the PR graph, active jobs, the hold and
the date -- at the moment it runs.

Local facts come from git and the process and scheduled-task tables. The
repository's recent CI runs are one authenticated read of the project's own
repository (``gh run list``), receipted in the cost ledger as a metadata
request. Nothing is written anywhere but the output file and the ledger.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import r37_fetch
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
PR_GRAPH = ATTEMPT / "evidence" / "external" / "BAS_OPEN_PULL_REQUESTS.json"
PREPARED_BASE = "2202b2b2d48217ecfcf52df4464c21abd077ef06"
JOB_WORDS = ("python", "pytest", "node", "git", "gh", "codex", "cursor", "claude")


def run(args: list[str], cwd: Path = ROOT) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=False).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_01_STATE_REFRESH.json")
    parser.add_argument("--skip-ci", action="store_true", help="do not read CI runs (no network)")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc).isoformat()
    head = run(["git", "rev-parse", "HEAD"]).strip()
    state: dict[str, Any] = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-01-AC03", "observed_at": now,
        "git": {"branch": run(["git", "branch", "--show-current"]).strip(), "head": head,
                "tree": run(["git", "rev-parse", "HEAD^{tree}"]).strip(), "prepared_base": PREPARED_BASE,
                "commits_since_base": int(run(["git", "rev-list", "--count", f"{PREPARED_BASE}..HEAD"]).strip() or 0),
                "dirty": [line for line in run(["git", "status", "--porcelain"]).splitlines() if line.strip()],
                "worktrees": [line.split()[0] for line in run(["git", "worktree", "list"]).splitlines() if line.strip()]},
        "module_paths": {"aggie_analytics": str(ROOT / "src" / "aggie_analytics")},
    }
    pr = json.loads(PR_GRAPH.read_text(encoding="utf-8"))["data"]["repository"]["pullRequests"]
    state["pr_graph"] = {"source": str(PR_GRAPH), "read_by": "one read-only GraphQL call earlier this attempt",
                         "open": pr["totalCount"],
                         "stack": [{"number": n["number"], "head": n["headRefName"], "base": n["baseRefName"],
                                    "head_oid": n.get("headRefOid"), "unresolved_threads": (n.get("reviewThreads") or {})
                                    .get("totalCount")} for n in pr["nodes"]]}
    processes = []
    for row in csv.reader(io.StringIO(run(["tasklist", "/fo", "csv", "/nh"]))):
        if row and any(word in row[0].lower() for word in JOB_WORDS):
            processes.append({"image": row[0], "pid": row[1]})
    tasks = []
    for row in csv.reader(io.StringIO(run(["schtasks", "/query", "/fo", "csv", "/nh"]))):
        if row and any(word in row[0].lower() for word in ("bas", "aggie", "battered", "codex", "claude", "cycle")):
            tasks.append({"task": row[0], "next_run": row[1] if len(row) > 1 else None,
                          "status": row[2] if len(row) > 2 else None})
    state["active_jobs"] = {"local_processes": processes, "scheduled_tasks": tasks}
    if not args.skip_ci:
        raw = run(["gh", "run", "list", "--limit", "20", "--json",
                   "databaseId,workflowName,headBranch,status,conclusion,createdAt,event"])
        runs = json.loads(raw) if raw.strip().startswith("[") else []
        receipt = r37_fetch.record_render(
            "https://api.github.com/repos/KevinSGarrett/BatteredAggieSyndrome/actions/runs", "metadata",
            "R37-01-AC03: recent CI runs of the project's own repository (read-only)",
            json.dumps(runs, sort_keys=True).encode("utf-8"), rendered_utc=now, method="GH_CLI_READ_ONLY")
        state["ci_runs"] = {"read": "gh run list --limit 20", "runs": runs,
                            "in_progress": [r for r in runs if r.get("status") != "completed"],
                            "receipt_sha256": receipt["sha256"]}
    state["hold"] = "RETAIN_PROTECTED_LANE_BLOCKED; no push, merge, retarget, activation or hold release authorised"
    _bas_atomic.write_text(args.out, json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items() if k not in ("pr_graph", "ci_runs")}, indent=1)[:3000])
    print("ci runs:", len(state.get("ci_runs", {}).get("runs", [])), "in progress:",
          len(state.get("ci_runs", {}).get("in_progress", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
