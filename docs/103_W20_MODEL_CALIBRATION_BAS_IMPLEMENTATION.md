# W20 Starter Model / Calibration / BAS Implementation

## Status
Wave 20 implements a **functional starter**, not a trained production forecasting system and not an empirical model winner.

## Adaptive dependency repair
The inherited W20 critical path included `TASK-087`, but it depended on W19-owned `TASK-083`–`TASK-086`, which remained PLANNED after W19's narrower foundation gate. W20 pulls those functional advanced-state starter dependencies forward rather than falsely clearing the gate. The 25-wave count is unchanged.

## Runtime boundary
`FeatureVector` requires an immutable W19 feature snapshot ID, an aware forecast cutoff and explicit lineage. `ModelArtifact` requires training-data lineage and a training cutoff. Runtime prediction rejects a model whose training cutoff is not strictly earlier than the prediction cutoff.

## Baselines
Functional dependency-free starters include:
- constant empirical probability sanity baseline;
- Elo probability mapping;
- linear/logistic feature baseline;
- independent-Poisson coherent joint-score baseline.

A boosting adapter contract supports XGBoost/LightGBM/CatBoost/sklearn-compatible injection **without making an optional boosting package a base dependency**. No boosting winner is selected.

## Coherent forecast output
The independent-Poisson starter produces `JointScoreDistribution`, then win/loss, expected scores, margin and BAS severity probabilities derive from that same distribution through the W16 coherence functions. This prevents contradictory independently published summaries.

## Calibration and ensemble
Identity and parameterized logistic calibration starters are implemented. Calibration parameters are explicitly development-only. A weighted probability ensemble validates nonnegative weights summing to one. W20 does not fit calibration on protected seasons.

## Uncertainty
W16 uncertainty categories remain authoritative. W20 forecast snapshots may carry uncertainty signals but do not claim calibrated numeric uncertainty without supporting calibration evidence.

## Texas A&M specialization
The A&M adapter requires:
1. a canonical/PIT-backed high-resolution A&M state overlay;
2. a specialization candidate;
3. an explicit national no-adjustment forecast reference.

`TAMU-SP-00` remains the required no-adjustment reference. No nonzero A&M adjustment is production-selected in W20.

## BAS
The W15 protected anchor/label contract is reused. Starter BAS probability forecasts must preserve nested severity probabilities `P21 <= P14 <= P7 <= P3` and retain anchor/model lineage. No Aggie Excess significance claim is made.

## Model registry
The local starter registry is content-addressed by immutable `ModelArtifact` SHA-256. Allowed W20 states stop at candidate/development/protected-ready/rejected/inconclusive. The registry cannot self-declare promotion.

## W17 protection
W20 does not inspect or tune on protected 2024–2025 results, set blank W17 promotion thresholds, select a feature/model winner, or fabricate Brier/log-loss/MAE/RMSE results.

## W21 handoff
W21 should orchestrate these W19/W20 functional boundaries into an idempotent weekly pipeline: ingest → QA/quarantine → PIT state → features → candidate train/calibrate → governed evaluation/promotion → immutable prediction snapshot → postmortem/research queue.
