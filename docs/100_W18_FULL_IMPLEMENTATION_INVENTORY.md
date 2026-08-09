# Wave 18 Full Implementation Inventory

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Architecture

Canonical identity; lineage; local metadata store; append-only queue; resource scheduler; tracking adapters; HPO; feature tournament; model tournament; replay; artifact manifest; worktree locks; result comparison; negative evidence; promotion bridge; advanced challenger admission.

## Governance

Requirements/ADRs/risks/acceptance controls; master coverage; task→test matrix; requirement→artifact matrix; state-machine catalog; resource policy; artifact classes; HPO search policy; tournament matrices; protected-path policy; replay checks; failure taxonomy; tool decision matrix; W17 rule seal.

## Reference tooling

CLI commands initialize local store, create/freeze experiments, enqueue/advance work, run deterministic reference HPO/tournaments, build/validate artifact manifests, compare result packets, verify replay, verify judging seal, inspect local store and validate the full Wave-18 contract.

## Tests

Unit/integration tests cover lineage stability, store transactions, queue hash chains, permission denial, resource admission, HPO split rejection, search-space versioning, feature/model tournament baseline requirements, A&M no-adjustment baseline, BAS version consistency, result compatibility, replay mismatch, artifact policy, worktree locks, promotion-bridge denial and advanced-challenger blocking.

## Maturity

The result is still a **reference implementation and governance layer**, not a trained production research platform. Real source materialization begins W19; functional trained baseline/challenger models begin W20; weekly operational orchestration begins W21.
