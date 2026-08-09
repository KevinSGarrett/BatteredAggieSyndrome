# AI Work Packet — POST-SUBTASK-125

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement dependency-lock, vulnerability, secret, license/notice, restricted-data pattern, and artifact-integrity checks

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-042: CI, dependency, secret, license, and supply-chain controls.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-042 (CI, dependency, secret, license, and supply-chain controls): Implement dependency-lock, vulnerability, secret, license/notice, restricted-data pattern, and artifact-integrity checks. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-124`. Produce `artifacts/operations/security_supply_chain_report.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-126.

### In scope

- Perform the exact action: Implement dependency-lock, vulnerability, secret, license/notice, restricted-data pattern, and artifact-integrity checks.
- Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-124`.
- Demonstrate with saved evidence: Locks/hashes/findings/licenses/secrets/restricted patterns are recorded with severity/remediation or accepted-risk disposition and no credential/raw restricted payload reaches repository or CI artifacts.
- Demonstrate with saved evidence: The declared output `artifacts/operations/security_supply_chain_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/operations/security_supply_chain_report.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Establish clean-environment CI for repository tests, Jira validators, static checks, import dry-run, and deterministic packaging; Validate protected-branch/release blocking and auditable exception behavior.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SECURITY`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-132`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-125_implement_dependency_lock_vulnerability_secret_license_notice_restricted_data_pa.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-125.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-125`.
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
- docs/operations/OBSERVABILITY.md
- .github/workflows/ci.yml
- pyproject.toml
- requirements/product.lock
- tools/validate_dependency_policy.py

## Dependencies that must already be complete

- POST-SUBTASK-002
- POST-SUBTASK-124

## Files I may modify or create

- .github/dependabot.yml
- .github/workflows/ci.yml
- artifacts/operations/security_supply_chain_report.json
- artifacts/jira_evidence/POST-SUBTASK-125.json
- docs/operations/CI_SECURITY_SUPPLY_CHAIN.md
- pyproject.toml
- requirements/product.lock
- tests/test_product_supply_chain.py
- tools/validate_dependency_policy.py
- tools/validate_product_supply_chain.py

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

- artifacts/operations/security_supply_chain_report.json

## Acceptance criteria

1. Locks/hashes/findings/licenses/secrets/restricted patterns are recorded with severity/remediation or accepted-risk disposition and no credential/raw restricted payload reaches repository or CI artifacts.
2. The declared output `artifacts/operations/security_supply_chain_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-125; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-125; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-125; retain command, exit code, and relevant output.
- SECURITY / SECURITY: tests/test_product_supply_chain.py — Prove exact/hash lock parsing, direct-pin coverage, malformed or missing hash rejection, and deterministic installed license/notice inventory behavior.
- LEGAL_RIGHTS_REVIEW / LEGAL_RIGHTS_REVIEW: MANUAL_REVIEW_REQUIRED — A named human reviewer records source-specific access, retention, training, publication, and redistribution decisions with terms/version/date evidence.
- MANUAL / MANUAL: artifacts/operations/security_supply_chain_report.json — Verify reviewer identity, decision date, unresolved questions, and explicit allow/block conditions.
- SCIENTIFIC / SCIENTIFIC: artifacts/operations/security_supply_chain_report.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- SECURITY / SECURITY: artifacts/operations/security_supply_chain_report.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/operations/security_supply_chain_report.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- INTEGRATION / INTEGRATION: artifacts/operations/security_supply_chain_report.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/operations/security_supply_chain_report.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/operations/security_supply_chain_report.json` can be parsed and consumed by `POST-SUBTASK-126` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Stop instead of improvising when

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
