# HPO Pruning, Early Stopping, and Search Termination

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Purpose

Search termination is part of experiment governance because unconstrained optimization can burn compute, leak protected evidence, and manufacture overfitting through repeated search.

## Permitted stop conditions

Permitted conditions include fixed trial budget, development-only objective convergence, no-improvement patience on development evidence, resource budget exhaustion, repeated infrastructure failure, governance seal failure, materialized-data failure, and explicit user cancellation.

## Prohibited stop signals

Protected 2024–2025 performance, 2026+ forward-shadow outcomes, champion/promotion results, and manual inspection of protected subgroups cannot stop or redirect HPO.

## Nested optimization

When feature selection and model HPO interact, the outer search dimension must be explicit. The system may not report only the best inner-loop result while hiding the number of searched outer variants. Search multiplicity and parent/child study relationships are retained.

## Reproducibility

The study records sampler/pruner seed/config, trial order policy, concurrency, storage backend, objective definition hash, and code/environment version. Parallel scheduling may change trial order; if this makes the tuner nondeterministic, that fact is declared rather than hidden.
