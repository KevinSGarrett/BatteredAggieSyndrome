# AI Work Packet — POST-SUBTASK-156

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-052: Isolated event state, features, models, replay, and latency prototype.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-052 (Isolated event state, features, models, replay, and latency prototype): Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation. Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`, `POST-SUBTASK-155`. Produce `artifacts/live/live_prototype_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`, `POST-SUBTASK-155`.
- Demonstrate with saved evidence: Every event retains provider sequence, published/received time, canonical game/entity identity, correction lineage, and prior evidence; out-of-order/duplicates/corrections reconstruct deterministically.
- Demonstrate with saved evidence: Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.
- Demonstrate with saved evidence: Replay under duplicate/delayed/corrected/missing events passes, prototype cannot corrupt/degrade pregame operation, and prototype completion does not imply production admission.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/live/live_prototype_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Build immutable event-stream snapshots and event-time as-of game-state reconstruction handling duplicates, delay, correction, and sequence; Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Treating deferred live/in-game work as admitted production scope or describing it as Wave 26.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `DEFERRED`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DEFERRED` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-159`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-156_validate_event_time_integrity_replay_determinism_latency_failure_behavior_and_pr.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-156.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-156`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/OPEN_ISSUES.md

## Dependencies that must already be complete

- POST-SUBTASK-153
- POST-SUBTASK-154
- POST-SUBTASK-155

## Files I may modify or create

- artifacts/live/live_prototype_gate.json
- artifacts/jira_evidence/POST-SUBTASK-156.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- live-modeling
- live

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

- artifacts/live/live_prototype_gate.json

## Acceptance criteria

1. Every event retains provider sequence, published/received time, canonical game/entity identity, correction lineage, and prior evidence; out-of-order/duplicates/corrections reconstruct deterministically.
2. Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.
3. Replay under duplicate/delayed/corrected/missing events passes, prototype cannot corrupt/degrade pregame operation, and prototype completion does not imply production admission.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- BENCHMARK / BENCHMARK: artifacts/live/live_prototype_gate.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/live/live_prototype_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/live/live_prototype_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/live/live_prototype_gate.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/live/live_prototype_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/live/live_prototype_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

An admitted prototype reconstructs and predicts from licensed historical event streams deterministically while remaining isolated from pregame state. The gate decision must explicitly reevaluate downstream issues: POST-STORY-053, POST-SUBTASK-157, POST-SUBTASK-158, POST-SUBTASK-159.

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
