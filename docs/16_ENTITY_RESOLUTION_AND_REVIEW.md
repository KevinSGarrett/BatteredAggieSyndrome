# Entity Resolution & Review — Wave 07

## Goal
Resolve source identities into canonical identities with high precision while making uncertainty auditable.

## Resolution pipeline
1. Reuse a previously verified, non-superseded source mapping when its scope is valid.
2. Apply a validated direct-source-ID or authoritative crosswalk contract.
3. Normalize labels only for candidate generation; originals remain preserved.
4. Generate exact scoped aliases and composite-context candidates.
5. Optionally rank fuzzy name/context candidates.
6. Auto-accept **only** verified existing/direct/crosswalk classes in W07.
7. Send other ambiguity/conflicts to review.
8. Append an immutable decision and supersede earlier records when correction is necessary.

## No name-only durable joins
Names may seed candidates. They cannot by themselves establish production player/coach identity. This protects against transfers, duplicate names, suffixes, spelling changes and source normalization differences.

## Fuzzy matching policy
Fuzzy matching is a retrieval/ranking aid, not truth. `THR-008` remains unset because no labeled resolver benchmark exists yet. W07 therefore enables **no fuzzy auto-accept threshold**. W19 must build labeled fixtures/review evidence before any such threshold can be considered.

## Resolution states
See `governance/ENTITY_RESOLUTION_STATES.csv`.

Unresolved/review-required is a valid state. Unknown does not become zero, a random match or the top fuzzy candidate merely to keep a pipeline moving.

## Review queue
The review queue is a derived view over unresolved candidate/decision events, not a mutable truth table. Review produces an immutable `resolution_decision` event.

## Merge
When two canonical IDs are proven to be the same identity:
- choose a survivor;
- mark duplicate ID deprecated;
- append `entity_redirect`;
- supersede affected mappings;
- preserve old data/version lineage.

## Split
When one canonical identity was incorrectly conflated:
- preserve the original decision history;
- create new canonical identity/identities;
- append corrected mappings;
- supersede incorrect mappings;
- rebuild later canonical/PIT derivatives under a new dataset version.

## LLM policy
An LLM may assist candidate extraction from unstructured evidence, but it cannot directly promote an ambiguous mapping to canonical truth without the same deterministic evidence/review policy.
