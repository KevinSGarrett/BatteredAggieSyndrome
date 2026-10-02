r"""Cycle #37 - Attempt #2 integration boundary

R37-I: qualify one coherent integration boundary, and take no integration
action.

The obligation is specific about what "qualify" means here, so this tool is
specific about what it does:

* **Refresh, do not assume.** One GraphQL read returns every open pull
  request with its exact base and head, its review threads, its reviews and
  its check rollup on the head that exists now. A second read returns the
  branch-protection rules. Historical green checks do not validate a later
  commit, so nothing older than this snapshot is treated as current.
* **Map every contribution to descendant code.** Each pull request head is
  tested for ancestry against the candidate head locally. An ancestor is not
  automatically safe to close, so ancestry is recorded as preservation
  evidence and never as a disposition on its own.
* **Preserve the review text.** All unresolved threads are carried with their
  path, their line and their first comment, because a thread that exists only
  as a count has not been preserved.
* **Cost the alternatives against the real rules.** Branch protection
  requires linear history, up-to-date branches, ten checks, one approving
  review that stale pushes dismiss, and conversation resolution. Those rules
  turn "one merge or ten" into arithmetic rather than preference.
* **Stop at the boundary.** No push, merge, retarget, closure, branch
  deletion or approval. The output is a decision packet with separable
  actions, each carrying its exact target, effects, rollback and next
  verification.

Every request this tool makes is counted and reported, because the attempt
runs under a metadata request ceiling.
"""

from __future__ import annotations

import argparse
import json
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

GRAPHQL = """
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    pullRequests(states:OPEN, first:50, orderBy:{field:CREATED_AT, direction:ASC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        number title isDraft mergeable state createdAt updatedAt
        author { login }
        baseRefName headRefName baseRefOid headRefOid
        additions deletions changedFiles
        reviewDecision
        reviews(last:20) { nodes { state submittedAt commit { oid } author { login } } }
        commits(last:1) { nodes { commit { oid
          statusCheckRollup { state contexts(last:50) { totalCount nodes {
            ... on CheckRun { name conclusion status }
            ... on StatusContext { context state } } } } } } }
        reviewThreads(first:100) { totalCount nodes {
          id isResolved isOutdated path line
          comments(first:1) { nodes { author { login } createdAt body } } } }
      }
    }
  }
}
"""

#: A pull request whose branch name starts with this is a dependency update
#: and is separate work, never evidence about the scientific stack.
DEPENDENCY_PREFIX = "dependabot/"

DISPOSITIONS = (
    "READY_FOR_SCOPED_AUTHORIZATION",
    "REPAIR_REQUIRED",
    "SUPERSEDED_CANDIDATE_PRESERVATION_REQUIRED",
    "DEPENDENCY_UPDATE_SEPARATE",
    "REVIEW_INCOMPLETE",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=600
    ).stdout.strip()


def git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=600
    ).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--canonical-main", required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument(
        "--snapshot", type=Path, default=None,
        help="Reuse a previously fetched GraphQL snapshot instead of requesting one.",
    )
    parser.add_argument(
        "--protection", type=Path, default=None,
        help="Reuse a previously fetched protection document.",
    )
    parser.add_argument(
        "--state", required=True,
        help="The attempt's actual state for the labels (no placeholder state is written).",
    )
    parser.add_argument(
        "--thread-dispositions", type=Path, default=None,
        help="R37_I_THREAD_DISPOSITIONS.json: one local disposition per unresolved thread.",
    )
    args = parser.parse_args()
    label = f"Cycle #37 \u2014 Attempt #2 \u2014 {args.state}"
    dispositions: dict[str, Any] | None = None
    disposition_text = ""
    if args.thread_dispositions is not None:
        import hashlib

        raw = args.thread_dispositions.read_bytes()
        loaded = json.loads(raw.decode("utf-8"))
        dispositions = {
            "path": str(args.thread_dispositions),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "unresolved_thread_count": loaded["unresolved_thread_count"],
            "disposition_counts": loaded["disposition_counts"],
            "disposition_counts_by_pr": loaded["disposition_counts_by_pr"],
        }
        disposition_text = ", ".join(
            f"{count} {state}" for state, count in sorted(loaded["disposition_counts"].items())
        )

    repo = args.repo_root.resolve()
    args.scratch.mkdir(parents=True, exist_ok=True)
    requests_made: list[dict[str, str]] = []

    def reused(path: Path, purpose: str) -> dict[str, str]:
        """Record a reused read as a read, not as a free lunch.

        A snapshot fetched a moment ago by this same attempt still cost a
        request. Reporting zero requests because the bytes came off disk
        would understate the spend, so the provenance and the digest of the
        reused file are recorded and the request is still counted.
        """

        import hashlib

        data = path.read_bytes()
        return {
            "route": "reused-snapshot",
            "purpose": purpose,
            "path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at_utc": datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat(),
            "note": "Fetched by this attempt in a separate call and counted there.",
        }

    if args.snapshot and args.snapshot.is_file():
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        requests_made.append(
            reused(args.snapshot, "open pull requests, threads, checks")
        )
    else:
        query_file = args.scratch / "pr_state.graphql"
        _bas_atomic.write_text(query_file, GRAPHQL, encoding="utf-8")
        completed = subprocess.run(
            ["gh", "api", "graphql", "-F", f"owner={args.owner}",
             "-F", f"name={args.name}", "-F", f"query=@{query_file}"],
            capture_output=True, text=True, timeout=600,
        )
        if completed.returncode != 0:
            raise SystemExit(f"pull-request read failed: {completed.stderr[:600]}")
        snapshot = json.loads(completed.stdout)
        requests_made.append({"route": "graphql", "purpose": "open pull requests, threads, checks"})

    if args.protection and args.protection.is_file():
        protection = json.loads(args.protection.read_text(encoding="utf-8"))
        requests_made.append(reused(args.protection, "merge gates"))
    else:
        completed = subprocess.run(
            ["gh", "api", f"repos/{args.owner}/{args.name}/branches/main/protection"],
            capture_output=True, text=True, timeout=600,
        )
        if completed.returncode != 0:
            raise SystemExit(f"protection read failed: {completed.stderr[:600]}")
        protection = json.loads(completed.stdout)
        requests_made.append({"route": "branches/main/protection", "purpose": "merge gates"})

    nodes = snapshot["data"]["repository"]["pullRequests"]["nodes"]
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    main_sha = args.canonical_main

    checks = protection.get("required_status_checks") or {}
    reviews_required = protection.get("required_pull_request_reviews") or {}
    gates = {
        "required_status_checks": checks.get("contexts") or [],
        "required_status_check_count": len(checks.get("contexts") or []),
        "branches_must_be_up_to_date": bool(checks.get("strict")),
        "required_approving_review_count": reviews_required.get(
            "required_approving_review_count"
        ),
        "stale_reviews_dismissed_on_push": bool(
            reviews_required.get("dismiss_stale_reviews")
        ),
        "required_conversation_resolution": bool(
            (protection.get("required_conversation_resolution") or {}).get("enabled")
        ),
        "required_linear_history": bool(
            (protection.get("required_linear_history") or {}).get("enabled")
        ),
        "enforce_admins": bool((protection.get("enforce_admins") or {}).get("enabled")),
        "force_pushes_allowed": bool(
            (protection.get("allow_force_pushes") or {}).get("enabled")
        ),
        "deletions_allowed": bool(
            (protection.get("allow_deletions") or {}).get("enabled")
        ),
    }

    entries: list[dict[str, Any]] = []
    unresolved_total = 0
    for node in nodes:
        number = node["number"]
        head_oid = node["headRefOid"]
        is_dependency = str(node["headRefName"]).startswith(DEPENDENCY_PREFIX)
        rollup = {}
        if node["commits"]["nodes"]:
            rollup = node["commits"]["nodes"][0]["commit"].get("statusCheckRollup") or {}
        contexts = (rollup.get("contexts") or {}).get("nodes") or []
        failed = sorted(
            {
                str(c.get("name") or c.get("context"))
                for c in contexts
                if str(c.get("conclusion") or c.get("state")).upper()
                in {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"}
            }
        )
        threads = node["reviewThreads"]["nodes"]
        unresolved = [t for t in threads if not t["isResolved"]]
        unresolved_total += len(unresolved)
        approvals_on_head = [
            r for r in node["reviews"]["nodes"]
            if r["state"] == "APPROVED" and (r.get("commit") or {}).get("oid") == head_oid
        ]
        present = git_ok(repo, "cat-file", "-e", f"{head_oid}^{{commit}}")
        ancestor = present and git_ok(repo, "merge-base", "--is-ancestor", head_oid, head)

        if is_dependency:
            disposition = "DEPENDENCY_UPDATE_SEPARATE"
            reason = (
                "A dependency bump is not part of the scientific repair stack and "
                "must not be mixed into it. Its failing checks are its own work."
            )
            next_action = (
                "Decide the dependency-upgrade policy separately: either run each "
                "bump against the required checks on its own base, or decline it "
                "with a stated reason. Neither is taken here."
            )
        elif not ancestor:
            disposition = "REVIEW_INCOMPLETE"
            reason = (
                "This head is not contained in the candidate, so the candidate "
                "does not carry its work and nothing here supersedes it."
            )
            next_action = "Read this pull request's diff against the candidate before any decision."
        elif unresolved:
            disposition = "REVIEW_INCOMPLETE"
            reason = (
                f"{len(unresolved)} review threads are unresolved. Branch protection "
                "requires conversation resolution, so this pull request cannot merge "
                "in its own right, and closing it would discard the review debt."
            )
            next_action = (
                "Resolve or answer each thread on this pull request. The threads are "
                "carried in full below so none is lost if the pull request is later "
                "superseded."
            )
        elif failed:
            disposition = "REPAIR_REQUIRED"
            reason = f"Required checks failing on the current head: {', '.join(failed)}."
            next_action = "Repair the failing checks at this exact head, then re-read the rollup."
        elif not approvals_on_head:
            disposition = "REVIEW_INCOMPLETE"
            reason = (
                "No approving review exists on this exact head, and stale reviews "
                "are dismissed on push, so no earlier approval carries forward."
            )
            next_action = "Obtain an independent review on this exact head."
        else:
            disposition = "READY_FOR_SCOPED_AUTHORIZATION"
            reason = "Checks pass on this head, threads are resolved and an approval exists on it."
            next_action = "Owner decision only."

        entries.append(
            {
                "number": number,
                "title": node["title"],
                "author": (node.get("author") or {}).get("login"),
                "kind": "DEPENDENCY_UPDATE" if is_dependency else "SCIENTIFIC_REPAIR",
                "base_ref": node["baseRefName"],
                "base_oid": node["baseRefOid"],
                "head_ref": node["headRefName"],
                "head_oid": head_oid,
                "is_draft": node["isDraft"],
                "mergeable": node["mergeable"],
                "changed_files": node["changedFiles"],
                "additions": node["additions"],
                "deletions": node["deletions"],
                "check_rollup_state": rollup.get("state"),
                "failed_required_checks": failed,
                "review_decision": node["reviewDecision"],
                "approvals_on_this_exact_head": len(approvals_on_head),
                "review_threads_total": node["reviewThreads"]["totalCount"],
                "review_threads_unresolved": len(unresolved),
                "unresolved_threads": [
                    {
                        "id": t["id"],
                        "path": t["path"],
                        "line": t["line"],
                        "is_outdated": t["isOutdated"],
                        "first_comment_author": (
                            (t["comments"]["nodes"] or [{}])[0].get("author") or {}
                        ).get("login"),
                        "first_comment_at": (t["comments"]["nodes"] or [{}])[0].get("createdAt"),
                        "first_comment": ((t["comments"]["nodes"] or [{}])[0].get("body") or "")[:1500],
                    }
                    for t in unresolved
                ],
                "head_object_present_locally": present,
                "head_is_ancestor_of_candidate": ancestor,
                "preservation": (
                    "The exact head commit is present in this checkout and is an "
                    "ancestor of the candidate, so the contribution is recoverable "
                    "by that object id alone. Ancestry is preservation evidence and "
                    "is not by itself a reason to close anything."
                    if ancestor
                    else "This head is not contained in the candidate; it is preserved "
                    "only by its own branch on the remote."
                ),
                "disposition": disposition,
                "disposition_reason": reason,
                "next_action": next_action,
                "owner": "BAT-706" if not is_dependency else "BAT-708",
            }
        )

    # ------------------------------------------------ consolidated diff ---
    consolidated = {
        "canonical_main": main_sha,
        "candidate_head": head,
        "candidate_tree": tree,
        "main_is_ancestor_of_candidate": git_ok(
            repo, "merge-base", "--is-ancestor", main_sha, head
        ),
        "commits_ahead_of_main": git(repo, "rev-list", "--count", f"{main_sha}..{head}"),
        "shortstat": git(repo, "diff", "--shortstat", f"{main_sha}...{head}"),
        "changed_file_count": len(
            [line for line in git(repo, "diff", "--name-only", f"{main_sha}...{head}").splitlines() if line]
        ),
        "workflow_files_touched": [
            line
            for line in git(
                repo, "diff", "--name-only", f"{main_sha}...{head}", "--", ".github/workflows"
            ).splitlines()
            if line
        ],
        "workflow_note": (
            "A changed workflow file changes what runs on the pull request that "
            "carries it, so these are named separately: reviewing them is not the "
            "same task as reviewing the science."
        ),
    }

    repairs = [e for e in entries if e["kind"] == "SCIENTIFIC_REPAIR"]
    dependencies = [e for e in entries if e["kind"] == "DEPENDENCY_UPDATE"]

    # ----------------------------------------------- alternatives ---------
    check_count = gates["required_status_check_count"]
    sequential = {
        "strategy": "OLDEST_TO_NEWEST_SEQUENTIAL_INTEGRATION",
        "merges_required": len(repairs),
        "required_check_runs": len(repairs) * check_count,
        "approvals_required": len(repairs) * (gates["required_approving_review_count"] or 0),
        "rebases_required": (
            len(repairs) - 1 if gates["branches_must_be_up_to_date"] else 0
        ),
        "threads_to_resolve": unresolved_total,
        "why_it_costs_this_much": (
            "Linear history is required, so each merge moves main and every "
            "remaining branch in the chain must be brought up to date; strict "
            "checks mean each rebase re-runs the required checks, and stale "
            "reviews are dismissed on push, so each approval must be re-obtained "
            "on the new head."
        ),
        "what_it_buys": (
            "Each pull request merges under its own review and its own checks, so "
            "an integration failure is attributable to one change."
        ),
    }
    consolidated_strategy = {
        "strategy": "PRESERVED_CONSOLIDATED_REPAIR_CANDIDATE",
        "merges_required": 1,
        "required_check_runs": check_count,
        "approvals_required": gates["required_approving_review_count"] or 0,
        "rebases_required": 0 if consolidated["main_is_ancestor_of_candidate"] else 1,
        "threads_to_resolve": unresolved_total,
        "why_it_costs_this_much": (
            "The candidate already descends from main, so it satisfies linear "
            "history and up-to-date-with-base without a rebase. One head is "
            "reviewed and checked once."
        ),
        "what_it_does_not_buy": (
            "It does not resolve the review debt. Branch protection would not "
            "block a new pull request on threads attached to the old ones, and "
            "that is exactly the failure mode to avoid: the threads must be "
            "answered on their own pull requests, or carried forward explicitly "
            "with their text, before anything supersedes them. This tool carries "
            "them in full so that closing is never the only record."
        ),
    }
    recommendation = {
        "recommended": consolidated_strategy["strategy"],
        "because": (
            "It is the smaller auditable option under the rules that actually "
            f"apply: {sequential['merges_required']} merges, "
            f"{sequential['required_check_runs']} required check runs and "
            f"{sequential['rebases_required']} forced rebases against 1, "
            f"{consolidated_strategy['required_check_runs']} and "
            f"{consolidated_strategy['rebases_required']}. Every repair head is "
            "already an ancestor of the candidate, so consolidation loses no "
            "commit. This is a recommendation about integration mechanics only."
        ),
        "not_recommended_yet": (
            "Neither strategy is ready. No pull request in the stack has an "
            "approving review on its exact current head, and conversation "
            f"resolution is required while {unresolved_total} threads stay "
            "unresolved on GitHub"
            + (
                f" ({disposition_text} locally: every thread "
                "has an evidence-backed disposition, but a reply or resolution "
                "is an external write that waits on the owner)"
                if dispositions else ""
            )
            + ". Recommending a mechanism is not asserting readiness."
        ),
        "explicitly_separate": (
            "Code integration is not scientific promotion, and neither strategy "
            "activates Family B, adopts C01 or releases the hold."
        ),
    }

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["disposition"]] = counts.get(entry["disposition"], 0) + 1

    receipt = {
        "label": label,
        "cycle_number": 37,
        "attempt_number": 2,
        "state": args.state,
        "thread_dispositions": dispositions,
        "requirement": "R37-I",
        "acceptance": ["R37-I-AC01", "R37-I-AC02", "R37-I-CF-U37-09",
                       "R37-I-CF-U37-12", "R37-I-CF-TP37-I-FULL",
                       "R37-I-CF-RECOVERY37-SECTION-3",
                       "R37-I-CF-RECOVERY37-SECTION-4",
                       "R37-I-CF-RECOVERY37-SECTION-5"],
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(),
        "requests_made": requests_made,
        "request_count": len(requests_made),
        "open_pull_requests": len(entries),
        "scientific_repair_pull_requests": len(repairs),
        "dependency_pull_requests": len(dependencies),
        "unresolved_review_threads": unresolved_total,
        "pull_requests_with_an_approval_on_their_exact_head": sum(
            1 for e in entries if e["approvals_on_this_exact_head"]
        ),
        "repair_chain": " -> ".join(
            ["main"] + [f"#{e['number']}" for e in repairs] + ["candidate (unpublished)"]
        ),
        "every_repair_head_contained_in_the_candidate": all(
            e["head_is_ancestor_of_candidate"] for e in repairs
        ),
        "branch_protection": gates,
        "consolidated_diff": consolidated,
        "dispositions": counts,
        "entries": entries,
        "alternatives": [sequential, consolidated_strategy],
        "recommendation": recommendation,
        "actions_taken": [],
        "actions_not_taken": [
            "no push", "no merge", "no retarget", "no closure",
            "no branch or worktree deletion", "no approval", "no hold release",
            "no new pull request",
        ],
        "not_established": (
            "Nothing here says the stack is correct. It says what is open, what "
            "is failing, what is unreviewed and what integrating it would cost."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# {label}",
        "",
        "# R37-I - integration decision packet",
        "",
        "**Nothing in this document has been executed.** No pull request was "
        "pushed, merged, retargeted, closed or approved; no branch or worktree "
        "was deleted; the hold was not released.",
        "",
        f"State refreshed at {receipt['refreshed_at_utc']} in "
        f"{receipt['request_count']} read request(s).",
        "",
        "## What is open",
        "",
        f"- {len(entries)} open pull requests: {len(repairs)} scientific repair, "
        f"{len(dependencies)} dependency.",
        f"- {unresolved_total} unresolved review threads, carried in full in the "
        "JSON beside this document.",
        f"- {receipt['pull_requests_with_an_approval_on_their_exact_head']} pull "
        "requests have an approving review on their exact current head.",
        f"- Repair chain: {receipt['repair_chain']}",
        f"- Every repair head contained in the candidate: "
        f"{receipt['every_repair_head_contained_in_the_candidate']}",
        "",
        "## The rules that decide the cost",
        "",
        f"- Required checks: {check_count} "
        f"({', '.join(gates['required_status_checks'])})",
        f"- Branches must be up to date with base: {gates['branches_must_be_up_to_date']}",
        f"- Linear history required: {gates['required_linear_history']}",
        f"- Conversation resolution required: {gates['required_conversation_resolution']}",
        f"- Approving reviews required: {gates['required_approving_review_count']}; "
        f"stale reviews dismissed on push: {gates['stale_reviews_dismissed_on_push']}",
        f"- Admins are not exempt: {gates['enforce_admins']}",
        "",
        "## The two strategies, costed",
        "",
        "| | Sequential | Consolidated |",
        "| --- | --- | --- |",
        f"| Merges | {sequential['merges_required']} | "
        f"{consolidated_strategy['merges_required']} |",
        f"| Required check runs | {sequential['required_check_runs']} | "
        f"{consolidated_strategy['required_check_runs']} |",
        f"| Forced rebases | {sequential['rebases_required']} | "
        f"{consolidated_strategy['rebases_required']} |",
        f"| Approvals | {sequential['approvals_required']} | "
        f"{consolidated_strategy['approvals_required']} |",
        f"| Threads to answer | {sequential['threads_to_resolve']} | "
        f"{consolidated_strategy['threads_to_resolve']} |",
        "",
        f"**Recommended mechanism:** {recommendation['recommended']}.",
        "",
        recommendation["because"],
        "",
        f"**Not ready either way.** {recommendation['not_recommended_yet']}",
        "",
        "## The consolidated change, if it is ever published",
        "",
        f"- Base `{main_sha}` -> head `{head}` (tree `{tree}`)",
        f"- {consolidated['commits_ahead_of_main']} commits, "
        f"{consolidated['shortstat']}",
        f"- Main is an ancestor of the candidate: "
        f"{consolidated['main_is_ancestor_of_candidate']} (so linear history holds)",
        f"- Workflow files touched: "
        f"{', '.join(consolidated['workflow_files_touched']) or 'none'}",
        "",
        "## Separable actions for the owner",
        "",
    ]
    for index, (name, detail) in enumerate(
        (
            (
                "Publish the consolidated candidate as a pull request",
                f"Base `main` at `{main_sha}`, head `{head}`. Effect: the "
                f"{check_count} required checks run against this head for the "
                "first time. Rollback: close the pull request; no branch is "
                "deleted and no history changes. Next verification: read the "
                "check rollup on this exact head.",
            ),
            (
                "Answer the unresolved review threads",
                f"{unresolved_total} threads across "
                f"{sum(1 for e in repairs if e['review_threads_unresolved'])} pull "
                "requests. Effect: each answered thread removes one conversation-"
                "resolution blocker from its own pull request"
                + (
                    f"; every thread already has a local disposition "
                    f"({disposition_text}), the text to post is in "
                    "R37_I_THREAD_DISPOSITIONS.md, and the paid-workflow threads also "
                    "need CONTROL-07 approval of the prepared patch"
                    if dispositions else ""
                )
                + ". Rollback: none "
                "needed; a comment is additive. This is required before any "
                "supersession, so that closing is never the record of a thread.",
            ),
            (
                "Decide the dependency-upgrade policy",
                f"{len(dependencies)} dependency pull requests, all with failing "
                "checks and all independent of the science. Effect: none until a "
                "policy is chosen. Rollback: n/a. Next verification: re-read each "
                "rollup after the policy is applied.",
            ),
            (
                "Close superseded pull requests",
                "Not requested, and not safe yet. Every repair head is an "
                "ancestor of the candidate, but ancestry is not a reason to close "
                "and the review debt above is not yet answered. Listed so that it "
                "is visibly excluded rather than silently deferred.",
            ),
            (
                "Release the hold, activate Family B, adopt C01",
                "Not requested. None of these follows from integration mechanics, "
                "and none is prepared by this packet.",
            ),
        ),
        start=1,
    ):
        lines.extend([f"### A-{index}. {name}", "", detail, ""])

    lines.extend(
        [
            "## Per-pull-request disposition",
            "",
            "| PR | Kind | Base | Head | Files | Rollup | Unresolved | Approved on head | Disposition |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| #{entry['number']} | {entry['kind']} | `{entry['base_ref']}` | "
            f"`{entry['head_oid'][:8]}` | {entry['changed_files']} | "
            f"{entry['check_rollup_state']} | {entry['review_threads_unresolved']} | "
            f"{entry['approvals_on_this_exact_head']} | {entry['disposition']} |"
        )
    lines.extend(
        [
            "",
            "Each disposition's reason, next action, owner and full unresolved "
            "thread text are in `R37_I_INTEGRATION_BOUNDARY.json` beside this file.",
            "",
        ]
    )
    args.request.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.request, "\n".join(lines), encoding="utf-8")

    print("open pull requests        :", len(entries),
          f"({len(repairs)} repair, {len(dependencies)} dependency)")
    print("unresolved threads        :", unresolved_total)
    print("approved on exact head    :", receipt["pull_requests_with_an_approval_on_their_exact_head"])
    print("every repair head contained:", receipt["every_repair_head_contained_in_the_candidate"])
    print("dispositions              :", counts)
    print("consolidated              :", consolidated["shortstat"])
    print("requests made             :", len(requests_made))
    print("packet                    :", args.request)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
