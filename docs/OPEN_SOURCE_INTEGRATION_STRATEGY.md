# Open-Source Repository Corpus Review and Integration Strategy

Status: implementation-active

Review registry: `configs/open_source_integration_registry.json`
Complete decision matrix: `artifacts/open_source/repository_review_decisions.csv`

## Scope and method

This review covers every repository heading in the owner-supplied `repohelp_001.txt` and `repohelp_002.txt`, every explicitly named alternative in those documents, the explicitly discouraged infrastructure stack, the graph-model reference implied by the named PyTorch/GNN stack, and the Chroma architecture used by AggieFYI. The resulting corpus contains 42 upstream repositories; all 42 were reachable and none was omitted.

Each repository was pinned to an exact default-branch commit and inspected through its README, license metadata/file where present, dependency manifests, repository tree, representative source, representative tests, and relevant docs. Package candidates were independently resolved against the project's actual Python 3.11.9 Windows runtime. The immediate core and isolated SportsDataverse environments were installed, import-smoked, and vulnerability-audited outside Git.

Evidence indexes outside Git:

- Upstream metadata: SHA-256 `03b10e0882d59444bad93f45b86b5cbe44bf8dfcfaec4d4a33ce583617d1d901`
- Repository tree summaries: SHA-256 `224702c057d921a87a5ae4a441bceadb34fdcb80e0ac81337211ce33f9ef22b7` (42/42 reachable, zero truncated)
- Representative source/test/docs/license captures: SHA-256 `f5d29572e24035fe3cf2f73714e31e4d8cbf4150ddf03644ef5d999e176f5128` (288 pinned files across 42/42 repositories)
- PyPI package evidence: SHA-256 `a73821f941b3a71434e370f558e77d76a531bb0533f706b451eaa397a747d30e`
- Remediated core dependency audit: SHA-256 `e280b12f6d02ae8868a9a3c6fbd5c8e0966b949769c10424db4c8c49d8c9e76d` (`0` known vulnerabilities)
- Isolated SportsDataverse dependency audit: SHA-256 `d5206eacd4669c14a0eb0d22b95f7de0bc5e0e3dd7a11aea1fd3b73320191438` (`0` known vulnerabilities)
- Real SportsDataverse acquisition smoke: SHA-256 `c8716e408700596136053a52342a128c693d5f19d1a920128d4dec34c6f73a12`
- Combined core integration smoke: SHA-256 `b0a4a6fd466be898f724faa14dd0e0694e84eb8c49f86253169af2fedc6fdbb9`

The full per-repository rationale, pinned identity, dependency surface, inspected paths, PIT/provenance risk, empirical admission gate, and implementation action are in the registry and CSV rather than being compressed into undocumented narrative judgment.

## Decisions

The 42 dispositions are:

- 7 `ADOPT_NOW`
- 4 `ADAPT_NOW`
- 8 `ADOPT_AT_DEPENDENCY`
- 2 `ADAPT_AT_DEPENDENCY`
- 6 `DEFER_CONDITIONAL`
- 4 `REFERENCE_ONLY`
- 11 `REJECT_NOT_FIT`

### Implement now

| Component | Decision | Integration |
|---|---|---|
| SportsDataverse Python | Adapt now | Run in a separately pinned acquisition environment; translate outputs through `SourceAdapter` and `RawSnapshotStore`; never make its schema canonical. |
| cfbfastR CFB data | Adopt now | Retain as the bulk historical bootstrap with release hashes, domain/season coverage, upstream lineage, schema drift, and PIT eligibility measured independently. |
| SportsDataverse data release store | Adapt now | Use as a release catalog and asset resolver, not a completeness or canonical-schema authority. |
| CFBD Python client | Adapt now | Optional typed endpoint client; preserve direct HTTP JSON as immutable raw evidence and prevent bearer credentials from entering artifacts. |
| DuckDB | Adopt now | Read-only analytical SQL over external Parquet/JSON for joins, coverage and PIT assembly. |
| Polars | Adopt now | Default lazy transformation/dataframe engine behind project interfaces. |
| Pandera | Adopt now | Executable Polars/pandas contracts at raw/canonical/PIT/training boundaries. |
| RapidFuzz | Adopt now | Candidate generation only; its score can never auto-promote a canonical identity. |
| Splink | Adapt now | Multi-field probabilistic player/coach linkage only after deterministic and RapidFuzz candidate generation; labeled thresholds and quarantine remain mandatory. |
| Hypothesis | Adopt now | Deterministic property tests for PIT, canonical identity, alias normalization, probability coherence, season boundaries, and malformed data. |
| Open-Meteo Python client | Adopt now | Efficient decoder/client after immutable HTTP capture; archive/reanalysis data remains realized-weather evidence, not a historical pregame forecast. |

### Admit when their existing dependency gates open

| Component | Intended role | Required gate |
|---|---|---|
| scikit-learn | Logistic/calibration/pipeline baselines | Approved chronological model matrices and sealed evaluation wiring. |
| statsmodels | GLM, Poisson, generalized Poisson and negative-binomial baselines | Convergence, dispersion and chronological residual diagnostics. |
| XGBoost | First tree challenger | Development lift, calibration, stability and resource value over simple baselines. Pin `3.2.0` on Python 3.11, not current `3.4.0`. |
| MLflow | Local experiment-search mirror | Use `mlflow-skinny`; canonical experiment manifests and promotion authority remain in Aggie Analytics. |
| Optuna | Bounded development-only HPO | No protected objective access; reproducible chronological studies. |
| SHAP | Offline tree explanations | Admit only after a tree model; pin `0.51.0` on Python 3.11 and make no causal claim. |
| MAPIE | Conformal uncertainty challenger | Exchangeability diagnostics, rolling calibration and regime-specific coverage. |
| scoringrules | Brier/log/CRPS/energy/tail scoring | Pin `0.10.0` on Python 3.11 and verify orientation/weighting against reference calculations. |
| NGBoost | Distributional challenger | Beat point-model-plus-calibration baselines on chronological NLL/CRPS/calibration. |
| InterpretML | EBM glass-box challenger | Earn lift and explanation stability relative to GLM and XGBoost. |

### Reference without importing runtime code

- `sportsdataverse/cfbfastR`: pinned CFB play taxonomy and EPA/WPA parity reference.
- `nflverse/nflfastR`: data-release, incremental enrichment, EP/WP and drive/series architecture reference; NFL semantics are not CFB truth.
- `sportsdataverse/cfb4th`: fourth-down feature hypotheses and parity fixtures; the experimental R model's assumptions and post-play inputs are not pregame features.
- `drewddudney/TAMU_KyleField`: A&M/Kyle Field, home-road, attendance, opponent-strength, penalty and turnover hypotheses only. Its notebook has no tests/license and uses outcome-era observations, so no reported conclusion is imported.

### Explicit negative and deferred findings

- AggieFYI is rejected. Its acquisition code only makes direct CFBD calls already covered more robustly here; it has no unique A&M data source, no tests/license, hard-coded years and facts, an obsolete OpenAI/Chroma stack, broad exception swallowing, and a UTC conversion defect.
- Feast, Airflow, Dagster, Prefect, Spark, Ray, Kubernetes, DVC, Great Expectations, and Chroma are rejected for the current architecture because they duplicate authoritative local systems or introduce a service/cluster/data-authority burden without a measured requirement.
- LightGBM and CatBoost remain conditional challengers after XGBoost proves that tree boosting is valuable.
- Evidently remains conditional until weekly operation exists; its 26 mandatory dependencies are not justified for pre-production validation.
- PyMC remains conditional on a demonstrated hierarchical pooling need; Python 3.11 would use `5.28.5`, not current `6.2.0`.
- PyTorch and PyTorch Geometric remain protected P3 candidates. They require a specific sequence/graph hypothesis, leakage-safe graph construction, conventional-baseline saturation, and protected lift/resource evidence.

## Runtime architecture

```text
isolated source-client environment
  SportsDataverse / CFBD / Open-Meteo decoder
                    |
                    v
credential-free AcquisitionRequest + immutable RawSnapshotStore
                    |
                    v
external raw/canonical Parquet and JSON
          |                         |
          v                         v
  DuckDB read-only SQL       Polars lazy transforms
          \                         /
           +---- Pandera contracts -+
                    |
                    v
deterministic canonical/PIT pipeline
                    |
          +---------+----------+
          |                    |
          v                    v
RapidFuzz candidates   Splink multi-field candidates
          |                    |
          +---- review/quarantine ----> canonical promotion
```

Open-source components remain replaceable engines. They cannot change canonical IDs, raw snapshot identity, PIT state, W17 judging, protected splits, promotion authority, A&M/BAS definitions, or publication controls.

## Verified host compatibility

The immediate stack installed together on Python 3.11.9 and passed import and vulnerability audits. A real-data smoke then proved:

- SportsDataverse returned 76 schedule rows for `2024-09-07`, a raw summary for game `401628455`, and 230 roster rows.
- Polars and DuckDB independently agreed on 76 unique games.
- Pandera accepted the pinned schema and season checks.
- RapidFuzz generated the intended A&M alias candidate without canonical promotion.
- Splink compiled a DuckDB-backed multi-field player-linkage configuration.
- CFBD configured its typed client without exposing a real credential.
- Open-Meteo returned one realized-weather response explicitly marked ineligible as pregame forecast evidence.
- Hypothesis executed 250 deterministic alias-normalization cases.

The SportsDataverse environment occupies approximately 1.01 GB versus approximately 486 MB for the lean core candidate environment. It therefore remains an external acquisition runtime, not a base dependency.

## Implementation order

1. Commit the versioned optional-dependency groups and component registry.
2. Add the isolated SportsDataverse/CFBD/Open-Meteo adapter boundary with deterministic serialization and raw-snapshot integration.
3. Add DuckDB/Polars/Pandera analytical contracts and validate them on the existing historical lake.
4. Add RapidFuzz candidate generation and a Splink settings builder with explicit no-auto-accept behavior before player/coach identity work.
5. Add Hypothesis properties for canonical identity and temporal invariants.
6. Resume BAT-387 and consume these tools where they reduce implementation effort without changing accepted canonical identities.
7. Activate model/evaluation/operations candidates only when their recorded dependency and empirical gates open.

Temporary review environments and package caches are reconstructible. Preserve their freeze/audit/smoke reports, then delete the environments and cache after repository validation unless they are promoted into a named active runtime.

## Execution traceability

Live Jira work unit `BAT-511` owns this owner-amended review and integration execution. `BAT-363` remains the completed source-universe predecessor, `BAT-387` is the immediate canonical-registry consumer, and `BAT-475` owns the broader dependency/supply-chain control. The review branch must use a protected GitHub pull request before BAT-387 consumes these interfaces.
