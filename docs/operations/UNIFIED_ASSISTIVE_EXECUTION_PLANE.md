# Unified Assistive Execution Plane Operations

1. Build or refresh the ready-work inventory before routing.
2. Assign effort before provider selection and preserve the unit identity.
3. Require one route disposition and an exact readiness record.
4. Reserve provider-specific paid budget before any billable request.
5. Execute through the registered adapter only.
6. Preserve request, response/result, usage, validation, and disposition hashes outside Git.
7. Reconcile inventory, dispatch, usage, result, cleanup, Jira, and Git evidence.

Current capability checkpoint:

- Cursor authentication, repository catalog, and exact `gpt-5.3-codex` catalog presence are verified without exposing the token. The separate USD 200 cap and USD 20 initial stage authorize two serial safety pilots; zero qualifying real agents have executed.
- The exact evaluated `qwen2.5:7b-instruct` and `qwen3-vl:8b-instruct-q4_K_M` evidence-critical routes are rejected. New coder and embedding identities require separate shadow qualification.
- The controller laptop and expected Tailscale worker are online. The historical CPU prototype is disabled; the corrected private-HTTPS/signing/least-privilege route remains blocked pending deployment and live qualification.
- OpenRouter has a separate USD 25 cap and USD 5 initial stage for capability and bounded real-work pilots. It is authorized but has no qualifying paid real work yet. Direct OpenAI retains its independent governed budget and candidate-only operation.

Never copy `.env` into a worktree or worker packet. Never delete a dirty or unverified worktree. Stop local models and remove only reconstructible temporary artifacts after evidence preservation.

## Private CPU worker

The worker identity is `comfy-v4-cpu-01.tail9b05ab.ts.net` plus its verified Tailscale node ID, Windows hostname, OS/hardware profile, and verification timestamp. Never use a committed Tailscale IP as durable identity. The service binds `127.0.0.1:8765`; Tailscale Serve proxies the MagicDNS endpoint over private HTTPS; grants restrict the coordinator; Funnel stays off. The backend accepts only trusted Serve identity headers and a valid expiring HMAC envelope.

Run `tools/refresh_cpu_worker_readiness.py` before setup. On the exact peer, an administrator may run `tools/install_cpu_worker_service.ps1` from an immutable source checkout; use `-WhatIf` first. The installer verifies hostname/Tailscale self identity, transfers only the manifest-bound minimal worker plus the Sigstore-verified pinned CPython 3.11.9 64-bit embeddable runtime, rejects runtime hash/size/coverage/version/architecture mismatches, and never schedules a user-profile Python executable. It accepts a controller-generated 32-byte signing key through a one-time local input path, installs under restricted worker ACLs without displaying the key, deletes the transfer file, registers the service as `LOCAL SERVICE` with limited run level, disables Funnel, and configures persistent Serve HTTPS. It preserves a verified prior v2 install as a recovery root when `-Replace` is used. The service exposes only health and three fixed functions and accepts no arbitrary file path, URL, command, module, or shell payload.

Run `tools/qualify_cpu_worker.py` only after the private HTTPS heartbeat is valid and the controller-side signing key copy is available through the secure bootstrap channel. Operational readiness additionally requires three byte-identical replay tranches, deduplication, worker and controller restart recovery, interrupted-job recovery, unauthorized/corrupt/expired/invalid-signature rejection, resource admission, result-hash verification, and cleanup evidence. A reachable RDP port, online peer, or historical prototype success is not route readiness.

Current evidence is `BLOCKED_CORRECTED_ARCHITECTURE_REQUIRED` / `PARTIAL`. The prior three-tranche/dedup/restart mechanics result is preserved, but the direct-HTTP, source-IP-only, broad-package, SYSTEM-task prototype was disabled and does not qualify the corrected route. Continue historical acquisition, deterministic work, direct OpenAI, staged Cursor/OpenRouter pilots, and local shadow research while deployment is pending.
