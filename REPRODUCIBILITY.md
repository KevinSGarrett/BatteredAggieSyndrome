# Reproducibility and scientific review

The goal is to make an expectation inspectable: which data, which cutoff, which transformation, which model, and which evaluation population produced it?

## Record enough to reproduce a result

A research result should identify:

- source requests, raw content hashes, provider rights, and actual acquisition receipts;
- canonical game and participant identities;
- event time, source publication/availability evidence, and forecast cutoff;
- input populations, exclusions, missingness, and field-level feature admission;
- code and dependency versions, model parameters, and random seeds;
- chronological training, calibration, and evaluation partitions;
- immutable forecast and label identities;
- formulas, denominators, confidence or prediction intervals, and limitations.

Do not publish secrets, licensed bulk payloads, private medical information, or account-specific operational records to make a reproduction convenient. Use permitted data, synthetic fixtures, and clear access requirements.

## What tests can establish

| Check | What it establishes | What it does not establish |
|---|---|---|
| Content hash | Bytes match a recorded identity | Source truth, publication time, or scientific validity |
| Deterministic rebuild | Fixed inputs produce the same output | That the specification is appropriate |
| Independent numerical reconstruction | Another implementation agrees on a calculation | That the selected population or features are justified |
| Semantic and temporal audit | The reviewed meaning and evidence fit the stated claim | Predictive accuracy in a new population |
| Prospective evaluation | Performance on the declared future cohort | Universal accuracy or a causal explanation |

## Essential statistical checks

Chronological splits must keep a target game out of its own training and features. Oriented team rows from one game are not independent games. Coverage denominators must match the stated population. A paired probability, margin, and prediction interval must have a compatible statistical interpretation.

Report Brier score and log loss alongside calibration, coverage, abstention, and sample size. For margin models, report error and interval coverage. Account for paired games and repeated teams when estimating uncertainty. Do not select a model on the same outcomes used to announce its success.

## Running available tests

Install the package as described in [usage](docs/public/GETTING_STARTED.md), then run a targeted suite:

```bash
python -B -m unittest discover -s tests -p "test_independent_scientific_reference.py"
python -B -m unittest discover -s tests -p "test_w22_product_serving.py"
```

The second command uses the current filename of the snapshot-serving tests. It does not require a live sports-data feed. Some optional dependency or operating-system tests may skip; record those skips.

Full discovery has additional data and operational dependencies. It is not a portable zero-configuration public acceptance test yet. Never report skipped tests as successful scientific validation.

Current validation limits are documented in [research status](docs/public/STATUS.md). There is no validated BAS score or demonstrated persistent A&M effect to reproduce yet.
