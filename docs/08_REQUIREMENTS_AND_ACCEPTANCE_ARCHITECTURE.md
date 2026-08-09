# Requirements Hardening & Acceptance Architecture — W04

## Purpose
Wave 04 converts the cumulative requirements into **verifiable contracts without pretending later-wave implementation evidence already exists**. It preserves stable requirement IDs and separates three dimensions:

1. **Constraint class** — A invariant/mandatory, B strong default, C hypothesis/research candidate.
2. **Requirement lifecycle** — ACTIVE, DEFAULT, RESEARCH, COMPLETE/SUPERSEDED where applicable.
3. **Acceptance evidence state** — currently verified, partial, contract-defined/owner-pending, or experiment-required/nonblocking.

A mandatory future requirement is not a W04 PASS merely because the requirement is accepted.

## Acceptance layers
- **Program/package gates:** pair binding, manifests, IDs, secrets, forbidden artifacts.
- **Architecture gates:** PIT gateway, research/live isolation, snapshot serving, dependency direction.
- **Data/PIT gates:** source contracts, canonical provenance, known-at replay, leakage, split safety, quarantine.
- **Feature/model science gates:** feature lifecycle, baselines, walk-forward, protected tests, calibration, coherence, uncertainty.
- **A&M/BAS gates:** null/shrinkage allowed, cross-fit BAS label, peer/stability/anti-circularity evidence.
- **Reproducibility/operations gates:** lineage replay, environment capture, stochastic config, freshness, benchmark, backup/restore.
- **Security/source gates:** untrusted-input and malware validation, dependency integrity, safe logging, credentials, private-personal-data exclusion, schema compatibility, provenance, PIT, and leakage. License/redistribution status is metadata-only for private use.

## Evidence modes
Acceptance is intentionally multi-modal. `STATIC` is appropriate for repository or dependency rules; `UNIT`/`INTEGRATION` for deterministic software contracts; `TEMPORAL_REPLAY` for PIT correctness; `SCIENTIFIC` for predictive claims; `BENCHMARK` for performance; and `MANUAL_REVIEW` for ambiguous semantic or future-publication decisions. Licensing ambiguity never blocks private local acquisition or training.

Forcing every requirement into a unit test would create fake automation. Conversely, manual judgment cannot silently waive a protected deterministic/scientific control.

## Blocking semantics
Each acceptance control declares the gate where it matters. A future control can be release-blocking **at its owning gate** while remaining `DEFINED_PENDING_OWNER` today. W04 does not claim future data/model/product completion.

Protected temporal/leakage controls fail closed. If known-at semantics are ambiguous, the field is unsafe/review-required, not presumed eligible.

## Quantitative thresholds
W04 deliberately does not invent Brier/log-loss/calibration/MAE, entity-confidence, completeness, freshness, RAM or runtime thresholds. `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` assigns these decisions to the wave that will have the required protected data or target-hardware benchmark evidence.

## Traceability
- Requirements → `REQUIREMENT_ACCEPTANCE_MATRIX.csv`
- ADRs → `ADR_ACCEPTANCE_TRACEABILITY.csv`
- Risks → `RISK_ACCEPTANCE_TRACEABILITY.csv`
- Controls → `ACCEPTANCE_CONTROL_CATALOG.csv` and `configs/acceptance_registry.json`
- Thresholds → `ACCEPTANCE_THRESHOLD_REGISTRY.csv`

`tools/validate_acceptance.py` validates exact coverage and protected acceptance semantics.

## Promotion/release rule
A control may report PASS only when its required evidence exists. Design-only contracts remain pending. Research hypotheses remain nonblocking until formally promoted. Protected test windows and promotion criteria are frozen before protected-result inspection.
