# Source of Truth and Conflict Resolution

The machine-readable precedence is canonical in `instructions/policies/source_precedence.json`. This document defines how to apply it without silently improvising.

## 1. Precedence hierarchy

1. Current explicit user instruction, subject to applicable safety, legal, license, privacy, authorization, and access restrictions.
2. Security, legal, license, privacy, access, authorization, and platform restrictions when they constrain the requested action.
3. `AGENTS.md`, `instructions/START_HERE.md`, and the canonical machine policies in this pack.
4. Terminal W25 handoff and immutable/protected governance.
5. Current state, final backlog, final maturity, known gaps, and implementation priority.
6. Current machine-readable requirements, ADR, acceptance, WBS, schema, configuration, and source/provenance registries.
7. Approved task-linked technical sources, including applicable architecture, schemas, interfaces, current code, tests, validators, and runtime evidence.
8. Verified live Jira execution metadata.
9. Sanitized local Jira mirror/index.
10. Historical wave and superseded records.
11. Agent inference.

The hierarchy does not mean code is unimportant. Code and tests prove current behavior, while accepted requirements/ADRs define intended behavior. A mismatch is a defect or controlled change decision, not permission to silently choose whichever is convenient.

## 2. Authority partition

| Information | Authority |
|---|---|
| User intent for the current task | Current explicit user instruction |
| Legal/license/access/security boundary | Applicable restriction or approved policy |
| Terminal program state/no Wave 26 | W25 handoff and current governance |
| Technical requirements and accepted architecture | Repository REQ/ADR/protected governance |
| Acceptance criteria and scientific judging rules | Repository acceptance registries and protected seal |
| Current issue status, assignee, hierarchy, blockers | Live Jira BAT after verified hydration |
| Current code behavior | Code plus executable tests/runtime evidence |
| PR/commit/check state | GitHub and local Git, reconciled by SHA |
| Local AI search/index | `jira/` mirror and instruction catalogs; derived, never overriding |

## 3. Conflict-resolution algorithm

When two sources materially disagree:

1. Record the exact claims, paths/IDs, versions/dates, and affected decision.
2. Assign each source a precedence level and authority scope.
3. Check supersession artifacts, current-state files, linked ADRs, acceptance mappings, and issue/PR history.
4. Determine whether the difference is real conflict, different scope, historical truth, maturity mismatch, or stale execution metadata.
5. Apply the higher-authority source only within its scope.
6. If the conflict changes requirements, architecture, protected rules, data semantics, or destructive integration, create a conflict/change record and obtain the required approval.
7. If safe work can continue without resolving the conflict, isolate and continue it.
8. If proceeding would risk wrong architecture, data corruption, leakage, security, or lost work, block the affected task with a precise unblock condition.
9. Update the canonical source or explicit supersession record; do not leave two active policies.

Use `instructions/templates/REPOSITORY_RECONCILIATION_RECORD.md` for repository/history conflicts and `instructions/templates/ARCHITECTURE_CHANGE_PROPOSAL.md` for material technical conflicts.

## 4. Historical document rule

Older wave documents may correctly describe the state at the time they were written. Phrases such as “next wave” or old branch patterns are historical, not necessarily current instructions. Do not rewrite historical evidence simply because W25 superseded its operational status. Add a current pointer or supersession record only when an active reader could reasonably mistake it for current policy.

## 5. Jira versus repository conflict examples

- Jira says Done but required acceptance evidence or merged code is absent: Jira is stale; do not accept Done. Reconcile Jira to technical evidence.
- Repository task row says `DONE_W07` but final maturity says functional starter: interpret the task as completed planning/contract work, not production capability.
- Jira summary conflicts with linked REQ/ADR: repository technical source wins; update or clarify Jira rather than implementing from summary alone.
- Local mirror differs from live Jira: live Jira wins for work state; regenerate the mirror.
- Code behavior conflicts with a protected requirement: treat it as a defect unless a valid controlled change supersedes the requirement.

## 6. Inference boundary

Inference may fill a low-risk local detail only when no authoritative source exists and the choice is reversible, testable, and recorded. Inference may never create credentials, live Jira metadata, source rights, performance evidence, A&M/BAS effects, target-hardware thresholds, protected evaluation rules, or facts about unknown local Git history.
