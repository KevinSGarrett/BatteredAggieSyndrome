# AI Work Packet — POST-SUBTASK-135

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish final coverage metrics and unresolved release-blocker register

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-045: Final traceability, maturity, gap, risk, and evidence audit.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-045 (Final traceability, maturity, gap, risk, and evidence audit): Publish final coverage metrics and unresolved release-blocker register. Consume only verified prerequisite outputs from `POST-SUBTASK-105`, `POST-SUBTASK-114`, `POST-SUBTASK-123`, `POST-SUBTASK-132`, `POST-SUBTASK-133`, `POST-SUBTASK-134`. Produce `artifacts/release/final_coverage_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish final coverage metrics and unresolved release-blocker register.
- Consume only verified prerequisite outputs from `POST-SUBTASK-105`, `POST-SUBTASK-114`, `POST-SUBTASK-123`, `POST-SUBTASK-132`, `POST-SUBTASK-133`, `POST-SUBTASK-134`.
- Demonstrate with saved evidence: Every active obligation/release-blocking control maps to current evidence and Jira; all 14 final gaps and 310 final risks have actionable, accepted/deferred, N-A, or verified-closed dispositions, with historical-only mappings flagged.
- Demonstrate with saved evidence: Synthetic validation is not real empirical validation, functional starters are not production-ready, and every DESIGN_ONLY→OPERATING claim cites verifiable evidence or remains blocked/conflicted/manual.
- Demonstrate with saved evidence: Coverage reports unmapped/invalid/orphan/cycle/missing-AC/DoD/test/evidence/source issues and zero blockers only when supported; conditional advanced and deferred live work are excluded only explicitly.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/release/final_coverage_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Regenerate bidirectional source, requirement, acceptance, ADR, gap, risk, test, artifact, issue, and evidence traceability; Audit every component maturity and completion claim against actual repository/runtime artifacts, tests, real-data runs, and applicable scope.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DESIGN_ONLY` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-141`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-135_publish_final_coverage_metrics_and_unresolved_release_blocker_register.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-135.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-135`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- docs/final/FINAL_RISK_REGISTER.csv
- tests/test_w24_readiness.py
- tests/test_w25_final_handoff.py
- docs/111_W24_END_TO_END_READINESS_AUDIT.md

## Dependencies that must already be complete

- POST-SUBTASK-105
- POST-SUBTASK-114
- POST-SUBTASK-123
- POST-SUBTASK-132
- POST-SUBTASK-133
- POST-SUBTASK-134

## Files I may modify or create

- artifacts/release/final_coverage_gate.json
- artifacts/jira_evidence/POST-SUBTASK-135.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- release-readiness
- release

## What I must not modify or weaken

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Exact outputs / integrated artifacts

Produce and validate these outputs within this atomic work unit:

- artifacts/release/final_coverage_gate.json

## Acceptance criteria

1. Every active obligation/release-blocking control maps to current evidence and Jira; all 14 final gaps and 310 final risks have actionable, accepted/deferred, N-A, or verified-closed dispositions, with historical-only mappings flagged.
2. Synthetic validation is not real empirical validation, functional starters are not production-ready, and every DESIGN_ONLY→OPERATING claim cites verifiable evidence or remains blocked/conflicted/manual.
3. Coverage reports unmapped/invalid/orphan/cycle/missing-AC/DoD/test/evidence/source issues and zero blockers only when supported; conditional advanced and deferred live work are excluded only explicitly.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-135; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w25_final_handoff.py — Run as a regression check after completing POST-SUBTASK-135; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w25_final.py — Run as a regression check after completing POST-SUBTASK-135; retain command, exit code, and relevant output.
- OPERATIONS / OPERATIONS: artifacts/release/final_coverage_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/release/final_coverage_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/release/final_coverage_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Every release claim and exclusion can be traced to concrete current evidence, with no gap, risk, requirement, or control disappearing behind historical Done labels. The gate decision must explicitly reevaluate downstream issues: POST-STORY-046, POST-SUBTASK-136, POST-SUBTASK-137, POST-SUBTASK-138.

## Stop instead of improvising when

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Completion protocol

1. Produce an acceptance-evidence matrix for every criterion.
2. Run every applicable validation entry; implement each declared new automated test.
3. Hash and register every output and all source/data/code/config/tool/runtime identities.
4. Preserve negative, null, blocked, and failed results.
5. Confirm that the claimed maturity—not merely code or files—exists.
6. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md`.
7. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`.
8. Recompute READY/BLOCKED state and run `python -B jira/tools/validate_second_pass.py`.
9. Reevaluate every downstream issue in `blocks`.
