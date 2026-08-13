# Unified Assistive Execution Plane Architecture

## Durable execution-enforcement layer

The operational architecture is now explicitly two-process and evidence-derived:

1. An OS-supervised provider-neutral controller is the sole admitted dispatcher. It owns a SQLite WAL state database, process and database leader leases, immutable work identities and effort, transactional state transitions, provider/local-resource admission, reservations and settlement, retry/dead-letter recovery, scheduler cycles, reconciliation, and cleanup.
2. An independently OS-supervised read-only watchdog opens the state database read-only, checks the controller and live systems directly, derives the maximum justified state, and reports disagreement. It cannot dispatch or mutate controller, Jira, Git, canonical, or protected state.

The versioned state implementation is `src/aggie_analytics/assistive_plane/controller_state.py`; runtime discovery and immutable pointer refresh are in `src/aggie_analytics/assistive_plane/inventory_runtime.py`; the fail-closed dispatcher is `src/aggie_analytics/assistive_plane/scheduler_runtime.py`; and the independent inspection implementation is `src/aggie_analytics/assistive_plane/watchdog.py`. The controller refreshes a small current pointer while retaining immutable material snapshots, discovers only allowlisted bounded external BAS manifest packets, and binds every packet to content, Jira, schema, authority, effort, and exact worker-route identities. The scheduler verifies pointer freshness, snapshot hash, validation identity, coverage, authority, and Git binding before work can move through `DISCOVERED -> ELIGIBLE -> LEASED -> ADMITTED -> DISPATCHED -> RESULT_RECEIVED -> VALIDATED -> REVIEWED -> SETTLED -> CLEANED -> CLOSED`. A cycle with zero dispatch never establishes operational scheduling. Cold-boot behavior, broader provider adapters, provider campaigns, and the seven-day soak remain required external evidence.

All 204 operational acceptance contracts and their single primary Jira owners are versioned in `configs/unified_assistive_acceptance_ownership.json`. `tools/validate_unified_assistive_completeness.py` emits all rows and exits nonzero until the full applicable evidence population is `PASS`.

```text
canonical ready-work inventory
  -> immutable effort + exactly one disposition
  -> exact route-readiness key
  -> provider-specific budget/security admission
  -> one adapter (Codex/OpenAI/OpenRouter/Cursor/Ollama/CPU worker)
  -> candidate or deterministic result
  -> schema/evidence/scope/PIT/test validation
  -> Codex disposition
  -> reconciled utilization/provenance/cleanup
```

The existing direct-OpenAI and OpenRouter components are preserved behind adapters. `aggie_analytics.assistive_plane.orchestration` owns provider-neutral inventory, readiness, policy, and evidence identities. Provider modules own only their wire/runtime-specific validation and payload construction. No adapter owns canonical, protected, Git/GitHub, Jira, or scientific authority.

Readiness is keyed by provider, exact resolved model and digest, task format, prompt version, schema version/hash, policy version, and execution surface. Budget authorization is an independent gate. This prevents a credential, model alias, successful probe, human-edited status, or another provider's budget from being treated as operational admission.

Storage is external and content-addressed under `C:\BatteredAggieSyndrome.data\assistive`. The forecast path has no dependency on this plane.

The private CPU adapter is deliberately fixed-function rather than a remote shell. A request identity binds contract version, Jira unit, task, and complete payload. The worker recomputes that identity, permits only `CANONICAL_JSON`, `LINE_HASH_MANIFEST`, or `EXACT_TEXT_DEDUP`, emits a deterministic result hash, and records a content-addressed request/result pair. The controller validates the same deterministic result before accepting the artifact. Both sides record zero canonical writes and zero protected decisions.

The original direct-HTTP/source-IP prototype is retired. The corrected worker binds only `127.0.0.1`, and Tailscale Serve exposes the MagicDNS endpoint through private HTTPS. Tailnet grants restrict the verified coordinator, Funnel remains disabled, and the loopback application requires a trusted Serve identity header plus an HMAC-signed content-addressed envelope with issue/job identity, issued/expiry times, nonce, payload hash, policy/schema identity, fixed task, and signature. A replay with the same envelope is idempotent; a nonce reused with changed content fails closed.

Durable worker identity uses Tailscale node identity, MagicDNS, Windows hostname, OS/hardware profile, and verification time; resolved IP addresses are deployment evidence only. Installation uses a minimal hash-manifested bundle and low-privilege service identity. The route remains `BLOCKED / PARTIAL` until unauthorized, corrupt, expired, signature, replay, disk, hash, restart, interrupted-job, and cleanup gates pass live.

## Revision and semantic-evidence boundary

Controller schema v4 preserves a logical unit's immutable observed revisions separately from its current pre-dispatch pointer. A revision can be superseded only while the unit remains `DISCOVERED`, has no consequential transition, no route identity, and no reservation. The prior revision, inventory observations, supersession timestamp, successor hash, same-state audit transition, and closed idle interval remain durable. Any later mutation is `IMMUTABLE_ACTIVE_WORK_UNIT_IDENTITY_CONFLICT` and produces a blocked scheduler artifact without a provider call. Separate durable tables now bind dependencies, work leases, dispatch attempts, provider runs, retry admission, route-readiness observations, artifacts, validation, review disposition, cleanup, incidents, and Jira/result reconciliation.

Inventory generation reads provider evidence semantically. Exact local-model readiness must be supported by its content-addressed qualification artifact. CPU-worker readiness requires the exact corrected-v2 PASS, zero canonical/protected authority, unrecorded signing key, and three byte-identical fixed-function tranches. Cursor summaries bind unique job/agent identities, review dispositions, settlement, and dispatch origin; transitional CLI work never becomes controller-routed by inference.

The first admitted dispatcher is deliberately narrow: it performs exact CPU-worker canonicalization/provenance QA for the real acquisition and normalization `run.json`/`progress.json` spine. It persists the signed request before submission, independently recomputes every deterministic result, records a `REVIEW_ONLY` candidate disposition, settles zero paid cost, records cleanup and Jira/result reconciliation, and closes or bounded-retries the lease. This proves only that exact route. It does not qualify another format/provider, grant canonical authority, complete the CPU campaign, prove cold-start recovery, or establish sustained operation.
