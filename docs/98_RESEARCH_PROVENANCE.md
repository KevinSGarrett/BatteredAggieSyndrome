# Research Provenance, Search Multiplicity, and Negative-Evidence Ledger

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Search provenance

Every automated search records parent hypothesis, experiment/study IDs, search-space version, count of attempted/pruned/failed/completed candidates, stopping reason, and resource usage. The system must be able to answer how many alternatives were tried before the reported candidate appeared.

## Multiplicity

Feature tournaments, interaction searches, model-family comparisons, and HPO can create selection bias even when each individual metric is computed correctly. W18 therefore retains search multiplicity for later W17 interpretation rather than presenting a single best result as if it were predeclared.

## Negative evidence

Negative-result records include enough identity to avoid accidental reruns: hypothesis, data/feature/model version, reason, replay status, and what changed would justify reconsideration.

## Supersession

A bug-fixed child does not erase the old invalid result. Results can be marked superseded/invalidated with reason and replacement IDs. Historical evidence remains discoverable.

## Auditability

The complete lineage from hypothesis → experiments/studies → attempts → artifacts/results → replay → research disposition → promotion-review packet is traversable without relying on an external tracking UI.
