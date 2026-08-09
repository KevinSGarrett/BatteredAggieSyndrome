# Local Windows Development Setup

Primary user environment remains Windows, Ryzen 7 HX-class CPU, 32 GB RAM, RTX 5060-class GPU and NVMe storage.

## Preferred interpreter
`.python-version` selects CPython 3.12 as the preferred local interpreter. `pyproject.toml` deliberately accepts Python 3.11–3.13 during the planning/starter period so repository tooling is not unnecessarily locked to one minor interpreter before model-library compatibility is evaluated.

## Bootstrap
From PowerShell:

`powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1`

This creates `.venv` and installs the current package scaffold. No model/data stack is installed in Wave 02 because its exact dependency set depends on later architecture and source decisions.

Portable baseline: normal Python `venv` + `pip`. Faster environment managers may be used locally, but the repository does not require one in Wave 02.

## Paths and large data
Use `pathlib` and project-relative paths in code. Raw/processed historical data and model artifacts belong outside the Git repository; `AGGIE_ANALYTICS_DATA_ROOT` is reserved for later local data-root configuration.
