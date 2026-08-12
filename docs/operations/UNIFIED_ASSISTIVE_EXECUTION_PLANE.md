# Unified Assistive Execution Plane Operations

1. Build or refresh the ready-work inventory before routing.
2. Assign effort before provider selection and preserve the unit identity.
3. Require one route disposition and an exact readiness record.
4. Reserve provider-specific paid budget before any billable request.
5. Execute through the registered adapter only.
6. Preserve request, response/result, usage, validation, and disposition hashes outside Git.
7. Reconcile inventory, dispatch, usage, result, cleanup, Jira, and Git evidence.

Current capability checkpoint:

- Cursor authentication, repository catalog, and exact `gpt-5.3-codex` catalog presence are verified without exposing the token. Paid execution remains budget-blocked.
- Ollama `0.32.6` and installed Qwen models are present locally; no model was loaded during foundation inspection.
- The controller laptop and both expected Tailscale peers were online. The CPU worker still requires service-level identity, software, storage, access, replay, and recovery qualification before jobs are admitted.
- OpenRouter paid execution remains blocked at USD 0. Direct OpenAI retains its independent governed budget.

Never copy `.env` into a worktree or worker packet. Never delete a dirty or unverified worktree. Stop local models and remove only reconstructible temporary artifacts after evidence preservation.

## Private CPU worker

The worker is admitted only at `comfy-v4-cpu-01.tail9b05ab.ts.net` / `100.77.151.3` with Windows identity evidence. The controller is `kevin.tail9b05ab.ts.net` / `100.79.129.63`. The service uses direct HTTP inside Tailscale's encrypted network, binds only `100.77.151.3:8765`, and the Windows firewall admits only the controller address. Do not bind wildcard or loopback-plus-public-proxy interfaces and never enable Funnel.

Run `tools/refresh_cpu_worker_readiness.py` before setup. On the exact peer, an administrator may run `tools/install_cpu_worker_service.ps1` from an immutable source checkout; use `-WhatIf` first and `-Replace` only for the exact project task and firewall rule. The service exposes only health and three fixed functions: canonical JSON, line hashing, and exact normalized-text deduplication. It accepts no arbitrary file path, URL, command, module, or shell payload.

Run `tools/qualify_cpu_worker.py` only after the service heartbeat is valid. Operational readiness additionally requires three byte-identical replay tranches, the deduplication pilot, an independently captured service-restart recovery result, worker-side storage/software identity, and cleanup evidence. A reachable RDP port or online Tailscale peer is not route readiness.

Current evidence is `BLOCKED_REMOTE_SETUP_OR_SERVICE_REQUIRED`: the exact Windows peer is online and RDP is reachable, but SSH/WinRM are closed, current-identity DCOM/CIM authentication failed, no saved RDP credential target exists, and port 8765 is not listening. Continue deterministic and direct-OpenAI work while this route remains unavailable.
