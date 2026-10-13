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

## Reference implementation boundaries

These helpers are executable reference components, not accepted trained forecasts.
The opponent-history helper selects the latest strictly prior observation by its
time, independently of input order; conflicting values at that time are refused.
An Elo home adjustment requires the selected team's signed home indicator
(`+1` home, `-1` away, `0` neutral). The default zero adjustment needs no site
claim. Mirroring both ratings and role produces complementary probabilities.

The independent Poisson reference refuses finite support that omits more than
the distribution's existing numerical tolerance (`1e-9`) on either marginal.
Callers must supply sufficient score support; normalization alone does not make
a materially censored distribution a valid approximation. This numerical bound
is not an empirical model-quality or scientific-admission threshold.

Scenario mixtures require one immutable baseline snapshot and distinct scenario
identities. Numeric uncertainty claims require finite nonnegative values and a
calibration evidence reference; validating that reference's presence does not
establish empirical calibration. BAS labels refuse nonfinite margins and
overflowed residuals, while preserving the original shortfall definition and
the 3, 7, 14 and 21 point severity thresholds.

Retained research may contain both an unfixed predecessor and a supported
successor. The saved historical game-grain adapter repairs paired probabilities
in older prediction files without refitting those models. It remains an
untrusted development artifact and supplies no joint score/interval, PIT or
predictive-skill acceptance. New planning must inspect that successor before
assigning the same correction again.
