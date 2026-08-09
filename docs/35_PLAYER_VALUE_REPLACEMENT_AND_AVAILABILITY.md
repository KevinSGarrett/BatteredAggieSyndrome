# Player Value, Replacement & Availability — Wave 12

## Core rule
Availability impact is player-specific and replacement-specific. W12 does not define permanent point penalties by position.

Conceptually the information needed is:
- healthy player value;
- availability probability;
- effectiveness if active;
- expected usage/snap share;
- replacement identity/identities;
- replacement value;
- redistributed usage;
- matchup/unit context;
- uncertainty.

The production model does not have to multiply these terms literally.

## Scenario representation
A player may have multiple mutually exclusive scenarios such as:
- full role;
- active but limited;
- unavailable with direct backup;
- unavailable with committee/rotation redistribution.

Each scenario carries a probability and lineup contribution in abstract player-value units. W12 does **not** map those units to expected game points.

## Replacement logic
Replacement quality must emerge from evidence. `QB1 out` can often matter more than a low-usage specialist because usage and replacement gaps differ, but W12 does not encode a universal QB penalty.

A replacement may be:
- one backup;
- a position change;
- multiple players sharing snaps;
- a changed scheme/role distribution.

## Anti-double-counting
Do not independently add all of:
- starter-out flag;
- injury count;
- position injury count;
- team injury index;
- replacement downgrade;
- availability probability penalty

unless later ablation shows distinct incremental information.

## Position-aware player value
W12 registers position-specific evidence families but freezes no player-value formula or manual weights. Player value remains an estimate with uncertainty and must be learned/evaluated chronologically.

## Available-strength handoff
W11 `underlying_strength` remains the baseline team quality abstraction. W12 supplies structured availability/replacement evidence that later modeling can use to derive `available_strength`; W12 itself does not claim a calibrated team-strength adjustment.
