# W17 Scoring, Calibration and Scorecards

## Metric hierarchy
Win probability uses **Brier score** as the primary proper score and log loss as a required secondary proper score. Calibration intercept/slope and reliability diagnostics are reported separately; ECE is diagnostic and cannot be the sole promotion gate.

Margin and score point estimates use MAE as the primary point metric and RMSE as a tail-sensitive secondary diagnostic. Distributional forecasts require a proper score such as joint log score/NLL and margin CRPS when implemented.

BAS severity probabilities use Brier/log loss/calibration separately for >=3, >=7, >=14 and >=21, and every forecast must obey:
`P21 <= P14 <= P7 <= P3`.

## Scorecards
Scorecards are predeclared before protected evaluation. The required dual view is:
- national reference scorecard;
- Texas A&M scorecard.

Additional diagnostics include early season, favorite/underdog, SEC/high-strength opponents, FCS/lower-division opponents, availability stress, high travel/body-clock, home/away-neutral and regime transitions.

Subgroup findings do not automatically override the primary scorecard. Small or sparse subgroups may be `INCONCLUSIVE`.

## Paired comparison
Where candidates and baselines score the same canonical games, comparisons are paired by canonical game. Mirrored rows are not independent samples. Season/game clustering is preserved in uncertainty estimation.

## Calibration
Calibration methods are selected using development-only evidence. Protected-test calibration results assess the frozen method; they do not authorize refitting on protected outcomes.
