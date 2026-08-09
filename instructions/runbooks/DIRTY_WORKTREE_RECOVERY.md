# Runbook — Dirty Worktree Recovery

## Trigger

Staged, unstaged, or untracked files exist when starting/resuming work or switching branches/worktrees.

## Inspect every class

```powershell
git status --short --branch
git diff --stat
git diff
git diff --cached --stat
git diff --cached
git ls-files --others --exclude-standard
```

Also inspect active worktrees, Jira claims, and open PRs.

## Classify each path

- current task and intended;
- current task but accidental/generated;
- another task/agent;
- user-owned;
- unknown;
- safe ignored/local artifact;
- secret/sensitive incident.

## Recovery choices

### Current-task changes

Verify correct branch and task packet. Continue or create a coherent commit only after tests and staged-scope review.

### Another owner/user/unknown

Do not modify, stage, stash, reset, or delete. Record paths/ownership and use another approved worktree for independent work.

### Accidental staged path

```powershell
git restore --staged -- path\to\file
```

This preserves working content. Reinspect.

### Proven disposable generated path

Remove only the exact path after confirming it is reproducible, ignored/policy-excluded, unowned, and contains no evidence needed elsewhere.

### Secret found

Stop and use the secret incident runbook.

## Prohibited shortcuts

No automatic `reset --hard`, `clean -fdx`, force checkout, generic stash of unknown work, or replacement clone.

## Exit criteria

- every dirty path has an owner/classification;
- active task scope is isolated;
- unknown work is preserved;
- branch/worktree is correct;
- status is understood, even if intentionally dirty.
