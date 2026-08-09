# Task Selection, Granularity, Claiming, and Sequencing

The canonical ranking rules are in `instructions/policies/task_selection_policy.json`. Live Jira controls active work state after hydration; the repository controls technical priority, dependencies, and accepted requirements.

## 1. Selection inputs

Read only the current sources needed to build a Ready set:

1. live Jira assignments/status/dependencies after hydration;
2. valid local branches/worktrees and open PRs;
3. `docs/final/FINAL_BACKLOG.csv`;
4. `docs/final/FINAL_IMPLEMENTATION_PRIORITY.md`;
5. `docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md`;
6. `governance/CURRENT_BACKLOG.yaml` and current gaps;
7. generated `jira/final_handoff_catalog.json`, `dependency_graph.json`, and relevant task records;
8. shared-contract ownership, source/access, resource, and permission constraints.

Do not resurrect old `NEXT_WAVE` instructions or select from historical WBS novelty alone.

## 2. Resume-first rule

Before claiming a new item:

1. resume valid owned `IN_PROGRESS` work;
2. address actionable review comments or required CI on an existing coherent PR;
3. resume a previously blocked item only after verifying its unblock condition;
4. select new Ready work only when no higher-priority valid continuation exists.

This prevents duplicate branches, abandoned PRs, and conflicting partial implementations.

## 3. Readiness gates

A candidate is Ready only when:

- its live/current state permits work;
- mandatory predecessors are Done or an authorized gate explicitly substitutes;
- required data, source, credentials, rights, environment, and inputs are available;
- no other agent owns the same shared mutation surface;
- the scope can produce a coherent outcome and acceptance evidence;
- the next material action is permitted by the autonomy matrix;
- executing it will not bypass a higher-priority foundational gate.

A task is not Ready merely because its title is interesting or code can be written.

## 4. Ranking algorithm

1. Priority: P0 before P1 before P2 before P3.
2. Downstream unblocking/critical-path impact.
3. Risk reduction and evidence value.
4. Smallest coherent vertical slice with usable integration.
5. Resource fit and reversibility.
6. Stable interface/low shared-conflict risk.

Do not rank by model sophistication, number of files, ease of generating boilerplate, or apparent visual progress.

The read-only selector can expose the evidence:

```powershell
python -B tools\select_next_work.py --repo-root . --format markdown
```

Its result is advisory. The agent must re-read live Jira and current ownership before claiming.

## 5. Terminal sequence and current fallback

### P0

- target-hardware evidence;
- credentials/access/rights;
- immutable national history;
- canonical entities/population profiling;
- PIT historical state and leakage/replay validation.

### P1

- simple baselines;
- chronological evaluation and calibration;
- sealed champion/challenger promotion;
- A&M specialization against no adjustment;
- BAS/Aggie Excess science with null acceptance.

### P2

- weekly real-data operation;
- immutable forecast serving and freshness;
- backup/restore, observability, security, drift.

### P3

- advanced neural/sequence/graph/live/distributed complexity only after admission.

`HANDOFF-001` is blocked on representative target hardware. `HANDOFF-002` is the repository-evidenced independent Ready P0 fallback, subject to real access and rights. Live Jira may supersede which concrete BAT issue represents that work.

## 6. Professional ticket granularity

### Epic

A substantial business/technical capability or outcome spanning multiple independently meaningful deliveries.

### Story/Task

A coherent implementation or evidence-producing deliverable that can be owned, reviewed, tested, integrated, and rolled back as one unit.

### Subtask

Use only when separate ownership/status/evidence materially improves execution inside a parent. A checklist or commit is preferable for micro-work.

Do not create one issue for each file, function, test, command, refactor step, retry, or documentation edit. Create a new issue only when it is independently meaningful, not required to make the current issue Done, can be accepted separately, and duplicate search shows it does not already exist.

Use `instructions/templates/NEW_ISSUE_DECISION.md` before autonomous issue creation.

## 7. Claim contract

A claim must identify:

- Jira key and internal task/handoff IDs;
- owner agent/session;
- branch and worktree;
- outcome and explicit scope boundaries;
- shared contracts/paths claimed;
- dependencies and required access;
- planned evidence/gates;
- claim time and release condition.

One coherent implementation unit should have one active claim, branch/worktree, and PR. Do not reserve unrelated future tasks.

## 8. Planning the implementation slice

The plan should specify:

- observable outcome;
- exact interfaces/files likely to change;
- unchanged/protected boundaries;
- compatibility/migration needs;
- focused and integration tests;
- evidence artifacts;
- rollback and stop conditions.

If the plan expands beyond a reviewable coherent unit, split by architecture/risk/rollback boundary—not by file count.

## 9. Blocked selection behavior

Record the blocker category, evidence, attempted distinct approaches, owner/unblock condition, and whether independent work exists. Do not create fake substitute data, synthetic performance, invented Jira state, or housekeeping. Re-rank the Ready set and continue.
