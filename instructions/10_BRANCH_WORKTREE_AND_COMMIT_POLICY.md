# Branch, Worktree, and Commit Policy

The machine companion is `policies/git_policy.json`.

## Branch model

Default model: protected `main` plus short-lived Jira-linked task branches. No permanent `dev` branch exists unless a real multi-lane integration requirement is documented and approved.

Canonical branch format:

`codex/BAT-123-short-kebab-description`

Rules:

- one Jira key at the start;
- lowercase short description;
- deterministic and searchable;
- no names such as `final`, `fix2`, `new`, `test-branch`, or agent-session IDs alone;
- branch scope matches one meaningful Jira implementation unit or coherent vertical slice;
- reuse the branch/PR when the issue already has active work.

Do not create branches for pure read-only analysis unless a durable repository change is expected.

## Worktree model

Canonical sibling root:

`C:\BatteredAggieSyndrome.worktrees`

Example:

`C:\BatteredAggieSyndrome.worktrees\BAT-123-short-description`

Use `scripts/new_worktree.ps1` after reconciliation and claim checks.

### Use a worktree when

- the canonical worktree is occupied by another valid task;
- an independent task can proceed behind stable interfaces;
- an experiment may be rejected;
- isolated dependency/environment/testing state materially helps;
- parallelism is within resource and shared-contract limits.

### Do not parallelize

- the same unfrozen schema/API/manifest/migration;
- canonical IDs/entity semantics;
- PIT/known-at/leakage rules;
- protected judging/promotion rules;
- shared acceptance/requirements/ADR ledgers;
- forecast snapshot/API contracts;
- the same data partition or stateful migration;
- any contract with a single active mutation owner.

### Worktree creation gates

1. Confirm canonical repo identity and fetch metadata.
2. Confirm Jira claim and no existing branch/worktree/PR for the issue.
3. Confirm branch name.
4. Confirm base branch/SHA.
5. Confirm resource/shared-contract admission.
6. Create worktree without deleting or cleaning anything.
7. Record path/branch/base/owner in Jira/task packet.

### Worktree cleanup

Only after merge/intentional abandonment, with no uncommitted files, unique commits, active PR, or owner. Run `git worktree remove <path>` then `git worktree prune`; never delete the directory blindly first.

## Staging policy

Stage explicit reviewed paths only:

```powershell
git add -- path\one.py path\two_test.py
git diff --cached --stat
git diff --cached
```

Forbidden defaults:

- `git add -A`
- `git add --all`
- `git add .`

These commands can accidentally stage secrets, user work, generated artifacts, or unrelated changes. If many files are legitimately in scope, generate/review an explicit path list.

## Commit unit

A commit should represent a coherent engineering step that can be understood and reverted:

- one behavior/contract/refactor slice;
- related tests and necessary docs in the same or clearly sequenced commit;
- no unrelated formatting/churn;
- no per-line/per-command micro-commits;
- no enormous mixed-purpose mega-commit.

Intermediate commits are acceptable when they preserve a meaningful working checkpoint, not to signal activity.

## Commit messages

Preferred format:

`type(BAT-123): imperative summary`

Examples:

- `feat(BAT-123): materialize PIT-safe roster snapshots`
- `fix(BAT-217): exclude target-game outputs from replay features`
- `test(BAT-305): cover interrupted weekly pipeline resume`
- `docs(BAT-144): document source-rights decision boundary`

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `revert`.

The body should explain why and material risk/compatibility when the subject is not enough. Never put secrets or large logs in commit messages.

## Commit gates

Before commit:

- staged paths are exactly the intended task scope;
- staged diff is reviewed;
- focused/impacted tests pass;
- secret/forbidden-artifact scan passes;
- generated files/manifests are intentional;
- no protected rule was weakened;
- traceability/doc updates are included where required.

## Rebase and force-with-lease

Rebase/update an owned unmerged task branch when it improves integration and the repository policy permits. Do not rebase shared branches.

`--force-with-lease` may be used only on the agent’s own unmerged task branch after verifying remote SHA and no collaborators. Plain `--force` is forbidden. Protected/shared branches are never force-pushed.

## Branch cleanup

After safe merge:

1. verify the PR and resulting commit on `main`;
2. verify no unique branch commits or uncommitted work;
3. verify no active owner/dependent stacked PR;
4. delete remote/local short-lived branch under policy;
5. remove/prune completed worktree;
6. update Jira/handoff.

Stale age alone is not proof that a branch is safe to delete.
