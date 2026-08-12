# AI Work Packet — POST-SUBTASK-126

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate protected-branch/release blocking and auditable exception behavior

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-042: CI, dependency, secret, license, and supply-chain controls.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-042 (CI, dependency, secret, license, and supply-chain controls): Validate protected-branch/release blocking and auditable exception behavior. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-124`, `POST-SUBTASK-125`. Produce `artifacts/operations/ci_security_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate protected-branch/release blocking and auditable exception behavior.
- Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-124`, `POST-SUBTASK-125`.
- Demonstrate with saved evidence: CI runs all required suites from a clean state, preserves failure logs/evidence, and cannot skip gates through naming/retry while keeping the local workflow runnable without Kubernetes/Kafka/Redis/cloud dependency.
- Demonstrate with saved evidence: Locks/hashes/findings/licenses/secrets/restricted patterns are recorded with severity/remediation or accepted-risk disposition and no credential/raw restricted payload reaches repository or CI artifacts.
- Demonstrate with saved evidence: Any release-blocking test, secret, integrity, rights, or protected-control failure stops release; manual exceptions are explicit, attributable, time-bounded, and cannot weaken science/PIT rules.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/operations/ci_security_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Establish clean-environment CI for repository tests, Jira validators, static checks, import dry-run, and deterministic packaging; Implement dependency-lock, vulnerability, secret, license/notice, restricted-data pattern, and artifact-integrity checks.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-132`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-126_validate_protected_branch_release_blocking_and_auditable_exception_behavior.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-126.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-126`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w23_operations.py
- src/aggie_analytics/operations/backup.py
- src/aggie_analytics/operations/observability.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/CI_SECURITY_SUPPLY_CHAIN.md
- docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md

## Dependencies that must already be complete

- POST-SUBTASK-002
- POST-SUBTASK-124
- POST-SUBTASK-125

## Files I may modify or create

- artifacts/operations/ci_security_gate.json
- artifacts/jira_evidence/POST-SUBTASK-126.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- operations

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

- artifacts/operations/ci_security_gate.json

## Acceptance criteria

1. CI runs all required suites from a clean state, preserves failure logs/evidence, and cannot skip gates through naming/retry while keeping the local workflow runnable without Kubernetes/Kafka/Redis/cloud dependency.
2. Locks/hashes/findings/licenses/secrets/restricted patterns are recorded with severity/remediation or accepted-risk disposition and no credential/raw restricted payload reaches repository or CI artifacts.
3. Any release-blocking test, secret, integrity, rights, or protected-control failure stops release; manual exceptions are explicit, attributable, time-bounded, and cannot weaken science/PIT rules.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-126; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-126; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-126; retain command, exit code, and relevant output.
- PUBLICATION_BOUNDARY_REVIEW / PUBLICATION_BOUNDARY_REVIEW: MANUAL — Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled.
- MANUAL / MANUAL: artifacts/operations/ci_security_gate.json — Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/operations/ci_security_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SECURITY / SECURITY: artifacts/operations/ci_security_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/operations/ci_security_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/operations/ci_security_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/operations/ci_security_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

A clean change cannot produce a release package unless code, Jira, security, integrity, and protected-governance gates all pass. The gate decision must explicitly reevaluate downstream issues: POST-STORY-043, POST-SUBTASK-127, POST-SUBTASK-128, POST-SUBTASK-129.

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
