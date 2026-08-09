# Canonical Entity Context — W07

- Canonical identity is separate from source IDs and mutable state.
- Surrogate IDs are opaque/stable; prefixed UUID4 is the current dependency-free representation default before real materialization.
- Domain identities: team, institution, conference, season, game, venue, player, coach, official.
- Evidence identities: source system, source resource, publication version, raw capture, source observation.
- Team↔institution, team↔conference, player↔team, coach↔role/team and game schedule/venue are relationships/observations, not identity.
- Source mappings and review/correction decisions are append-only.
- No name-only durable joins.
- Fuzzy matching is candidate ranking only; fuzzy auto-accept is disabled and THR-008 is deferred to W19 labeled evidence.
- Merge/split corrections preserve old IDs/decisions/data versions through redirect/supersession.
- PostgreSQL remains optional; current workflow is single-writer append-only behind storage ports.
- W08 owns final PIT/known-at/effective-date semantics. W19 owns materialized resolver/storage benchmarks.
