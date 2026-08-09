# Runbook — Jira, GitHub, and Local State Desynchronization

## Trigger

Jira status/claim, local branch/worktree, PR state, or merged state disagree.

## Read all live sources

- live Jira issue and transitions;
- GitHub PR/check/merge state;
- remote branch/head;
- local status/log/worktrees;
- task packet/handoff;
- local Jira sync metadata.

## Authority

- Jira controls workflow/ownership;
- GitHub controls PR/check/merged state;
- local worktree controls uncommitted work;
- repository governance controls technical meaning.

## Common cases

### Jira In Progress, branch missing

Search remote/local/worktrees/PRs and handoff. Do not create a new branch until unique work/ownership is ruled out.

### PR merged, Jira not Done

Verify DoD and completion evidence, then perform verified Jira transition/update. Do not mark Done automatically if operational/evidence criteria remain.

### Jira Done, PR unmerged

Treat as inconsistency. Preserve work, verify whether another integration path exists, and correct Jira through authorized workflow.

### PR closed unmerged

Determine rejected/superseded versus work still required. Move Jira accordingly; not Done by default.

### Local uncommitted work, Jira assigned elsewhere

Preserve local changes, stop conflict, resolve ownership before mutation.

## Write safety

Read back after each write. Never blindly duplicate comments/transitions/PRs.

## Exit criteria

All systems represent the same real state or an explicit sync-pending/blocker record exists without data loss.
