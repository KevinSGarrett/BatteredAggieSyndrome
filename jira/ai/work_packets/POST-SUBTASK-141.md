# AI Work Packet — POST-SUBTASK-141

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-047: Documentation, independent handoff, go-live review, and operating authorization.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-047 (Documentation, independent handoff, go-live review, and operating authorization): Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline. Consume only verified prerequisite outputs from `POST-SUBTASK-138`, `POST-SUBTASK-139`, `POST-SUBTASK-140`. Produce `artifacts/release/OPERATING_AUTHORIZATION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline.
- Consume only verified prerequisite outputs from `POST-SUBTASK-138`, `POST-SUBTASK-139`, `POST-SUBTASK-140`.
- Demonstrate with saved evidence: A new operator can execute exact verified commands, configure external roots/credentials, inspect Jira blockers, run/recover/rollback the product, and understands every manual/legal boundary without stale Wave-26 language.
- Demonstrate with saved evidence: Documentation reports actual coverage/metrics/calibration/uncertainty/OOD/A&M/BAS decisions/limitations/nulls and links every claim to immutable evidence with no unsupported SLA, causal, performance, or scientific claim.
- Demonstrate with saved evidence: Review records conflicts/residual risk/manual gates; authorization names exact release/model/data/product/Jira identities and supported modes or lists unmet evidence, never infers completion from planning or starter tests, and captures the operating baseline.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/release/OPERATING_AUTHORIZATION.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides; Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

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

1. `jira/records/issues/subtasks/POST-SUBTASK-141_conduct_technical_scientific_security_rights_operations_product_review_and_publi.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-141.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-141`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- docs/final/FINAL_RISK_REGISTER.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_w24_readiness.py
- tests/test_w25_final_handoff.py

## Dependencies that must already be complete

- POST-SUBTASK-138
- POST-SUBTASK-139
- POST-SUBTASK-140

## Files I may modify or create

- artifacts/release/OPERATING_AUTHORIZATION.json
- artifacts/jira_evidence/POST-SUBTASK-141.json

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

- artifacts/release/OPERATING_AUTHORIZATION.json

## Acceptance criteria

1. A new operator can execute exact verified commands, configure external roots/credentials, inspect Jira blockers, run/recover/rollback the product, and understands every manual/legal boundary without stale Wave-26 language.
2. Documentation reports actual coverage/metrics/calibration/uncertainty/OOD/A&M/BAS decisions/limitations/nulls and links every claim to immutable evidence with no unsupported SLA, causal, performance, or scientific claim.
3. Review records conflicts/residual risk/manual gates; authorization names exact release/model/data/product/Jira identities and supported modes or lists unmet evidence, never infers completion from planning or starter tests, and captures the operating baseline.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-141; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w25_final_handoff.py — Run as a regression check after completing POST-SUBTASK-141; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/release/OPERATING_AUTHORIZATION.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/release/OPERATING_AUTHORIZATION.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- SECURITY / SECURITY: artifacts/release/OPERATING_AUTHORIZATION.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/release/OPERATING_AUTHORIZATION.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/release/OPERATING_AUTHORIZATION.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/release/OPERATING_AUTHORIZATION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

An independent operator can reproduce and safely operate the exact approved release, or the system remains truthfully blocked with concrete evidence gaps. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-016, POST-EPIC-017, POST-STORY-048, POST-STORY-051, POST-SUBTASK-142, POST-SUBTASK-143, POST-SUBTASK-144, POST-SUBTASK-151, POST-SUBTASK-152, POST-SUBTASK-153.

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
