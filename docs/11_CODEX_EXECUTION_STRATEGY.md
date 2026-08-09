# 11 — Codex Continuous Execution Strategy

Status: W05 operating plan; implementation begins only in the active owner wave.

## Queue behavior
Codex pulls the highest-priority **READY** packet whose dependencies and owner-wave gate are satisfied. It must not pull work from a future wave merely because local capacity is idle.

## Packet contract
Each packet carries: stable packet/epic/task IDs, owner wave, dependencies, mutation scope, worktree pattern, declared outputs, requirement IDs, acceptance controls, evidence expectations and explicit stop conditions.

## 24/7 operating principle
Continuous operation means continuously selecting valid ready work, not bypassing governance. When no packet is ready, the correct action is to stop/await the next user-authorized wave or unresolved dependency rather than invent work.

## Parallelism
Parallelism is **bounded and adaptive**, not a fixed concurrency target. Independent packets may run in parallel only when they do not mutate the same unfrozen shared contract and local CPU/RAM/storage pressure remains acceptable.

## Integration sequence
1. Verify active wave and parent pair.
2. Select READY packet.
3. Create `codex/<epic>-<task>` worktree/branch.
4. Read relevant contracts/REQ/ADR/AC IDs.
5. Mutate only declared scope.
6. Run focused tests, then repository/architecture/acceptance/backlog gates as applicable.
7. Mark `EVIDENCE_PENDING` until required evidence is recorded.
8. Integrate only after shared-contract ownership and acceptance gate clear.
9. Update task/backlog/provenance state.

## Stop conditions
Stop the packet rather than improvising when: a source/access assumption is invalid; a protected PIT/leakage/evaluation rule is ambiguous; a required predecessor is not accepted; a shared contract has another mutation owner; requested work would enter a future wave; or a change would require rewriting the judging rules.

## Research-agent separation
Research may propose challengers and create isolated experiments. It cannot change protected splits, leakage rules, BAS primary definition, promotion thresholds after protected results, or champion state to make itself pass.
