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

## Local artifact identity and legacy compatibility
New publications carry `publication_format=aggie.forecast.publication.v1`. Their filename is `{snapshot_id}-{stable_hash(payload)}.json`, including `published_at` in the hashed document. Serving binds the requested game, directory, stored game, snapshot ID and complete content identity. A genuine repeated publication returns the existing verified artifact and retains its original publication time; changing a serving value or time under the existing identity is refused.

Publication takes an exclusive per-game/snapshot filesystem claim and rechecks existing artifacts under that claim. A concurrent owner receives an in-progress refusal instead of creating another timestamp identity. The owner releases its claim on normal completion or handled failure. A process crash can leave the claim behind; the publisher never waits, polls, or breaks it as stale. Recovery requires explicit ownership review. An already published, verified artifact remains readable and an identical repeat remains idempotent.

Original W21/W22 publications excluded `published_at` from the filename hash. Those original hash names and legacy `{snapshot_id}-{market_lane}.json` names are readable only with explicit `legacy_artifact_sha256` configuration on `PublishedSnapshotRepository` or `create_app`: a map of root-relative POSIX filenames to separately retained SHA-256 hashes of the complete file bytes. The server does not generate these pins from files being admitted. Unknown formats and renamed/edited artifacts do not fall back to unverified serving. No retained publication is rewritten by this compatibility path.

These checks establish local content consistency with the selected identity or pin. They are not service timestamps, official kickoff evidence, historical point-in-time admission, model acceptance or proof of predictive skill.
