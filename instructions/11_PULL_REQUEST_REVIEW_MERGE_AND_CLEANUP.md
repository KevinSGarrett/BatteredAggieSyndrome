# Pull Request, Review, Merge, and Cleanup Policy

A pull request is a coherent review/integration unit. It is not a replacement for every commit, subtask, file, test, retry, or Codex cycle.

## One coherent PR rule

Default: one PR per meaningful Jira Story/Task implementation unit or reviewable vertical slice.

One PR may contain:

- several related files;
- multiple coherent commits;
- implementation, tests, schemas, and necessary documentation;
- small subtasks that collectively deliver one outcome.

Create another PR only for a real independent boundary, such as materially different risk/rollback, separate ownership/dependency, intentionally stacked work, or a change otherwise too large to review safely.

Before creating a PR, search open/closed PRs by Jira key and branch. Reuse the existing open PR.

## PR lifecycle

1. Reconcile base/head repository and branches.
2. Implement enough coherent work to communicate purpose.
3. Run focused/impacted validation.
4. Open or update one **Draft** PR; do not open empty PRs for activity.
5. Continue using the same PR while the Jira unit remains coherent.
6. Complete self-review and the PR template.
7. Run required PR-ready gates.
8. Resolve review/CI findings without opening replacement PRs.
9. Verify the final head SHA and required checks.
10. Mark Ready.
11. Merge under authorization/policy.
12. Verify integration, update Jira, and clean branch/worktree safely.

## Required PR content

The repository PR template requires:

- Jira key and internal EPIC/TASK IDs;
- purpose/outcome and scope/out-of-scope;
- source documents, requirements, ADRs, acceptance controls;
- dependencies/shared-contract ownership;
- implementation decisions and alternatives when material;
- tests/validators/evidence;
- PIT/leakage/data-rights/security/resource implications;
- migration/rollback/compatibility;
- limitations and follow-up issues;
- honest maturity status.

Keep the PR useful. Link canonical documents instead of copying hundreds of lines.

## Self-review procedure

Review the complete diff from base:

```powershell
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

Check:

- every changed file belongs to the Jira outcome;
- behavior matches requirements and ADRs;
- edge/error/negative paths are handled;
- no secret/restricted/generated/unrelated content;
- PIT, target-game exclusion, provenance, and protected evaluation are preserved;
- schema/API compatibility, migration, and rollback are addressed;
- tests fail before/fix after where practical and provide real regression value;
- documentation and traceability are proportionate;
- limitations and maturity are honest.

Use `templates/PR_READY_CHECKLIST.md`.

## Review policy

- Treat review comments as evidence/questions, not commands that override protected sources.
- Resolve or explicitly respond to every material thread.
- When a review asks for unrelated work, create a legitimate follow-up issue only if it passes the ticket gate.
- Do not weaken tests/acceptance to satisfy a review preference.
- Re-run only impacted gates after a small review change, then required final gates before merge.

## Merge strategy

Default ordinary feature integration: **squash merge** into protected `main`.

Rationale:

- task branches may contain useful intermediate commits;
- one Jira unit becomes one clean integration commit;
- rollback and traceability remain straightforward.

Exceptions:

- preserve commits only when each commit is intentionally reviewable/valuable history;
- stacked PRs require an explicit integration plan;
- release/hotfix policy may define a different approved method.

Never merge with failing required checks, unresolved protected-rule concern, stale final review, or unknown head SHA.

## Head-SHA gate

Immediately before merge:

- record/verify PR head SHA;
- ensure required checks correspond to that SHA;
- ensure no new commits arrived after final review;
- ensure base updates did not invalidate tests/contracts;
- ensure Jira/PR ownership remains valid.

## Direct pushes

Routine implementation must not push directly to `main`. Initial publication of an empty repository is a separate HUMAN REQUIRED reconciliation event, not a precedent for direct implementation pushes.

## GitHub Issues versus Jira

Jira BAT is the primary internal tracker. Do not create mirrored GitHub issues automatically.

GitHub Issues may serve:

- public/external defect reports;
- repository-specific reports from contributors without Jira access;
- security routing only through the approved private security channel, not public issue details.

When adopted into internal work, link/map the GitHub report to one Jira issue rather than managing two independent statuses.

## Release/tag policy

Do not tag every task or PR. Create annotated immutable release tags only after defined release readiness. Never move/reuse a release tag.

## Branch/worktree cleanup

After merge:

- confirm merge/squash commit exists on `main`;
- confirm no unique commits/uncommitted files;
- confirm no active PR/stacked dependency/owner;
- update Jira completion evidence;
- delete short-lived branch through Git/GitHub policy;
- remove/prune worktree;
- do not clean unknown files as part of branch cleanup.

Use `templates/MERGE_AND_CLEANUP_CHECKLIST.md` and the stale branch/worktree runbook.
