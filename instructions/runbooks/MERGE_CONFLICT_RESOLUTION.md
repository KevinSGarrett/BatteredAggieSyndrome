# Runbook — Merge or Rebase Conflict Resolution

## Trigger

Git reports conflicts or semantic incompatibility after updating/merging/rebasing.

## Preserve and orient

```powershell
git status
git diff --name-only --diff-filter=U
git ls-files -u
```

Identify operation type, base/head branches, Jira issues, shared-contract ownership, and whether the update itself was authorized.

## Resolve each conflict semantically

1. read both sides and merge base;
2. identify governing requirement/ADR/contract;
3. understand why each side changed;
4. choose combined behavior based on source precedence—not “ours/theirs” convenience;
5. update dependent code/tests/docs/traceability;
6. preserve data migrations and registry history correctly;
7. run focused and impacted tests.

For protected/shared-contract conflicts, stop until the mutation owner or architecture decision is clear.

## Abort safely when necessary

An abort may be appropriate when resolution scope is invalid or wrong base was used, but only after confirming uncommitted work is preserved and the abort command matches the active operation.

## Verification

- no conflict markers;
- Git status expected;
- complete diff reviewed;
- semantic contract tests pass;
- requirements/ADRs/ACs remain satisfied;
- PR explains material resolution.

Do not resolve by accepting one side wholesale without understanding it.
