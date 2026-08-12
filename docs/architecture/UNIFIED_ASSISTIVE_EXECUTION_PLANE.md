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

Readiness is a five-part identity: provider, exact resolved model, task format, schema hash, and policy version. Budget authorization is an independent gate. This prevents a credential, model alias, successful probe, or another provider's budget from being treated as operational admission.

Storage is external and content-addressed under `C:\BatteredAggieSyndrome.data\assistive`. The forecast path has no dependency on this plane.
