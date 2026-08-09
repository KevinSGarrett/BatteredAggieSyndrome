# 12 — Shared Contracts & Worktree Strategy

## Why serialization exists
Parallel work is valuable only across independent boundaries. Canonical IDs, PIT semantics, feature-registry schemas, model target schemas, protected evaluation rules and forecast snapshot schemas are shared contracts: concurrent mutation before freeze creates semantic split-brain.

## Rules
- One mutation owner per unfrozen shared contract.
- Other worktrees consume the latest accepted interface or remain blocked.
- Contract-breaking changes require an ADR/traceability update and dependent-task impact review.
- Worktree integration order follows dependency edges, not branch completion order.
- Rebase/merge success is not sufficient if semantic acceptance controls fail.

See `governance/SHARED_CONTRACT_OWNERSHIP.csv` for current ownership and gate rules.
