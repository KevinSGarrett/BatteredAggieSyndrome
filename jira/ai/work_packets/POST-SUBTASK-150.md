# AI Work Packet — POST-SUBTASK-150

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-050: Protected comparison and production disposition.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-050 (Protected comparison and production disposition): Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`, `POST-SUBTASK-149`. Produce `artifacts/advanced/challenger_closeout.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence.
- Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`, `POST-SUBTASK-149`.
- Demonstrate with saved evidence: The challenger receives identical evaluation, uncertainty/calibration/robustness/resource reporting, cannot alter prior champion evidence, and incomplete runs are not selectively summarized.
- Demonstrate with saved evidence: Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.
- Demonstrate with saved evidence: Active identities change only on successful promotion, all decisions/Jira/evidence reconcile, and GAP-013 remains conditional or closed by explicit disposition rather than a core blocker.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/advanced/challenger_closeout.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Generate challenger predictions on identical sealed protected games/cutoffs/metrics and complete scientific/resource scorecards; Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `P3`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONDITIONAL` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-150`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-150_reconcile_registries_artifacts_documentation_jira_state_operating_baseline_and_c.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-150.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-150`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_advanced_challenger_full.py
- docs/72_ADVANCED_CHALLENGER_ADMISSION.md
- docs/91_ADVANCED_CHALLENGER_GATE.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv

## Dependencies that must already be complete

- POST-SUBTASK-147
- POST-SUBTASK-148
- POST-SUBTASK-149

## Files I may modify or create

- artifacts/advanced/challenger_closeout.json
- artifacts/jira_evidence/POST-SUBTASK-150.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- advanced-challengers
- advanced

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

- artifacts/advanced/challenger_closeout.json

## Acceptance criteria

1. The challenger receives identical evaluation, uncertainty/calibration/robustness/resource reporting, cannot alter prior champion evidence, and incomplete runs are not selectively summarized.
2. Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.
3. Active identities change only on successful promotion, all decisions/Jira/evidence reconcile, and GAP-013 remains conditional or closed by explicit disposition rather than a core blocker.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_advanced_challenger_full.py — Run as a regression check after completing POST-SUBTASK-150; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/check_advanced_challenger_admission.py — Run as a regression check after completing POST-SUBTASK-150; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/advanced/challenger_closeout.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/advanced/challenger_closeout.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- OPERATIONS / OPERATIONS: artifacts/advanced/challenger_closeout.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/advanced/challenger_closeout.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/advanced/challenger_closeout.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

An optional challenger either survives the identical sealed production gate or remains preserved negative evidence without destabilizing the operating system. The gate decision must explicitly record that no downstream issue is silently unlocked.

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
