# Replay, Result Comparison & Challenger Adoption

## Result packet
A research result packet contains development evidence only:
- experiment ID;
- attempt ID;
- artifact-manifest hash;
- development metrics;
- metric context/direction;
- environment fingerprint;
- warnings;
- failure class;
- replay state;
- recommendation;
- rationale.

Protected W17 metrics are structurally forbidden.

## Comparison compatibility
Candidates are directly comparable only when target/label version, development split, data snapshot family, metric registry, lane, BAS anchor, and A&M baseline semantics are compatible.

Otherwise the comparison result is `INCOMPARABLE`.

## Replay sequence
1. Verify W17 judging-rule seal.
2. Verify experiment identity.
3. Resolve code/data/features/environment.
4. Verify artifact manifest.
5. Execute required replay level.
6. Compare replay evidence with original result.
7. Record verifier/timestamp and mismatch class.

## Replay failures
- HASH_MISMATCH
- INPUT_MISSING
- ENVIRONMENT_UNAVAILABLE
- DETERMINISTIC_OUTPUT_MISMATCH
- STATISTICAL_TOLERANCE_FAILURE
- ARTIFACT_MANIFEST_MISMATCH
- RULE_SEAL_MISMATCH

None is silently waived.

## Adoption
A replay-verified candidate may be adopted by the research governor as a challenger. This does not change production champion state. Production promotion remains external W17 authority.
