# Technology stack

The package uses Python 3.11–3.13 and setuptools. Its core dependency list is empty; larger libraries are installed through optional extras. This inventory follows [pyproject.toml](../../pyproject.toml), not a claim that every library is active in a validated model.

## Data and source tooling

| Extra | Declared libraries | Intended role |
|---|---|---|
| `data` | Polars, DuckDB, Pandera | Data frames, analytical queries, validation |
| `entity-resolution` | RapidFuzz, Splink | Matching research; authoritative IDs and abstention remain necessary |
| `source-clients` | cfbd, openmeteo-requests | CollegeFootballData and weather clients |
| `sportsdataverse` | sportsdataverse, XGBoost, scikit-learn, Polars, RapidFuzz | Optional sports-data ecosystem integration |

Source-specific tools also handle official football records and weather evidence. Access, quotas, redistribution rights, and historical coverage depend on the provider. Installing a client does not supply credentials or a data lake.

## Modeling and evaluation

| Extra | Declared libraries | Intended role |
|---|---|---|
| `modeling` | scikit-learn, statsmodels, XGBoost, NGBoost, Interpret | Baselines, statistical models, and optional challengers |
| `evaluation` | MAPIE, scoringrules, SHAP | Interval/calibration research, proper scores, explanation tools |
| `experimentation` | mlflow-skinny, Optuna | Experiment recording and explicitly authorized search |

The repository also contains Elo and regularized-model experiments plus independent numerical reference modules. Dependency availability does not imply adoption, empirical superiority, or permission to tune against an evaluation cohort.

## API, interface, and testing

- `product`: FastAPI and Uvicorn serve existing immutable JSON snapshots.
- Dashboard: HTML, CSS, and JavaScript; no frontend build framework is required by the current adapter.
- Data formats: JSON/JSONL, CSV, and Parquet-oriented analytical workflows; bulk payloads live outside Git.
- Testing: standard-library unittest; `test` installs optional Hypothesis.
- Repository checks: Ruff, GitHub Actions, security analysis, and coverage/review tooling.

## Install only what you need

```bash
# Core research modules
python -m pip install -e .

# Read-only API/dashboard
python -m pip install -e ".[product]"

# Optional data and statistical tooling
python -m pip install -e ".[data,entity-resolution,source-clients,modeling,evaluation]"

# Optional property-based tests
python -m pip install -e ".[test]"
```

Exact versions are pinned in the package metadata. Large combinations and provider-dependent workflows need their own environment validation; the commands do not promise that every optional combination was tested on every platform. Private development automation is not part of this scientific/product stack.
