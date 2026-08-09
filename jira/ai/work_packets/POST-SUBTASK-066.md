# AI Work Packet — POST-SUBTASK-066

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate identity, timing, source-scale compatibility, sparse-history shrinkage, and experimental eligibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-022: Recruiting, transfer, freshman, coaching, and continuity intelligence.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-022 (Recruiting, transfer, freshman, coaching, and continuity intelligence): Validate identity, timing, source-scale compatibility, sparse-history shrinkage, and experimental eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-063`, `POST-SUBTASK-064`, `POST-SUBTASK-065`. Produce `artifacts/context_intelligence/program_intelligence_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate identity, timing, source-scale compatibility, sparse-history shrinkage, and experimental eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-063`, `POST-SUBTASK-064`, `POST-SUBTASK-065`.
- Demonstrate with saved evidence: Events preserve published/effective times, source scales, identity confidence, decommitments/re-rankings/portal withdrawals, interim/overlapping staff roles, and prior versions.
- Demonstrate with saved evidence: Aggregates use only prior eligible state, distinguish returning production/recruits/transfers, expose early-season uncertainty, and do not encode culture/clutch/collapse without measurable definitions.
- Demonstrate with saved evidence: Temporal perturbation, coverage, and scale tests pass; sparse/unsupported candidates remain experimental or rejected and are not assumed predictive.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/context_intelligence/program_intelligence_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize recruiting class, prospect, commitment, signing, enrollment, transfer, coach, coordinator, role, tenure, and transition events; Build PIT roster-talent, experience, retention, transfer/freshman, staff/QB/system continuity, prior-performance, and bounded scheme-proxy candidates.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-069`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-066_validate_identity_timing_source_scale_compatibility_sparse_history_shrinkage_and.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-066.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-066`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/context_intelligence/context.py
- src/aggie_analytics/player_intelligence/advanced_state.py
- docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md
- docs/29_TEAM_STATE_ARCHITECTURE.md

## Dependencies that must already be complete

- POST-SUBTASK-063
- POST-SUBTASK-064
- POST-SUBTASK-065

## Files I may modify or create

- artifacts/context_intelligence/program_intelligence_gate.json
- artifacts/jira_evidence/POST-SUBTASK-066.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- player-context-intelligence
- advanced-football

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

- artifacts/context_intelligence/program_intelligence_gate.json

## Acceptance criteria

1. Events preserve published/effective times, source scales, identity confidence, decommitments/re-rankings/portal withdrawals, interim/overlapping staff roles, and prior versions.
2. Aggregates use only prior eligible state, distinguish returning production/recruits/transfers, expose early-season uncertainty, and do not encode culture/clutch/collapse without measurable definitions.
3. Temporal perturbation, coverage, and scale tests pass; sparse/unsupported candidates remain experimental or rejected and are not assumed predictive.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_player_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-066; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_context_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-066; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_team_state_governance.py — Run as a regression check after completing POST-SUBTASK-066; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/context_intelligence/program_intelligence_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/context_intelligence/program_intelligence_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/context_intelligence/program_intelligence_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Recruiting, portal, freshman, coaching, coordinator, and continuity state is reproducible at each cutoff without current-season hindsight. The gate decision must explicitly reevaluate downstream issues: POST-STORY-027, POST-SUBTASK-079, POST-SUBTASK-080, POST-SUBTASK-081.

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
