# W18 Implementation & Validation Inventory

This document ensures W18 is more than a thin prose contract.

## Reference modules
- experiment identity/contracts;
- hash-chained queue;
- judging-rule verification;
- hypothesis lifecycle;
- artifact manifests;
- replay checking;
- feature/model tournament specification and deterministic development ranking;
- HPO study/search-space validation;
- worktree/resource plan validation;
- adoption recommendation;
- advanced challenger admission.

## CLI/reference tools
- `tools/validate_experimentation.py`
- `tools/create_experiment.py`
- `tools/run_tournament_reference.py`
- `tools/verify_experiment_replay.py`
- `tools/verify_judging_seal.py`
- `tools/create_research_packet.py`

## Explicit non-implementation
W18 does not train production models, require MLflow/Optuna at runtime, run protected HPO, inspect protected metrics for tuning, run expensive advanced challengers, promote a champion, or materialize the W19 data lake.

## Required tests
Tests cover deterministic IDs, role separation, protected HPO denial, feature/model tournament rules, replay mismatch detection, negative-result retention, artifact determinism, protected-path denial, paid-compute authorization, and W17 seal integrity.
