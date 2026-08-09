# AI Work Packet — POST-SUBTASK-024

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Establish source API/schema/terms drift baselines and monitoring inputs

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-008: Production acquisition contracts, rate limits, fallbacks, and drift hooks.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-008 (Production acquisition contracts, rate limits, fallbacks, and drift hooks): Establish source API/schema/terms drift baselines and monitoring inputs. Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`. Produce `artifacts/source_governance/source_drift_baseline.json`, `configs/source_drift_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Establish source API/schema/terms drift baselines and monitoring inputs.
- Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`.
- Demonstrate with saved evidence: Baseline captures endpoint/version, schema hash, terms version, expected freshness, and upstream dependencies.
- Demonstrate with saved evidence: A changed contract cannot silently overwrite the prior baseline.
- Demonstrate with saved evidence: Detected drift produces a blocked/review state before downstream training.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_drift_baseline.json`.
- Produce, validate, content-hash, and register `configs/source_drift_registry.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications; Implement compliant retries, caching, rate-limit handling, and fallback activation.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `OPERATING`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-024_establish_source_api_schema_terms_drift_baselines_and_monitoring_inputs.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-024.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-024`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- src/aggie_analytics/data/adapters.py
- docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv
- docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Dependencies that must already be complete

- POST-SUBTASK-018
- POST-SUBTASK-021
- POST-SUBTASK-022
- POST-SUBTASK-023

## Files I may modify or create

- configs/source_drift_registry.json
- artifacts/source_governance/source_drift_baseline.json
- artifacts/jira_evidence/POST-SUBTASK-024.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- data-sources
- sources

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

- artifacts/source_governance/source_drift_baseline.json
- configs/source_drift_registry.json

## Acceptance criteria

1. Baseline captures endpoint/version, schema hash, terms version, expected freshness, and upstream dependencies.
2. A changed contract cannot silently overwrite the prior baseline.
3. Detected drift produces a blocked/review state before downstream training.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-024; retain command, exit code, and relevant output.
- LEGAL_RIGHTS_REVIEW / LEGAL_RIGHTS_REVIEW: MANUAL_REVIEW_REQUIRED — A named human reviewer records source-specific access, retention, training, publication, and redistribution decisions with terms/version/date evidence.
- MANUAL / MANUAL: artifacts/source_governance/source_drift_baseline.json — Verify reviewer identity, decision date, unresolved questions, and explicit allow/block conditions.
- SCIENTIFIC / SCIENTIFIC: artifacts/source_governance/source_drift_baseline.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/source_governance/source_drift_baseline.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: configs/source_drift_registry.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/source_drift_baseline.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `configs/source_drift_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Exercise the complete Production acquisition contracts, rate limits, fallbacks, and drift hooks path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-003, POST-EPIC-014, POST-STORY-036, POST-STORY-043, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-127, POST-SUBTASK-128, POST-SUBTASK-129.

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
