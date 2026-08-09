# Local Runtime Path Contract

`AGGIE_ANALYTICS_DATA_ROOT` is the single configuration input for local bulk data and operational artifacts. It must be a concrete absolute path that is disjoint from the Git repository. The configured value belongs in the host or an ignored local launcher environment; never commit it.

## Required roots

The resolver in `aggie_analytics.operations.environment` derives seven distinct roots from the configured data root:

| Alias | Relative location | Intended content |
| --- | --- | --- |
| `raw` | `raw` | Immutable source snapshots; source rights still apply. |
| `curated` | `canonical` | Canonicalized/curated records. |
| `model` | `model_artifacts` | Versioned model artifacts. |
| `forecast` | `forecast_snapshots` | Immutable published forecast snapshots. |
| `log` | `runtime/logs` | Local operational logs. |
| `backup` | `runtime/backups` | Local backup artifacts. |
| `quarantine` | `quarantine` | Rejected or held inputs. |

`EXTERNAL_DATA_ROOT` is the documentation alias for the configured absolute root; it is not a literal directory name. No absolute user path or environment value is required in repository evidence.

## Runtime use

The process launcher must provide `AGGIE_ANALYTICS_DATA_ROOT` on every start. A host-level environment variable or ignored local launcher file is acceptable. The resolver fails closed when the value is absent, relative, placeholder-like, equal to the repository, nested inside it, or a parent containing it.

```python
from pathlib import Path
from aggie_analytics.operations.environment import provision_local_runtime_paths

paths = provision_local_runtime_paths(repo_root=Path.cwd())
raw_root = paths["roots"]["raw"]
```

Provisioning creates only the declared directories and performs a small create/write/delete probe in each. It does not authorize source access, assert redistribution rights, validate storage durability, test quarantine semantics, or claim production/release readiness. Those remain downstream gates.

## Evidence and consumer contract

The machine-readable contract is `artifacts/implementation_preflight/local_path_contract.json`. `POST-SUBTASK-005` must verify its schema, canonical content hash, prerequisite identities, seven distinct aliases, path-safety rejection result, restart match, and retained rights/release blockers. Missing, stale, malformed, hash-mismatched, repository-overlapping, or rights-incomplete input must fail closed without manual reconstruction.

The current evidence proves configuration and path safety only. It contains no bulk source data, credential values, user-identifying paths, model metrics, protected results, source-rights approval, or claim that AC-038/THR-011/THR-012 are resolved.
