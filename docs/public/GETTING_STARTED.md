# Installation and technical usage

The usable interface today is a local, read-only API/dashboard over compatible forecast snapshots, alongside Python research modules. Starting it does not train a national model, download a data lake, or generate a validated BAS score.

## Install

Use Git and Python 3.11–3.13.

```bash
git clone https://github.com/KevinSGarrett/BatteredAggieSyndrome.git
cd BatteredAggieSyndrome
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install the API extra:

```bash
python -m pip install -e ".[product]"
```

For core modules without the web interface, install the package without extras. Optional data/model extras are listed in [technology](TECHNOLOGY.md).

## Run the snapshot API and dashboard

```bash
python tools/run_product.py --help
python tools/run_product.py --snapshot-root /absolute/path/to/published-snapshots
```

Windows example, replacing the path with your own snapshot directory:

```powershell
python tools/run_product.py --snapshot-root "D:\FootballData\published"
```

The default host is 127.0.0.1 and the default port is 8000. An absent or empty root produces an empty store, not an automatic download or a forecast. Do not expose the development server publicly.

Visit the local dashboard at http://127.0.0.1:8000/ and interactive documentation at http://127.0.0.1:8000/api/docs.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/games
```

Use a game ID returned by the game list:

```text
GET /api/v1/games/{game_id}/snapshots
GET /api/v1/games/{game_id}/forecast
GET /api/v1/games/{game_id}/snapshots/{snapshot_id}/lineage
```

The forecast endpoint accepts:

- snapshot_id: an existing immutable snapshot identity;
- market_lane: defaults to PURE_FOOTBALL;
- as_of: an ISO 8601 timestamp with timezone, used when selecting the latest eligible published snapshot.

A stored market-augmented lane is separate from an independent no-market model. Snapshot serving does not check every research gate or certify a forecast's scientific validity. Keep experimental or untrusted outputs local and clearly labeled.

## Snapshot layout and input contract

```text
published-snapshots/
  canonical-game-id/
    snapshot-file.json
```

The reader inventories game subdirectories and JSON files; it does not consume arbitrary model gate files or JSONL feature tables. Accepted snapshot contracts are declared in [product/contracts.py](../../src/aggie_analytics/product/contracts.py).

| Required field | Meaning |
|---|---|
| snapshot_id, game_id | Snapshot and game identities |
| forecast_cutoff, published_at | Timezone-aware timestamps; publication cannot precede the cutoff |
| model_artifact_sha256 | Bound model identity |
| feature_snapshot_id | Bound feature snapshot |
| public_summary | Numeric result fields |
| lineage_refs | Nonempty list of evidence references |

The extended contract supports team labels, market lane, uncertainty, warnings, availability, explanations, model metadata, and data references. Schema acceptance alone does not prove that hashes were independently verified or that probabilities, scores, and intervals are coherent.

Do not fabricate a model identity or move an unreviewed forecast into a published store just to populate the dashboard. No production-ready real-game snapshot bundle is distributed with this guide.

## Research modules and tests

For source, feature, and modeling work, follow the [architecture](../../ARCHITECTURE.md) and [data-domain guide](DATA_DOMAINS.md). Acquisition commands are source-specific; credentials, provider quotas, and legal access must be configured separately. There is no documented one-command end-to-end validated BAS training workflow yet.

```bash
python -B -m unittest discover -s tests -p "test_independent_scientific_reference.py"
python -B -m unittest discover -s tests -p "test_w22_product_serving.py"
```

These exercise numerical references and synthetic serving cases, not predictive accuracy. Full discovery has additional local-data and operational dependencies; inspect failures and skips rather than assuming an unset data-root environment makes every test portable.

See [reproducibility](../../REPRODUCIBILITY.md) and [research status](STATUS.md).
