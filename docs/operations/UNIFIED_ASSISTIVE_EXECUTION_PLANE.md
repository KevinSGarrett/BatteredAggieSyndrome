# Unified Assistive Execution Plane Operations

## Enforced operating state

The current overall state is `INCOMPLETE`. Do not substitute foundation code, credentials, catalog checks, smoke tests, merged PRs, or Jira status for runtime completion.

Runtime state belongs under `C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3`, including `state\orchestrator.sqlite3`, snapshots, leases, usage, results, review, reconciliation, logs, watchdog reports, backups, runtime, and temporary output. Git contains only small policies, contracts, code, tests, schemas, and documentation.

Before service deployment:

- validate all 204 ownership rows with `python -B tools/validate_unified_acceptance_ownership.py`;
- initialize a disposable state database and run controller state/property tests;
- verify the controller and watchdog use separate OS-supervised identities and the watchdog has no write authority;
- bind service configuration to the exact current-main build commit and external runtime root;
- preserve backup/restore, forced-crash, cold-boot, drain, emergency-stop, rollback, and cleanup evidence.

## Controller service release and installation

The controller and watchdog are separate long-lived processes. The controller holds both an OS process lock and a renewable SQLite leader lease for its full lifetime. It writes a content-addressed heartbeat every 30 seconds and observes the queue every 60 seconds, but the current service-shell unit records zero real scheduler cycles and performs no provider dispatch. The watchdog uses its own process lock, opens SQLite read-only, and writes independent content-addressed reports even when the controller is stopped.

After the implementation commit is merged and exact-main validation passes, build the immutable minimal release from a clean exact-main worktree:

```powershell
python -B tools/build_unified_assistive_release.py --expected-commit <exact-main-sha>
```

The release contains only the controller/watchdog entry points and their required standard-library modules under `C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3\releases\<commit>`. Every file and the source tree are SHA-256 bound in `RELEASE_MANIFEST.json`. Rebuilding an existing commit verifies it rather than overwriting it.

Run the installer in read-only preview first, then register the two distinct limited tasks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/install_unified_assistive_services.ps1 -ReleaseRoot <release> -WhatIf
powershell -NoProfile -ExecutionPolicy Bypass -File tools/install_unified_assistive_services.ps1 -ReleaseRoot <release>
```

The installer refuses SYSTEM, verifies every release hash, exports any replaced task definition, and uses a limited current-user interactive token. This proves OS supervision while that user is logged on; cold boot before user logon remains explicitly unproven and blocks the corresponding acceptance row until a separately reviewed bounded service identity is deployed. A controller heartbeat or watchdog health result does not establish operational completion, campaign completion, or soak progress.

Provider campaign accounting uses distinct base units and frozen effort, not raw calls. Retries, health checks, catalog requests, smoke tests, duplicate submissions, and self-correction follow-ups never count as accepted work. Material Jira transitions synchronize within 15 minutes or create an explicit queued finding. The seven-day clock starts only after qualified routes process real production-like work through the deployed controller.

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

Run `tools/refresh_cpu_worker_readiness.py` before setup. On the exact peer, an administrator may run `tools/install_cpu_worker_service.ps1` from an immutable source checkout; use `-WhatIf` first. The installer verifies hostname/Tailscale self identity, transfers only the manifest-bound minimal worker plus the Sigstore-verified pinned CPython 3.11.9 64-bit embeddable runtime, rejects runtime hash/size/coverage/version/architecture mismatches, and never schedules a user-profile Python executable. It accepts a controller-generated 32-byte signing key through a one-time local input path, installs under restricted worker ACLs without displaying the key, deletes the transfer file, registers the service as `LOCAL SERVICE` with limited run level, disables Funnel, and configures persistent Serve HTTPS. With `-Replace`, it stops the verified existing task before atomically preserving the prior v2 install as a recovery root. At startup, the service removes only digest-bound stale leases and scratch from interrupted work and emits immutable recovery evidence before accepting new work. The service exposes only health and three fixed functions and accepts no arbitrary file path, URL, command, module, or shell payload.

Run `tools/qualify_cpu_worker.py` only after the private HTTPS heartbeat is valid and the controller-side signing key copy is available through the secure bootstrap channel. Operational readiness additionally requires three byte-identical replay tranches, deduplication, worker and controller restart recovery, interrupted-job recovery, unauthorized/corrupt/expired/invalid-signature rejection, resource admission, result-hash verification, and cleanup evidence. A reachable RDP port, online peer, or historical prototype success is not route readiness.

Current evidence is `BLOCKED_CORRECTED_ARCHITECTURE_REQUIRED` / `PARTIAL`. The prior three-tranche/dedup/restart mechanics result is preserved, but the direct-HTTP, source-IP-only, broad-package, SYSTEM-task prototype was disabled and does not qualify the corrected route. Continue historical acquisition, deterministic work, direct OpenAI, staged Cursor/OpenRouter pilots, and local shadow research while deployment is pending.
