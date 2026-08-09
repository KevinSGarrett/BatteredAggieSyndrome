# Player, Roster & Depth Architecture — Wave 12

## Purpose
W12 turns the W11 `available_strength` boundary into a player-aware contract without pretending that player impact has already been calibrated in game points.

## Source-derived principles
The source conversation and reconnaissance require:
- one canonical player identity across seasons, teams, transfers and position changes;
- roster membership, depth role, starter expectation, rotation and actual participation as separate facts;
- dated depth observations rather than backfilling historical depth from later snap counts;
- expected snap/opportunity shares for rotation-heavy positions rather than starter-only logic;
- explicit uncertainty when historical role/depth evidence is inferred or missing.

## Canonical state chain
`canonical player`
→ `effective-dated team membership`
→ `position/role observation`
→ `pregame depth/rotation expectation`
→ `pregame availability scenarios`
→ `scenario-specific lineup contribution`
→ `position-group available state`
→ `W11 team available_strength interface`

Actual same-game snaps remain outcome/evaluation evidence for that game and cannot leak into its pregame state.

## Roster is not depth
An official roster proves listed membership at the capture/known-at time. It does not prove:
- starting status;
- first/second-team depth;
- expected snap share;
- health;
- availability.

## Depth evidence
Official game-week depth charts/game notes are preferred when available. If a historical role is inferred from contemporaneous evidence, the record must say `INFERRED` and retain confidence/provenance. Later snap counts may evaluate the inference but cannot be relabeled as pregame truth.

## Rotations
The model must support multi-player rotation distributions. A defensive line or running-back room cannot be reduced to one starter and one backup when expected snaps are shared across several players.

## W12 maturity
These are contracts/reference semantics. Historical roster/depth materialization and quantitative player-value fitting remain later implementation/evidence work.
