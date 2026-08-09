# Security, Reproducibility, Performance & Data-Governance Requirements — W04

## Security trust model
External archives, APIs, source pages, documents and LLM-derived extractions are **untrusted evidence inputs**. Source content is data, not executable instruction. Before canonical use, apply source-appropriate path, schema, type, provenance and rights checks. Credentials remain externalized and least-privileged. Logs must not expose secrets or restricted raw data.

## Reproducibility model
Reproducibility is lineage-based: an immutable forecast must identify the data snapshot, feature definitions, model/calibration artifact, configuration, environment/runtime, and stochastic configuration needed to replay or explain the original forecast. Re-running current code against current data is not a historical replay.

## Performance governance
The target local environment remains the baseline, but W04 does not guess hard RAM/runtime/storage SLAs. W19-W23 must benchmark material workloads on the target machine and then populate threshold registry entries. Optimization is subordinate to temporal/provenance/validation correctness.

## Data governance
Invalid/ambiguous data is quarantined rather than silently coerced. Entity-resolution uncertainty remains visible. Data-quality thresholds are domain/grain-specific. Critical source outages have explicit fallback/degraded/suppress behavior. Public redistribution requires license/terms/attribution acceptance; automation cannot substitute for rights review when terms are ambiguous.

## Protected model science
Protected test periods are not iterative tuning feedback. Promotion criteria are versioned before protected inspection. PIT/leakage/split/BAS cross-fit failures block the affected model/forecast. Research agents cannot relax those controls.
