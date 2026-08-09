# Runbook — Repository Identity and Remote Reconciliation

## Trigger

Use when `.git` is missing, the remote is empty/unexpected, histories may be unrelated, default branch is absent, or canonical identity is uncertain.

## Preserve

- do not initialize, reset, push, clone a replacement, or delete anything;
- preserve exact directory contents and timestamps where relevant;
- record current path and any `.git` file/directory.

## Diagnose

```powershell
Set-Location C:\BatteredAggieSyndrome
Resolve-Path .
Get-ChildItem -Force .git
git rev-parse --show-toplevel
git status --short --branch
git remote -v
git branch --all --verbose --no-abbrev
git worktree list --porcelain
git log --graph --decorate --oneline --all -n 100
```

Inspect GitHub repository metadata, branches, commits, PRs, default branch, visibility, and settings through the authorized connector/UI.

## Classify

- healthy shared history;
- no local Git history;
- local history, empty remote;
- remote history, no local Git history;
- unrelated/divergent histories;
- wrong/multiple remotes;
- worktree metadata issue;
- permission/authentication issue.

## Safe actions

- read/fetch metadata after remote verification;
- create a reconciliation record;
- compare content and manifests read-only;
- preserve both histories/trees;
- request a narrowly scoped human decision when bootstrap/lineage is ambiguous.

## Human decision required

For empty/unrelated bootstrap, provide:

- local tree identity/hash and whether any Git history exists;
- remote identity/state/visibility;
- options: preserve local history, preserve remote history, controlled import, archive-only publication;
- risks and rollback;
- recommended canonical lineage.

Do not use force push or `--allow-unrelated-histories` automatically.

## Exit criteria

- canonical path and Git top-level confirmed;
- intended remote URL confirmed;
- local/remote merge relationship known;
- default branch/base SHA known;
- dirty/uncommitted ownership known;
- publication/reconciliation authority recorded;
- normal branch/worktree policy can proceed.
