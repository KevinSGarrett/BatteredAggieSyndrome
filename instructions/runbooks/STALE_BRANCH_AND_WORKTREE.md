# Runbook — Stale Branch and Worktree Review

## Trigger

A branch/worktree appears old, unused, merged, abandoned, or blocks cleanup.

## Inspect

```powershell
git worktree list --porcelain
git branch --all --verbose --no-abbrev
git -C <worktree> status --short --branch
git log --oneline origin/main..<branch>
git branch --contains <branch-tip>
```

Also inspect Jira ownership, open/closed PRs, last activity, and handoff.

## Classify

- active;
- merged and clean;
- abandoned with no unique work;
- blocked but intentionally preserved;
- unique commits/uncommitted files;
- ownership unknown;
- broken metadata/path missing.

Age alone is not a deletion criterion.

## Cleanup

Only merged/approved-abandoned, clean, unowned worktrees may be removed. Verify no unique artifacts. Remove through Git worktree commands, then delete merged branch and prune remote refs when policy permits.

Do not delete directories directly or run prune as a substitute for inspection.

## Exit criteria

Cleanup decision and evidence are recorded; no unique or unknown work is lost.
