# Unified Assistive Execution Plane Architecture

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
