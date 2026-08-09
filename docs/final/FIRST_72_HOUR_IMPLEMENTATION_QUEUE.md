# First 72-Hour Codex Implementation Queue

These are sequencing windows for the first implementation push, **not task-duration guarantees**.

## 0-24 hour focus — prove environment and acquire truth
- Verify the final W25 pair and repository manifest before mutation.
- Run full tests and `tools/validate_w25_final.py`.
- On the declared target Windows machine, run `scripts/benchmark_target.ps1`; preserve the JSON evidence.
- Configure `AGGIE_ANALYTICS_DATA_ROOT` and credentials locally; never commit secrets.
- Confirm current CFBD/API access and the approved source-rights lane.
- Materialize a narrow end-to-end historical slice (multiple teams/seasons, including Texas A&M) into immutable raw snapshots.
- Run source-contract/schema/entity/PIT validators on that slice.

## 24-48 hour focus — construct real replay inputs
- Expand materialization for schedule/game/PBP/team/roster sources needed by the first baseline matrix.
- Produce population missingness/schema reports for materialized datasets.
- Resolve canonical team/game/player IDs and quarantine unresolved collisions.
- Build strictly pregame PIT states/features for a bounded chronological replay period.
- Run W24 leakage battery against the materialized slice; stop on any leakage finding.

## 48-72 hour focus — establish the first empirical baseline loop
- Train Elo/logistic/simple score baselines on development chronology only.
- Persist model/data/feature lineage and replay artifacts.
- Run development/walk-forward metrics; do not inspect protected periods outside W17 protocol.
- Exercise calibration only on allowed development evidence.
- Generate a first immutable forecast snapshot through W21 publication and read it through W22 API/service surfaces.
- Record failures/gaps in the experiment/research queue; do not promote on development-only evidence.

## Exit from the first 72-hour queue
The next implementation block should be chosen from evidence generated above. If source contracts, PIT tests, entity quality or target-hardware limits fail, repair those before scaling data or model complexity.
