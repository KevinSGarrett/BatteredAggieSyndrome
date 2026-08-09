# AI Work Packet — POST-SUBTASK-105

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`. Produce `artifacts/validation/PROMOTION_DECISION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`.
- Demonstrate with saved evidence: Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
- Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Demonstrate with saved evidence: A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/validation/PROMOTION_DECISION.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-105_publish_signed_champion_retain_incumbent_no_champion_artifacts_and_the_full_prom.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-105.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-105`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md

## Dependencies that must already be complete

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102
- POST-SUBTASK-103
- POST-SUBTASK-104

## Files I may modify or create

- artifacts/validation/PROMOTION_DECISION.json
- artifacts/jira_evidence/POST-SUBTASK-105.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- validation-promotion
- validation

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

- artifacts/validation/PROMOTION_DECISION.json

## Acceptance criteria

1. Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
2. No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
3. A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_validation_science_governance.py — Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_validation_science.py — Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/validation/PROMOTION_DECISION.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/validation/PROMOTION_DECISION.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/validation/PROMOTION_DECISION.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/validation/PROMOTION_DECISION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-012, POST-STORY-036, POST-STORY-045, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

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
