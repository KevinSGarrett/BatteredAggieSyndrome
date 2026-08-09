# AI Work Packet — POST-SUBTASK-092

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Estimate A&M excess versus FBS, precommitted peers/regimes, and matched contexts plus offensive/defensive/special-teams/collapse component evidence

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-031: General FBS baseline, Aggie excess, and components.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-031 (General FBS baseline, Aggie excess, and components): Estimate A&M excess versus FBS, precommitted peers/regimes, and matched contexts plus offensive/defensive/special-teams/collapse component evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-091`. Produce `artifacts/bas/aggie_excess_components.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-093.

### In scope

- Perform the exact action: Estimate A&M excess versus FBS, precommitted peers/regimes, and matched contexts plus offensive/defensive/special-teams/collapse component evidence.
- Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-091`.
- Demonstrate with saved evidence: A&M analyses use sealed expectations/peers, report effect/sample/sensitivity uncertainty, accept zero/negative/unstable excess, and make components unavailable when granular evidence is absent.
- Demonstrate with saved evidence: The declared output `artifacts/bas/aggie_excess_components.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/bas/aggie_excess_components.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Estimate out-of-sample general FBS severity probabilities and residual distributions across seasons/regimes/contexts; Validate peer sensitivity, multiple comparisons, component coherence, uncertainty, coverage, and null-result handling.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `SCIENTIFIC`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-096`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-092_estimate_a_and_m_excess_versus_fbs_precommitted_peers_regimes_and_matched_contex.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-092.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-092`.
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
- docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md

## Dependencies that must already be complete

- POST-SUBTASK-084
- POST-SUBTASK-090
- POST-SUBTASK-091

## Files I may modify or create

- artifacts/bas/aggie_excess_components.json
- artifacts/jira_evidence/POST-SUBTASK-092.json

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

- artifacts/bas/aggie_excess_components.json

## Acceptance criteria

1. A&M analyses use sealed expectations/peers, report effect/sample/sensitivity uncertainty, accept zero/negative/unstable excess, and make components unavailable when granular evidence is absent.
2. The declared output `artifacts/bas/aggie_excess_components.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
5. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_bas_science_governance.py — Run as a regression check after completing POST-SUBTASK-092; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-092; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_bas_science.py — Run as a regression check after completing POST-SUBTASK-092; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/bas/aggie_excess_components.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/bas/aggie_excess_components.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/bas/aggie_excess_components.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/bas/aggie_excess_components.json` can be parsed and consumed by `POST-SUBTASK-093` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
