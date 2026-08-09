# Architecture Interface Contracts

W03 defines conceptual cross-boundary contracts so later waves can change internal implementations without rewriting the entire system.

## IF-001 — SourcePayloadEnvelope
Provider/source ID, retrieval timestamp, request/acquisition metadata, content hash, native payload reference.

## IF-002 — ValidationResult
Source payload reference, contract version, validation status, findings, quarantine disposition.

## IF-003 — CanonicalObservationBatch
Stable canonical IDs plus source-mapped observations, effective/known-at timestamps, source lineage and confidence.

## IF-004 — AsOfContext
Prediction timestamp, data cutoff and applicable rule/version context. Every historical feature build carries it explicitly.

## IF-005 — PITStateRef
Immutable reference to the reconstructed eligible state for a prediction context.

## IF-006 — FeatureMatrixRef
Feature-set version, PIT snapshot reference, row/game IDs, transform lineage and hash.

## IF-007 — ModelArtifactRef
Immutable model/calibration artifact identity, training-data lineage, code/version and status.

## IF-008 — NationalForecast
National baseline distribution/representation with uncertainty and model lineage.

## IF-009 — TamuSpecializationResult
A&M-specific adjustment/representation, uncertainty and provenance relative to national baseline.

## IF-010 — ForecastDistribution
Coherent team-score/opponent-score/margin/win distribution plus scenario/uncertainty metadata.

## IF-011 — BASResult
BAS severity probabilities derived from leakage-safe expected performance, with label/model lineage.

## IF-012 — ForecastSnapshot
Immutable product artifact tying the eligible data snapshot, features, models, outputs and warnings to one prediction timestamp.

## IF-013 — ExperimentProposal
Research-only candidate with hypothesis, inputs, code/config, requested evaluation and provenance.

Exact Python/Pydantic/Arrow/database schemas remain later-wave work. The semantic boundaries above are the W03 contract.
## W08 PITStateRef freeze
`IF-005 PITStateRef` is now governed by `configs/temporal_registry.json`. It returns observation/state references selected under an immutable cutoff/policy, not unversioned current values. `feature_factory` may not bypass this interface.
