# Parallelism, Resource Management, Context, and Handoff

Long autonomous work must be recoverable from durable systems and must not create conflicting “busy” lanes.

## Durable state hierarchy

Persist facts in the system that owns them:

- Jira: issue status, claim, dependencies, blocker, acceptance outcome;
- Git: exact code/diff/commit/branch/worktree state;
- GitHub PR: proposed integration, review, CI, merge state;
- repository governance/docs: requirements, architecture, decisions, protected rules;
- tests/provenance/artifacts: objective evidence;
- task packet/handoff: only transient coordination facts not represented elsewhere.

Do not create broad AI-memory journals or duplicate the entire Jira/PR history in Markdown.

## Parallel work admission

Parallelism is allowed only when all are true:

- tasks are dependency-independent or integration order is explicit;
- interfaces/contracts consumed are stable;
- mutation scopes do not overlap materially;
- each Jira item has a unique claim, branch, worktree, scope, and owner;
- shared-contract single-owner rules are satisfied;
- CPU/RAM/GPU/disk/API/cost/ports/locks allow it;
- expected benefit exceeds coordination and merge risk.

One productive lane is better than several starved/conflicting lanes.

## Required active-lane record

Each lane records:

- Jira key and internal IDs;
- agent/session owner;
- branch/worktree;
- outcome and mutation scope;
- shared contracts/locks;
- base SHA and expected integration order;
- resource budget/ports/local data partitions when relevant;
- PR/handoff state.

## Shared-contract serialization

Use `governance/SHARED_CONTRACT_OWNERSHIP.csv` and live claims. Serialize changes to:

- REQ/ADR/AC/WBS ledgers;
- architecture/acceptance/entity/temporal registries;
- canonical identity and PIT semantics;
- feature/model target/lifecycle schemas;
- protected evaluation/promotion rules;
- forecast snapshot/API schema;
- migrations/manifests or the same stateful data partition.

Consumers may code against an accepted frozen interface, but cannot mutate it concurrently without ownership.

## Resource admission

Before another lane or expensive run, inspect:

- available CPU and RAM, including peak contention;
- GPU/VRAM and whether the task actually needs it;
- disk capacity, I/O, artifact/cache growth;
- API/provider rate and daily/monthly budget;
- local databases/files/locks/ports;
- Windows versus Linux execution needs;
- shared test fixtures and generated manifests;
- target-hardware evidence status.

Do not assign THR-011/THR-012 or declare feasibility from a different machine without an explicitly accepted equivalence argument and evidence.

## Integration order

Dependency order and contract readiness control integration, not which agent finishes first.

A downstream branch that finishes early remains pending until its predecessor/interface is accepted. Before merge:

- update against the current base;
- inspect upstream contract changes;
- rerun impacted validation;
- resolve semantic conflicts;
- maintain one coherent PR/traceability path.

## Context recovery at session start

1. Inspect Git status/branch/worktrees/remotes/recent commits.
2. Read active Jira issue and meaningful latest update.
3. Inspect open PR/check/review state.
4. Read task packet/handoff if present.
5. Inspect current diff/untracked files.
6. Rerun the smallest check needed to confirm state.
7. State the next concrete action and continue.

Do not restart full repository discovery merely because chat memory was lost.

## Task packet

Use `templates/TASK_EXECUTION_PACKET.md` for material work. It records:

- identity and coherent outcome;
- source/requirements/ADRs/ACs;
- in/out scope and mutation boundary;
- dependencies/shared contracts;
- risks and stop conditions;
- implementation/validation/evidence plan;
- current continuation state.

It is not a command diary.

## Handoff

Use `templates/HANDOFF_RECORD.md` only when:

- work is interrupted before Jira/PR state is sufficient;
- ownership transfers;
- uncommitted/generated state must be explained;
- a blocker needs exact continuation context.

Required facts:

- Jira item/outcome and owner;
- branch/worktree/PR/base;
- committed and uncommitted paths;
- tests run and exact current failures;
- blocker/attempts/unblock condition;
- shared contracts/locks/resources;
- next executable action.

Update/remove stale handoffs. Do not accumulate session diaries.

## Interrupted session recovery

- Never assume the worktree is disposable.
- Inspect status and unique untracked files.
- Resolve owner from Jira/branch/PR/task packet.
- Preserve unique work before environment changes.
- Resume or formally transfer; do not silently take over a shared contract.

## End-of-session minimum

Before voluntarily stopping, ensure Jira + PR + task packet/handoff collectively identify:

- real current state;
- branch/worktree/owner;
- achieved outcome;
- pending/uncommitted work;
- tests/evidence and failures;
- blocker/locks;
- next action.

Do not leave an unexplained dirty canonical worktree.
