# Feature Engineering Architecture — Wave 10

## Purpose
W10 converts the W09 raw-field handoff into a **candidate experiment system**, not a production feature list. Every feature candidate must enter through W08 PIT state, preserve W07 identity and W09 raw-field lineage, and remain target-specific.

## Hard boundary
`raw evidence -> canonical identity -> PIT state -> raw-field registry -> versioned transform -> candidate feature -> chronological evidence -> lifecycle decision`

No transform may query mutable provider/current state directly. For trailing game outputs, the target game's observations are excluded by construction.

## Transformation templates
W10 registers 14 templates including lagged last value, rolling aggregates, EWMA, trend, rate normalization, opponent-adjusted residuals, matchup differences/interactions and conditional missingness indicators. Parameters such as rolling window or EWMA alpha are **experiment parameters**. W10 does not declare one universal 3-game/5-game/season window.

## Opponent adjustment versus schedule load
Opponent adjustment asks how performance compares with expectation given opposition. Schedule load asks what burden the team has endured. They remain separate representations and may later interact; one must not be substituted for the other.

## Interactions
Interactions must be explicitly registered and evaluated. Cartesian/brute-force interaction generation is prohibited because it inflates multiple-testing risk, compute and false discovery.

## Lineage
Every derived candidate ultimately records parent raw fields/observations, transform ID/version/parameters, PIT cutoff and downstream experiment/evaluation version. Derived values are not permitted to become anonymous columns.

## Current maturity
The reference transform library is functional on synthetic inputs, but W10 does not have the historical materialized training matrices needed to claim predictive value.
