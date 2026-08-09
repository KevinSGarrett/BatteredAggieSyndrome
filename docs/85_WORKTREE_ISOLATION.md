# Research Worktree Isolation and Mutation Boundaries

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Isolation

Code-changing experiments execute in dedicated `codex/<epic>-<task>`-style worktrees or verified immutable source snapshots. The authoritative canonical repository is not an experiment scratch directory.

## Protected paths

The W17 protected split, metric, threshold-method, promotion-rule and judging-seal artifacts are read-only to experiment workers. W08 PIT rules, W15 BAS label definitions, and other shared contracts are also outside ordinary mutation scope unless the active owner wave explicitly authorizes a contract change.

## Allowed mutation

Typical experiment worktrees may alter experiment-local model/feature code, configuration, tests, and reports within declared scope. Outputs are written under experiment-local artifact locations and later adopted through reviewed changes; no worker writes directly into champion/model registry state.

## Merge discipline

A successful experiment does not imply merge approval. The research evidence packet identifies the relevant commit/diff and review requirements. Failed/rejected worktrees may be retained until evidence/artifacts are captured, then archived or deleted according to policy.

## Parallelism

Parallel work is bounded by CPU/RAM/GPU/storage and shared-contract conflicts. Multiple experiments can run when inputs are immutable and mutation scopes do not overlap. Shared schema/governance changes serialize.
