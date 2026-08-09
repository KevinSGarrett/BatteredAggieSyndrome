# Feature Screening and Selection — Wave 10

W10 adopts a multi-stage evidence pipeline rather than one ranking statistic.

1. PIT/leakage eligibility gate.
2. Materialized source/data-quality evidence.
3. Low-variance/exact-duplicate screening.
4. Correlation/redundancy and exploratory mutual information.
5. Conditional value from regularization/model-based/permutation evidence.
6. Chronological feature-family ablation.
7. Temporal and subgroup stability.
8. Target-specific calibration/error/proper-score impact.
9. Promotion/demotion decision under precommitted protected evaluation rules.

## What cannot promote a feature by itself
- correlation;
- mutual information;
- tree importance;
- SHAP/importance-style explanation;
- a regularized nonzero coefficient;
- one season of gain;
- football intuition;
- an LLM recommendation;
- synthetic unit-test behavior.

## Multiple comparisons
Large candidate sets make false discoveries likely. W17 must use predeclared evaluation plans, chronological folds and protected test periods; W10 therefore records families and evidence requirements instead of selecting the apparent best field from the full history.

## Correlated features
Permutation/regularization importance can be unstable when predictors are correlated. W10 treats redundancy as a cluster/conditional-value question, not an excuse to delete all but one same-name/correlated field automatically.

## Backward elimination
Allowed as an optional challenger after a stronger baseline exists; it is not a mandatory universal algorithm.
