# Runbook — Interrupted Session or Process Recovery

## Trigger

Session ended unexpectedly, context was lost, process was interrupted, or another agent must continue.

## Recover durable state

1. verify path and worktree identity;
2. inspect Git status/branch/log/upstream;
3. read live Jira and PR;
4. read task packet/handoff;
5. inspect running processes/output/artifacts;
6. determine whether the last command completed;
7. verify partial writes/downloads/migrations/publications;
8. compare current HEAD with last evidence.

## Idempotency guard

Do not retry until determining whether the previous operation succeeded, especially for:

- Jira comments/transitions/issue creation;
- PR creation/merge;
- source downloads;
- migrations;
- forecast publication;
- external API writes;
- branch deletion.

## Partial data

Quarantine and validate incomplete downloads/artifacts. Do not treat partial files as valid snapshots.

## Exit criteria

Current state is reconciled, next action is explicit, and no duplicate/unsafe operation will occur.
