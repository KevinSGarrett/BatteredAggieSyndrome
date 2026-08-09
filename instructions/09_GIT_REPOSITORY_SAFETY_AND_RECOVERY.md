# Git Repository Safety and Recovery

The canonical repository is `C:\BatteredAggieSyndrome`. Git problems are solved through inspection, ownership, branches, worktrees, and preservation—not replacement repositories or destructive cleanup.

## Absolute prohibitions without explicit HUMAN REQUIRED approval

Do not automatically run or perform the equivalent of:

- `git reset --hard`;
- `git clean -fd` or `git clean -fdx`;
- restoring/checkout of unknown paths;
- deleting unknown untracked files;
- force-checkout over work;
- deleting a branch/worktree with unique state;
- rewriting shared/protected history;
- force-pushing `main` or shared branches;
- initializing/publishing a new history when trusted history is unresolved;
- creating a replacement `-clean/-new/-fixed/-copy` repository.

## Dirty worktree decision tree

### Step 1 — inspect

```powershell
git status --short --branch
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
```

Inspect actual diffs and untracked content. File names are insufficient.

### Step 2 — identify ownership

For each path determine:

- active task-owned;
- another agent/worktree-owned;
- intentional user edit;
- reproducible generated/ignored output;
- unknown.

Use Jira claims, branches, PRs, task packets, handoffs, recent commits, file timestamps only as supporting evidence—not proof by themselves.

### Step 3 — choose the safe path

**Current task-owned:** continue, stage explicit files later, or commit a coherent checkpoint when gates pass.

**Another owner:** do not touch. Work in the owner’s worktree or choose a nonconflicting task.

**Intentional user change:** preserve and avoid. Ask only if a material ambiguity cannot be resolved from context/state.

**Reproducible generated file:** verify ignored status, reproducibility, no unique evidence, and task ownership before removal.

**Unknown:** preserve. Create a reconciliation record and do not discard.

### Step 4 — isolate if necessary

A sibling worktree may be created when:

- the target branch does not already have a worktree;
- the new work is dependency-independent and interface-stable;
- current dirty changes are understood and not being escaped/abandoned;
- shared-contract ownership is clear.

A worktree is not permission to ignore the canonical worktree’s unexplained state.

## Stash policy

Do not automatically stash unknown changes. A stash can hide ownership and be lost.

A stash is allowed only when:

- all included paths are identified and owned;
- a descriptive message includes Jira key, owner, and timestamp;
- untracked files are included only after review;
- the task packet/handoff records the stash reference;
- it is promptly restored or converted into a branch/commit.

Prefer a task branch/worktree and coherent checkpoint over long-lived stashes.

## Missing `.git`

An archive without `.git` is a content snapshot, not a proven repository history.

Before `git init`, first push, or replacing a remote:

- locate any trusted local checkout/backup;
- inspect remote state;
- identify whether history exists elsewhere;
- scan content and intended history for secrets/large forbidden files;
- record the proposed initial commit/base/default branch;
- obtain explicit approval.

## Divergence and conflicts

### Shared ancestry

Update only an owned task branch. Inspect both sides, resolve semantically, run impacted tests, and preserve authorship/traceability.

### Unrelated histories

Stop. Preserve both. Do not force-push or merge unrelated histories automatically. Determine which is authoritative and whether content import/archive is intended.

### Merge conflicts

For every conflict:

1. identify the requirements/contracts represented by each side;
2. determine task and shared-contract ownership;
3. resolve behavior, not just conflict markers;
4. inspect callers/consumers and generated manifests;
5. run focused and impacted validation;
6. record material resolution in PR/Jira/ADR when needed.

Do not choose “ours” or “theirs” wholesale because it is easier.

## Repository copies and backups

A read-only extraction, forensic backup, or temporary packaging stage may exist outside the canonical repository. It must be clearly labeled, never receive independent implementation work, and never become a competing source.

Before risky reconciliation, a preservation backup may be appropriate, but it does not authorize destructive action in the canonical tree.

## Safe recovery order

1. Stop mutation.
2. Capture status/diffs/branch/worktree/remotes/log.
3. Identify owners and unique work.
4. Preserve unique state on an owned branch/commit or approved backup.
5. Determine authoritative history and intended integration.
6. Apply the least destructive reversible action.
7. Validate repository and task behavior.
8. Record resolution and clean only after verification.

Use `18_OPERATIONAL_RUNBOOKS.md` for exact scenarios.
