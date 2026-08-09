# Contributing / Codex Mutation Contract

The repository is wave-governed. Before changing files, read `AGENTS.md`, `governance/NEXT_WAVE.md`, relevant requirements and ADRs, and inspect the actual files you intend to modify.

## Core rules
- Preserve point-in-time correctness, provenance and protected governance.
- Do not invent model performance or source payloads.
- Do not commit `.env`, credentials, raw data lakes, large model files, virtual environments or caches.
- Use a focused branch/worktree for isolated tasks. Default branch pattern: `codex/<epic>-<task>`.
- Run `python tools/validate_repository.py --repo-root . --strict` before proposing a merge.
- Shared contracts should not be modified concurrently from multiple worktrees unless ownership is explicit.

Wave 02 establishes repository operations only. Domain/service boundaries remain intentionally revisable in Wave 03.
