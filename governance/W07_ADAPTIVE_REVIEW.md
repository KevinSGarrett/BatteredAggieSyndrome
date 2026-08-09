# Wave 07 Adaptive Review

## Planned objective still correct?
Yes. W06 cleared source research/replan and made canonical source/evidence identity the critical prerequisite to W08 PIT semantics.

## Dependencies discovered
W06 requires mutable official report identity to distinguish source system, resource, publication version and retrieval capture. This is pulled explicitly into W07 before W08 temporal eligibility.

## Invalidated assumptions
- PostgreSQL is **not** demonstrated as mandatory under the current single-writer append-only review workflow.
- Exact/fuzzy name matching is not sufficient canonical truth.
- Identical raw content does not imply identical retrieval-event evidence.

## Higher-value additions
- merge/split/redirect correction history;
- source evidence identity hierarchy;
- conservative review policy with no fuzzy auto-accept;
- backward-compatible prior-wave verifier/state-key cleanup.

## Redundant work removed
No database server or graph database is introduced simply because entity resolution is relational/graph-like.

## Blockers
No blocker to design-contract completion. Full resolver accuracy, data-volume performance and auto-accept thresholds cannot be honestly measured before W19 materialization/labeled fixtures.

## Future-wave revisions
No wave renumbering. W08 inherits W07 identities; W19 owns materialized resolver/storage/labeled threshold evidence.

## Highest-value W07 outcome
A stable, auditable identity boundary that prevents source/name ambiguity from contaminating PIT state and future model training.
