# AI Work Packet — POST-SUBTASK-052

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Reconcile feature IDs, source fields, transformations, temporal classes, missingness, code paths, aliases, duplicates, and lifecycle states

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-018: Population feature registry and computability.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-018 (Population feature registry and computability): Reconcile feature IDs, source fields, transformations, temporal classes, missingness, code paths, aliases, duplicates, and lifecycle states. Consume only verified prerequisite outputs from `POST-SUBTASK-048`. Produce `artifacts/features/production_feature_inventory.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-053.

### In scope

- Perform the exact action: Reconcile feature IDs, source fields, transformations, temporal classes, missingness, code paths, aliases, duplicates, and lifecycle states.
- Consume only verified prerequisite outputs from `POST-SUBTASK-048`.
- Demonstrate with saved evidence: Every feature maps to source, transformation, temporal class, owner, tests, lineage, and CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED state; design presence is not promotion evidence.
- Demonstrate with saved evidence: The declared output `artifacts/features/production_feature_inventory.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/features/production_feature_inventory.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Measure feature computability, missingness class, fallback use, and coverage by season/team/cutoff/regime/A&M segment; Freeze the experiment-eligible production feature-registry version.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-060`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-052_reconcile_feature_ids_source_fields_transformations_temporal_classes_missingness.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-052.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-052`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/features/factory.py
- src/aggie_analytics/features/lifecycle.py
- src/aggie_analytics/features/screening.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md

## Dependencies that must already be complete

- POST-SUBTASK-048

## Files I may modify or create

- artifacts/features/production_feature_inventory.csv
- artifacts/jira_evidence/POST-SUBTASK-052.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- feature-engineering
- features

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

- artifacts/features/production_feature_inventory.csv

## Acceptance criteria

1. Every feature maps to source, transformation, temporal class, owner, tests, lineage, and CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED state; design presence is not promotion evidence.
2. The declared output `artifacts/features/production_feature_inventory.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_registry_governance.py — Run as a regression check after completing POST-SUBTASK-052; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_lifecycle_governance.py — Run as a regression check after completing POST-SUBTASK-052; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_tournament_full.py — Run as a regression check after completing POST-SUBTASK-052; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/features/production_feature_inventory.csv — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/features/production_feature_inventory.csv — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/features/production_feature_inventory.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/features/production_feature_inventory.csv` can be parsed and consumed by `POST-SUBTASK-053` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
