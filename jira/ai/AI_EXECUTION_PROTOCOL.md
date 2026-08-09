# AI Execution Protocol

1. Confirm the selected record is `READY=true`, is a Subtask, and has no unresolved external blocker.
2. Verify every hard dependency is `DONE` with `COMPLETE` or `VERIFIED` evidence at the required maturity.
3. Verify canonical source hashes; relocate changed anchors through controlled regeneration rather than trusting stale line numbers.
4. Read only required sources and implementation files.
5. Use the declared execution lane:
   - `SOLO_WORKTREE`: isolated changes with no protected shared-contract mutation.
   - `SHARED_CONTRACT`: serialize/coordinate contract changes and rerun affected consumers.
   - `PROTECTED_GATE`: never weaken or bypass; stop on ambiguity.
   - `RESEARCH_LANE`: preserve negative/null results and prohibit production promotion without gate evidence.
   - `DATA_MATERIALIZATION`: enforce source rights, immutable raw evidence, provenance, PIT rules, and resource limits.
   - `OPERATIONS`: preserve rollback, observability, security, and recovery behavior.
6. Execute only in-scope work. Record unexpected necessary work as a new review/gap proposal rather than silently expanding scope.
7. Save artifacts at declared paths or update the issue through a controlled specification change before producing alternatives.
8. Return exact commands, exit codes, hashes, row/season/source coverage, failures, and unresolved assumptions.

## Aggregate-gate review protocol


An `AGGREGATE_GATE` packet is never an implementation queue item. Use it only after child atomic work is complete to verify maturity/evidence, execute or review the integrated end-to-end gate, record residual blockers/nulls/accepted risks, and issue an evidence-backed closure decision. Route any code/data/contract mutation to a scoped atomic Subtask packet.
