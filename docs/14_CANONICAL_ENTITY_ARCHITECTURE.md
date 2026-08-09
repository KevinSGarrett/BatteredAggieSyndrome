# Canonical Entity Architecture — Wave 07

## Status
**Accepted design contract.** This wave freezes identity semantics and machine-readable contracts. It does **not** claim that the national historical entity lake has been materialized; real resolver/data-adapter implementation remains primarily W19.

## Identity rules

1. Canonical identity is separate from every provider/source identity.
2. Identity is separate from mutable state. A player remains the same player when team, position, weight or availability changes; a coach remains the same coach when role changes.
3. Surrogate canonical IDs are opaque and immutable after assignment. They do not encode a source ID, name, team, season or mutable business meaning.
4. The current implementation-friendly default is a type prefix plus UUID4 hex, e.g. `player_<uuidhex>`. The representation is a Level-B default until real IDs are materialized; the invariants are opacity, stability and no source coupling.
5. Football season is the explicit natural-key exception: the canonical season is the football season integer. Fiscal/academic/resource years remain separate observations/keys.
6. Texas A&M receives higher-resolution evidence but uses the **same canonical identity system** as every other team.

## Core entity types
See `governance/CANONICAL_ENTITY_CATALOG.csv` and `configs/entity_registry.json`.

Required domain identities are team, institution, conference, season, game, venue, player, coach and official. Required evidence/technical identities are source system, source resource, publication version, raw capture and source observation.

## Identity versus episode/observation

The following are not identity:
- player team/position/class/height/weight;
- coach role/team/title/play-caller status;
- team conference/classification/name;
- venue name/capacity/surface;
- game kickoff/venue/status/home-away-neutral orientation;
- official role/crew assignment.

They are effective-dated episodes or observations. W08 owns final PIT temporal semantics.

## Team versus institution
A football team/program is not assumed to be identical to an institution string. Resource datasets use institutional identifiers, while football datasets use team/program identities. `team_institution_affiliation` is therefore explicit and may be effective-dated.

## Player transfer identity
A transfer does not create a new player. Roster/team memberships become episodes linked to one canonical player when evidence supports that identity. Name alone is never sufficient for durable production linkage.

## Coach identity
Coach identity is independent of role. Promotions and team changes create new role episodes, not new coach records.

## Game identity
A canonical game represents an underlying contest reconciled across source evidence.
- kickoff/venue reschedule: normally same game if official continuity and participants establish the same contest;
- cancellation: same scheduled contest identity with changed status;
- replacement opponent/new matchup: new game identity;
- forfeit/vacated result: result/status annotation, not new identity;
- home/away/neutral: participant-orientation observation, not canonical identity.

Direct provider game-ID equality is mapping evidence only until the join contract is validated.

## Identity correction
Assigned canonical IDs are not destructively rewritten. Duplicate merges create a redirect from deprecated identity to a survivor. Splits create new IDs and supersede incorrect mappings. Old decisions and dataset versions remain reproducible.

## Ownership boundary
W07 freezes identity semantics. W08 adds PIT/effective-dated joins; W09 expands schema/field registry; W19 implements source adapters/entity resolution against materialized data.
