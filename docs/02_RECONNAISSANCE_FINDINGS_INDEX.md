# Reconnaissance Findings Index

The FINAL v1.2 pre-25-wave reconnaissance pack is accepted as authoritative starting evidence, not as a complete historical data lake.

## Confirmed high-level evidence contracts
- SportsDataverse/cfbfastR as primary processed historical/PBP foundation; CFBD as primary supplemental source.
- Canonical entities and source mappings; immutable raw evidence; dated mutable observations.
- 1,197-field/evidence temporal registry in the pack with explicit leakage/as-of classes.
- Field-specific source confidence and provenance requirements.
- Weather/venue/travel and forecast-vs-observed temporal separation.
- Program-resource strategy with EADA universal baseline and public-school enrichment; no fabricated private-school values.
- A&M official sources as high-resolution target evidence, with roster ≠ depth chart and mutable pages requiring snapshots.
- v1.1 contracts for transfer translation, availability impact, role-conditioned coaching, preseason honors, draft leakage and learned home-field strength.
- v1.2 contracts for possession/tempo, field position, special teams, fourth down/clock, score state, officiating, stakes, rule eras, market snapshots, joint score, uncertainty/OOD, live replay, edge cases and source-rights governance.

## Materialization gaps
The pack explicitly leaves full historical source materialization, population profiling, large-scale entity resolution, historical A&M depth/injury reconstruction, market timestamps, rule timelines and other implementation tasks unresolved. Those are preserved in `governance/UNRESOLVED_QUESTIONS.csv`.

## Integrity note
The final manifest contains 216 entries and all 216 hashes validate. The root `PACK_MANIFEST.csv` contains 219 rows but its self-referential entry is stale because writing the manifest changes itself; no other root-manifest mismatch exists. Wave 01 therefore designates the final manifest/hash set as authoritative and records the root self-entry as a non-blocking packaging artifact.
