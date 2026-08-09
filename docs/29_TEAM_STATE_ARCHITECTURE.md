# Team State Architecture — Wave 11

## Purpose
Wave 11 defines the semantic state carried into later player, matchup and model systems. It does **not** train a production team-strength model.

## Four distinct ideas
1. **Prior strength** — what the system believed before enough current-season direct evidence exists.
2. **Underlying strength** — current team quality abstracting short-term availability limitations.
3. **Available strength** — strength usable at the forecast cutoff after known availability/role constraints.
4. **Current-form signal** — recent PIT-safe evidence, ideally opponent adjusted; it is evidence, not automatically the state itself.

These must not be collapsed into one static rating.

## PIT boundary
Every state input must already have passed the W08 PIT gateway. Same-game/postgame evidence cannot enter a pregame state.

## W12 boundary
Wave 11 freezes the `available_strength` interface but does not build player-specific injury/replacement adjustments. Until W12 materializes those contracts, a reference implementation may carry underlying strength forward unchanged and mark availability uncertainty explicitly.

## Lineage
A state snapshot must identify team, forecast cutoff, state version, prior/underlying/available estimates, current-season evidence count, regime identity, opponent translation where applicable, and uncertainty components.

## No production winner in W11
The exact state estimator remains evidence-selectable. W11 compares representation families by contract and synthetic semantics only. Chronological real-data selection belongs to W17/W19.
