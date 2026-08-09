# Jira BAT Operating Contract

Jira BAT is the authoritative execution/work-state system for this project. It is not the canonical technical specification and must not become a prose copy of the entire repository.

The machine companion is `policies/jira_operating_policy.json`. Exact workflow names/transitions are governed by the verified live snapshot in `jira/status_map.json`; conceptual states alone are never permission to write a transition.

## 1. Mandatory live-board discovery

Before any Jira write or exact workflow instruction:

1. Resolve accessible Atlassian resources.
2. Require the site `https://kevinsgarrett.atlassian.net`.
3. Require project key `BAT` and verify project/board identity.
4. Read issue types, field catalog, statuses, transitions, board filter, and current issue population.
5. Read a representative issue in each relevant hierarchy/status to understand actual field use.
6. Hydrate `jira/project.json`, `jira/field_map.json`, `jira/workflow_snapshot.json`, and `jira/status_map.json` read-only.
7. Run `python -B tools/validate_jira_control_plane.py --repo-root . --strict`.

If the correct site is unavailable, do not substitute another Atlassian site, invent fields/statuses, or write Jira. Record an access blocker. Repository/Git analysis and independent implementation planning may continue when safe.

## 2. Jira authority and repository authority

### Live Jira owns

- issue existence and hierarchy;
- current workflow status;
- assignment/claim and active execution lane;
- Jira-native dependencies/blockers and priority;
- concise implementation/integration evidence;
- PR and branch/worktree links where fields support them.

### Repository owns

- requirements and their exact meaning;
- accepted architecture and ADRs;
- protected acceptance/evaluation rules;
- schemas/interfaces/code/tests;
- source, PIT, identity, provenance, model/BAS contracts;
- final W25 handoff and technical backlog rationale.

A Jira summary is a work order and navigation point. It is not enough to implement a material task by itself.

## 3. Mandatory issue-reading sequence

Before implementation, inspect in order:

1. Jira issue description and acceptance criteria.
2. Parent Story/Task and Epic.
3. Inward/outward dependency links and blockers.
4. Linked internal `EPIC-###` and `TASK-###` identifiers.
5. Linked `REQ-###` identifiers.
6. Linked `ADR-###` identifiers.
7. Linked `AC-###` acceptance-control identifiers.
8. Linked source/project-plan documents.
9. Relevant architecture and protected governance.
10. Existing implementation and recent related PRs/commits.
11. Relevant tests, schemas, interfaces, and consumers.
12. Shared-contract ownership and active claims.

Then create the task packet. Do not begin coding because the issue title sounds clear.

## 4. Traceability contract

Every material issue should be able to answer:

- Why does this work exist?
- Which internal epic/task or final handoff workstream requires it?
- Which requirements must be satisfied?
- Which ADRs constrain the design?
- Which acceptance controls prove completion?
- Which documents/contracts are canonical?
- Which predecessors and shared contracts matter?
- Which branch/worktree/agent owns it?
- Which PR and important commit(s) implement it?
- Which tests/evidence prove it?
- Which limitations/follow-ups remain?

Use `templates/JIRA_SOURCE_REFERENCE_BLOCK.md`. Stable technical mappings belong in `jira/issue_source_map.json`; live status/assignment stays in Jira.

## 5. Issue selection and claim

Select work using `05_TASK_SELECTION_AND_SEQUENCING.md` and live Jira.

Before moving Ready → In Progress or its verified live equivalent, record:

- agent/session identifier;
- branch;
- worktree path or canonical worktree justification;
- one-sentence outcome and scope;
- shared-contract ownership/locks;
- start timestamp;
- expected integration order when parallel work exists.

Do not claim multiple items merely to reserve them. Release or transfer a claim when ownership changes.

## 6. Status hygiene

The conceptual state machine is:

`BACKLOG → READY → IN_PROGRESS → REVIEW → DONE`

with `BLOCKED` and `CANCELED` paths.

Actual BAT names may differ. Use only verified live transitions.

### Backlog

Known work not yet dependency-ready, selected, or fully sourced.

### Ready

All mandatory predecessors, inputs, rights/access, ownership, and protected gates permit a coherent implementation unit.

### In Progress

One real implementation lane is active. The issue has an owner, branch/worktree, scope, and meaningful work underway.

### Blocked

A specific evidenced condition prevents safe progress. “Hard” or “taking time” is not a blocker. Record category, evidence, unblock condition, owner, affected dependencies, and independent work selected.

### Review

A coherent change exists and is in Draft/Ready PR, CI, review, or integration. Do not move to review for an empty branch or speculative plan.

### Done

The canonical Definition of Done is satisfied and integration/evidence are recorded. Code merely existing, a PR being opened, or a unit test passing is insufficient.

### Canceled

Duplicate, rejected, superseded, or no longer required, with rationale and downstream review.

## 7. Meaningful Jira updates

Update Jira at these events:

1. **Claim/start** — owner, branch/worktree, scope, sources.
2. **Material change** — scope, architecture decision, dependency, or acceptance change.
3. **Blocker/unblock** — exact evidence and next condition.
4. **Review/integration** — Draft/Ready PR and meaningful test state.
5. **Completion** — outcome, acceptance, tests, PR/merge, limitations/follow-ups.

Do not comment every command, file edit, test rerun, or commit. Jira is not a terminal transcript.

## 8. Completion update content

A concise completion update should include:

- delivered outcome;
- acceptance criteria/control status;
- test/validator commands and results;
- PR URL/number and merge commit or squash SHA;
- important data/model/provenance artifact IDs when applicable;
- security/PIT/leakage/source-rights implications;
- limitations and legitimate follow-ups;
- cleanup/handoff state.

Do not paste secrets, raw restricted data, huge logs, or entire project documents.

## 9. Blockers

Use categories defined in `policies/blocker_taxonomy.json`, including dependency, data/source, credentials/access, rights, shared contract, protected governance, CI/environment, ambiguity, external service, human approval, and resource capacity.

A blocker record must include:

- exact condition and evidence;
- attempted approaches with changed hypotheses;
- what specifically unblocks it and who owns that action;
- dependent issues affected;
- safe independent Ready work chosen.

Never mark Done to escape a blocker or create fake substitute data.

## 10. Ticket granularity and anti-spam

### Epic

A substantial product capability/outcome spanning multiple meaningful implementation units.

### Story/Task

A coherent independently reviewable implementation or deliverable with acceptance evidence.

### Subtask

Use only when separate ownership, dependency, status, or review tracking provides value.

### Checklist/commit/PR detail

Use for micro-steps, files, functions, tests, commands, small refactors, retries, and task-internal documentation.

Before creating an issue, search Jira and the local source map for duplicates and verify that the internal WBS/final backlog does not already represent the outcome.

## 11. Jira and GitHub synchronization

- Branch/PR title and description include `BAT-###`.
- Jira records branch/worktree and PR once meaningful.
- PR records Jira, internal task/REQ/ADR/AC/source references.
- Status changes reflect real PR/CI/integration state.
- Reuse the existing PR for the issue; do not create a new PR for every retry.
- GitHub Issues do not mirror every Jira issue.

GitHub Issues may be used for public/external repository defects where Jira access is inappropriate, but internal work must still be mapped to Jira when adopted.

## 12. Secret, data, and evidence hygiene

Never place credentials, tokens, `.env` values, full restricted source payloads, private keys, sensitive local paths containing credentials, or unredacted secret-bearing logs in Jira.

Use environment-variable names, artifact IDs, redacted excerpts, and repository paths. Attach only evidence permitted by source rights and privacy policy.
