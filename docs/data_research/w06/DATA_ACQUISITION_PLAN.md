# Wave 06 Data Acquisition Plan

## Acquisition tiers

1. **Immutable official/primary evidence** — NCAA, conferences, schools, NOAA, federal datasets. Snapshot payload/document, retrieval time, publication/effective time when known, URL, hash and terms metadata.
2. **Practical structured national foundation** — SportsDataverse/cfbfastR and CollegeFootballData. Version releases/API schemas, preserve raw responses, record upstream provenance and source IDs.
3. **Derived canonical layer** — normalize only after contract validation and entity mapping; never overwrite historical observations.
4. **Optional licensed enrichment** — timestamped odds, aggregated injuries, commercial advanced charting/live. Isolate behind adapters; raw restricted data stays local and is never committed/redistributed unless license permits.

## Highest-priority W07–W09 materialization

- SportsDataverse core datasets and CFBD endpoint samples/contracts.
- NCAA/team/conference identity mappings and official reconciliation.
- SEC/A&M availability archive first, followed by other official conference report families.
- NOAA/Open-Meteo issued-forecast run examples with model initialization + lead time.
- EADA/Knight/IPEDS resource datasets.
- NCAA/NAIA/NJCAA lower-division statistics needed for bounded strength priors.
- Effective-dated NCAA playing/regulatory rule records.

## Refresh semantics

- Raw snapshots are immutable.
- Mutable pages/APIs generate new observations rather than replacing history.
- Forecast weather stores model/provider/run/lead/valid time.
- Availability stores every retrieved/publication version.
- Markets store provider/book/market/observed time; never collapse open/current/close into one value.
- Rules store adoption/publication/effective dates and supersession.

## Failure behavior

A missing optional source does not block the pure-football system. Missing critical canonical/PIT evidence triggers quarantine, degraded-mode labeling or forecast suppression according to later source contracts.
