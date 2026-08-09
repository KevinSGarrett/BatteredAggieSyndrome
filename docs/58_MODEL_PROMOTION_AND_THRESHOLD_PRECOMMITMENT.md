# W17 Model Promotion and Threshold Precommitment

## Core rule
No feature, model, A&M specialization, BAS component, OOD detector, market lane or research agent may self-promote.

## Threshold governance
W17 freezes the **method for deriving** THR-001..007 and THR-014..015. Numerical values remain blank because materialized development model evidence does not yet exist.

A required blank threshold is not interpreted as zero and is not waived. The decision gate returns:

`BLOCKED_THRESHOLD_UNSET`

until the value is derived from development-only evidence, versioned and sealed before protected evaluation.

Protected results may never be used to choose or relax a threshold.

## Promotion states
The decision system distinguishes protocol/artifact/threshold blocks, development-only candidates, protected-ready candidates, reject, inconclusive, shadow-only, promote and rollback-required states.

## Promotion evidence
A promotion record must identify:
- champion and challenger artifact/version;
- data/feature/model/calibration lineage;
- protected split protocol/version;
- metric registry/version;
- threshold registry/version;
- subgroup scorecard version;
- result hashes;
- decision and rationale.

## No-result path
If evidence is mixed or insufficient, the champion/no-change state remains valid. Complexity does not earn promotion merely because it was expensive to build.
