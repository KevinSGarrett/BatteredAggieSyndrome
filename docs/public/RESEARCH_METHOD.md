# Research method: expectation is not the result

## 1. Define the question before looking for an answer

The project asks whether A&M's results are unusually low relative to defensible expectations and comparable programs. It does not assume that the effect exists. A preseason poll, an independent model, and a market price measure different notions of expectation and should not be conflated.

## 2. Establish a national baseline

Compare national team-game observations under consistent identities and chronological rules. Respect changes in conference and subdivision membership. Select peer cohorts using declared, measurable criteria rather than choosing teams after seeing the desired result.

## 3. Preserve what was knowable before kickoff

Every feature needs a cutoff, source, and defensible availability basis. A current capture may establish present availability; it does not by itself establish historical availability. Roster membership is not pregame player availability. Observed postgame weather is not a pregame forecast vintage.

## 4. Keep the statistical quantities distinct

- **Win probability:** a model's probability of victory under its stated assumptions.
- **Expected margin:** the modeled average scoring difference, with an explicit team orientation.
- **Predictive interval:** a range intended to cover a future result at a declared rate. It is not automatically a confidence interval for the mean.
- **Margin residual:** actual margin minus expected margin. Negative values indicate a shortfall relative to that model.
- **Outcome residual:** observed win indicator minus predicted win probability.

An expected margin alone does not determine an exact final score. A score projection requires a total-points or team-score model. Combining an independent margin with a market total would be a hybrid, not an independent forecast.

If a candidate presents a probability and interval as summaries of one predictive distribution, both must be derived consistently from that distribution. An expectation and a probability need not universally have matching signs for every possible asymmetric distribution; any imposed symmetry or link assumption must be stated and validated, not treated as a universal theorem.

## 5. Evaluate before drawing conclusions

Use chronological training/evaluation separation, fold-local transforms and calibration, and explicit game-level accounting. Two oriented team rows from one game are not independent games. Neither are several models' predictions for the same contest.

Report probability scores such as Brier score and log loss, margin error, calibration diagnostics, interval coverage, sample sizes, abstentions, and sensitivity to model choices. A small sample cannot establish robust calibration or a persistent program effect.

Expected-versus-actual residuals are conditional on the expectation model. Descriptive residual differences do not by themselves establish a causal effect, a treatment effect, or a scientifically proven counterfactual.

## 6. Preserve prospective evidence

Freeze the candidate, inputs, cutoff, and prediction before the relevant game. Never backfill a missed pregame forecast. Score only after valid final-result authority exists. Keep later corrections in distinct, traceable versions.

Market benchmarks remain separately labeled. Neither market disagreement nor a disappointing A&M prediction authorizes an arbitrary model adjustment.

## Reading the risk concept

The README artwork illustrates the intended report format, not a computed game
forecast. Its shortfall bars represent nested tail probabilities,
`P(shortfall >= threshold)`, rather than disjoint outcome bins. The example values
are illustrative; a released risk report would require a declared predictive
distribution, evaluated calibration, and explicit evidence for any risk category.
