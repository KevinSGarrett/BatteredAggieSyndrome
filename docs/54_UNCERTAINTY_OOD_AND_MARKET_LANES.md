
# W16 Uncertainty, OOD, Disagreement and Market Lanes

## Uncertainty is multi-source
W16 distinguishes:
- aleatoric game randomness;
- epistemic/model uncertainty;
- data-quality uncertainty;
- player availability uncertainty;
- weather uncertainty;
- opponent/lower-division strength uncertainty;
- regime uncertainty;
- A&M-specialization uncertainty;
- model disagreement.

These components are not blindly added as if they share a calibrated numeric unit.

## OOD
Candidate signals include feature-space distance, training-support density, categorical novelty, missingness shift, regime novelty, lower-division sparsity and validated model disagreement.

OOD generally widens warnings/uncertainty. It does **not** automatically say which team is better.

`THR-014` remains blank until W17 evidence.

## Model disagreement
Disagreement may use probability spread, expected-margin spread, distribution divergence or decision discordance. Correlated models are not independent votes.

`THR-015` remains blank until W17 evidence.

## Market lanes
**PURE_FOOTBALL** contains no market-derived features.

**MARKET_AUGMENTED** may use only immutable PIT-safe market observations known at the forecast cutoff.

**MARKET_BENCHMARK** may compare forecasts with market information at the relevant market timestamp. A closing line cannot leak into a Wednesday forecast.

W16 selects no market provider.
