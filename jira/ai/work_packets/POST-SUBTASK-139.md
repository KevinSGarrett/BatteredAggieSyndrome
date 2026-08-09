# AI Work Packet — POST-SUBTASK-139

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-047: Documentation, independent handoff, go-live review, and operating authorization.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-047 (Documentation, independent handoff, go-live review, and operating authorization): Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides. Consume only verified prerequisite outputs from `POST-SUBTASK-138`. Produce `docs/operations/PRODUCTION_OPERATOR_GUIDE.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-140.

### In scope

- Perform the exact action: Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides.
- Consume only verified prerequisite outputs from `POST-SUBTASK-138`.
- Demonstrate with saved evidence: A new operator can execute exact verified commands, configure external roots/credentials, inspect Jira blockers, run/recover/rollback the product, and understands every manual/legal boundary without stale Wave-26 language.
- Demonstrate with saved evidence: The declared output `docs/operations/PRODUCTION_OPERATOR_GUIDE.md` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `docs/operations/PRODUCTION_OPERATOR_GUIDE.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest; Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DESIGN_ONLY` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-141`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-139_finalize_verified_operator_developer_installation_credentials_rights_weekly_run_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-139.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-139`.
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
- docs/readiness/W24_END_TO_END_READINESS.md

## Dependencies that must already be complete

- POST-SUBTASK-138

## Files I may modify or create

- docs/operations/PRODUCTION_OPERATOR_GUIDE.md
- artifacts/jira_evidence/POST-SUBTASK-139.json

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

- docs/operations/PRODUCTION_OPERATOR_GUIDE.md

## Acceptance criteria

1. A new operator can execute exact verified commands, configure external roots/credentials, inspect Jira blockers, run/recover/rollback the product, and understands every manual/legal boundary without stale Wave-26 language.
2. The declared output `docs/operations/PRODUCTION_OPERATOR_GUIDE.md` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-139; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-139; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: docs/operations/PRODUCTION_OPERATOR_GUIDE.md — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- SECURITY / SECURITY: docs/operations/PRODUCTION_OPERATOR_GUIDE.md — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: docs/operations/PRODUCTION_OPERATOR_GUIDE.md — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- STATIC_VALIDATION / STATIC_VALIDATION: docs/operations/PRODUCTION_OPERATOR_GUIDE.md — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `docs/operations/PRODUCTION_OPERATOR_GUIDE.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `docs/operations/PRODUCTION_OPERATOR_GUIDE.md` can be parsed and consumed by `POST-SUBTASK-140` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
