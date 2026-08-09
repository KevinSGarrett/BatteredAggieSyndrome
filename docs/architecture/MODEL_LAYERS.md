# Model-Layer Architecture

## Layer 1 — National foundation

Learns broad college-football behavior using the national historical foundation, with meaningful FCS support and coarser lower-division priors.

Its contract should expose representations usable by downstream matchup/forecast components, not only a single hard-coded classifier.

## Layer 2 — Texas A&M specialization

Consumes:
- national representation;
- A&M high-resolution PIT state;
- opponent/matchup context;
- uncertainty.

It may later be implemented as:
- residual adapter;
- hierarchical multi-task model;
- partially pooled specialization;
- mixture-of-experts;
- stacked calibration/residual system.

W03 freezes the **interface purpose**, not the statistical family.

## Layer 3 — Forecast assembly

Produces coherent joint outcomes from approved model components. Win probability, team/opponent score, margin and BAS-related residuals cannot be independent contradictory outputs.

## Layer 4 — Calibration and uncertainty

Calibration is first-class. Model disagreement, data coverage, OOD state, player availability and other uncertainty sources must be able to widen or qualify the forecast.

## Model registry boundary

Model files are immutable artifacts with metadata. A registry identifies candidate/champion/rollback state. Experiment tracking and promotion governance are related but not identical responsibilities.

Research may write challenger artifacts. Protected evaluation decides whether champion state changes.

## Baseline-first rule

Architecture permits boosting, GLMs, Bayesian/hierarchical methods, neural models and ensembles, but simple baselines remain mandatory. Complexity is promoted only when empirical walk-forward evidence justifies it.
