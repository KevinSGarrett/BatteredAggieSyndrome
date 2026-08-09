# Source Authority Map

## Precedence model

1. Explicit protected/immutable project rules and sealed judging/split artifacts outrank ordinary planning text.
2. Final W25 handoff and current-state artifacts outrank stale wave-transition summaries.
3. Current machine-readable governance registries outrank older narrative counts for the same registry.
4. Final known gaps, risk register, implementation priority, backlog, and component maturity determine post-wave actionability.
5. Later accepted ADRs may supersede earlier revisable assumptions, but recency never overrides a protected invariant by itself.
6. Earlier architecture and wave documents remain authoritative detailed design/provenance unless explicitly superseded.
7. Executable source/tests prove current starter behavior; they do not prove real-data, protected, target-hardware, scientific, or operating results not present in evidence.

## Conflict handling

Conflicts are recorded in `CONFLICT_REGISTER.csv`. The generator never guesses through an unresolved conflict that affects safety, scientific validity, rights, target configuration, or completion state. A newer file is not automatically authoritative; authority class, protected status, explicit supersession, and final handoff context are evaluated together.

## Canonical source references

Repository-relative paths are canonical. Absolute Windows paths are convenience metadata. Every generated source reference stores SHA-256, heading/line metadata, and an anchor hash/excerpt so drift can be detected and relocated.
