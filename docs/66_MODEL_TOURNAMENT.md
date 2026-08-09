# Model Tournament System

## Objective
Compare model architectures under a common development protocol before external W17 promotion review.

## Required baseline ladder
At minimum retain:
- empirical/sanity baseline;
- Elo/rating baseline;
- logistic/GLM baseline;
- simple coherent score-distribution baseline;
- strong boosted-tabular baseline once materially implemented.

A complex model cannot compete only against other complex models.

## Candidate groups
- rating/logistic baselines;
- coherent count/distributional score models;
- boosted tabular candidates;
- calibrated ensembles;
- Texas A&M specialization challengers;
- market-augmented lane;
- uncertainty/OOD challengers;
- advanced neural/sequence/graph challengers after admission.

## Lane isolation
`PURE_FOOTBALL`, `MARKET_AUGMENTED`, and `MARKET_BENCHMARK` are separate tournament lanes. Market data cannot contaminate the pure-football comparator.

## A&M rule
Every A&M specialization comparison includes `TAMU-SP-00` no-adjustment baseline. Nonzero specialization is optional.

## BAS rule
Model candidates may predict BAS targets but cannot redefine W15 BAS labels or contaminate the BAS-independent expectation anchor.

## Coherence
Candidates producing team score/opponent score/margin/win outputs must satisfy W16 coherence checks. Better performance on one target cannot excuse contradictory joint outputs.

## Development evidence
May include Brier score, log loss, score MAE/RMSE, joint likelihood/CRPS when available, calibration diagnostics, declared development subgroup scorecards, runtime/memory, missing-source robustness, and fold/season stability.

## Research decisions
- REJECT
- INCONCLUSIVE
- RETAIN_RESEARCH
- ADOPT_AS_CHALLENGER
- PROMOTION_REVIEW_REQUIRED

No tournament emits production PROMOTE.
