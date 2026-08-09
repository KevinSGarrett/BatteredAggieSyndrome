# AI Work Packet — POST-SUBTASK-140

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-047: Documentation, independent handoff, go-live review, and operating authorization.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-047 (Documentation, independent handoff, go-live review, and operating authorization): Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest. Consume only verified prerequisite outputs from `POST-SUBTASK-138`, `POST-SUBTASK-139`. Produce `docs/final/PRODUCTION_SYSTEM_CARD.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-141.

### In scope

- Perform the exact action: Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest.
- Consume only verified prerequisite outputs from `POST-SUBTASK-138`, `POST-SUBTASK-139`.
- Demonstrate with saved evidence: Documentation reports actual coverage/metrics/calibration/uncertainty/OOD/A&M/BAS decisions/limitations/nulls and links every claim to immutable evidence with no unsupported SLA, causal, performance, or scientific claim.
- Demonstrate with saved evidence: The declared output `docs/final/PRODUCTION_SYSTEM_CARD.md` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `docs/final/PRODUCTION_SYSTEM_CARD.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides; Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SCIENTIFIC`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DESIGN_ONLY` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-141`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-140_finalize_production_system_data_model_a_and_m_bas_cards_limitations_protected_re.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-140.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-140`.
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

## Dependencies that must already be complete

- POST-SUBTASK-138
- POST-SUBTASK-139

## Files I may modify or create

- docs/final/PRODUCTION_SYSTEM_CARD.md
- artifacts/jira_evidence/POST-SUBTASK-140.json

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

- docs/final/PRODUCTION_SYSTEM_CARD.md

## Acceptance criteria

1. Documentation reports actual coverage/metrics/calibration/uncertainty/OOD/A&M/BAS decisions/limitations/nulls and links every claim to immutable evidence with no unsupported SLA, causal, performance, or scientific claim.
2. The declared output `docs/final/PRODUCTION_SYSTEM_CARD.md` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-140; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w25_final_handoff.py — Run as a regression check after completing POST-SUBTASK-140; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-140; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: docs/final/PRODUCTION_SYSTEM_CARD.md — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: docs/final/PRODUCTION_SYSTEM_CARD.md — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- OPERATIONS / OPERATIONS: docs/final/PRODUCTION_SYSTEM_CARD.md — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- STATIC_VALIDATION / STATIC_VALIDATION: docs/final/PRODUCTION_SYSTEM_CARD.md — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `docs/final/PRODUCTION_SYSTEM_CARD.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `docs/final/PRODUCTION_SYSTEM_CARD.md` can be parsed and consumed by `POST-SUBTASK-141` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
