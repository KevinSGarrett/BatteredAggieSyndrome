# Forecast Product API Contract — W22

## Boundary
The serving layer is **read only**. It reads immutable JSON forecast artifacts published by the W21 publisher. It must not import or invoke raw ingestion, PIT-state builders, feature construction, training, protected evaluation, calibration fitting, champion selection, or model inference from an HTTP/dashboard request path.

## API v1
- `GET /health`
- `GET /api/v1/games`
- `GET /api/v1/games/{game_id}/snapshots`
- `GET /api/v1/games/{game_id}/forecast`
- `GET /api/v1/games/{game_id}/snapshots/{snapshot_id}/lineage`

The forecast endpoint defaults to `PURE_FOOTBALL`. `MARKET_AUGMENTED` is an explicit separate lane and cannot overwrite or obscure the pure-football view.

## Required user-facing payload
A served forecast exposes:
- forecast snapshot identity and cutoff;
- published time and freshness classification;
- win/loss probability, projected score and expected margin when present in the published summary;
- BAS severity probabilities when present;
- precomputed uncertainty evidence;
- material warnings;
- precomputed player-availability context;
- precomputed matchup drivers and historical analogs;
- national/A&M comparison context when published;
- model artifact hash;
- feature snapshot identity;
- data/source lineage references.

Explanations are explicitly **precomputed associative/model evidence, not causal claims**.

## Freshness
`THR-010` remains `TBD_BY_OPERATIONS`; W22 does not invent a production SLA. Without a configured threshold the product exposes exact times/age and labels freshness `UNASSESSED_THRESHOLD_TBD`, never `CURRENT`. When an operations-configured threshold is supplied, stale snapshots are labeled `STALE` and a user warning is added.
