# AI Work Packet — POST-STORY-051

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Decide whether live scope should ever activate without weakening the pregame product.

## Why?

This coherent capability closes a defined portion of Deferred live and in-game modeling and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-051 (Live need, source, rights, latency, cost, and value gate) as one coherent, gated capability inside Epic POST-EPIC-017. Execute child subtasks POST-SUBTASK-151, POST-SUBTASK-152, POST-SUBTASK-153 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-153` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-151` — Research licensed live play/state/market feeds, authentication, terms, history, replayability, latency, reliability, cost, retention, and redistribution.
- Complete and verify child `POST-SUBTASK-152` — Define exact live use cases, incremental value versus pregame, latency/reliability/resource/failure targets, isolation, and no-build criteria.
- Complete and verify child `POST-SUBTASK-153` — Apply the separate live-scope admission gate without creating Wave 26.
- Integrate the child outputs and execute final gate `POST-SUBTASK-153`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `DEFERRED`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `DEFERRED` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-159`

## Read first

1. `jira/records/issues/stories/POST-STORY-051_live_need_source_rights_latency_cost_and_value_gate.json`
2. `jira/sources/issue_source_manifests/POST-STORY-051.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-051`.
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

- POST-SUBTASK-141

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-051.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

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

Review and integrate these child-produced outputs; do not recreate them directly from this aggregate packet:

- artifacts/live/live_source_research.json
- artifacts/live/live_value_feasibility.json
- artifacts/live/live_admission_decision.json

## Acceptance criteria

1. Research does not bypass CAPTCHA/authentication/rate limits/access controls, assumes no public-equals-redistributable rights, and records unavailable/unaffordable sources as blockers.
2. The declared output `artifacts/live/live_source_research.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Use cases distinguish in-game from pregame updates, targets are evidence-backed, pregame operation remains isolated, and no-build is valid when rights/history/cost/value/resources are inadequate.
5. The declared output `artifacts/live/live_value_feasibility.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. TASK-169–172 remain deferred unless user/governance explicitly admits the separate scope; no Wave 26 exists and deferred live work is not unfinished core v1.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- END_TO_END / END_TO_END: POST-SUBTASK-153 — The final child gate `POST-SUBTASK-153` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-151, POST-SUBTASK-152, POST-SUBTASK-153.
- Final gate decision from `POST-SUBTASK-153` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

Live work remains deferred unless licensed replayable evidence and clear value justify a separate isolated program.

## Stop instead of improvising when

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.
