# Canonical Repository / Remote Reconciliation Record

Use this record before first publication, unrelated-history resolution, remote replacement, or any material local/remote discrepancy. Redact credentials and private URLs/tokens.

- Audit timestamp (UTC):
- Operator/agent/session:
- Expected canonical Windows path: `C:\BatteredAggieSyndrome`
- Resolved repository path:
- Git top-level:
- `.git` present:

## Local identity and mutable state

- Current branch/upstream:
- HEAD SHA:
- `git status --short --branch` summary:
- Staged changes and owner:
- Unstaged changes and owner:
- Untracked files and owner:
- Local branches/tags/worktrees:
- Active Jira/PR/task packet claims:

| Path/group | State | Owner | Required preservation/action |
|---|---|---|---|

## Remote identity and state

- Remote names and sanitized URLs:
- Verified expected remote:
- Declared/default branch:
- Remote heads/tags:
- Open PRs:
- Remote empty/nonempty:

## History relationship evidence

- Trusted local-history source:
- Merge base:
- Ahead/behind:
- Shared ancestry / local-only / remote-only / diverged / unrelated / empty:
- Unique local commits:
- Unique remote commits:
- Content/provenance comparison:
- Evidence commands and outputs retained at:

## Risks and protected work

## Options considered

| Option | Preserves local history/work | Preserves remote history/work | Risks | Permission class |
|---|---|---|---|---|

## Selected decision

- Decision:
- Rationale:
- Required explicit human approval:
- Authorized commands/actions:
- Explicitly prohibited commands/actions:

## Exit criteria and verification

- [ ] Canonical path and remote identity confirmed.
- [ ] Unknown/user/other-agent work preserved.
- [ ] No secret exposed in record/logs.
- [ ] History relationship proven rather than assumed.
- [ ] Required approval captured before destructive/initial-publication action.
- [ ] Branch/upstream/default branch and remote state verified after action.
- [ ] Jira/PR/worktree ownership reconciled.
- [ ] Repository validators and applicable tests pass.
