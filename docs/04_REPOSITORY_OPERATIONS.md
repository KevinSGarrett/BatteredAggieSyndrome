# Repository Operations — Wave 02

## Objective
Wave 02 turns the Wave 01 planning baseline into a reproducible local engineering repository without prematurely deciding the Wave 03 system/service architecture.

## Accepted operational tree
- `src/aggie_analytics/`: minimal installable package scaffold only.
- `tools/`: deterministic repository, prior-pack verification, validation and packaging tools.
- `scripts/`: Windows-first operator wrappers/bootstrap helpers.
- `configs/`: machine-readable repository and hydration policies.
- `.github/`: minimal CI/review structure.
- `.codex/`: worktree/task-packet operating contracts.
- `tests/`: executable tests for Wave 02 tooling and package scaffold.
- `docs/`, `governance/`, `provenance/`: cumulative canonical planning/evidence state.
- `data/`, `artifacts/`: documentation/placeholders only; large local state remains outside pack artifacts.

## Intentionally deferred
Wave 02 does not freeze future folders such as `players/`, `coaching/`, `models/`, `simulation/`, `api/`, `orchestration/` or database/service decomposition. Wave 03 must compare logical/system architecture alternatives first.

## One-command checks
Cross-platform Python:

`python tools/validate_repository.py --repo-root . --strict`

`python -m unittest discover -s tests -v`

Windows wrapper:

`powershell -ExecutionPolicy Bypass -File scripts/validate_repo.ps1`

## Generated evidence
`provenance/PROJECT_FILE_MANIFEST.csv`, `PROJECT_FILE_HASHES.sha256` and `CURRENT_TREE.txt` are generated from canonical files. Manifest/hash files exclude themselves to avoid recursive hashing.
