# Project Charter — Aggie Analytics Engine

## Mission
Construct a reproducible, leakage-safe, empirically validated college-football forecasting platform whose primary product and evaluation target is Texas A&M.

## Product outcomes
- calibrated A&M win/loss probabilities;
- predicted A&M/opponent scores and expected margin;
- coherent outcome distributions and uncertainty;
- matchup/team/unit/player strength and availability effects;
- explainability and historical analogs;
- pure-football and optional timestamp-safe market-augmented forecasts;
- scientific BAS underperformance probabilities and postmortems;
- autonomous weekly updating, challenger evaluation and lineage.

## Statistical scope
Broad FBS history is the main learning universe. FCS receives meaningful supporting modeling; lower divisions terminate into increasingly coarse priors/uncertainty. A&M is specialized without monopolizing the training sample.

## Scientific posture
Data availability does not equal feature adoption. Features/models must pass temporal safety, data-quality, walk-forward, ablation, calibration and stability gates. Null results—including failure to find a persistent A&M-specific BAS effect—are valid outcomes.

## Current phase
Wave 03 logical/system architecture is accepted. No trained performance claims exist; detailed data/entity/feature/model implementations remain future-wave work.