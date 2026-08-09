
# W16 Model Architecture Candidates

The architecture keeps strong simple baselines and increasingly expressive challengers.

## Mandatory baselines
- empirical/home-rate sanity reference;
- Elo with probability mapping;
- logistic/GLM feature baseline;
- simple coherent score-distribution baseline such as Poisson/Skellam.

A market benchmark is maintained separately and cannot contaminate the pure-football lane.

## Joint/distribution candidates
Candidate families include independent Poisson, bivariate Poisson, hierarchical overdispersed count models, possession x efficiency generative models, flexible latent/correlated distributions, copula/dependence constructions, boosted tabular models, small neural challengers, and calibrated ensembles.

These are **candidates**, not commitments. XGBoost, LightGBM, CatBoost, PyTorch, or a complicated joint model must earn their place against simpler baselines.

## A&M specialization
W14's national no-adjustment prediction remains mandatory. Residual/hierarchical/multi-task A&M specialization may be layered only after protected evidence supports incremental value. Model architecture may not force a nonzero Aggie adjustment.

## Calibration
Calibration is a separately versioned contract/artifact even when a method is trained together with a base model. W17 owns calibration methodology and thresholds.
