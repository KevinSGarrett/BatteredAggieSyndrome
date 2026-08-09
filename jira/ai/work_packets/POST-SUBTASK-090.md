# AI Work Packet — POST-SUBTASK-090

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate direction, thresholds, row lineage, fold isolation, and anti-circularity

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-030: Cross-fitted expectation and protected severity labels.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-030 (Cross-fitted expectation and protected severity labels): Validate direction, thresholds, row lineage, fold isolation, and anti-circularity. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`. Produce `artifacts/bas/bas_label_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate direction, thresholds, row lineage, fold isolation, and anti-circularity.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`.
- Demonstrate with saved evidence: Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
- Demonstrate with saved evidence: Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
- Demonstrate with saved evidence: Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/bas/bas_label_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game; Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-096`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-090_validate_direction_thresholds_row_lineage_fold_isolation_and_anti_circularity.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-090.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-090`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Dependencies that must already be complete

- POST-SUBTASK-051
- POST-SUBTASK-078
- POST-SUBTASK-088
- POST-SUBTASK-089

## Files I may modify or create

- artifacts/bas/bas_label_gate.json
- artifacts/jira_evidence/POST-SUBTASK-090.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- bas-science
- bas

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

- artifacts/bas/bas_label_gate.json

## Acceptance criteria

1. Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
2. Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
3. Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
5. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
6. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_bas_science_governance.py — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_bas_science.py — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/bas/bas_label_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/bas/bas_label_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/bas/bas_label_gate.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/bas/bas_label_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/bas/bas_label_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-011, POST-STORY-031, POST-STORY-033, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097, POST-SUBTASK-098, POST-SUBTASK-099.

## Stop instead of improvising when

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

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
