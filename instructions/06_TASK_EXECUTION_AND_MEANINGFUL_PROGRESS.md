# Task Execution, Meaningful Progress, Context Recovery, and Continuation

This document turns a selected Jira implementation unit into sustained, reviewable progress. It is deliberately procedural: an autonomous session should be able to recover after interruption without relying on chat memory or producing a giant diary.

Machine companions: `policies/task_state_machine.json`, `policies/loop_and_retry_policy.json`, and `policies/read_budget.json`.

## 1. Task-start contract

Before editing, the agent must be able to state:

- the active Jira key or an explicitly documented pre-Jira repository work item;
- the internal epic/task/handoff IDs and why the work exists;
- the exact observable outcome;
- included and excluded scope;
- predecessors, blockers, shared contracts, and integration order;
- governing requirements, ADRs, acceptance controls, source documents, and protected rules;
- branch, worktree, agent/session ownership, and permission class;
- focused tests, impacted tests, required gates, evidence artifacts, and rollback;
- stop conditions and the next concrete action.

Use `templates/TASK_EXECUTION_PACKET.md`. Do not begin implementation from a Jira title alone.

## 2. Smallest coherent implementation

“Small” means the narrowest change that delivers a complete, independently reviewable outcome—not the fewest lines or files. A coherent unit may include implementation, schemas, migrations, tests, docs, and evidence when all are necessary for one acceptance outcome.

Split only when there is a real boundary in architecture, ownership, risk, reviewability, dependency, rollback, or integration order. Do not split by file, function, test, command, retry, or Codex cycle.

## 3. Execution loop inside one task

### Orient

Reconfirm repository/worktree identity, active claim, current diff, latest issue/PR state, and changed external conditions. Read only the task-specific sources selected through the repository navigation catalog.

### Plan the next slice

Choose one near-term observable state and its proof:

> By the end of this slice, `<behavior/state>` will be true, demonstrated by `<test/evidence>`.

The slice should normally be completable without broad redesign. Record only material plan changes.

### Implement

- Edit only owned scope and directly required integration surfaces.
- Preserve existing style and accepted design unless a material architecture change is justified.
- Reuse existing utilities/contracts before adding abstractions.
- Handle failure states and validation at the boundary where bad data or input enters.
- Keep generated/local artifacts outside versioned paths unless the repository explicitly governs them.
- Never silently weaken a requirement or acceptance gate.

### Validate progressively

1. static/schema/contract check closest to the edit;
2. focused unit or component test;
3. impacted integration or replay test;
4. mapped domain validator;
5. repository and full-suite gates at PR readiness or major integration.

A deterministic failure requires diagnosis or a changed hypothesis before rerun. A credible transient failure may be retried once unchanged.

### Self-review

Review the entire diff, not only the last edit. Check:

- requirement and acceptance coverage;
- unintended scope or generated files;
- caller/consumer/interface compatibility;
- security, secrets, path traversal, untrusted inputs, and dependency implications;
- PIT, target-game exclusion, identity, immutable evidence, provenance, and evaluation boundaries;
- migration, rollback, observability, resource use, and operational failure behavior;
- test quality and false-positive evidence;
- documentation and traceability accuracy;
- fabricated or overstated claims.

### Integrate and record

Commit coherent units, update the single matching PR, run required CI, resolve review semantically, merge under policy, update Jira with concise evidence, and safely clean completed state.

### Continue

Re-evaluate the Ready set after integration or a blocker. Continue automatically to the next valid unit rather than stopping after every micro-step. Stop only for a human-required operation or a global blocker with no independent Ready work.

## 4. Meaningful-progress rule

A cycle produces meaningful progress when it materially advances or resolves a project outcome, such as:

- implemented and validated behavior;
- a defect fixed with regression evidence;
- a required source contract, rights decision, or access path resolved;
- governed historical data materialized and profiled;
- entity/PIT/leakage/replay evidence produced;
- an acceptance or dependency gap closed;
- a coherent PR integrated;
- a precise blocker established with actionable unblock ownership.

The following do not count by themselves:

- rereading the same documents;
- repeatedly checking Git/Jira/CI with no changed state;
- renaming, reorganizing, or rewriting prose without operational benefit;
- generating another plan for already-planned work;
- rerunning the same deterministic failure;
- creating bookkeeping files, branches, commits, PRs, or tickets merely to show activity;
- broad cleanup unrelated to the active issue.

Housekeeping is legitimate only when it directly unblocks implementation, validation, integration, security, or recovery.

## 4.1 Material-milestone interlock

The machine policy is `policies/execution_focus_policy.json`; run
`python -B tools/validate_execution_focus.py --repo-root .` at PR readiness.

- After the policy baseline, every integrated commit is classified exactly once in
  its subject as `[material]` or `[process]`.
- If an immutable squash commit accidentally omits its reviewed head's marker,
  repair it only through an exact commit-SHA, PR, head-SHA, classification, and
  reason record in the machine policy. The exception applies to no other commit
  and is not permission to rewrite history or accept future unclassified commits.
- `[material]` means the change creates a downstream-consumable project result:
  working behavior, acquired/normalized/validated data, a feature, a model or
  forecast artifact, or a defect correction that enables one of those outcomes.
- `[process]` means synchronization, evidence binding, documentation-only
  governance, cleanup, or validation-only activity. Process work is legitimate,
  but two consecutive process-only integrated commits are a hard failure.
- Use one PR for a coherent material milestone, including its directly required
  tests, evidence, and canonical status change. Do not open a companion Jira-sync-only PR.
- A live Jira comment or operational-status update does not require tracked mirror
  regeneration. When canonical specification, logical status, parent/dependency
  links, and repository behavior are unchanged, use the importer's read-only live
  verification mode and leave the worktree clean.
- Size acquisition and processing tranches from observed throughput, failure
  isolation, resumability, provider limits, disk headroom, validation cost, and a
  natural season/domain boundary. Micro-tranches are not the default.
- Run focused checks during implementation and the full required suite at coherent
  PR readiness or material integration boundaries, not after every micro-checkpoint.
- Handoffs lead with material delta and its downstream consumer. Process activity
  is reported separately and never substituted for material progress.

## 5. Progress checkpoint

At a meaningful checkpoint, update only durable state needed for another session to continue:

- current task/claim and branch/worktree;
- completed outcome and important decisions;
- files/interfaces materially changed;
- tests run and exact result/evidence path;
- current failures/blocker and distinct attempts;
- pending review/CI/integration state;
- next concrete action.

Jira, Git commits/PRs, repository tests, provenance, and a lightweight task packet/handoff are the durable memory system. Do not create hourly diaries or duplicate the same state in multiple files.

## 6. Context-loss recovery

After interruption or compaction:

1. verify canonical path and worktree;
2. run `git status --short --branch` and inspect unique work;
3. read the active Jira issue, branch/PR, task packet, blocker, and latest handoff;
4. inspect the diff and most recent relevant commits;
5. rerun the smallest state-confirming test;
6. state the next concrete action before editing;
7. continue the existing lane unless it is invalid, superseded, or formally transferred.

Do not reconstruct state from chat memory when durable project evidence exists.

## 7. Scope-growth gate

When new work appears during implementation, classify it:

- **required for current acceptance:** include it in the same coherent unit and update scope/evidence;
- **small directly related defect that blocks completion:** fix in the same PR when risk remains coherent;
- **independent outcome:** create/link a Jira issue only after duplicate/granularity checks;
- **speculative improvement or style preference:** do not perform it;
- **material architecture change:** stop the expansion and follow the architecture-change policy.

A follow-up ticket may not be used to defer work required for the current issue’s Definition of Done.

## 8. Stop and handoff conditions

Create a handoff when ownership/session changes, work is interrupted with meaningful unintegrated state, or a blocker requires another owner. Include only what the next agent needs to resume safely. A cleanly merged, fully recorded task normally needs no separate handoff.
