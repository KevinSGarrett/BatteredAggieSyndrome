# AI Work Packet — POST-SUBTASK-204

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Qualify the private Tailscale CPU worker for deterministic tranches and embedding or deduplication assistance

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Establish a private least-privilege deterministic service on exact Windows peer comfy-v4-cpu-01, then run three replayable tranches and one embedding/deduplication or small-model pilot.

### In scope

- Stable Tailscale node, MagicDNS, Windows hostname, OS/hardware, and controller identity verification without committed IP authority.
- A loopback-only fixed-function service exposed by private Tailscale Serve HTTPS, constrained by grants and HMAC-signed expiring envelopes.
- A minimal hash-manifested bundle under a restricted service identity with no arbitrary shell, URL, module, or path authority.
- Three byte-replayable tranches, exact deduplication, unauthorized/corrupt/expired/signature rejection, restart/interruption recovery, resource admission, provenance, and cleanup evidence.

### Out of scope

- Public Funnel exposure, arbitrary remote code execution, or credential capture.
- Canonical, PIT, label, protected-evaluation, model-promotion, forecast, publication, BAS, or Aggie Excess authority.
- Claiming route readiness before live exact-peer replay and restart evidence pass.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-204`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-204_qualify_the_private_tailscale_cpu_worker_for_deterministic_tranches_and_embedding_or_dedupli.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-204.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-204`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- configs/unified_assistive_policy.json
- governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md

## Dependencies that must already be complete

- None.

## Files I may modify or create

- artifacts/assistive/cpu_worker_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-204.json
- configs/cpu_worker_qualification.json
- configs/unified_assistive_policy.json
- configs/assistive_provider_registry.json
- src/aggie_analytics/assistive_plane/cpu_worker_backend.py
- tools/cpu_worker_service.py
- tools/install_cpu_worker_service.ps1
- tools/qualify_cpu_worker.py
- tools/refresh_cpu_worker_readiness.py
- tools/validate_cpu_worker_readiness.py
- tests/test_cpu_worker_backend.py
- docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- assistive-plane
- orchestration

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

- artifacts/assistive/cpu_worker_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-204.json

## Acceptance criteria

1. Peer identity, OS, storage, software lock, private binding/grants, heartbeat, timeouts, retry, idempotency, hashes, and cleanup pass before work.
2. Three deterministic tranches replay byte-identically where applicable and restart recovery succeeds.
3. No public Funnel exposure, credentials, canonical authority, or unverified remote mutation is introduced.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_cpu_worker_backend.py — Fixed task, identity, endpoint, authority, replay, and malformed-input gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-204.json — Three exact-peer tranches and one dedup pilot replay byte-identically after a service restart.
- REPRODUCIBILITY / REPRODUCIBILITY: artifacts/assistive/cpu_worker_readiness.json — Peer, controller, code, config, request, result, runtime, and cleanup identities are preserved.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-160.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Deploy only to the exact verified private Windows peer through the authorized Chrome bootstrap, verify Serve HTTPS/grants/HMAC/least-privilege identity, execute all fixed tasks and rejection cases, restart worker/controller, recover interruption, validate hashes/resources, and clean reconstructible temporary output.

## Stop instead of improvising when

- Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.
- Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.
- Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity.

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
