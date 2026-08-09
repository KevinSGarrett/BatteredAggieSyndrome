# GitHub + Codex Workflow — Wave 02

## Branching
Default: `codex/<epic>-<task>`. Use focused worktrees for isolated implementation. Avoid parallel edits to unfrozen shared contracts.

## Pull requests
Every material change should identify relevant REQ/ADR IDs, maturity level and validation evidence. A scaffold must not be labeled production-ready.

## CI boundary
Wave 02 provides a minimal cross-platform CI lane on Windows and Linux using Python 3.12. It checks the package scaffold, standard-library unit tests and the same repository-integrity command used locally.

Full security scanning, dependency automation, observability and deployment CI remain Wave 23 work unless an earlier dependency requires them.

## Codex
`.codex/` contains task/worktree contracts only. It intentionally avoids an unverified tool-specific configuration format. Codex should inspect the actual repository and active wave state before mutation.
