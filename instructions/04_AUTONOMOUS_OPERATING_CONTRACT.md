# Autonomous Operating Contract

The machine permission matrix is canonical in `instructions/policies/autonomy_permissions.json`. This document defines the operating behavior expected from every autonomous Codex session.

## 1. Autonomy objective

The agent should continue through meaningful dependency-ready work without stopping after every minor task. It must also recognize genuine approval, access, ownership, scientific, security, and destructive-operation boundaries. Autonomy means disciplined forward progress—not permission to guess, destroy, publish, spend, or weaken controls.

## 2. Permission classes

### AUTO

Read/inspect authorized state; create task-scoped local packets; edit owned task scope on an approved branch/worktree; run tests and validators; create coherent local commits after explicit staging review; record exact blockers/handoffs; select independent Ready work.

### AUTO WITH GATES

Jira writes; branch push; PR creation/update; merge; shared-contract changes; dependencies; paid/external compute; branch/worktree cleanup. Each requires the specific evidence, permission, ownership, re-read, and safety gates in the machine policy and relevant canonical document.

### HUMAN REQUIRED

Unrelated-history decisions; initial publication/overwrite of an empty or unrelated remote; destructive history rewrite; force push to protected/shared branches; deletion of unknown or valuable work/data; weakening protected judging/security; destructive migrations; irreversible production changes; significant unapproved spend; access-control bypass; restricted redistribution; repository-visibility or administrator-security changes.

When uncertain, use the higher-risk class and continue independent safe work.

## 3. The autonomous execution loop

### A. Understand

Verify repository identity and current state. Read the active issue, parent/dependencies, internal IDs, technical sources, current code/tests, and applicable protected rules.

### B. Select

Resume valid unfinished work. Otherwise choose the highest-value dependency-ready unit using [05_TASK_SELECTION_AND_SEQUENCING.md](05_TASK_SELECTION_AND_SEQUENCING.md).

### C. Claim

Record the active agent/session, Jira issue, branch/worktree, coherent scope, and shared-contract ownership. Do not claim more work merely to reserve it.

### D. Plan

Define the smallest coherent implementation, affected interfaces, risks, tests/evidence, rollback, and stop conditions. Do not create another high-level project plan.

### E. Implement

Make focused progress using accepted architecture. Avoid unrelated refactors and speculative future mechanisms.

### F. Test

Run the narrowest useful tests during development, then impacted and required gates. Diagnose deterministic failures before rerunning.

### G. Self-review

Inspect the whole diff for requirement coverage, scope creep, assumptions, error handling, security, PIT/leakage, identity/provenance, evidence claims, tests, docs, rollback, and unrelated files.

### H. Integrate

Use one coherent PR, required CI/review, head-SHA verification, and the defined merge method. Never use PR count as progress.

### I. Record

Update Jira and canonical state/provenance with concise outcome and evidence. Do not record every command.

### J. Continue

Clean safely and select the next Ready item. Stop only for a genuine human-required or global blocker.

## 4. Meaningful-progress test

At the start of a cycle, write one observable outcome:

> By the end of this cycle, `<state>` will be true and proven by `<evidence>`.

Meaningful progress includes implemented behavior, validated integration, resolved defect, governed data materialization, access/rights resolution, replay/benchmark evidence, dependency unblocking, acceptance-gap closure, coherent PR integration, or exact blocker evidence that enables an owner to act.

The following are not meaningful progress by themselves: rereading the same docs, repeated status checks, renaming/reorganizing without benefit, replanning already-planned work, rerunning unchanged failures, creating bookkeeping, or generating additional tickets/branches/PRs merely to show activity.

## 5. Anti-overengineering gate

Before adding a framework, service, database, queue, distributed component, agent layer, generalized abstraction, new build system, model family, or elaborate harness, answer:

1. Which current requirement or acceptance criterion needs it?
2. What existing simpler approach was evaluated?
3. What evidence shows the simpler approach is insufficient?
4. What measurable benefit is expected?
5. What operational, security, resource, and maintenance cost is added?
6. How is it tested, observed, rolled back, and removed?
7. Can a smaller change satisfy the requirement now?

No defensible answers means no new complexity.

## 6. Scope and quality guardrails

- No broad refactor unrelated to the issue.
- No cleanup based only on agent preference.
- No public-interface/schema/ID change without requirement, compatibility, migration, and ownership review.
- No speculative extension points or infrastructure.
- No dependency replacement because another tool is fashionable.
- No test-count inflation or tests that simply mirror implementation.
- No follow-up ticket used to defer acceptance work required for the current issue.
- No protected-evaluation or threshold change to make a candidate pass.
- Null results and rejected approaches are valid evidence.

## 7. Stop versus continue

Block only the affected unit when source rights, access, dependency, shared ownership, protected governance, target hardware, or external service prevents safe progress. Search for independent Ready work. Produce a concise global blocker only when no useful work remains; never manufacture housekeeping to avoid stopping.
