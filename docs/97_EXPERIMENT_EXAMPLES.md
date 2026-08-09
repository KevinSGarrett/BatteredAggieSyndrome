# Worked Experiment and Tournament Examples

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Feature-family example

Hypothesis: opponent-adjusted OL continuity adds stable margin value beyond the frozen baseline. The experiment binds one PIT-safe feature-family version, target `margin`, development split, baseline feature set, model baseline, and metric registry. The feature tournament runs plus-family, optional minus-family, stability and replay stages. If development evidence is unstable across seasons, disposition is RETAIN_EXPERIMENTAL or REJECT—not SUPPORTED.

## A&M specialization example

A residual A&M adapter enters a model tournament with `TAMU-SP-00` no-adjustment baseline. Both use the same national model/data/feature snapshot and development split. If the adapter improves one A&M slice but worsens other development slices or is unstable across regimes, it does not automatically advance.

## HPO example

A boosted-tree challenger has a versioned depth/learning-rate/subsample search space. Optuna or the reference enumerator runs only on development evidence. Trial failures and pruned trials stay in history. Expanding bounds after seeing results creates a new search-space version.

## Replay example

An experiment is adopted as challenger only after a fresh worktree resolves identical data/feature/model hashes and reproduces development outputs within the predeclared tolerance. A changed package environment produces ENVIRONMENT_MISMATCH rather than silently accepting approximate output.

## Negative example

A graph model cannot run merely because player/coach relationships form a graph. Until conventional baselines exist, graph inputs are materialized, and a specific incremental hypothesis is approved, admission remains BLOCKED.
