# Unified Assistive Execution Plane Architecture

## Durable execution-enforcement layer

The operational architecture is now explicitly two-process and evidence-derived:

1. An OS-supervised provider-neutral controller is the sole admitted dispatcher. It owns a SQLite WAL state database, process and database leader leases, immutable work identities and effort, transactional state transitions, provider/local-resource admission, reservations and settlement, retry/dead-letter recovery, scheduler cycles, reconciliation, and cleanup.
2. An independently OS-supervised read-only watchdog opens the state database read-only, checks the controller and live systems directly, derives the maximum justified state, and reports disagreement. It cannot dispatch or mutate controller, Jira, Git, canonical, or protected state.

The initial versioned state implementation is `src/aggie_analytics/assistive_plane/controller_state.py`; the independent inspection implementation is `src/aggie_analytics/assistive_plane/watchdog.py`. These implementations are foundation code, not deployment or operational-completion evidence. The service identities, cold-boot behavior, forced-crash recovery, provider campaigns, and seven-day soak remain required external evidence.

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
