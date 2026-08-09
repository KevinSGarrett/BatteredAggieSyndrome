# Merge, Post-Merge, and Cleanup Checklist

Use after a PR is Ready and all review/CI requirements are satisfied. Release-only gates live in `RELEASE_READINESS_CHECKLIST.md`.

## Identity and final-head verification

- [ ] Correct repository, base branch, head branch, Jira key, PR number, and expected head SHA are recorded.
- [ ] The reviewed head SHA equals the current PR head SHA.
- [ ] Required checks and reviews apply to that exact SHA and are not stale, skipped without policy basis, or from another branch.
- [ ] No newer Jira blocker, dependency change, conflicting PR, ownership claim, or shared-contract claim invalidates integration.

## Definition of Done and risk gates

- [ ] All applicable core and domain-specific Definition-of-Done checks pass.
- [ ] All material review threads, conflicts, and requested changes are resolved with evidence.
- [ ] Security, secrets, dependency, source-rights, PIT/provenance/evaluation, migration, and protected-governance gates pass where applicable.
- [ ] Known limitations and independently meaningful follow-ups are explicit and do not conceal incomplete acceptance criteria.
- [ ] Rollback or forward-fix behavior is credible for the risk of the change.

## Merge action

- [ ] Merge method matches verified repository settings; ordinary coherent task PRs use squash by default when enabled.
- [ ] Merge title/message contains the Jira key and describes the delivered outcome.
- [ ] The actor is authorized and no `HUMAN_REQUIRED` boundary is being bypassed.
- [ ] Protected/shared branches are not force-pushed and required checks are not bypassed.
- [ ] A post-merge verification and Jira-update owner is identified.

## Post-merge proof

- [ ] PR state is `MERGED`, not merely closed.
- [ ] Expected merge/squash SHA is present on protected `main`.
- [ ] Required post-merge checks are green or a documented incident/rollback is active.
- [ ] Jira is updated with final acceptance evidence only after integration is verified.
- [ ] Repository/governance/provenance state is updated only where the merged outcome actually changed canonical state.

## Safe cleanup

- [ ] No unique commit, uncommitted file, active PR, pending review, or unknown owner remains on the branch/worktree.
- [ ] The branch is merged or explicitly abandoned with recorded rationale.
- [ ] No active agent/session owns the branch or worktree.
- [ ] Local worktree is removed with Git worktree commands, then local/remote branch cleanup follows verified policy.
- [ ] Remote references are pruned only after fetch and ownership checks.
- [ ] Any deferred cleanup has an owner and reason; nothing is deleted merely because it looks stale.

Decision: `MERGE | DO_NOT_MERGE | HUMAN_DECISION_REQUIRED`

PR/head SHA:  
Merge result/SHA:  
Post-merge evidence:  
Cleanup result or deferral:
