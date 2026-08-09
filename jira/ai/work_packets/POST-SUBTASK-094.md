# AI Work Packet — POST-SUBTASK-094

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-032: Protected calibration, stability, scientific decision, and product semantics.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-032 (Protected calibration, stability, scientific decision, and product semantics): Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions. Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-102`. Produce `artifacts/bas/bas_protected_scorecard.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-095.

### In scope

- Perform the exact action: Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions.
- Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.
- Demonstrate with saved evidence: The declared output `artifacts/bas/bas_protected_scorecard.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/bas/bas_protected_scorecard.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses; Publish the final BAS scientific decision and prediction-first product language contract.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `SCIENTIFIC`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-096`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-094_evaluate_3_7_14_21_calibration_discrimination_reliability_uncertainty_and_nation.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-094.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-094`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md
- docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md

## Dependencies that must already be complete

- POST-SUBTASK-093
- POST-SUBTASK-102

## Files I may modify or create

- artifacts/bas/bas_protected_scorecard.json
- artifacts/jira_evidence/POST-SUBTASK-094.json

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

- artifacts/bas/bas_protected_scorecard.json

## Acceptance criteria

1. Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.
2. The declared output `artifacts/bas/bas_protected_scorecard.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
5. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_bas_science_governance.py — Run as a regression check after completing POST-SUBTASK-094; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-094; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_bas_science.py — Run as a regression check after completing POST-SUBTASK-094; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/bas/bas_protected_scorecard.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/bas/bas_protected_scorecard.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/bas/bas_protected_scorecard.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/bas/bas_protected_scorecard.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/bas/bas_protected_scorecard.json` can be parsed and consumed by `POST-SUBTASK-095` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Stop instead of improvising when

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.
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
