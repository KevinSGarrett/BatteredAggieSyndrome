
# W16 Joint Score and Simulation

## Joint score
A joint score distribution provides the coherent parent object for:
- team score;
- opponent score;
- margin;
- total;
- win/loss;
- spread-cover probability in the market-augmented lane;
- candidate BAS residual/severity probabilities relative to the W15 anchor.

## Overtime
A regulation-score model may have tie mass. It must therefore carry an explicit overtime resolution model/probability. A final-score model should have no final tie support.

## Scenario engine
Scenario simulation is an interface around a baseline immutable forecast snapshot, not permission to rewrite historical state.

Candidate scenario dimensions include:
- player availability/effectiveness/usage/replacement;
- QB availability;
- issued weather forecast ensembles;
- pace/expected possessions;
- lower-division opponent strength uncertainty.

Scenario weights must be explicit and normalized. Scenario state still passes W08 PIT rules.

## Reproducibility
Stochastic simulation records:
- scenario IDs;
- underlying model/data/feature/calibration versions;
- cutoff;
- random seed;
- sample count or exact-mixture method.

Monte Carlo noise is not epistemic uncertainty. When exact distribution mixtures are practical, they are preferred for deterministic summary calculations.
