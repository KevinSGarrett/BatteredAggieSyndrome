# Temporal Context — W08

- PIT is bitemporal: knowledge/system time and real-world validity/event time are separate.
- `first_known_at` must be defensible; `retrieved_at` is the conservative fallback when earlier public timing is unproven.
- `prediction_eligible_at` is derived under a policy version, never a raw source truth or sole eligibility test.
- Feature construction may not bypass `CMP-005 pit_state`.
- Revisions are replayed as-known-at-cutoff; later corrections never rewrite old snapshots.
- Availability noncoverage is UNKNOWN, weather requires issued model-run provenance, markets are provider/timestamp scoped, regulatory/resources separate publish and effective/reporting periods.
- W08 contains contract-level executable synthetic fixtures only; real historical leakage freedom remains W19+/W24 evidence.
