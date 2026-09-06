# START HERE — Battered Aggie Syndrome Autonomous Codex Control System

**Instruction-pack version:** `3.0.0`
**Canonical repository:** `C:\BatteredAggieSyndrome`  
**Approved worktree root:** `C:\BatteredAggieSyndrome.data\worktrees`
**GitHub repository:** `KevinSGarrett/BatteredAggieSyndrome`  
**Expected Jira project:** `BAT` at `https://kevinsgarrett.atlassian.net`  
**Program state:** the exactly-25-wave planning and starter-build program is complete. W25 is terminal. **There is no Wave 26.**

This is the single operational entrypoint for an autonomous Codex implementation session. It does not replace the repository’s requirements, ADRs, acceptance controls, schemas, protected evaluation rules, or final W25 handoff. It defines how an agent must navigate, select, implement, test, integrate, record, and continue work without drifting or destroying state.

## Retired assistive pipeline — not required reading

The Fort Knox assistive-execution interlock is `RETIRED_HISTORICAL_ONLY`. Do not
read it before material BAS work. Do not run `tools/validate_codex_usage_interlock.py`
as an acceptance gate. Prove absence of active assistive authority with
`tools/validate_retired_assistive_pipeline_decommission.py`.

The required operating cycle is:

> **UNDERSTAND → SELECT → IMPLEMENT → TEST → REVIEW → INTEGRATE → RECORD → CONTINUE**

The material-milestone interlock in
[06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md](06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md)
is mandatory. It prevents consecutive process-only integrations, companion
Jira-sync-only PRs, and micro-tranche/full-suite churn from replacing project
outcomes.

Claiming, planning, validation, and cleanup are gates inside that cycle; they do not create additional project “waves.”

## 1. What this system is designed to prevent

The agent must not:

- **create Wave 26** or restart the historical wave-generation program;
- treat historical planning completion as proof that production implementation is complete;
- choose advanced ML work before data, PIT, replay, baseline, and protected-evaluation foundations exist;
- create duplicate repositories to escape a dirty worktree;
- discard unknown user or agent changes;
- create hundreds of branches, micro-commits, micro-PRs, or unnecessary Jira issues;
- repeatedly rerun an unchanged failing command;
- invent Jira workflow details, source access, source rights, data, model results, A&M lift, BAS effects, or hardware benchmarks;
- change protected judging, PIT, identity, or provenance rules merely to make implementation pass;
- leak secrets, restricted payloads, or sensitive logs;
- spend most of its time generating plans and bookkeeping instead of delivering meaningful outcomes.

## 2. Honest activation boundary

The instruction system was constructed from the supplied repository archive and external read-only checks. Three live-system facts could not be fully reconciled inside that archive:

1. The archive contained no `.git` directory. Its current branch, commit graph, upstreams, staged/unstaged changes, tags, and worktrees are therefore unverified.
2. The connected GitHub repository existed but was empty during discovery. Initial publication or reconciliation with any trusted local history is not authorized automatically.
3. The connected Atlassian identity did not expose the requested `kevinsgarrett.atlassian.net` BAT project. Exact live issue types, fields, statuses, transitions, board configuration, and issue contents remain intentionally unhydrated.

These are **activation boundaries**, not permission to invent values. The pack includes read-only audit, reconciliation, Jira-hydration, and validation procedures so the future session can complete those checks on the user’s machine. Initial publication, unrelated-history resolution, and any destructive reconciliation remain `HUMAN_REQUIRED`.

See [audit/REPOSITORY_DISCOVERY_REPORT.md](audit/REPOSITORY_DISCOVERY_REPORT.md) and [audit/EXTERNAL_INTEGRATION_AUDIT.md](audit/EXTERNAL_INTEGRATION_AUDIT.md).

## 3. Deterministic startup procedure

Perform the following in order. Startup is bounded; do not reread the entire repository each session.

### 3.1 Verify the canonical path and instruction integrity

```powershell
Set-Location C:\BatteredAggieSyndrome
Resolve-Path .
Get-Item .\AGENTS.md, .\instructions\START_HERE.md
python -B tools\validate_autonomous_controls.py --repo-root . --strict
```

Do not switch to `BatteredAggieSyndrome-clean`, `-new`, `-fixed`, `-copy`, `-final2`, or another replacement clone. A deliberately created Git worktree under `C:\BatteredAggieSyndrome.data\worktrees` is allowed because it shares the canonical repository history and remains outside Git. Do not create a new project-specific sibling root.

### 3.2 Audit local Git and remote metadata read-only

```powershell
python -B tools\audit_control_plane.py --repo-root . --output artifacts\control-plane-audit.json
git rev-parse --show-toplevel
git status --short --branch
git remote -v
git branch --all --verbose --no-abbrev
git worktree list --porcelain
git log --graph --decorate --oneline --all -n 50
```

After verifying that remotes do not contain embedded credentials and point to the intended repository, a metadata fetch is normally safe:

```powershell
git fetch --all --prune --tags
```

Fetching does not authorize reset, merge, rebase, deletion, push, publication, or force operations. Use [09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md](09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md) and the reconciliation runbook whenever identity or history is uncertain.

### 3.3 Read the always-read set

Read only:

1. `AGENTS.md`;
2. this file;
3. `governance/CURRENT_STATE.yaml`;
4. the active Jira issue, branch/worktree, PR, task packet, and handoff, if any;
5. the current blocker record, if the active unit is blocked.

On first hydration, after material context loss, or when project state is disputed, also read:

- [01_PROJECT_IDENTITY_AND_HANDOFF.md](01_PROJECT_IDENTITY_AND_HANDOFF.md);
- [02_SOURCE_OF_TRUTH_AND_CONFLICT_RESOLUTION.md](02_SOURCE_OF_TRUTH_AND_CONFLICT_RESOLUTION.md);
- `docs/final/CODEX_HANDOFF.md`;
- `docs/final/FINAL_IMPLEMENTATION_PRIORITY.md`;
- `docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md`.

Use [03_REPOSITORY_ARCHITECTURE_AND_NAVIGATION.md](03_REPOSITORY_ARCHITECTURE_AND_NAVIGATION.md) and `catalogs/repository_navigation.json` to retrieve only the technical sources needed by the current task.

### 3.4 Resume valid unfinished work before selecting new work

Inspect in this order:

1. live Jira work already assigned or claimed by the session/agent;
2. active local branches and worktrees with unique work;
3. open Draft or Ready PRs for the same Jira issue;
4. required CI failures and unresolved review comments;
5. the latest task packet, blocker, and handoff records.

Do not create a second branch, worktree, claim, or PR when an existing coherent lane should be resumed.

### 3.5 Verify Jira state before any Jira write

```powershell
python -B tools\validate_jira_control_plane.py --repo-root . --strict
```

If the mirror remains `UNVERIFIED_TARGET_SITE_NOT_ACCESSIBLE_IN_AUDIT`, Jira reads/writes that require exact live metadata are disabled. Do not substitute another Atlassian site. Follow [07_JIRA_OPERATING_CONTRACT.md](07_JIRA_OPERATING_CONTRACT.md), [08_LOCAL_JIRA_MIRROR_AND_SYNC.md](08_LOCAL_JIRA_MIRROR_AND_SYNC.md), and the Jira/GitHub desynchronization runbook.

### 3.6 Select and claim one coherent implementation unit

```powershell
python -B tools\select_next_work.py --repo-root . --format markdown
```

The selector is read-only and advisory. After live Jira hydration, live status, assignment, and dependencies control the execution claim. Selection must follow [05_TASK_SELECTION_AND_SEQUENCING.md](05_TASK_SELECTION_AND_SEQUENCING.md): resume first, then choose the highest-priority dependency-ready unit capable of producing usable evidence without violating access, rights, resource, ownership, protected-governance, or approval gates.

### 3.7 Create or resume the task packet

Use [templates/TASK_EXECUTION_PACKET.md](templates/TASK_EXECUTION_PACKET.md). Record:

- Jira key and internal `EPIC-*`, `TASK-*`, `REQ-*`, `ADR-*`, and `AC-*` identifiers;
- observable outcome and explicit out-of-scope boundary;
- source documents and governing contracts;
- branch, worktree, owner/session, and shared-contract claim;
- dependencies, access/rights assumptions, and permission class;
- focused, impacted, and merge-gate tests;
- evidence, rollback, stop conditions, and next concrete action.

A task packet is durable recovery context—not a second project plan or terminal diary.

## 4. The execution loop

### UNDERSTAND

Read the Jira issue and parent chain, dependencies, internal IDs, linked requirements/ADRs/acceptance controls, source documents, protected governance, current implementation, schemas, tests, consumers, and recent related integration history. Resolve material conflicts using the precedence policy; do not silently choose a convenient source.

### SELECT

Resume valid owned work. Otherwise select from the dependency-ready set by priority, critical-path impact, risk reduction, evidence value, coherent scope, reversibility, and resource fit. Do not select work because it is sophisticated or easy to generate.

### IMPLEMENT

Claim one coherent unit, establish a short-lived Jira-linked branch/worktree, and implement the smallest correct change. Preserve unrelated work. Avoid speculative infrastructure, broad refactors, and ticket/branch/PR explosion.

### TEST

Use progressive testing: focused checks while editing, impacted unit/integration tests before commit or PR update, required domain and repository gates before PR readiness, and complete appropriate suites at integration/release checkpoints. Diagnose deterministic failures before rerunning.

### REVIEW

Inspect the entire diff, staged paths, assumptions, interfaces, security, PIT/leakage, source rights, identity/provenance, model claims, test quality, documentation, migrations, rollback, and unrelated changes. Re-read the issue and current PR head before state-changing operations.

### INTEGRATE

Use one coherent PR per meaningful Jira implementation unit or reviewable vertical slice. Reuse an existing matching PR. Require applicable CI, review, protected-branch policy, and head-SHA verification. Follow the configured merge policy; never force-push protected/shared branches.

### RECORD

Update Jira at meaningful milestones with concise outcome, acceptance status, tests/evidence, PR/commit, blockers, limitations, and legitimate follow-up. Update repository governance/provenance only when the work actually changes canonical state. Do not post every command or micro-step.

### CONTINUE

Verify integration, clean the merged branch/worktree only after unique-work and ownership checks, and select the next valid Ready item. Continue until a genuine `HUMAN_REQUIRED` boundary or global blocker exists. Do not manufacture housekeeping to avoid stopping.

## 5. Hard-stop conditions

Stop the affected operation, preserve evidence, and follow [17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md](17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md) when:

- repository identity or related history cannot be established;
- unknown changes or unique commits could be overwritten or deleted;
- another owner controls the same shared schema, ID space, PIT/evaluation contract, migration, manifest, or integration interface;
- source authorization, terms, licensing, redistribution, privacy, or trust boundaries are unclear;
- PIT, known-at, target-game exclusion, identity, snapshot immutability, provenance, or leakage validation fails;
- a candidate would need its own judge, protected split, or threshold weakened to pass;
- completion, performance, A&M lift, Aggie Excess, BAS, source data, or target-hardware evidence would have to be fabricated;
- a destructive, irreversible, production-affecting, security-sensitive, or materially expensive action lacks required approval;
- the same failure is repeating with unchanged inputs, hypothesis, and result.

A task blocker does not automatically block the project. Record it and select independent Ready work when safe.

## 6. Canonical instruction map and read budget

| Need | Canonical document | Read trigger |
|---|---|---|
| Project identity, W25 handoff, current honesty boundary | [01_PROJECT_IDENTITY_AND_HANDOFF.md](01_PROJECT_IDENTITY_AND_HANDOFF.md) | first hydration, state dispute, task selection |
| Source precedence and conflict resolution | [02_SOURCE_OF_TRUTH_AND_CONFLICT_RESOLUTION.md](02_SOURCE_OF_TRUTH_AND_CONFLICT_RESOLUTION.md) | source conflict or ambiguity |
| Repository architecture/navigation | [03_REPOSITORY_ARCHITECTURE_AND_NAVIGATION.md](03_REPOSITORY_ARCHITECTURE_AND_NAVIGATION.md) | task start, unfamiliar subsystem |
| Autonomy permission model | [04_AUTONOMOUS_OPERATING_CONTRACT.md](04_AUTONOMOUS_OPERATING_CONTRACT.md) | always; before high-risk action |
| Task selection, granularity, sequence | [05_TASK_SELECTION_AND_SEQUENCING.md](05_TASK_SELECTION_AND_SEQUENCING.md) | task selection or issue creation |
| Execution loop and meaningful progress | [06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md](06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md) | task start, drift, or context recovery |
| Live Jira operations | [07_JIRA_OPERATING_CONTRACT.md](07_JIRA_OPERATING_CONTRACT.md) | Jira read/write/status work |
| Local Jira mirror and traceability | [08_LOCAL_JIRA_MIRROR_AND_SYNC.md](08_LOCAL_JIRA_MIRROR_AND_SYNC.md) | hydration, sync, mapping |
| Git identity, dirty state, reconciliation | [09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md](09_GIT_REPOSITORY_SAFETY_AND_RECOVERY.md) | startup, dirty/uncertain repo |
| Branch/worktree/commit policy | [10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md](10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md) | branch, worktree, staging, commit |
| PR/review/merge/cleanup | [11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md](11_PULL_REQUEST_REVIEW_MERGE_AND_CLEANUP.md) | PR or integration lifecycle |
| CI, testing, evidence, DoD | [12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md](12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md) | validation and completion |
| Security, secrets, data rights, dependencies | [13_SECURITY_SECRETS_DATA_RIGHTS_AND_DEPENDENCIES.md](13_SECURITY_SECRETS_DATA_RIGHTS_AND_DEPENDENCIES.md) | external inputs, credentials, deps |
| Data/ML/PIT/provenance/evaluation | [14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md](14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md) | data/feature/model/BAS work |
| Architecture, docs, release, rollback | [15_ARCHITECTURE_DOCUMENTATION_RELEASE_AND_ROLLBACK.md](15_ARCHITECTURE_DOCUMENTATION_RELEASE_AND_ROLLBACK.md) | contract/design/release change |
| Parallelism, resources, context, handoff | [16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md](16_PARALLELISM_RESOURCES_CONTEXT_AND_HANDOFF.md) | multiple sessions or interruption |
| Blockers, loops, overengineering | [17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md](17_BLOCKERS_LOOPS_OVERENGINEERING_AND_RECOVERY.md) | failure, stall, scope growth |
| Runbook index | [18_OPERATIONAL_RUNBOOKS.md](18_OPERATIONAL_RUNBOOKS.md) | operational failure |
| GitHub settings/enforcement | [19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md](19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md) | repository activation/admin |
| Instruction maintenance | [20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md](20_INSTRUCTION_MAINTENANCE_AND_CHANGE_CONTROL.md) | policy changes |
| Packaging/integrity/installation | [21_PACKAGING_INTEGRITY_AND_INSTALLATION.md](21_PACKAGING_INTEGRITY_AND_INSTALLATION.md) | export or hydrate pack |
| Prompt compliance ledger | [22_MASTER_PROMPT_COMPLIANCE_LEDGER.md](22_MASTER_PROMPT_COMPLIANCE_LEDGER.md) | audit/review only |
| First activation and next-session launch | [23_ACTIVATION_AND_NEXT_SESSION.md](23_ACTIVATION_AND_NEXT_SESSION.md) | first use on Windows/live systems |
| Retired assistive/Fort Knox historical evidence | [25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md](25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md) | never as required reading; historical provenance only |

The machine-readable read tiers are in `policies/read_budget.json`; the file-by-file authority and trigger map is in `manifest.json`.

## 7. Current dependency truth

The final implementation order remains:

- **P0:** target-hardware evidence; source credentials/access/rights; immutable national historical materialization; canonical identity/population profiling; PIT historical state and leakage/replay validation.
- **P1:** simple baselines; chronological protected evaluation; calibration; champion/challenger promotion; A&M specialization; BAS/Aggie Excess validation with null-result acceptance.
- **P2:** weekly operation; immutable publication/serving; freshness measurement; backup/restore; observability; security; drift monitoring.
- **P3:** neural, sequence, graph, live/in-game, distributed, or other costly complexity only after admission evidence.

`HANDOFF-001` remains blocked until the representative target host exists. `HANDOFF-002` is the repository-evidenced independent P0 lane, subject to real credentials, access, source rights, and live Jira mapping. No source access or rights approval is implied by this pack.

## 8. Standard validation commands

During instruction/control changes:

```powershell
python -B tools\validate_autonomous_controls.py --repo-root . --strict
python -B tools\validate_jira_control_plane.py --repo-root . --strict
python -B -m unittest tests.test_instructions_pack tests.test_jira_control_plane -v
```

Before ordinary PR readiness, add the task’s focused and impacted tests plus:

```powershell
python -B tools\validate_w25_final.py --repo-root .
python -B tools\validate_repository.py --repo-root . --strict
python -B -m unittest discover -s tests -v
```

Run only gates applicable to the changed surface during development. The complete command and surface catalog is `catalogs/validation_command_catalog.json`.

## 9. Definition of Done reminder

A task is not Done because code exists, a test passed, or a PR was opened. Done requires the applicable acceptance criteria, implementation, integration, validation, security, traceability, evidence, documentation, provenance, Jira/PR linkage, limitation disclosure, and cleanup gates in [12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md](12_CI_TESTING_EVIDENCE_AND_DEFINITION_OF_DONE.md) and `policies/definition_of_done.json`.
