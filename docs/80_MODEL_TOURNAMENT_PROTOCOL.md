# Model Tournament — Full Protocol

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Objective

The model tournament compares development-only challengers against mandatory simple baselines under W16 coherent target/output contracts. It is research triage, not champion promotion.

## Baseline ladder

Applicable tournaments must include at least one simple reproducible comparator from the empirical, Elo/rating, logistic/GLM, or simple coherent score-distribution families. Complex candidates are never evaluated only against other complex candidates.

Texas A&M specialization tournaments must include `TAMU-SP-00`, the no-adjustment national forecast. If no specialized model beats it under protected evidence, zero adjustment remains correct.

## Lane isolation

PURE_FOOTBALL and MARKET_AUGMENTED entrants are not placed into one direct model ranking unless the comparison is explicitly a lane comparison. Market data cannot silently enter the pure-football baseline.

BAS tournaments use one frozen W15 label/anchor version. Candidates cannot tune the BAS definition to improve their own result.

## Coherence gate

Any candidate producing team score, opponent score, margin, or win probability must satisfy W16 coherence. A model cannot win on one metric if its outputs contradict the joint-score/target semantics.

## Stages

Admission verifies target/lane/baseline/coherence. Baselines are replayed. Candidates are trained/evaluated on development splits. Calibration/uncertainty layers are compared where relevant. Resource cost and inference/training complexity are recorded. Independent replay is mandatory before adoption as a challenger.

The final W18 disposition can be REJECT, INCONCLUSIVE, RETAIN_RESEARCH, ADOPT_AS_CHALLENGER, or PROMOTION_REVIEW_REQUIRED. `PROMOTE` is not a tournament outcome.

## Pareto and multi-metric handling

The tournament retains the W17 primary metric but does not discard secondary proper scores, calibration, subgroup stability, score-distribution coherence, resource cost, or data requirements. A candidate that is Pareto-dominated across comparable metrics can be rejected without inventing a scalar composite score.

If evidence conflicts across targets or subgroups, the result is INCONCLUSIVE or target-specific rather than forcing one global winner.

## Advanced candidates

Neural, sequence, Transformer, and graph challengers require explicit admission evidence: materialized conventional baseline, demonstrated unresolved modeling gap or baseline saturation, development-only plan, resource budget, rights-cleared inputs, maintenance owner, and a falsifiable incremental hypothesis.
