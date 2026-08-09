# Feature Tournament — Full Protocol

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Objective

The feature tournament is a governed development-only mechanism for deciding which PIT-safe candidate families deserve further consideration. It does not promote lifecycle states directly and cannot use protected 2024–2025 or 2026+ forward-shadow results as search feedback.

## Entry requirements

A candidate family must reference W09 raw-field IDs, W08 temporal eligibility states, W10 transformation/lifecycle metadata, a target, a frozen baseline feature set, and a feature-set version. Any BANNED or unresolved temporal candidate is rejected before training.

The tournament records the full search multiplicity: how many families, transformations, windows, interactions, and variants were evaluated. This is required so later interpretation does not pretend the best-looking result came from a single predeclared comparison.

## Stages

**Stage 0 — eligibility:** lineage, PIT, rights, missingness coverage, baseline ID, and development split are validated.

**Stage 1 — baseline reproducibility:** the baseline feature set is replayed before candidate comparisons.

**Stage 2 — plus-family:** candidate family is added to the frozen baseline.

**Stage 3 — minus-family/ablation:** when the family already exists in a larger candidate set, remove it to measure incremental dependence.

**Stage 4 — temporal stability:** inspect development folds/seasons and declared regime partitions.

**Stage 5 — subgroup stability:** evaluate declared A&M/national and relevant subgroup scorecards using development evidence only.

**Stage 6 — cost/maintainability:** compute/materialization cost, coverage, rights, and operational fragility are recorded.

**Stage 7 — replay:** candidate and baseline are independently replayed from frozen inputs.

**Stage 8 — research disposition:** reject, inconclusive, retain experimental, adopt as challenger, or request promotion review.

## Comparison discipline

All compared experiments must share target, split, data snapshot, metric-registry version, lane, and relevant BAS/A&M semantics. Metric differences from incomparable experiments cannot be sorted into one ranking table.

One favorable metric cannot erase calibration, stability, data-quality, or coherence failures. Feature families may be target-specific; a family can remain useful for margin while being rejected for win probability.

## No direct lifecycle promotion

The tournament can never output `CORE`, `SUPPORTED`, or production `PROMOTE`. A research disposition of `PROMOTION_REVIEW_REQUIRED` only packages evidence for the W10 lifecycle/W17 promotion governance.

## Negative evidence

Rejected, dominated, unstable, coverage-limited, or rights-blocked families remain in the searchable experiment history. The system should be able to explain why a previously tested family is not being rerun.

## W19/W20 handoff

Wave 19 materializes real feature matrices and coverage evidence; Wave 20 provides functional trained baseline/challenger models. The tournament engine then gains real empirical payloads without changing the W18 admission/comparison rules.
