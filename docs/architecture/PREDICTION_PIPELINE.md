# Pregame Prediction Pipeline

## Forecast-refresh lane

1. Acquire any newly available evidence.
2. Validate; quarantine failures.
3. Update canonical/effective-dated observations.
4. Build a PIT snapshot at the requested prediction timestamp.
5. Build deterministic feature inputs from that snapshot.
6. Load approved national model/calibration artifacts.
7. Produce national team/opponent/score/margin/win representations.
8. Add higher-resolution Texas A&M state.
9. Apply the accepted A&M specialization interface.
10. Assemble a coherent joint outcome distribution.
11. Compute BAS probabilities from valid expected-margin/forecast outputs.
12. Run uncertainty/OOD checks.
13. Persist an immutable forecast snapshot with lineage.
14. Publish/read that snapshot through serving surfaces.

## Pure and market lanes

The same prediction timestamp may produce:
- `PURE_FOOTBALL`
- `MARKET_AUGMENTED`

The market lane may only use line observations known by the snapshot cutoff. It must never overwrite or replace the pure-football result.

## Serving behavior

The API/dashboard should normally answer:

`give me the latest eligible immutable forecast snapshot`

rather than:

`run ingestion + feature engineering + model inference synchronously for this HTTP request`.

This keeps the product reproducible, cheap and robust on local hardware.

## Forecast snapshot minimum lineage

A later schema wave should represent at least:
- canonical game ID;
- prediction timestamp;
- data snapshot ID;
- feature-set/version;
- model artifact IDs;
- calibration version;
- market lane;
- latest eligible weather/availability/market evidence IDs;
- national/A&M specialization versions;
- BAS version;
- code/repository version;
- output distribution reference;
- uncertainty/OOD warnings.

Exact field schemas remain later-wave work.
