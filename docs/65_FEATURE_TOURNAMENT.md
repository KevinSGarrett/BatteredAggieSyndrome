# Feature Tournament System

## Objective
Compare candidate feature families and transformations under one development-only protocol. A feature tournament is not a production promotion mechanism.

## Inputs
- W08 PIT eligibility;
- W09 raw-field lineage;
- W10 lifecycle state;
- target/label version;
- frozen baseline feature set;
- development split;
- resource budget.

## Target-specific tournaments
Separate tournaments may exist for win probability, margin, team/opponent score, BAS severity, A&M specialization, and uncertainty auxiliaries.

## Stages
### F0 Eligibility
Reject BANNED, PIT-unsafe, rights-blocked, or unresolved-lineage candidates.

### F1 Data quality
Evaluate materialized missingness, variance, cardinality, coverage, and schema stability.

### F2 Low-cost screening
Use redundancy, association, mutual information, regularization, or similar methods as evidence only.

### F3 Development comparison
Compare candidate family with the frozen baseline using common splits/models.

### F4 Ablation
Measure baseline ± family under the same protocol.

### F5 Stability
Review season/fold/regime/A&M subgroup stability on development evidence.

### F6 Cost/complexity
Record source fragility, compute cost, latency, maintenance, and explanation cost.

### F7 Research decision
Allowed outputs:
- REJECT
- INCONCLUSIVE
- RETAIN_EXPERIMENTAL
- ADOPT_AS_CHALLENGER

The tournament cannot emit CORE, SUPPORTED, or PROMOTE.

## Multiplicity
The number of searched feature families and transformations is retained so later protected interpretation can account for broad search.
