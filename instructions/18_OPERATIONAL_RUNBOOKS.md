# Operational Recovery Runbook Index

This file is the canonical runbook router. It intentionally does **not** restate each procedure; the scenario file linked below is the canonical procedure for that failure. The general rules in this file apply to every runbook.

## Universal recovery rules

1. Stop the unsafe or repetitive action.
2. Preserve unknown work, immutable evidence, logs, current hashes, and ownership information before mutation.
3. Confirm the canonical repository, branch/worktree, Jira issue, PR, source identity, and permission class.
4. Diagnose from evidence rather than retrying unchanged commands.
5. Apply the smallest reversible correction that preserves protected rules.
6. Re-run the narrowest proving check, followed by any affected integration gate.
7. Record material recovery, blocker, rollback, or ownership state in the durable system that owns it.
8. Return to implementation only after the unsafe condition is resolved or formally isolated.

A runbook never grants permission for an operation classified `HUMAN_REQUIRED` in `policies/autonomy_permissions.json`.

## Scenario router

| Trigger | Canonical runbook | Required durable record |
|---|---|---|
| Wrong path, missing `.git`, empty remote, wrong remote, or unrelated history | [Repository identity and remote reconciliation](runbooks/REPOSITORY_IDENTITY_AND_REMOTE_RECONCILIATION.md) | `templates/REPOSITORY_RECONCILIATION_RECORD.md` |
| Staged, unstaged, or untracked changes with uncertain ownership | [Dirty worktree recovery](runbooks/DIRTY_WORKTREE_RECOVERY.md) | task packet or reconciliation record |
| Merge/rebase/cherry-pick conflict | [Merge conflict resolution](runbooks/MERGE_CONFLICT_RESOLUTION.md) | PR decision note; ADR only if architecture changed |
| Failed GitHub Actions or required check | [Failed CI diagnosis](runbooks/FAILED_CI_DIAGNOSIS.md) | PR evidence and blocker when external |
| Dependency/environment installation failure | [Dependency installation failure](runbooks/DEPENDENCY_INSTALLATION_FAILURE.md) | task packet; dependency proposal when material |
| Jira, GitHub, local branch, or PR state disagree | [Jira/GitHub desynchronization](runbooks/JIRA_GITHUB_DESYNCHRONIZATION.md) | Jira/PR correction evidence |
| Suspected stale branch/worktree | [Stale branch and worktree](runbooks/STALE_BRANCH_AND_WORKTREE.md) | cleanup decision with unique-work proof |
| Repeated command/edit/test without new evidence | [Agent loop recovery](runbooks/AGENT_LOOP_RECOVERY.md) | blocker/attempt ledger |
| Interrupted session or ownership transfer | [Interrupted session recovery](runbooks/INTERRUPTED_SESSION_RECOVERY.md) | `templates/HANDOFF_RECORD.md` |
| Source/API unavailable, credentials rejected, rate limited, or contract changed | [Source/API outage and access failure](runbooks/SOURCE_API_OUTAGE_AND_ACCESS_FAILURE.md) | blocker plus redacted provider evidence |
| Secret or restricted data discovered | [Secret or sensitive-data incident](runbooks/SECRET_OR_SENSITIVE_DATA_INCIDENT.md) | approved incident channel; never Jira/PR secret value |
| Destructive migration/data state needs recovery | [Migration and data recovery](runbooks/MIGRATION_AND_DATA_RECOVERY.md) | migration/rollback record and evidence |
| Instruction links, policies, manifest, hashes, or ZIP fail | [Instruction integrity failure](runbooks/INSTRUCTION_INTEGRITY_FAILURE.md) | instruction changelog and final validation report |

## Project-specific recovery triggers

### PIT, leakage, or target-outcome contamination

Quarantine the affected data, feature, model, and result from promotion/publication. Preserve cutoff/source/join evidence. Repair upstream eligibility or state construction; never weaken the protected judge. Rebuild affected historical state and rerun replay and leakage gates under `14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md`.

### Target hardware unavailable

Keep `AC-038`, `THR-011`, and `THR-012` unresolved. Do not treat a non-equivalent machine as authoritative. Record the exact representative host and evidence still required, then continue only independent Ready work.

### Source-rights ambiguity

Disable ingestion, redistribution, and packaging beyond clearly authorized use. Preserve adapter/schema work only when it remains useful without pretending the data is approved. Escalate for authoritative rights review.

### Release rollback

Use the prevalidated rollback/forward-fix plan, preserve immutable forecast/data/model evidence, verify the intended known-good version, and record incident scope, recovery evidence, and re-entry gates. Production and destructive rollback authority remains governed by the permission matrix.

## Recovery decision classes

Every recovery must end in exactly one of these states:

| State | Meaning | Required next action |
|---|---|---|
| `RECOVERED` | Root cause corrected and proving gates pass. | Resume the active task at the next uncompleted step. |
| `ISOLATED` | Fault remains but is safely separated from independent work. | Record the boundary and select a dependency-ready item outside it. |
| `BLOCKED_EXTERNAL` | Resolution requires unavailable access, provider action, representative hardware, or rights approval. | Update Jira/blocker evidence without fabricating a substitute. |
| `HUMAN_REQUIRED` | Proposed recovery is irreversible, destructive, protected, security-sensitive, paid, or otherwise gated. | Stop before the operation and present the exact decision/evidence required. |
| `ABANDONED_WITH_EVIDENCE` | An experiment or approach is intentionally rejected without losing useful evidence. | Preserve the result, explain the rejection, and return to the governing task plan. |

## Recovery evidence minimum

A material recovery record should identify the trigger, repository/Jira/branch/worktree/PR identity, observed evidence, attempted approaches, ownership boundary, selected correction, files or external state changed, tests run, remaining risk, and the exact continuation point. Do not copy secrets, large logs, or command-by-command diaries into Jira.

## Retry boundary

A transient command may be retried once unchanged. A deterministic failure must not be rerun unchanged. Before another attempt, state a new diagnosis, changed input, changed environment, or changed implementation. After several genuinely different failed approaches, use the blocker taxonomy and move to independent Ready work when possible.

## Protected recovery boundary

A recovery may repair an implementation, environment, adapter, test fixture, manifest, or corrupted unprotected state. It may not weaken PIT eligibility, target-outcome exclusion, protected evaluation, acceptance thresholds, source rights, secret handling, or irreversible data/history safeguards merely to make a gate pass.
