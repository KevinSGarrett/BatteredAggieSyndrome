# Team-State Comparison and W11 Gate

## Candidate representations
W11 registers six comparison families:
1. previous-state/static baseline;
2. recency-only;
3. regime-only;
4. recency × regime;
5. change-point shrinkage;
6. hierarchical dynamic prior + observed evidence.

## Chronological evidence design
Real selection must use rolling/walk-forward evaluation with at least:
- national overall;
- Weeks 1–3 / early season;
- mature season;
- major staff/QB/roster transitions;
- FCS/lower-division opponents;
- A&M subgroup later;
- calibration and uncertainty diagnostics.

The game remains the split unit and all data obey W08 cutoffs.

## What Wave 11 proves
Wave 11 proves:
- interface semantics;
- deterministic reference math;
- validation of parameter bounds;
- no hard-coded winner;
- bounded lower-division scope.

It does **not** prove predictive superiority of any weighting scheme.

## Gate
`W11_TEAM_STATE_GATE = CLEARED_W11_CONTRACT_ONLY`.

Downstream waves may rely on the state interface. They may not claim that W11 selected empirical decay, prior blend, change-point threshold or cross-division translation parameters.
